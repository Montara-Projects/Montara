"""Native, outbound-only presence client for the isolated pairing prototype."""
import json
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

    def redeem(self, code):
        request = Request(self.base + "redeem", json.dumps({"code": code}).encode(),
                          {"Content-Type": "application/json"})
        with self.http.open(request, timeout=10) as response:
            return json.loads(response.read(1024))

    def run(self, token, stop):
        """Retry transient failures; exit on expiry or revocation."""
        delay = 15
        while not stop.is_set():
            request = Request(self.base + "heartbeat", b"", {"Authorization": "Bearer " + token})
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
