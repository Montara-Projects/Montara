"""Native, outbound-only presence client for the isolated pairing prototype."""
import json
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OutboundPresence:
    def __init__(self, origin):
        address = urlsplit(origin)
        if (address.scheme != "https" or not address.hostname or address.username or
                address.password or address.query or address.fragment or address.path):
            raise ValueError("Exact HTTPS broker origin required")
        self.base = origin + "/urano/v1/companion/"
        self.http = build_opener(NoRedirect())

    def redeem(self, code, public_key):
        request = Request(self.base + "redeem", json.dumps({"code": code, "public_key": public_key}).encode(),
                          {"Content-Type": "application/json"})
        with self.http.open(request, timeout=10) as response:
            return json.loads(response.read(1024))

    def run(self, token, signer, stop):
        """Retry transient failures; exit on expiry or revocation."""
        delay = 15
        while not stop.is_set():
            timestamp = int(time.time())
            nonce = secrets.token_urlsafe(16)
            message = f"montara-companion-v1\nPOST\nheartbeat\n{token}\n{timestamp}\n{nonce}".encode("ascii")
            body = json.dumps({"timestamp": timestamp, "nonce": nonce, "proof": signer(message)})
            request = Request(self.base + "heartbeat", body.encode(),
                              {"Authorization": "Bearer " + token, "Content-Type": "application/json"})
            try:
                with self.http.open(request, timeout=10):
                    delay = 15
            except HTTPError as error:
                if error.code in (401, 403):
                    return
                delay = min(delay * 2, 60)
            except (URLError, TimeoutError):
                delay = min(delay * 2, 60)
            stop.wait(delay)
