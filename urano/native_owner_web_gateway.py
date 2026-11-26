"""Authenticated Owner -> private Chema New/Latest gateway, no project picker.

Owner verifies Google session + rotating CSRF + stable workspace ID.
The root broker independently verifies those same credentials, generation,
project ownership and the DynamicUser/cgroup before granting a worker FD.
The worker then validates native project and media paths against its own
per-owner data_root. No shared Engine or public native JM endpoints.

Only a small, explicitly reviewed set of original Chema JSON routes is
forwarded here. Uploads, previews, native exports, Music/Push/Show APIs and
large media are NOT enabled by this first H3 gate.
"""
from __future__ import annotations

import io
import os
import json
import re
import math
import time
from contextlib import closing
from http.client import HTTPException

from flask import Blueprint, Response, current_app, g, jsonify, request

from urano.native_owner_new_latest_http import native_new_latest_target
from urano.native_owner_stage_http import native_stage_route
from urano.native_owner_full_session_http import full_session_target
from urano.native_owner_mix_http import native_mix_target
from urano.first_valid_upload_gate import valid_first_upload
from urano.jm_private_proxy_overlay import private_proxy_limit_mib
from urano.native_owner_workspace_registry import (
    NativeOwnerWorkspaceRegistry, ExistingOwnerProjects,
)
from urano.owner_broker_preview import broker_request
from urano.owner_private_http_client import authenticated_private_jm_connection
from urano.session_auth import SESSION_COOKIE, SessionStore

_GEN = re.compile(r"[1-9][0-9]{0,9}\Z")
_MAX_BODY = 256_000
_MAX_REPLY = 1_000_000
_MAX_SESSION_JSON = 8 * 1024 * 1024
_MAX_PREVIEW = 128 * 1024 * 1024
_MAX_DIRECT_MEDIA = 256_000_000
_MAX_CHUNK = 16 * 1024 * 1024

