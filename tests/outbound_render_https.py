"""Opt-in real macOS Engine smoke test through isolated TLS and an Owner session."""
import hashlib
import json
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, Request, build_opener

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Flask
from werkzeug.serving import WSGIRequestHandler, make_server

from companion.outbound_presence import NoRedirect, OutboundPresence
from companion.outbound_render import OutboundRender
from urano.companion_jobs import CompanionJobs
from urano.companion_pairing import CompanionPairing
from urano.companion_pairing_http import companion_pairing_blueprint
from urano.companion_proof import encode
from urano.project_catalog import ProjectCatalog
from urano.session_auth import SESSION_COOKIE, SessionStore
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "companion"))
from video_jobs import VideoJobs


ENGINE = "34c338d6d12e5d91e76b95e3e147714ea896cdf9"


class QuietHandler(WSGIRequestHandler):
    def log(self, *args, **kwargs):
        pass


class OutboundRenderSmoke(unittest.TestCase):
    def test_real_render_through_https(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video"
            video.mkdir()
            runtime = Path(os.environ["MONTARA_TEST_QA_VIDEO"])
            self.assertEqual((runtime / "ENGINE_COMMIT").read_text().strip(), ENGINE)
            for name in ("venv", "local_video.py", "engine", "brand", "ENGINE_COMMIT"):
                (video / name).symlink_to((runtime / name).resolve(strict=True))
            cert, keyfile = root / "cert.pem", root / "key.pem"
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                            "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
                            "-keyout", str(keyfile), "-out", str(cert)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            app = Flask(__name__)
            server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler,
                                 ssl_context=(str(cert), str(keyfile)))
            self.addCleanup(server.server_close)
            origin = f"https://localhost:{server.server_port}"
            context = ssl.create_default_context(cafile=str(cert))
            sessions = SessionStore(root / "sessions.db")
            catalog = ProjectCatalog(root / "catalog.db")
            project = catalog.create("alice", "Synthetic HTTPS export").id
            foreign = catalog.create("bob", "Synthetic other owner").id
            pairing = CompanionPairing(root / "devices.db")
            jobs = CompanionJobs(pairing, catalog)
            app.register_blueprint(companion_pairing_blueprint(sessions, pairing, origin=origin, jobs=jobs))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                http = build_opener(NoRedirect(), HTTPSHandler(context=context))
                connection = OutboundPresence(origin)
                connection.http = http
                identity = Ed25519PrivateKey.generate()
                alice, bob = sessions.issue("alice"), sessions.issue("bob")
                prefix = origin + "/urano/v1/companion/"

                def call(path, session, data=None):
                    headers = {"Cookie": f"{SESSION_COOKIE}={session.token}"}
                    if data is not None:
                        headers.update({"Origin": origin, "X-Urano-CSRF": session.csrf,
                                        "Content-Type": "application/json"})
                    request = Request(prefix + path, json.dumps(data).encode() if data is not None else None,
                                      headers)
                    with http.open(request, timeout=15) as response:
                        return response.read(), response.headers

                invitation, _ = call("invite", alice, {})
                device = connection.redeem(json.loads(invitation)["code"],
                                           encode(identity.public_key().public_bytes_raw()))
                asset = "montara-render-source-" + "a" * 32 + ".mp4"
                master = "montara-render-audio-" + "b" * 32 + ".audio"
                subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                                "testsrc2=size=640x360:rate=24", "-t", "5",
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(root / asset)], check=True)
                subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                                "sine=frequency=440:sample_rate=48000", "-t", "5",
                                "-f", "wav", str(root / master)], check=True)
                recipe = {"version": 1, "engine": ENGINE, "platform": "youtube",
                          "sources": [{"key": 0}], "segments": [{
                              "source": 0, "clip_start_sec": 0, "master_start_sec": 0,
                              "duration_sec": 5, "playback_speed": 1}]}
                approved = {"project": project, "master": master, "recipe": recipe,
                            "originals": [{"source": 0, "asset": asset}], "name": "Synthetic"}
                created, _ = call(f"projects/{project}/jobs", alice,
                                  {"request_id": "c" * 32, "device": device["device"]})
                job = json.loads(created)["id"]
                renderer = OutboundRender(connection, device["token"], lambda data: encode(identity.sign(data)),
                                          VideoJobs(root), {project: (approved, {project: root}, lambda _: None)})
                if not renderer.run_one(threading.Event()):
                    for log in root.glob(".montara-renders/*/render.log"):
                        print(log.read_text()[-2500:])
                    print("outputs", [(p.name, p.stat().st_size) for p in root.glob("*.mp4")])
                    print("job", call(f"projects/{project}/jobs/{job}", alice)[0])

                    self.fail("Render did not complete")
                path = f"projects/{project}/jobs/{job}"
                status, _ = call(path, alice)
                self.assertEqual(json.loads(status), {"progress": 100, "state": "ready"})
                media, headers = call(path + "/result", alice)
                self.assertEqual(hashlib.sha256(media).hexdigest(), headers["X-Content-SHA256"])
                with self.assertRaises(HTTPError) as denied:
                    call(f"projects/{foreign}/jobs/{job}/result", bob)
                self.assertEqual(denied.exception.code, 404)
                result = Path(os.environ.get("MONTARA_TEST_QA_OUTPUT", str(root / "download.mp4")))
                with result.open("xb") as output:
                    output.write(media)
                probe = subprocess.check_output(["ffprobe", "-v", "error", "-show_streams",
                                                 "-show_format", "-of", "json", str(result)])
                payload = json.loads(probe)
                streams = {row["codec_type"]: row for row in payload["streams"]}
                self.assertEqual(streams["video"]["codec_name"], "h264")
                self.assertEqual(streams["audio"]["codec_name"], "aac")
                self.assertEqual((streams["video"]["width"], streams["video"]["height"]), (1920, 1080))
                self.assertAlmostEqual(float(payload["format"]["duration"]), 5, delta=.15)
                subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(result),
                                "-f", "null", "-"], check=True)
                print(f"HTTPS MP4 {len(media)} bytes SHA-256 {hashlib.sha256(media).hexdigest()}")
            finally:
                server.shutdown()
