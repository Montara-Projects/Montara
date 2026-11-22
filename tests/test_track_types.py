"""Track types the person chooses: validation, mixer roles, stereo sides, music never muted as noise."""
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import track_types
from mixer_adapter.single_song import SingleSongMix


def test_validate_keys_by_track_and_drops_unknown_types():
    types = track_types.validate({'Bass.wav.opus': {'type': 'bass', 'chosen': True, 'side': 'X'},
                                  'Robi.wav': {'type': 'podcast_voice'}, 'Bad.wav': {'type': 'kazoo'}, 'x': 'bass'})
    assert types == {'bass': {'type': 'bass', 'side': '', 'chosen': True},
                     'robi': {'type': 'podcast_voice', 'side': '', 'chosen': False}}
    files = track_types.for_files(types, ['/s/Bass.wav', '/s/Robi.wav', '/s/Keys.wav'])
    assert set(files) == {'Bass.wav', 'Robi.wav'}
    assert track_types.noise_exempt(files) == {'Bass.wav'}  # only what the person chose


def test_roles_and_stereo_sides():
    types = {'Keys L.wav': {'type': 'keys', 'side': 'L', 'chosen': True},
             'Keys R.wav': {'type': 'keys', 'side': 'R', 'chosen': True},
             'Narr.wav': {'type': 'narration', 'side': '', 'chosen': True}}
    assert track_types.mixer_roles(types) == {'Keys L.wav': 'keys_l', 'Keys R.wav': 'keys_r', 'Narr.wav': 'vocal'}
    assert track_types.stereo_sides(types) == {'Keys L.wav': 'L', 'Keys R.wav': 'R'}


def test_page_list_matches_server_list():
    js = (ROOT / 'web' / 'track-types.js').read_text()
    block = js[js.index('const TYPES = ['):js.index('];', js.index('const TYPES = ['))]
    assert set(re.findall(r"\['([a-z_]+)',", block)) == set(track_types.TYPES)


def test_single_song_mixer_uses_the_chosen_role_and_side(tmp_path):
    tracks = tmp_path / 'tracks'; tracks.mkdir()
    sr = 22050
    tone = (.1 * np.sin(2 * np.pi * 220 * np.arange(sr * 2) / sr)).astype('float32')
    for name in ('Robi.wav', 'Novation.wav'):
        sf.write(tracks / name, tone, sr, subtype='FLOAT')
    types = track_types.validate({'Robi.wav': {'type': 'bass', 'chosen': True}, 'Novation.wav': {'type': 'strings', 'side': 'R', 'chosen': True}})
    job = SingleSongMix(tracks, tmp_path / 'job', track_types=types)
    state = job._register()
    roles = {s.path.name: s.role for s in state['stems']}
    assert roles == {'Robi.wav': 'bass', 'Novation.wav': 'synth'}
    assert job.pipeline.NOISE_EXEMPT_STEMS == {'Robi.wav', 'Novation.wav'}
    assert job.pipeline.enforced_pan('synth', 'Novation') == 1.0
    # Another job without types must not inherit these globals.
    other = SingleSongMix(tracks, tmp_path / 'other')
    other._register()
    assert other.pipeline.NOISE_EXEMPT_STEMS == set() and other.pipeline.STEREO_SIDES == {}


def test_every_type_has_a_dictionary_entry_with_the_same_role():
    sys.path.insert(0, str(ROOT / 'mixer'))
    import instrument_dictionary
    for key, (_label, role) in track_types.TYPES.items():
        assert instrument_dictionary.INSTRUMENTS[track_types.PRESET_ALIASES.get(key, key)]['role'] == role, key


def test_the_mixer_gets_the_instrument_of_each_track(tmp_path):
    tracks = tmp_path / 'tracks'; tracks.mkdir()
    sr = 44100
    sf.write(tracks / 'Host.wav', (.1 * np.sin(np.arange(sr) / 5)).astype('float32'), sr, subtype='FLOAT')
    job = SingleSongMix(tracks, tmp_path / 'job', track_types=track_types.validate({'Host.wav': {'type': 'podcast_voice', 'chosen': True}}))
    job._register()
    assert job.pipeline.STEM_INSTRUMENTS == {'Host.wav': 'podcast_voice'}
    assert job.pipeline.role_eq_bands('vocal', name='Host.wav')[0][2] == 80


def test_compact_preview_and_extracted_wav_share_instrument_and_stereo_choice():
    types=track_types.validate({'Mic.ogg':dict(type='keys',side='R',chosen=True)})
    assert track_types.for_files(types,['Mic.wav'])=={'Mic.wav':dict(type='keys',side='R',chosen=True)}
    assert track_types.mixer_roles(track_types.for_files(types,['Mic.wav']))=={'Mic.wav':'keys_r'}


def test_multivoice_roles_are_explicit_and_nondestructive():
    raw={
      'Singer One.wav': {'type':'vocal','chosen':True},
      'Singer Two.wav': {'type':'co_lead_vocal','chosen':True},
      'Harmony.wav': {'type':'backing_vocal','chosen':True},
      'Choir.wav': {'type':'choir','chosen':True},
      'Unknown.wav': {'type':'other','chosen':False},
    }
    selected=track_types.validate(raw)
    files=track_types.for_files(selected,list(raw))
    assert len(files)==5
    assert track_types.mixer_roles(files)=={name:'other' if name=='Unknown.wav' else 'vocal' for name in raw}
    assert track_types.PRESET_ALIASES['co_lead_vocal']=='vocal'
    assert track_types.PRESET_ALIASES['choir']=='backing_vocal'
    assert track_types.noise_exempt(files)==set(raw)-{'Unknown.wav'}

def test_manual_multivoice_type_matches_mixer_preset(tmp_path):
    tracks=tmp_path/'tracks';tracks.mkdir()
    sr=22050
    audio=(.05*np.sin(2*np.pi*220*np.arange(sr)/sr)).astype('float32')
    for name in ('Lead.wav','Second.wav','Choir.wav'):
        sf.write(tracks/name,audio,sr,subtype='FLOAT')
    types=track_types.validate({'Lead.wav':dict(type='vocal',chosen=True),
       'Second.wav':dict(type='co_lead_vocal',chosen=True),
       'Choir.wav':dict(type='choir',chosen=True)})
    job=SingleSongMix(tracks,tmp_path/'job',track_types=types)
    job._register()
    assert {s.path.name:s.role for s in job.state['stems']}=={n:'vocal' for n in ('Lead.wav','Second.wav','Choir.wav')}
    assert job.pipeline.STEM_INSTRUMENTS=={'Lead.wav':'vocal','Second.wav':'vocal','Choir.wav':'backing_vocal'}