def native_owner_gateway_blueprint(
        sessions: SessionStore, registry: NativeOwnerWorkspaceRegistry,
        *, https_origin: str, ensure_worker=broker_request,
        connect_worker=authenticated_private_jm_connection,
        private_preview_limit_mib: int = 256,
) -> Blueprint:
    proxy_cap=private_proxy_limit_mib(private_preview_limit_mib)*1024**2
    bp = Blueprint("urano_native_chema_owner_gateway", __name__,
                   url_prefix="/urano/v1/native")

    @bp.after_request
    def stage_response_trace(response):
        # One sanitized diagnostic marker: a remote 503/409 received intact
        # from the worker is distinct from the Owner gateway's own 503/409.
        # A Cloudflare-generated response has neither marker nor Timing.
        if (request.endpoint in {
                "urano_native_chema_owner_gateway.native_rpc",
                "urano_native_chema_owner_gateway.ensure"}):
            if response.status_code in (409,503):
                response.headers.setdefault(
                    "X-Montara-Stage-Origin","owner-gateway")
            started=getattr(g,"_montara_stage_start",None)
            if started is not None:
                elapsed=max(0.0,(time.monotonic()-started)*1000)
                # Do not emit original path, owner, project, token or file.
                timings=[f"owner;dur={elapsed:.1f}"]
                started_connect=getattr(g,"_montara_stage_connect",None)
                connected=getattr(g,"_montara_stage_connected",None)
                worker_done=getattr(g,"_montara_stage_worker_done",None)
                if started_connect is not None and connected is not None:
                    timings.append(
                        f"broker;dur={max(0,(connected-started_connect)*1000):.1f}")
                if connected is not None and worker_done is not None:
                    timings.append(
                        f"engine;dur={max(0,(worker_done-connected)*1000):.1f}")
                response.headers["Server-Timing"]=", ".join(timings)
        return response

    def verified():
        if request.host_url.rstrip("/") != https_origin:
            return None, None, (jsonify(error="Trusted HTTPS origin required"),403)
        origin = request.headers.get("Origin")
        if (request.method not in ("GET","HEAD") and origin != https_origin or
                request.method in ("GET","HEAD") and origin not in (None,https_origin)):
            return None, None, (jsonify(error="Trusted HTTPS origin required"),403)
        token = request.cookies.get(SESSION_COOKIE)
        session = sessions.verify(token)
        if session is None:
            return None,None,(jsonify(error="Authentication required"),401)
        csrf = request.headers.get("X-Urano-CSRF")
        if not session.matches_csrf(csrf):
            return None,None,(jsonify(error="Invalid private session"),403)
        return token,csrf,None

    def owned_workspace(token):
        session = sessions.verify(token)
        if session is None:
            return None
        return registry.get(session.owner_id)

    @bp.post("/ensure")
    def ensure():
        token,csrf,error = verified()
        if error is not None:
            return error
        if request.content_length not in (None,0) or request.headers.get("Transfer-Encoding"):
            return jsonify(error="Body unsupported"),400
        session = sessions.verify(token)
        try:
            workspace = registry.get(session.owner_id)
            if workspace is None:
                # Only new Owners can be enrolled automatically. Existing beta
                # projects must be reconciled by the operator, never silently
                # chosen or modified by browser login.
                workspace = registry.reserve_new(session.owner_id)
        except ExistingOwnerProjects:
            return jsonify(error=(
                "Existing private projects require a safe one-time migration; "
                "nothing has been changed")),409
        try:
            result = ensure_worker("ensure_owner",token,csrf,workspace.workspace_id)
        except (OSError,ValueError,RuntimeError,TimeoutError) as exc:
            # This used to return an unqualified 503 for every socket/JSON/
            # broker failure, making unrelated incidents look identical.
            # Log ONLY the exception class and numeric OS errno: never the
            # exception message, URI, project, session cookie, CSRF or owner.
            errno = getattr(exc,"errno",None)
            current_app.logger.warning(
                "private_owner_ensure_failed exception=%s errno=%s",
                type(exc).__name__,errno if type(errno) is int else "none")
            return jsonify(error="Private Engine unavailable"),503
        if (not isinstance(result,dict) or result.get("ok") is not True or
                result.get("project_id") != workspace.workspace_id or
                result.get("state") != "ready" or
                type(result.get("generation")) is not int or
                not 1 <= result["generation"] < 2**31):
            return jsonify(error="Private Engine not ready"),503
        response = jsonify(state="ready",generation=result["generation"])
        response.headers["Cache-Control"] = "no-store"
        return response

    @bp.route("/rpc/<path:operation>",
              methods=["GET","POST","PUT","DELETE","PATCH"])
    def native_rpc(operation: str):
        g._montara_stage_start=time.monotonic()
        path = "/" + operation
        if not request.query_string.isascii():
            return jsonify(error="Unsupported original editor query"),404
        query=request.query_string.decode("ascii")
        # Companion version is the actual root-protected LAB-JM Engine pin, not
        # the installed Mac version and not a fabricated installer. This metadata
        # remains Owner/CSRF-protected even though it needs no worker RPC.
        if path == "/montara/companion/version" and request.method == "GET" and not query:
            token,csrf,error=verified()
            if error is not None:
                return error
            if owned_workspace(token) is None:
                return jsonify(error="Private workspace unavailable"),409
            pin=os.environ.get("MONTARA_JM_ENGINE_PIN","")
            if not re.fullmatch(r"[a-f0-9]{40}",pin):
                return jsonify(error="Owner Engine pin unavailable"),503
            # MAIN does not publish LAB-JM packages or unsigned installers.
            # Keep metadata tied to the operator-pinned Engine only.
            response=jsonify(
                engine=pin,installer_available=False,download=None)
            response.headers["Cache-Control"]="private, no-store"
            return response
        # H4 Cloudflare accepts POST but rejects PATCH and can strip custom
        # transport headers. Use one dedicated, non-generic save alias; only
        # the verified Owner gateway restores the original Engine PATCH.
        shot_tunnel=(request.method=="POST" and
                     path=="/api/v1/edit/shot/save" and not query)
        timeline_tunnel=(request.method=="POST" and
                         path=="/api/v1/edit/timeline/save" and not query)
        upstream_method="PATCH" if shot_tunnel or timeline_tunnel else request.method
        upstream_path=("/api/v1/edit/shot" if shot_tunnel else
                       "/api/v1/edit/timeline" if timeline_tunnel else path)
        target = native_new_latest_target(upstream_method,upstream_path,query)
        extra = None if target is not None else (
            native_stage_route(upstream_method,upstream_path,query) or
            full_session_target(upstream_method,upstream_path,query) or
            native_mix_target(upstream_method,upstream_path,query))
        if target is None and extra is None:
            return jsonify(error="Original editor operation not enabled"),404
        if extra is not None:
            target=extra.upstream
        kind="json" if extra is None else extra.kind
        token,csrf,error = verified()
        if error is not None:
            return error
        workspace = owned_workspace(token)
        if workspace is None:
            return jsonify(error="Private workspace unavailable"),409
        generation = request.headers.get("X-Montara-Engine-Generation","")
        if not _GEN.fullmatch(generation) or int(generation)>=2**31:
            return jsonify(error="Private Engine generation required"),409
        if request.headers.get("Transfer-Encoding"):
            return jsonify(error="Unsupported request framing"),400
        length = request.content_length
        if request.method in ("GET","HEAD","DELETE"):
            if length not in (None,0):
                return jsonify(error="Body unsupported"),400
            body=None
        elif kind=="logo-upload":
            limit=10*1024*1024
            if (type(length) is not int or not 0 < length <= limit
                    or request.mimetype != "multipart/form-data"
                    or not request.mimetype_params.get("boundary")):
                return jsonify(error="A PNG, JPEG or WebP logo up to 10 MiB is required"),400
            request.max_content_length=limit
            body=request.stream
        elif kind=="upload-direct":
            if (type(length) is not int or not 0 < length <= _MAX_DIRECT_MEDIA
                    or request.mimetype!="application/octet-stream"):
                return jsonify(error="Invalid media transfer"),400
            meta={
                "PATH_INFO":"/api/v1/wizard/upload","REQUEST_METHOD":"POST",
                "CONTENT_LENGTH":str(length),
                "CONTENT_TYPE":request.content_type,
                "HTTP_X_ZUCKER_FILENAME":request.headers.get("X-Zucker-Filename",""),
            }
            if not valid_first_upload(meta):
                return jsonify(error="Invalid private media metadata"),400
            # Owner app defaults to a 300 KB control-plane cap; only reviewed
            # upload routes may widen Flask's per-request streaming limit.
            request.max_content_length=_MAX_DIRECT_MEDIA
            body=request.stream
        elif kind=="upload-chunk":
            offset=request.headers.get("Upload-Offset","")
            if (type(length) is not int or not 0 < length <= _MAX_CHUNK
                    or request.mimetype!="application/octet-stream"
                    or not offset.isascii() or not offset.isdecimal()
                    or len(offset)>16):
                return jsonify(error="Invalid private media chunk"),400
            request.max_content_length=_MAX_CHUNK
            body=request.stream
        else:
            limit=8192 if kind=="upload-init" else _MAX_BODY
            if (type(length) is not int or length < 2 or
                    length > limit or request.mimetype != "application/json"):
                return jsonify(error="Expected bounded JSON body"),400
            body=request.get_data(cache=False)
            if len(body) != length:
                return jsonify(error="Incomplete native request"),400
            try:
                value=json.loads(body)
            except (ValueError,TypeError):
                return jsonify(error="Invalid native JSON"),400
            if not isinstance(value,dict):
                return jsonify(error="Invalid native JSON object"),400
            if kind=="timeline-patch":
                if (set(value)!={"kind","project_id","revision","index","at"} or
                        value.get("kind")!="music" or
                        not isinstance(value.get("project_id"),str) or
                        not 1<=len(value["project_id"])<=1800 or
                        not value["project_id"].startswith("/") or
                        not re.fullmatch(r"[a-f0-9]{20}",str(value.get("revision",""))) or
                        type(value.get("index")) is not int or
                        not 1<=value["index"]<=9999 or
                        type(value.get("at")) not in (int,float) or
                        not math.isfinite(value["at"]) or
                        not 0<=value["at"]<=86400):
                    return jsonify(error="Invalid private music cut edit"),400
            if kind=="shot-patch":
                keys=set(value)
                allowed={"project_id","revision","index","choice",
                         "edit_component","apply_to_source","movement",
                         "playback_speed","flat_framing","yaw","pitch","fov",
                         "performer_roles","remember_musician"}
                if (keys-allowed or
                        not isinstance(value.get("project_id"),str) or
                        not re.fullmatch(r"[a-f0-9]{20}",
                                         str(value.get("revision",""))) or
                        type(value.get("index")) is not int or
                        not 0<=value["index"]<=9999 or
                        type(value.get("choice")) is not int or
                        not 0<=value["choice"]<=99 or
                        value.get("apply_to_source") is not False or
                        value.get("edit_component") not in
                        ("framing","movement")):
                    return jsonify(error="Invalid private shot edit"),400
            if kind=="branding":
                if set(value) != {"mode"} or value["mode"] not in ("montara","mine","none") or type(value["mode"]) is not str:
                    return jsonify(error="Unsupported branding mode"),400
            if kind=="upload-init":
                validation={
                    "PATH_INFO":"/montara/uploads","REQUEST_METHOD":"POST",
                    "CONTENT_LENGTH":str(length),
                    "CONTENT_TYPE":request.content_type,
                    "wsgi.input":io.BytesIO(body),
                }
                if not valid_first_upload(validation,max_proxy_bytes=proxy_cap):
                    return jsonify(error="Private proxy metadata rejected"),400
        # Chema's original GET /montara/uploads reports the real private
        # disk quota and negotiated chunk size. Never fabricate that reply.
        try:
            g._montara_stage_connect=time.monotonic()
            with closing(connect_worker(token,csrf,workspace.workspace_id,
                                         int(generation))) as conn:
                g._montara_stage_connected=time.monotonic()
                # Broker authorization retains its short timeout. Only after
                # obtaining the owner-checked FD may a bounded media operation
                # wait for slow upload chunks / local fsync / preview restore.
                # Never widen timeouts for ordinary JSON control-plane RPCs.
                if kind in ("upload-chunk", "upload-finish", "upload-direct", "shot-frame", "native-source", "native-master", "mix-media"):
                    conn.timeout = 95.0 if kind == "upload-finish" and upstream_method == "POST" else 35.0
                    if conn.sock is not None:
                        conn.sock.settimeout(35.0)
                headers={"Cache-Control":"no-store"}
                if body is not None:
                    headers["Content-Type"]=request.content_type
                    headers["Content-Length"]=str(length)
                if kind=="upload-direct":
                    headers["X-Zucker-Filename"]=request.headers["X-Zucker-Filename"]
                if kind=="upload-chunk":
                    headers["Upload-Offset"]=request.headers["Upload-Offset"]
                if kind=="audio-media" and request.headers.get("Range"):
                    return jsonify(error="Audio range unsupported in private beta"),416
                # A 45s reviewed Mixer audition may take >6s to prepare from
                # 15 stems. The original Owner client defaults to 6s, falsely
                # returning 503 even if the worker later responds 200. Extend
                # ONLY a bounded, owner-checked listen request, never all RPCs.
                if (kind == "session-media" and upstream_method == "GET" and
                        re.fullmatch(r"/montara/session/[a-f0-9]{12}/listen", upstream_path.split("?", 1)[0])):
                    conn.timeout = 75.0
                    if conn.sock is not None:
                        conn.sock.settimeout(75.0)
                # Saved full-song MP3s can exceed the reliable single-response
                # payload of the HTTPS tunnel. Permit only authenticated,
                # tightly bounded byte ranges for this exact Owner song route.
                if (kind == "session-media" and upstream_method == "GET" and
                        (re.fullmatch(r"/montara/session/[a-f0-9]{12}/mix-preview/result/[1-9][0-9]{0,3}", upstream_path) or
                         (query == "download=1" and
                          re.fullmatch(r"/montara/session/[a-f0-9]{12}/result/[1-9][0-9]{0,3}", upstream_path)))):
                    ranged = request.headers.get("Range", "")
                    match = re.fullmatch(r"bytes=([0-9]{1,12})-([0-9]{1,12})", ranged)
                    if (match is None or int(match[2]) < int(match[1]) or
                            int(match[2]) - int(match[1]) >= 2 * 1024 * 1024):
                        return jsonify(error="A bounded audio byte range is required"),416
                    headers["Range"] = ranged
                    conn.timeout = 35.0
                    if conn.sock is not None:
                        conn.sock.settimeout(35.0)
                # Stage GET review?render=1 may generate shot previews before
                # returning JSON. Worker logs show 14.28s HTTP 200 while the
                # default 6s owner socket turned the same call into HTTP 503.
                # Extend ONLY this reviewed, owner-scoped route (render=0/1
                # optionally shot index). Do not change authorization or other
                # control-plane timeouts. Auth + worker generation checks have
                # already completed above.
                if (upstream_method == "GET" and
                        upstream_path.split("?",1)[0] == "/api/v1/wizard/review" and
                        re.fullmatch(r"render=[01](?:&shot=[0-9]{1,5})?", query)):
                    conn.timeout = 75.0
                    if conn.sock is not None:
                        conn.sock.settimeout(75.0)
                # On-demand hover previews are FFmpeg operations; the worker
                # recorded successful HTTP 200 responses after 19–34 s, but
                # the Owner default 6 s returned HTTP 503 first. Only allow
                # the strictly reviewed single-shot video preview endpoint
                # an extended socket read, AFTER authenticated worker lookup.
                if (kind=="review-media" and upstream_method=="GET" and
                        re.fullmatch(r"/api/v1/wizard/review/preview/[0-9]{1,5}",
                                     upstream_path.split("?",1)[0])):
                    conn.timeout=75.0
                    if conn.sock is not None:
                        conn.sock.settimeout(75.0)
                # Review actions are real Engine jobs, not static JSON. With
                # ~305 shots the Engine recorded GET edit/shot 9.8 s,
                # POST review/replace 89.6 s, and GET review 77.3 s, all 200.
                # The owner bridge's default 6 s and prior review 75 s cut
                # these off prematurely. Only exact authenticated routes and
                # narrowly validated query shapes get this longer read window.
                if ((upstream_method=="GET" and upstream_path=="/api/v1/edit/shot" and
                     re.fullmatch(r"index=[0-9]{1,4}",query)) or
                    (upstream_method=="GET" and upstream_path=="/api/v1/edit/timeline" and query=="kind=music") or
                    (upstream_method=="GET" and upstream_path=="/api/v1/edit/shot/frame" and
                     re.fullmatch(r"index=[0-9]{1,4}&choice=[0-9]{1,2}&revision=[a-f0-9]{20}",query)) or
                    (upstream_method=="POST" and upstream_path=="/api/v1/wizard/review/replace" and not query) or
                    (upstream_method=="PATCH" and upstream_path in ("/api/v1/edit/shot","/api/v1/edit/timeline") and not query) or
                    (upstream_method=="GET" and upstream_path=="/api/v1/wizard/review" and
                     re.fullmatch(r"render=[01](?:&shot=[0-9]{1,5})?",query))):
                    conn.timeout=95.0
                    if conn.sock is not None:
                        conn.sock.settimeout(95.0)
                if kind=="review-media" and request.headers.get("Range"):
                    ranged=request.headers["Range"]
                    if (len(ranged)>80 or
                            re.fullmatch(r"bytes=[0-9]{1,12}-[0-9]{0,12}",
                                         ranged) is None):
                        return jsonify(error="Unsupported private preview range"),416
                    headers["Range"]=ranged
                conn.request(upstream_method,target,body=body,headers=headers)
                upstream=conn.getresponse()
                read_limit=(_MAX_PREVIEW if kind in (
                    "review-media","audio-media","shot-frame","native-master",
                    "native-source","session-media","mix-media") else
                    _MAX_SESSION_JSON if kind=="session-json" else _MAX_REPLY)
                reply=upstream.read(read_limit+1)
                code=upstream.status
                # Diagnostic is an allowlisted category only: no email, tokens,
                # request paths, filenames, track names or raw response in logs.
                if upstream_path == "/montara/session" and upstream_method == "POST" and code == 400:
                    try:
                        rejected=(json.loads(reply).get("error") or {}).get("message")
                    except (ValueError,TypeError,AttributeError):
                        rejected=None
                    categories={
                        "Invalid video session mode.":"video_mode",
                        "Add between 1 and 128 audio tracks.":"track_count",
                        "Invalid audio track.":"track_type",
                        "Choose audio from your own session.":"unavailable_or_outside_owner_root",
                        "Use a different name for each audio track.":"duplicate_track",
                    }
                    # Unclassified failures are not printed or echoed.
                    import logging
                    logging.getLogger("montara.main").warning(
                        "MAIN_SESSION_400_CATEGORY %s",categories.get(rejected,"other"))
                content_type=upstream.getheader("Content-Type","application/json")
                content_range=upstream.getheader("Content-Range")
                accept_ranges=upstream.getheader("Accept-Ranges")
                g._montara_stage_worker_done=time.monotonic()
        except (OSError,ValueError,TimeoutError,RuntimeError,HTTPException):
            return jsonify(error="Private original editor unavailable"),503
        empty_chunk_response=(
            kind=="upload-chunk" and 200<=code<300 and not reply)
        empty_delete_response=(
            request.method=="DELETE" and 200<=code<300 and not reply)
        media_type=content_type.split(";",1)[0].lower().strip()
        binary_media=(
            kind in ("review-media","audio-media","shot-frame","native-master",
                     "native-source","session-media","mix-media") and 200<=code<300 and
            media_type in (("audio/webm","audio/ogg","audio/mpeg",
                            "application/zip","audio/wav","audio/x-wav",
                            "audio/wave") if kind in ("session-media","mix-media") else
                           ("image/jpeg",) if kind=="shot-frame" else
                           ("video/mp4","application/octet-stream") if kind=="native-source" else
                           ("audio/mpeg","audio/mp4","audio/wav","audio/x-wav",
                            "audio/wave","audio/aiff","audio/x-aiff",
                            "audio/flac","audio/ogg","audio/opus",
                            "application/octet-stream") if kind=="native-master" else
                           ("image/jpeg","image/png","image/webp",
                           "video/mp4","application/octet-stream") if kind=="review-media"
                           else ("audio/wav","audio/x-wav","audio/wave","audio/mpeg",
                                 "audio/mp4","audio/aiff","audio/x-aiff","audio/flac",
                                 "audio/ogg","audio/opus","application/octet-stream")))
        limit=(_MAX_PREVIEW if kind in ("review-media","audio-media",
                "shot-frame","native-master","native-source","session-media",
                "mix-media") else
               _MAX_SESSION_JSON if kind=="session-json" else _MAX_REPLY)
        if kind in ("session-media","mix-media") and len(reply)>limit:
            return jsonify(error="Session preview or download exceeds private media limit"),413
        if (len(reply)>limit or not 100<=code<=599 or
                (not content_type.lower().startswith("application/json")
                 and not empty_chunk_response and not empty_delete_response
                 and not binary_media) or
                any(c in content_type for c in "\r\n")):
            return jsonify(error="Unexpected native worker response"),503
        # H4 offers a smaller, still worker-valid proxy chunk to avoid
        # long single-request uploads across Cloudflare/Tunnel. The original
        # Chema worker accepts any chunk <= its advertised maximum. Keep the
        # authoritative received offset, identity and completion unchanged.
        # This applies equally to initial, resumed and limit responses.
        if 200<=code<300 and media_type=="application/json" and (
            kind in ("upload-init","upload-limits") or
            (request.method=="GET" and
             re.fullmatch(r"/montara/uploads/[a-f0-9]{32}",path))):
            try:
                payload=json.loads(reply)
                if not isinstance(payload,dict):
                    raise ValueError("Not an upload JSON object")
                field=("chunk_bytes" if kind=="upload-limits"
                       else "chunk_size")
                advertised=payload.get(field)
                if type(advertised) is not int or not 0<advertised<=16*1024**2:
                    raise ValueError("Unexpected chunk negotiation")
                payload[field]=min(advertised,4*1024**2)
                reply=json.dumps(payload,separators=(",",":")).encode()
            except (ValueError,TypeError):
                return jsonify(error="Invalid native upload negotiation"),503
        response=Response(reply,status=code,content_type=content_type)
        response.headers["Cache-Control"]="no-store"
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["X-Montara-Engine-Generation"]=generation
        # This flag is set ONLY after receiving a validated Engine HTTP
        # response. All locally generated errors remain owner-gateway.
        if code in (409,503):
            response.headers["X-Montara-Stage-Origin"]="engine"
        if binary_media and code==206 and content_range and re.fullmatch(
                r"bytes [0-9]+-[0-9]+/[0-9]+",content_range):
            response.headers["Content-Range"]=content_range
        if binary_media and accept_ranges=="bytes":
            response.headers["Accept-Ranges"]="bytes"
        return response

    return bp
