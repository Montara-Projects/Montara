import pytest
import numpy as np
import soundfile as sf
from mixer_adapter.single_song import validate_pans,SingleSongMix
from mixer_adapter import single_song
from pathlib import Path

def test_pan_input_validation():
    assert validate_pans({"voice.wav":-.8},["voice.wav"])=={"voice.wav":-.8}
    for value in (-1.1,1.1,True,float("nan"),None,"left"):
        with pytest.raises(ValueError):validate_pans({"voice.wav":value},["voice.wav"])
    with pytest.raises(ValueError):validate_pans({"other.wav":.8},["voice.wav"])

def test_pan_actual_dsp_and_cleanup(tmp_path):
    tracks=tmp_path/"tracks";tracks.mkdir()
    rate=44100
    t=np.arange(rate*4)/rate
    tone=(.1*np.sin(2*np.pi*440*t)*np.minimum(1,t*10)).astype("float32")
    sf.write(tracks/"Guitar.wav",tone,rate,subtype="FLOAT")
    job=SingleSongMix(tracks,tmp_path/"job")
    job.analyze()
    original=job.pipeline.enforced_pan
    left=job.render({},tmp_path/"left.mp3",effects={},pans={"Guitar.wav":-1.})
    assert job.pipeline.enforced_pan is original
    right=job.render({},tmp_path/"right.mp3",effects={},pans={"Guitar.wav":1.})
    assert job.pipeline.enforced_pan is original
    a,_=sf.read(left,always_2d=True);b,_=sf.read(right,always_2d=True)
    rms=lambda x: np.sqrt(np.mean(x*x,axis=0))
    x,y=rms(a),rms(b)
    print("actual left/right RMS",x,y,flush=True)
    assert x[0]>4*x[1] and y[1]>4*y[0]
