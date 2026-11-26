"""Real compact Opus, concurrent registration/finalization and interrupted rename."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from flask import Flask
import soundfile as sf
from resumable_upload import register_resumable_upload, preview_original, compact_preview_metadata

@pytest.fixture
def source(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("needs ffmpeg")
    wav, opus = tmp_path/"tone.wav", tmp_path/"tone.wav.opus"
    subprocess.run(["ffmpeg","-v","error","-f","lavfi","-i","sine=f=440:d=3","-ar","48000","-c:a","pcm_s24le",str(wav)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(wav),"-c:a","libopus","-b:a","64k","-metadata","montara_sample_rate=48000","-metadata","time_reference=96000","-f","ogg",str(opus)],check=True)
    return wav, opus.read_bytes()

def setup(tmp_path):
    app = Flask(__name__)
    app.testing = True
    register_resumable_upload(app, tmp_path/"data", lambda paths: {"master":[{"path":paths[0]}]})
    return app

def body_for(i, wav, payload):
    return dict(name=f"Track{i:02}.wav.opus",size=len(payload),
        fingerprint=hashlib.sha256(payload[:65536]+payload[-65536:]).hexdigest(),
        original=dict(name=f"Track{i:02}.wav",size=wav.stat().st_size,
                      fingerprint=hashlib.sha256(str(i).encode()).hexdigest()),
        compact_preview=True)

def test_30_compact_stems_three_concurrent(tmp_path, source):
    wav,payload=source
    app=setup(tmp_path)
    def upload(i):
        body=body_for(i,wav,payload)
        with app.test_client() as c:
            r=c.post("/montara/uploads",json=body)
            assert r.status_code==201
            u="/montara/uploads/"+r.json["id"]
            assert c.put(u,data=payload,headers={"Upload-Offset":"0"}).status_code==200
            r=c.post(u+"/finish",json={})
            assert r.status_code==200
            p=Path(r.json["master"][0]["path"])
            assert p.suffix==".ogg" and p.read_bytes()==payload and sf.info(p).frames>0
            assert preview_original(p)==body["original"]
            assert compact_preview_metadata(p)["offset"]==2
            assert c.post(u+"/finish",json={}).json==r.json
            assert c.post("/montara/uploads",json=body).json["complete"]
            return p.stat().st_size
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        sizes=list(pool.map(upload,range(30)))
    assert sum(sizes)==30*len(payload)
    assert not list((tmp_path/"data").rglob("*.wav"))
    print("30 compact imports:",sum(sizes),"bytes vs",30*wav.stat().st_size,"PCM bytes")

@pytest.mark.parametrize("phase",["staged","compact"])
def test_finish_after_interrupted_rename(tmp_path,source,phase):
    wav,payload=source
    body=body_for(99,wav,payload)
    app=setup(tmp_path)
    with app.test_client() as c:
        r=c.post("/montara/uploads",json=body)
        u="/montara/uploads/"+r.json["id"]
        work=tmp_path/"data"/"Uploads"/r.json["id"]
        assert c.put(u,data=payload,headers={"Upload-Offset":"0"}).status_code==200
        target=work/(body["name"] if phase=="staged" else "Track99.ogg")
        (work/"source.part").rename(target)
        assert c.get(u).json["received"]==len(payload)
        assert c.post("/montara/uploads",json=body).json["id"]==u.rsplit("/",1)[-1]
        r=c.post(u+"/finish",json={})
        assert r.status_code==200
        assert Path(r.json["master"][0]["path"]).read_bytes()==payload
        assert c.post(u+"/finish",json={}).json==r.json

def test_compact_capacity_floor(tmp_path,source,monkeypatch):
    from types import SimpleNamespace
    wav,payload=source
    app=setup(tmp_path)
    monkeypatch.setattr("resumable_upload.shutil.disk_usage", lambda _:SimpleNamespace(free=5*1024**3+len(payload)-1))
    with app.test_client() as c:
        assert c.post("/montara/uploads",json=body_for(1,wav,payload)).status_code==507
        assert not list((tmp_path/"data").rglob("upload.json"))
