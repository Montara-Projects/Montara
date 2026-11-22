"""Issue #346: a bounded owner-project 360 frame, not an arbitrary media proxy."""
import unittest
from urllib.parse import urlencode

from urano.native_owner_stage_http import native_stage_route

ROUTE = "/api/v1/wizard/spherical-source-frame"
SOURCE = (
    "/var/lib/private/montara-h4-jmlab-owner-" + "a" * 40 +
    "/Uploads/" + "b" * 32 + "/C0020_RECUPERADO.small.mp4"
)


class SphericalRouteTests(unittest.TestCase):
    def test_owner_uploaded_video_only(self):
        route = native_stage_route("GET", ROUTE, urlencode({"source": SOURCE}))
        self.assertIsNotNone(route)
        self.assertEqual(route.kind, "review-media")
        self.assertEqual(route.upstream, ROUTE + "?" + urlencode({"source": SOURCE}))

    def test_fail_closed(self):
        bad = (
            ("POST", urlencode({"source": SOURCE})),
            ("HEAD", urlencode({"source": SOURCE})),
            ("GET", ""),
            ("GET", "source="),
            ("GET", urlencode({"source": SOURCE, "admin": "1"})),
            ("GET", urlencode({"source": SOURCE}) + "&" + urlencode({"source": SOURCE})),
            ("GET", urlencode({"source": "/etc/passwd"})),
            ("GET", urlencode({"source": SOURCE.replace("/Uploads/", "/Projects/")})),
            ("GET", urlencode({"source": SOURCE.replace("/" + "b"*32 + "/", "/../../")})),
            ("GET", urlencode({"source": SOURCE.replace(".mp4", ".png")})),
            ("GET", urlencode({"source": SOURCE.replace(".mp4", "/inside.mp4")})),
            ("GET", urlencode({"source": SOURCE + "\x00"})),
            ("GET", urlencode({"source": SOURCE + "\\"})),
        )
        for method, query in bad:
            with self.subTest(method=method, query=query[:140]):
                self.assertIsNone(native_stage_route(method, ROUTE, query))

    def test_no_other_route_granted(self):
        self.assertIsNone(native_stage_route("GET", "/api/v1/wizard/other", urlencode({"source": SOURCE})))


if __name__ == "__main__":
    unittest.main()
