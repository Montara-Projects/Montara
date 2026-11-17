"""Canonical proof for the outbound Companion heartbeat."""
import base64
import binascii
import re


def decode(value, size):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return None
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except binascii.Error:
        return None
    return raw if len(raw) == size and encode(raw) == value else None


def encode(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def heartbeat_message(token, timestamp, nonce):
    return f"montara-companion-v1\nPOST\nheartbeat\n{token}\n{timestamp}\n{nonce}".encode("ascii")

def job_message(token, timestamp, nonce, operation, payload):
    import hashlib
    import json

    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(body.encode("ascii")).hexdigest()
    return f"montara-companion-jobs-v1\nPOST\n{operation}\n{digest}\n{token}\n{timestamp}\n{nonce}".encode("ascii")
