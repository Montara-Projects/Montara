import tempfile
import unittest
from pathlib import Path

from urano.google_flow import OIDCSettings
from urano.native_owner_app import create_native_owner_api
from urano.session_auth import SESSION_COOKIE, SessionStore


class PilotGateTests(unittest.TestCase):
    def test_editor_and_api_are_restricted_to_configured_owner(self):
        origin = "https://work.test"
        settings = OIDCSettings("client", "secret", origin + "/urano/v1/google/callback",
                                frozenset({"pilot@example.test", "other@example.test"}))
        web = Path(__file__).resolve().parents[1] / "web"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for pilot in (None, "pilot"):
                app = create_native_owner_api(root, settings=settings, chema_web_root=web,
                                              companion_pilot_owner=pilot)
                sessions = SessionStore(root / "sessions.sqlite3")
                anonymous = app.test_client()
                devices = "/urano/v1/companion/devices"
                self.assertEqual(anonymous.get(devices, base_url=origin).status_code,
                                 404 if pilot is None else 401)
                for owner in ("pilot", "other"):
                    client = app.test_client()
                    session = sessions.issue(owner)
                    client.set_cookie(SESSION_COOKIE, session.token, domain="work.test")
                    editor = client.get("/urano/v1/native/", base_url=origin)
                    self.assertEqual(editor.status_code, 200)
                    self.assertIn(b"full-session.js", editor.data)
                    enabled = pilot == owner
                    self.assertEqual(b'id="montara-companion-pilot"' in editor.data, enabled)
                    self.assertEqual(client.get(devices, base_url=origin).status_code,
                                     200 if enabled else 404 if pilot is None else 401)
                    response = client.post("/urano/v1/companion/invite", base_url=origin,
                                           headers={"Origin": origin, "X-Urano-CSRF": session.csrf})
                    self.assertEqual(response.status_code,
                                     201 if enabled else 404 if pilot is None else 403)
