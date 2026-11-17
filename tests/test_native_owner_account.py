import sqlite3
import tempfile
import unittest
from pathlib import Path

from urano.google_flow import OIDCSettings
from urano.native_owner_app import create_native_owner_api
from urano.project_catalog import ProjectCatalog, ProjectNotFound
from urano.session_auth import SESSION_COOKIE, SessionStore


class WorkAccountTests(unittest.TestCase):
    def test_only_current_session_profile_and_csrf_logout(self):
        origin = "https://work.example.test"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = Path(__file__).resolve().parents[1] / "web"
            settings = OIDCSettings("client", "secret", origin + "/urano/v1/google/callback",
                                    frozenset({"a@example.test", "b@example.test"}))
            app = create_native_owner_api(root, settings=settings, chema_web_root=web)
            sessions = SessionStore(root / "sessions.sqlite3")
            a = sessions.issue("a" * 32, profile=("Ada", "a@example.test", ""))
            b = sessions.issue("b" * 32, profile=("Bea", "b@example.test", ""))
            first = app.test_client()
            second = app.test_client()
            first.set_cookie(SESSION_COOKIE, a.token, domain="work.example.test")
            second.set_cookie(SESSION_COOKIE, b.token, domain="work.example.test")
            account = "/urano/v1/session/account"
            logout = "/urano/v1/session/logout"
            self.assertEqual(first.get(account, base_url=origin).json["email"], "a@example.test")
            self.assertEqual(second.get(account, base_url=origin).json["email"], "b@example.test")
            self.assertEqual(first.post(logout, base_url=origin, headers={
                "Origin": origin, "X-Urano-CSRF": b.csrf,
            }).status_code, 403)
            response = first.post(logout, base_url=origin, headers={
                "Origin": origin, "X-Urano-CSRF": a.csrf,
            })
            self.assertEqual(response.status_code, 204)
            for attr in ("Max-Age=0", "Secure", "HttpOnly", "SameSite=Lax", "Path=/"):
                self.assertIn(attr, response.headers["Set-Cookie"])
            first.set_cookie(SESSION_COOKIE, a.token, domain="work.example.test")
            self.assertEqual(first.get(account, base_url=origin).status_code, 401)
            self.assertEqual(second.get(account, base_url=origin).status_code, 200)

            with sqlite3.connect(root / "sessions.sqlite3") as db:
                self.assertEqual(db.execute(
                    "SELECT count(*) FROM urano_auth_sessions WHERE owner_id=?", ("a" * 32,)
                ).fetchone()[0], 0)
            language = "/urano/v1/session/language"
            self.assertEqual(second.post(language, base_url=origin, json={"language": "fr"},
                headers={"Origin": origin, "X-Urano-CSRF": a.csrf}).status_code, 403)
            self.assertEqual(second.post(language, base_url=origin, json={"language": "fr"},
                headers={"Origin": origin, "X-Urano-CSRF": b.csrf}).status_code, 200)
            reopened = SessionStore(root / "sessions.sqlite3")
            self.assertEqual(reopened.language("b" * 32), "fr")
            self.assertEqual(reopened.language("a" * 32), "en")

            catalog = ProjectCatalog(root / "projects.sqlite3")
            for owner, other in (("a" * 32, "b" * 32), ("b" * 32, "a" * 32)):
                project = catalog.create(owner, "Synthetic project")
                with self.assertRaises(ProjectNotFound):
                    catalog.get(other, project.id)
                with self.assertRaises(ProjectNotFound):
                    catalog.save_recipe(other, project.id, {}, expected_revision=0)
                self.assertEqual(catalog.get(owner, project.id).revision, 0)
