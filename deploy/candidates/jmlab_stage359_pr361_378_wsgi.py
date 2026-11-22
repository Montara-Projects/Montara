"""MAIN-only reviewed Owner account and Music Session overlay."""
from __future__ import annotations
import hashlib
import os
import sys
from pathlib import Path

_OVERLAY = Path("/opt/montara/jmlab-stage359-pr361-378-candidate-20261122")
_PINNED = Path("/opt/montara/bundles/jm-61a57fd9ad46df4a8cfc0ae9c3b270b28119e009")
_REVIEWED_FULL_SESSION_JS = "004d2f6f14e53ef84e519a24c59ac2dd8384c2a86219fb92751cb62da482f824"
_EXPECTED = ("urano/__init__.py", "urano/native_owner_browser_bridge.js",
             "urano/native_owner_browser_surface.py",
             "urano/native_owner_web_gateway.py",
             "urano/native_owner_stage_http.py",
             "urano/native_owner_full_session_http.py",
             "urano/native_owner_mix_http.py",
             "urano/native_owner_app.py", "urano/google_flow.py",
             "urano/google_oidc.py", "urano/session_auth.py",
             "urano/owner_account.css", "web/full-session.js",
             "web/montara.js", "web/cut-editor.js",
             "web/track-types.js", "web/montara.css")


def _preflight():
    if "urano" in sys.modules:
        raise RuntimeError("MAIN Owner package imported before verified overlay")
    for base in (_OVERLAY, _PINNED):
        if not base.is_dir() or base.is_symlink() or base.stat().st_uid != 0 or base.stat().st_mode & 0o022:
            raise RuntimeError("Untrusted MAIN Owner overlay/bundle location")
    for name in _EXPECTED:
        p = _OVERLAY / name
        if (not p.is_file() or p.is_symlink() or p.stat().st_uid != 0
                or p.stat().st_mode & 0o022):
            raise RuntimeError("Untrusted MAIN Owner overlay asset")
    bridge = _OVERLAY / "urano/native_owner_browser_bridge.js"
    if hashlib.sha256(bridge.read_bytes()).hexdigest() != "25212ba72c9f34784eb866272a14e86eb945a3aa17a9733ae2c92668e33fcf20":
        raise RuntimeError("MAIN Owner bridge digest does not match reviewed route contract")
    # This candidate allows one new private video frame operation and one
    # bounded camera audio player. Both implementations are explicitly pinned.
    for relative, expected in (
            ("urano/native_owner_stage_http.py", "cabe2637629ea0b347db1cb44899386be1dce1925e6f97be9370b553f3d03452"),
            ("web/montara.js", "1fa06bf33bdcd2fcbe2551766172ac3f0d640f54340a359b05a74d62cf809b8c"),
            ("web/montara.css", "306c604a35feae0523236470f45a40dd1cd2a8b8c9cf56198eb286b233afa47e"),
            ("urano/native_owner_browser_surface.py", "68b207f76c602dd6dc3fe10d82e6803742258faf4756bb4a45b2486035f4f060")):
        source = _OVERLAY / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise RuntimeError("JM issue346 asset digest mismatch: " + relative)
    if hashlib.sha256((_OVERLAY / "web/cut-editor.js").read_bytes()).hexdigest() != "ba000bfa984aa54fc26b8c3117aba503cc2b0bdfc8a9759d41a7322f13de3e70":
        raise RuntimeError("JM reviewed cut-editor digest mismatch")
    # The private media gateway must also be pinned, not just the UI JS.
    gateway = _OVERLAY / "urano/native_owner_web_gateway.py"
    if hashlib.sha256(gateway.read_bytes()).hexdigest() != "b61dca5d66f7987e68ac8fb10accab6bd66a9c2a6549baeb9486f4c9a0acfe50":
        raise RuntimeError("MAIN private MP3 range gateway digest mismatch")
    script = _OVERLAY / "web/full-session.js"
    if hashlib.sha256(script.read_bytes()).hexdigest() != _REVIEWED_FULL_SESSION_JS:
        raise RuntimeError("MAIN Session JS does not match reviewed source")
    account_js = _OVERLAY / "urano/native_owner_browser_bridge.js"
    if b"Your Projects" not in account_js.read_bytes() or b"canonicalAudioForSession" not in account_js.read_bytes():
        raise RuntimeError("MAIN reviewed account + session JS not present")
    if not (_PINNED / "montara-jm-bundle.json").is_file():
        raise RuntimeError("MAIN immutable editor manifest unavailable")


_preflight()
sys.path.insert(0, str(_OVERLAY))
if str(_PINNED) not in sys.path:
    sys.path.append(str(_PINNED))
from urano import (native_owner_browser_surface, native_owner_web_gateway,
                   native_owner_full_session_http, native_owner_mix_http,
                   native_owner_app, google_flow, google_oidc, session_auth)
for module in (native_owner_browser_surface, native_owner_web_gateway,
               native_owner_full_session_http, native_owner_mix_http,
               native_owner_app, google_flow, google_oidc, session_auth):
    if Path(module.__file__).parent != _OVERLAY / "urano":
        raise RuntimeError("Native MAIN module not loaded from reviewed overlay")
os.environ["MONTARA_SESSION_SCRIPT_OVERRIDE"] = str(_OVERLAY / "web/full-session.js")
from urano.native_owner_trusted_wsgi import create_loopback_native_owner_application


def create_application():
    return create_loopback_native_owner_application()
