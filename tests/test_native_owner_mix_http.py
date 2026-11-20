"""Strict private Music mixer route contract; never a generic media proxy."""
import unittest
from urano.native_owner_mix_http import native_mix_target

SID="a"*12
BASE="/montara/mix/"+SID

class MixRouteTests(unittest.TestCase):
    def ok(self,method,path,query="",kind=None):
        entry=native_mix_target(method,path,query)
        self.assertIsNotNone(entry,(method,path,query))
        if kind:self.assertEqual(entry.kind,kind)
        self.assertTrue(entry.upstream.startswith("/montara/mix"))
        return entry
    def deny(self,method,path,query=""):
        self.assertIsNone(native_mix_target(method,path,query),
                          (method,path,query))
    def test_original_mixer_workflow(self):
        self.ok("POST","/montara/mix",kind="json")
        self.ok("GET",BASE,kind="json")
        self.ok("GET",BASE+"/track/Keys%20L.wav",kind="mix-media")
        self.ok("GET",BASE+"/track/Vox.wav","format=wav",kind="mix-media")
        self.ok("GET",BASE+"/fx/reverb/Keys%20L.wav",kind="mix-media")
        self.ok("GET",BASE+"/fx/delay/Vox.wav",kind="mix-media")
        self.ok("GET",BASE+"/result",kind="mix-media")
        self.ok("GET",BASE+"/result","download_name=Montara-song.mp3",kind="mix-media")
        self.ok("POST",BASE+"/render",kind="json")
        self.ok("POST",BASE+"/reference/link",kind="json")
        self.ok("GET",BASE+"/reference/link",kind="json")
    def test_decoded_flask_track_names_are_encoded_for_private_http(self):
        # Browser sends %20; Flask turns it into a literal space before
        # native_mix_target. http.client refuses an unescaped request target.
        self.assertEqual(
            self.ok("GET", BASE + "/track/Kick out.wav", kind="mix-media").upstream,
            BASE + "/track/Kick%20out.wav")
        self.assertEqual(
            self.ok("GET", BASE + "/track/Tom 2.wav", "format=wav",
                    kind="mix-media").upstream,
            BASE + "/track/Tom%202.wav?format=wav")
        self.assertEqual(
            self.ok("GET", BASE + "/fx/reverb/Voz José.wav",
                    kind="mix-media").upstream,
            BASE + "/fx/reverb/Voz%20Jos%C3%A9.wav")
        self.assertEqual(
            self.ok("GET", BASE + "/track/Pista #1+.wav",
                    kind="mix-media").upstream,
            BASE + "/track/Pista%20%231%2B.wav")

    def test_denies_arbitrary_mixer_urls(self):
        for method,path,query in [
            ("GET","/montara/mix",""),("POST","/montara/mix","debug=1"),
            ("GET","/montara/mix/latest",""),
            ("GET","/montara/mix/"+("a"*13),""),
            ("GET",BASE+"/track/../secret.wav",""),
            ("GET",BASE+"/track/Track%2Fsecret.wav",""),
            ("GET",BASE+"/track/.secret.wav",""),
            ("GET",BASE+"/track/x..wav",""),
            ("GET",BASE+"/fx/unknown/Keys.wav",""),
            ("GET",BASE+"/track/Keys.wav","path=/etc/passwd"),
            ("GET",BASE+"/track/Keys.wav","format=opus"),
            ("GET",BASE+"/track/Keys.wav","format=wav&format=wav"),
            ("DELETE",BASE+"/render",""),
            ("POST",BASE+"/reference",""),
            ("GET",BASE+"/result","download_name=.."),
            ("GET",BASE+"/result","download_name=%2Ftmp%2Fkeys.mp3"),
            ("GET",BASE+"/result","x=1"),
        ]:
            self.deny(method,path,query)

if __name__=="__main__":unittest.main()
