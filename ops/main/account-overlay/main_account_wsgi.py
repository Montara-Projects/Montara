"""MAIN-only reviewed Owner account and Music Session overlay."""
from __future__ import annotations
import hashlib
import os
import sys
from pathlib import Path

_OVERLAY = Path("/opt/montara-main-release/main-account-overlay-20261120")
_PINNED = Path("/opt/montara/bundles/jm-61a57fd9ad46df4a8cfc0ae9c3b270b28119e009")
_REVIEWED_FULL_SESSION_JS = "4abd596ceccbd973356aef4957d738eef9d82367c33b0c3f73534b91fe39917f"
_EXPECTED = ("urano/__init__.py", "urano/native_owner_browser_bridge.js",
             "urano/native_owner_browser_surface.py",
             "urano/native_owner_web_gateway.py",
             "urano/native_owner_full_session_http.py",
             "urano/native_owner_mix_http.py",
             "urano/native_owner_app.py", "urano/google_flow.py",
             "urano/google_oidc.py", "urano/session_auth.py",
             "urano/owner_account.css", "web/full-session.js")


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
