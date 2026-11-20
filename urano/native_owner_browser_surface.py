"""Owner-authenticated Chema ORIGINAL page, with no alternative navigation.

The page is the exact pinned Chema HTML with ONE removable control-plane
script before its own scripts. Music/Video, Stage/Push/Show, New and Latest
stay in their original positions. The public service must independently
configure real Google sessions and the explicit private RPC bridge.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from flask import Blueprint, Response, abort, make_response, request, send_file, redirect
import stat

from urano.private_jm_wsgi_socket import pinned_jm_static_assets
from urano.session_auth import SESSION_COOKIE, SessionStore


def native_owner_browser_blueprint(sessions: SessionStore, *,
                                   https_origin: str, web_root: Path) -> Blueprint:
    root = Path(web_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Reviewed original Chema web root required")
    root = root.resolve(strict=True)
    original = root / "index.html"
    if original.is_symlink() or not original.is_file():
        raise ValueError("Reviewed Chema index missing")
    manifest = pinned_jm_static_assets(root)
    anchor = '<script src="mix-levels.js"></script>'
    html = original.read_text(encoding="utf-8")
    if (html.count(anchor) != 1 or
            html.count('id="newVideo" data-go="mode"') != 1 or
            html.count('id="sessionResume"') != 1 or
            html.count('data-platform="youtube"') != 1 or
            html.count('data-platform="reel"') != 1 or
            html.count('data-platform="show"') != 1):
        raise ValueError("Pinned Chema UX anchors changed; re-audit required")

    # One external adapter only. No owner header, dashboard, project picker,
    # modified New/Latest controls, shortcut Stage, or HTML fragments.
    edited = html.replace(anchor,
        '<script src="owner-bridge.js"></script>\n' + anchor, 1)
    digests = {
        name: hashlib.sha256((root / name.lstrip("/")).read_bytes()).digest()
        for name in manifest
    }
    original_digest = hashlib.sha256(original.read_bytes()).digest()
    bp = Blueprint("urano_native_owner_browser", __name__,
                   url_prefix="/urano/v1/native")

    @bp.before_request
    def private_owner_only():
        if request.host_url.rstrip("/") != https_origin:
            abort(403)
        if sessions.verify(request.cookies.get(SESSION_COOKIE)) is None:
            # Opening a private download link from another browser can omit
            # the existing SameSite/HttpOnly Google Owner cookie.
            # Redirect only this exact installer URL to fixed Montara entry
            # (which starts Google OIDC). After login Owner clicks Download.
            # No caller-supplied next URL, anonymous file or token exposure.
            if (request.path == "/urano/v1/native/companion/download"
                    and request.method in ("GET", "HEAD")):
                response = redirect("/", code=302)
                response.headers["Cache-Control"] = "no-store"
                response.headers["Referrer-Policy"] = "no-referrer"
                return response
            abort(401)

    def safe_response(data: bytes | str, mimetype: str):
        response = Response(data, mimetype=mimetype)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @bp.get("/")
    def original_chema_page():
        if hashlib.sha256(original.read_bytes()).digest() != original_digest:
            abort(503)
        return safe_response(edited, "text/html")

    @bp.get("/companion/download")
    def private_jm_renderer_pkg():
        # A fixed, verified root-owned .pkg. The Owner's Google session and
        # exact HTTPS host are enforced by the blueprint's before_request.
        pkg = Path("/opt/montara/jmlab-downloads") / (
            "Montara-LAB-JM-Renderer-92c7bc33-Intel-v2.pkg")
        try:
            st = pkg.lstat()
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or
                    not 25 * 1024 * 1024 <= st.st_size <= 900 * 1024 * 1024 or
                    pkg.is_symlink()):
                abort(404)
        except OSError:
            abort(404)
        response = send_file(
            pkg, mimetype="application/octet-stream",
            as_attachment=True, download_name=pkg.name,
            conditional=True, max_age=0)
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @bp.get("/owner-bridge.js")
    def owner_adapter():
        # This file is the ONLY new browser behavior and never changes the
        # global original JM source or any private Owner project files.
        path = Path(__file__).with_name("native_owner_browser_bridge.js")
        if path.is_symlink() or not path.is_file():
            abort(503)
        return safe_response(path.read_bytes(), "application/javascript")

    @bp.get("/full-session.js")
    def private_review_audio_asset():
        # Only this lab's song listening behavior differs from the pinned
        # Chema source. Preserve the original index, navigational controls
        # and all other assets; never allow a browser-chosen override path.
        source = root / "full-session.js"
        if (source.is_symlink() or not source.is_file() or
                hashlib.sha256(source.read_bytes()).digest() !=
                digests.get("/full-session.js")):
            abort(503)
        addon = Path("/opt/montara/jmlab-session-overlay-d9014f6/web/full-session.js")
        try:
            meta = addon.lstat()
            if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != 0 or
                    not 1_000 <= meta.st_size <= 200_000 or
                    hashlib.sha256(addon.read_bytes()).hexdigest() !=
                    "4abd596ceccbd973356aef4957d738eef9d82367c33b0c3f73534b91fe39917f"):
                abort(503)
        except OSError:
            abort(503)
        return safe_response(addon.read_bytes(), "application/javascript")

    @bp.get("/<path:filename>")
    def original_chema_asset(filename: str):
        selected = "/" + filename
        if selected not in manifest:
            abort(404)
        path = root / filename
        if (path.is_symlink() or not path.is_file()
                or path.resolve(strict=True) != root / filename
                or hashlib.sha256(path.read_bytes()).digest() != digests[selected]):
            abort(503)
        suffix = path.suffix.lower()
        types = {
            ".js": "application/javascript", ".css": "text/css",
            ".svg": "image/svg+xml", ".png": "image/png",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".ico": "image/x-icon",
            ".woff2": "font/woff2",
        }
        mimetype = types.get(suffix)
        if mimetype is None:
            abort(404)
        return safe_response(path.read_bytes(), mimetype)

    return bp
