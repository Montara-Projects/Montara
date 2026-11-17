"""Consume one signed outbound job using an explicitly approved local project."""
import base64
import hashlib
import json
import secrets
import time
from urllib.error import HTTPError
from urllib.request import Request


class OutboundRender:
    def __init__(self, connection, token, sign, video_jobs, approved_projects):
        self.connection = connection
        self.token = token
        self.sign = sign
        self.video_jobs = video_jobs
        self.approved_projects = approved_projects

    def request(self, operation, payload):
        timestamp = int(time.time())
        nonce = secrets.token_urlsafe(16)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        checksum = hashlib.sha256(canonical.encode("ascii")).hexdigest()
        message = (f"montara-companion-jobs-v1\nPOST\n{operation}\n{checksum}\n"
                   f"{self.token}\n{timestamp}\n{nonce}").encode("ascii")
        body = json.dumps(dict(timestamp=timestamp, nonce=nonce,
                               proof=self.sign(message), payload=payload)).encode()
        request = Request(self.connection.base + "device/jobs/" + operation, body,
                          {"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        with self.connection.http.open(request, timeout=15) as response:
            return json.loads(response.read(4096))["result"]

    def run_one(self, stop):
        task = self.request("claim", {})
        if task is None:
            return False
        scope = {"job": task["id"], "lease": task["lease"]}
        local = None
        try:
            if task["operation"] != "render_video":
                raise ValueError("Unsupported Companion operation")
            # The remote job selects a previously approved UUID, never a local path.
            recipe, folders, find_original = self.approved_projects[task["project"]]
            local = self.video_jobs.start(recipe, folders, find_original)
            while not stop.is_set():
                status = self.video_jobs.status(local)
                if status["status"] in ("cancelled", "failed"):
                    raise RuntimeError("Local render failed")
                self.request("progress", {**scope, "value": min(99, int(status["progress"] * 100))})
                if status["status"] == "ready":
                    with self.video_jobs.output(local).open("rb") as media:
                        value = media.read(12 * 1024 * 1024 + 1)
                    if len(value) > 12 * 1024 * 1024:
                        raise ValueError("Pilot result exceeds 12 MiB")
                    self.request("finish", {**scope, "checksum": hashlib.sha256(value).hexdigest(),
                                           "media": base64.b64encode(value).decode("ascii")})
                    return True
                stop.wait(1)
        except HTTPError as error:
            if error.code not in (401, 403, 409):
                raise
        except (KeyError, ValueError, RuntimeError):
            self.request("fail", scope)
        finally:
            if local is not None:
                self.video_jobs.cancel(local)
        return False
