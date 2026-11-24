"""Fail-closed per-owner session route contract, no worker or cloud required."""
import unittest

from urano.native_owner_full_session_http import full_session_target


SID="a"*12


class FullSessionPrivateRouteTests(unittest.TestCase):
    def ok(self, method, path, query="", kind=None):
        target=full_session_target(method,path,query)
        self.assertIsNotNone(target, (method,path,query))
        if kind:self.assertEqual(target.kind,kind)
        self.assertTrue(target.upstream.startswith("/montara/session"))
        return target

    def deny(self, method, path, query=""):
        self.assertIsNone(full_session_target(method,path,query),
                          (method,path,query))

    def test_review_and_mix_lifecycle(self):
        self.ok("POST","/montara/session",kind="json")
        self.ok("GET","/montara/session/latest")
        self.ok("GET",f"/montara/session/{SID}")
        self.ok("GET",f"/montara/session/{SID}/waveform",kind="session-json")
        self.ok("GET",f"/montara/session/{SID}/video-source",kind="session-json")
        for action in ("cancel","include","prepare","songs","render",
                       "video-master","originals","local-result","suggest"):
            self.ok("POST",f"/montara/session/{SID}/{action}")
        self.ok("GET",f"/montara/session/{SID}/local-plan",
                "song=1&start=10.5&end=35&name=Verse")
        self.ok("GET",f"/montara/session/{SID}/originals",
                "song=1&start=10&end=35&name=Verse")
        self.ok("GET",f"/montara/session/{SID}/originals","song=1")
        self.ok("GET",f"/montara/session/{SID}/originals")
        self.ok("GET",f"/montara/session/{SID}/listen",kind="session-media")
        self.ok("HEAD",f"/montara/session/{SID}/listen",kind="session-media")
        self.ok("GET",f"/montara/session/{SID}/listen",
                "start=1&end=25",kind="session-media")
        self.ok("GET",f"/montara/session/{SID}/result/3",
                "download=1",kind="session-media")
        self.ok("GET",f"/montara/session/{SID}/result/3",
                "v=3",kind="session-media")
        self.ok("GET",f"/montara/session/{SID}/results.zip",
                kind="session-media")

    def test_other_owners_and_unreviewed_paths_denied(self):
        for path in (
            "/montara/session/unverified","/montara/session/invalid",
            "/montara/session/"+("f"*13),
            "/montara/session/"+SID+"/..",
            "/montara/session/"+SID+"/report.html",
            "/montara/session/"+SID+"/listen/../../other",
            "/montara/session/"+SID+"/result/100000",
            "/montara/session/"+SID+"/result/-1",
            "/montara/session/"+SID+"/originals/any",
        ):
            self.deny("GET",path)
        self.deny("DELETE","/montara/session/"+SID)
        self.deny("PATCH",f"/montara/session/{SID}/songs")
        self.deny("GET","/montara/session")
        self.deny("POST",f"/montara/session/{SID}/listen")
        self.deny("POST",f"/montara/session/{SID}/result/2")
        self.deny("HEAD",f"/montara/session/{SID}/result/2")
        self.deny("GET",f"/montara/session/{SID}/result/2","download=2")
        self.deny("GET",f"/montara/session/{SID}/result/2","download=1&x=1")
        self.deny("GET",f"/montara/session/{SID}/result/2","download=1&download=1")
        self.deny("GET",f"/montara/session/{SID}/listen","start=1")
        self.deny("GET",f"/montara/session/{SID}/listen","start=-1&end=9")
        self.deny("HEAD",f"/montara/session/{SID}/listen","start=1&end=9")
        self.deny("GET",f"/montara/session/{SID}/local-plan","song=1&start=1&end=2&path=/etc/passwd")
        self.deny("GET",f"/montara/session/{SID}/originals","song=1&song=2")
        self.deny("GET",f"/montara/session/{SID}/originals","start=1&end=2")
        self.deny("GET",f"/montara/session/{SID}/originals","song=1&start=1&end=2&name="+("x"*85))
        self.deny("POST",f"/montara/session/{SID}/render","x=1")
        self.deny("GET",f"/montara/session/{SID}/suggest")
        self.deny("POST",f"/montara/session/{SID}/suggest","x=1")
        self.deny("GET",f"/montara/session/{SID}","x=1")
        self.deny("GET","/montara/session/latest","x=1")


if __name__ == "__main__":
    unittest.main()
