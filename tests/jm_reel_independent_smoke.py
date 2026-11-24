"""Render a synthetic JM Reel with independent audio or no music."""
import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from app import create_montara_app
root=Path(tempfile.mkdtemp(prefix='montara-reel-independent-'))
def ff(*a): subprocess.run(['ffmpeg','-v','error',*map(str,a)],check=True)
video=root/'silent.mp4';audio=root/'independent.wav'
ff('-f','lavfi','-i','testsrc2=size=640x360:rate=24','-t','5','-an','-c:v','libx264',video)
ff('-f','lavfi','-i','sine=frequency=713:sample_rate=48000','-t','5',audio)
app=create_montara_app(root/'data',samples=False)
client=app.test_client()
if "--silent" in sys.argv:
    rejected = client.post("/montara/reel/silent-soundtrack", json={"seconds": 61})
    assert rejected.status_code == 400
    generated = client.post("/montara/reel/silent-soundtrack", json={"seconds": 20})
    assert generated.status_code == 200, generated.json
    audio = Path(generated.json["path"])
videos = [str(video)]
if "--multiple" in sys.argv:
    second = root / "different-audio.mp4"
    ff("-f", "lavfi", "-i", "smptebars=size=640x360:rate=24",
       "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000",
       "-t", "5", "-c:v", "libx264", "-c:a", "aac", second)
    videos.append(str(second))
if "--photo" in sys.argv:
    from PIL import Image
    image = io.BytesIO()
    Image.new("RGB", (640, 360), (120, 40, 170)).save(image, format="PNG")
    image.seek(0)
    uploaded = client.post("/montara/reel/still", data={"image": (image, "synthetic.png")})
    assert uploaded.status_code == 201, uploaded.json
    videos = [uploaded.json["path"]]
    mp3 = root / "independent.mp3"
    ff("-i", audio, "-codec:a", "libmp3lame", mp3)
    audio = mp3
assert client.post("/api/v1/wizard/start", json={
    "platform": "youtube", "videos": videos,
}).status_code == 400
body = dict(platform="reel", name="Independent soundtrack", videos=videos,
            master=str(audio), reel_duration_sec=20)
response = client.post('/api/v1/wizard/start', json=body)
assert response.status_code == 202, response.json
for i in range(150):
 s=client.get('/api/v1/wizard/status').json
 if s['status'] in ('done','completed'): break
 if s['status'] in ('failed','error'): raise RuntimeError(s)
 if s['status']=='waiting_review':
  r=client.post('/api/v1/wizard/review/render',json={});assert r.status_code in (200,202),r.json
 time.sleep(1)
else: raise RuntimeError(s)
result = s["result"]
assert result["platform"] == "reel"
output = Path(result["path"])
assert output.is_file()
probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
    "stream=codec_name:format=duration", "-of", "json", str(output)]))
assert {stream["codec_name"] for stream in probe["streams"]} == {"h264", "aac"}, probe
assert abs(float(probe["format"]["duration"]) - 5) < .25, probe
ff("-xerror", "-i", output, "-f", "null", "-")
print(output, probe, flush=True)
