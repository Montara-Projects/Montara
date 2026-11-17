"""Opt-in prototype with same-origin Owner control and native bearer endpoints."""
from flask import Blueprint, jsonify, request

from urano.session_auth import SESSION_COOKIE


def companion_pairing_blueprint(sessions, pairing, *, origin):
    routes = Blueprint("work_outbound_companion", __name__, url_prefix="/urano/v1/companion")

    @routes.before_request
    def enforce_origin():
        if request.host_url.rstrip("/") != origin:
            return jsonify(error="Unexpected host"), 403

    def owner():
        return sessions.verify(request.cookies.get(SESSION_COOKIE))

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

    @routes.after_request
    def prevent_caching(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    return routes
