"""Regression: switching FX on must not change a track's channel/pan gain."""
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mixer_adapter.single_song import SingleSongMix


@pytest.mark.parametrize("channels", [1, 2])
@pytest.mark.parametrize("effect", ["reverb", "delay"])
def test_effect_preserves_dry_level_and_channel_layout(tmp_path, channels, effect):
    tracks = tmp_path / "tracks"
    tracks.mkdir()
    sr = 44100
    tone = (.1 * np.sin(2 * np.pi * 440 * np.arange(sr) / sr)).astype("float32")
    dry = tone[:, None] if channels == 1 else np.column_stack((tone, .3 * tone))
    sf.write(tracks / "vocal.wav", dry, sr, subtype="FLOAT")
    job = SingleSongMix(tracks, tmp_path / "job")
    job._register()
    wet, _ = sf.read(job.effect_track("vocal.wav", effect), always_2d=True)
    assert wet.shape == dry.shape
    stem = job._effect_stems({"vocal.wav": {effect: 1e-7}})[0]
    audio, _ = sf.read(stem.path, always_2d=True)
    assert stem.channels == channels
    before = job.pipeline.apply_stereo_pan(dry[:, 0] if channels == 1 else dry, .25)
    after = job.pipeline.apply_stereo_pan(audio[:, 0] if channels == 1 else audio, .25)
    delta_db = 20 * np.log10(np.sqrt(np.mean(after ** 2)) / np.sqrt(np.mean(before ** 2)))
    assert abs(delta_db) < .001
    stem = job._effect_stems({"vocal.wav": {effect: .65}})[0]
    audio, _ = sf.read(stem.path, always_2d=True)
    np.testing.assert_allclose(audio, dry + .65 * wet, atol=1e-7)


def test_delay_uses_detected_song_bpm_instead_of_fixed_90(tmp_path, monkeypatch):
    """Wet preview FX and final mix share the same DSP/cache key."""
    tracks = tmp_path / "tracks"
    tracks.mkdir()
    rate = 22050
    count = rate * 6
    pulses = np.zeros(count, dtype=np.float32)
    # Kick on every beat, 120 BPM, with short energy transients.
    for start in range(0, count, rate // 2):
        pulses[start:start+220] = 0.4 * np.hanning(220)
    sf.write(tracks / "Kick.wav", pulses, rate, subtype="FLOAT")
    sf.write(tracks / "Vocal.wav", (.1*np.sin(2*np.pi*220*np.arange(count)/rate)).astype("float32"), rate, subtype="FLOAT")
    job = SingleSongMix(tracks, tmp_path / "job")
    job._register()
    observed = []
    base = job.pipeline.slap_delay_streaming
    def spy(buffer, sr, bpm, memory):
        observed.append(bpm)
        return base(buffer, sr, bpm, memory)
    monkeypatch.setattr(job.pipeline, 'slap_delay_streaming', spy)
    file = job.effect_track('Vocal.wav', 'delay')
    assert file.is_file()
    assert observed
    tempo = observed[0]
    assert tempo != 90.0 and 108 <= tempo <= 132
    assert all(v == tempo for v in observed)
    previous = len(observed)
    assert job.effect_track('Vocal.wav','delay') == file
    assert len(observed) == previous
    assert 0 <= job._song_tempo_cache[1] <= 1


def test_delay_fallback_when_no_rhythm_is_conservative(tmp_path, monkeypatch):
    tracks = tmp_path / 'tracks'
    tracks.mkdir()
    rate = 22050
    sf.write(tracks/'Vocal.wav',np.zeros(rate*2,dtype='float32'),rate,subtype='FLOAT')
    job=SingleSongMix(tracks,tmp_path/'job')
    job._register()
    assert job._song_tempo()==(90.0,0.0)
    result=job.effect_track('Vocal.wav','delay')
    assert result.is_file()
