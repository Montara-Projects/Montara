"""Opt-in prototype with same-origin Owner control and native bearer endpoints."""
import base64
import binascii
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, send_from_directory

from urano.companion_jobs import JobConflict
from urano.project_catalog import ProjectNotFound
from urano.session_auth import SESSION_COOKIE


def companion_pairing_blueprint(sessions, pairing, *, origin, jobs=None, pilot_owner=None):
    routes = Blueprint("work_outbound_companion", __name__, url_prefix="/urano/v1/companion")

    @routes.before_request
    def enforce_origin():
        if request.host_url.rstrip("/") != origin:
            return jsonify(error="Unexpected host"), 403

    def owner():
        verified = sessions.verify(request.cookies.get(SESSION_COOKIE))
        if verified is not None and (pilot_owner is None or verified.owner_id == pilot_owner):
            return verified

    def authorized_write():
        verified = owner()
        if (verified and request.headers.get("Origin") == origin
                and verified.matches_csrf(request.headers.get("X-Urano-CSRF"))):
            return verified

    @routes.post("/invite")
    def invite():
        verified = authorized_write()
        if verified is None:
            return jsonify(error="Forbidden"), 403
        return jsonify(code=pairing.invite(verified.owner_id), expires_in=300), 201

    @routes.post("/redeem")
    def redeem():
        if request.headers.get("Origin") or request.content_length is None or request.content_length > 512:
            return jsonify(error="Invalid native request"), 400
        data = request.get_json(silent=True)
        result = pairing.redeem(data.get("code"), data.get("public_key")) if isinstance(data, dict) else None
        return (jsonify(result), 201) if result else (jsonify(error="Invalid invitation"), 401)

    @routes.post("/heartbeat")
    def heartbeat():
        if request.headers.get("Origin") or request.content_length is None or request.content_length > 512:
            return jsonify(error="Invalid native request"), 400
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        data = request.get_json(silent=True)
        if isinstance(data, dict) and pairing.heartbeat(
                token, data.get("timestamp"), data.get("nonce"), data.get("proof")):
            return "", 204
        return jsonify(error="Invalid device proof"), 401

    @routes.get("/devices")
    def devices():
        verified = owner()
        if verified is None:
            return jsonify(error="Authentication required"), 401
        return jsonify(online=pairing.online(verified.owner_id))

    @routes.delete("/devices/<device>")
    def revoke(device):
        verified = authorized_write()
        if verified is None:
            return jsonify(error="Forbidden"), 403
        return ("", 204) if pairing.revoke(verified.owner_id, device) else ("", 404)

    if jobs is not None:
        @routes.get("/panel/<asset>")
        def panel(asset):
            if owner() is None:
                return jsonify(error="Authentication required"), 401
            if asset not in {"index.html", "panel.js", "panel.css"}:
                return "", 404
            response = send_from_directory(Path(__file__).with_name("companion_pilot"), asset)
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                "base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            return response

        @routes.get("/projects")
        def projects():
            verified = owner()
            if verified is None:
                return jsonify(error="Authentication required"), 401
            rows = jobs.catalog.list_for(verified.owner_id)
            return jsonify([{"id": row.id, "title": row.title} for row in rows])

        @routes.post("/projects/<project>/jobs")
        def create_job(project):
            verified = authorized_write()
            if verified is None:
                return jsonify(error="Forbidden"), 403
            data = request.get_json(silent=True)
            if not isinstance(data, dict) or set(data) != {"device", "request_id"}:
                return jsonify(error="Invalid job"), 400
            if not isinstance(data["device"], str):
                return jsonify(error="Invalid device"), 400
            try:
                job = jobs.create(verified.owner_id, project, data["device"], data["request_id"])
            except ProjectNotFound:
                return jsonify(error="Not found"), 404
            except JobConflict:
                return jsonify(error="Job conflict"), 409
            except ValueError:
                return jsonify(error="Invalid job"), 400
            return jsonify(id=job), 202

        @routes.route("/projects/<project>/jobs/<job>", methods=["GET", "DELETE"])
        def owner_job(project, job):
            verified = owner() if request.method == "GET" else authorized_write()
            if verified is None:
                return jsonify(error="Forbidden"), 403
            try:
                if request.method == "DELETE":
                    return ("", 204) if jobs.cancel(verified.owner_id, project, job) else ("", 409)
                return jsonify(jobs.status(verified.owner_id, project, job))
            except (ValueError, ProjectNotFound):
                return jsonify(error="Not found"), 404

        @routes.get("/projects/<project>/jobs/<job>/result")
        def download(project, job):
            verified = owner()
            if verified is None:
                return jsonify(error="Authentication required"), 401
            try:
                media, checksum = jobs.result(verified.owner_id, project, job)
            except (ValueError, ProjectNotFound):
                return jsonify(error="Not found"), 404
            return Response(media, mimetype="video/mp4", headers={
                "Content-Disposition": 'attachment; filename="Montara.mp4"',
                "X-Content-SHA256": checksum,
                "X-Content-Type-Options": "nosniff",
            })

        @routes.post("/device/jobs/<operation>")
        def device_job(operation):
            if (request.headers.get("Origin") or request.content_length is None
                    or request.content_length > (17000000 if operation == "finish" else 1024)):
                return jsonify(error="Invalid native request"), 400
            if operation == "finish" and getattr(type(request._get_current_object()).max_content_length, "fset", None) is not None:
                request.max_content_length = 17000000
            data = request.get_json(silent=True)
            if not isinstance(data, dict) or not isinstance(data.get("payload"), dict):
                return jsonify(error="Invalid job request"), 400
            payload = data["payload"]
            if operation == "claim" and not payload:
                action = jobs.claim
            elif (operation == "progress" and set(payload) == {"job", "lease", "value"}
                  and isinstance(payload["job"], str) and isinstance(payload["lease"], str)
                  and type(payload["value"]) is int and 0 <= payload["value"] <= 100):
                def action(db, owner_id, device):
                    return jobs.progress(db, owner_id, device, **payload)
            elif (operation == "fail" and set(payload) == {"job", "lease"}
                  and all(isinstance(payload[key], str) for key in ("job", "lease"))):
                def action(db, owner_id, device):
                    return jobs.fail(db, owner_id, device, **payload)
            elif (operation == "finish" and set(payload) == {"job", "lease", "media", "checksum"}
                  and all(isinstance(value, str) for value in payload.values())):
                def action(db, owner_id, device):
                    try:
                        value = base64.b64decode(payload["media"], validate=True)
                    except (ValueError, binascii.Error):
                        return False
                    return jobs.store_result(db, owner_id, device, payload["job"], payload["lease"],
                                             value, payload["checksum"])
            else:
                return jsonify(error="Invalid operation"), 400
            token = request.headers.get("Authorization", "").removeprefix("Bearer ")
            try:
                accepted, result = pairing.device_request(
                    token, data.get("timestamp"), data.get("nonce"), data.get("proof"),
                    operation=operation, payload=payload, action=action)
            except JobConflict:
                return jsonify(error="Result quota exceeded"), 409
            if not accepted:
                return jsonify(error="Invalid device proof"), 401
            if result is False:
                return jsonify(error="Lease inactive"), 409
            return jsonify(result=result)

    @routes.after_request
    def prevent_caching(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    return routes
