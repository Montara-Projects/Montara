import json
from pathlib import Path
import pytest
from audio_project_store import AudioProjects,AudioProjectConflict,AudioProjectError


def test_create_upsert_list_and_survive_restart(tmp_path):
    root=tmp_path/'ownerA'
    store=AudioProjects(root)
    sources=[str(root/'Uploads'/'kick.wav'),str(root/'Uploads'/'vocal.wav')]
    first=store.save(name='My Song',sources=sources,controls={'vocal.wav':{'fader_db':-2.5}},track_types={'vocal.wav':{'type':'vocal','chosen':True}})
    second=store.save(name='my song',sources=sources,controls={'vocal.wav':{'fader_db':-4.0}})
    assert first['id']==second['id'] and second['revision']==2
    assert len(AudioProjects(root).list())==1
    assert AudioProjects(root).get(first['id'])['controls']['vocal.wav']['fader_db']==-4
    assert len(list((root/'AudioProjects').glob('*.json')))==1
    assert (root/'AudioProjects'/f"{first['id']}.json").stat().st_mode & 0o077 == 0


def test_isolate_owners_and_never_remove_media(tmp_path):
    a=AudioProjects(tmp_path/'a');b=AudioProjects(tmp_path/'b')
    media=tmp_path/'a'/'song.wav';media.write_bytes(b'private')
    saved=a.save(name='Song',sources=[str(media)],controls={})
    assert b.list()==[]
    with pytest.raises(AudioProjectError):b.get(saved['id'])
    a.delete(saved['id'])
    assert media.read_bytes()==b'private'
    assert a.list()==[]


def test_revision_conflict_does_not_overwrite(tmp_path):
    store=AudioProjects(tmp_path)
    first=store.save(name='Song',sources=['/source.wav'],controls={'source.wav':{'fader_db':0}})
    changed=store.save(name='Song',sources=['/source.wav'],controls={'source.wav':{'fader_db':5}},project_id=first['id'],revision=1)
    with pytest.raises(AudioProjectConflict):store.save(name='Song',sources=['/source.wav'],controls={'source.wav':{'fader_db':-10}},project_id=first['id'],revision=1)
    assert store.get(first['id'])['controls']['source.wav']['fader_db']==5
    with pytest.raises(AudioProjectConflict):store.delete(first['id'],revision=1)
    assert store.get(first['id'])['revision']==changed['revision']


def test_untrusted_identifiers_and_invalid_json(tmp_path):
    store=AudioProjects(tmp_path)
    with pytest.raises(AudioProjectError):store.get('../../outside')
    with pytest.raises(AudioProjectError):store.get('x'*32)
    with pytest.raises(AudioProjectError):store.save(name=' ',sources=['x'],controls={})
    with pytest.raises(AudioProjectError):store.save(name='Good',sources=['x','x'],controls={})
    with pytest.raises(AudioProjectError):store.save(name='Good',sources=['x'],controls={'a':float('nan')})
    assert store.list()==[]


def test_reject_script_strings_in_audio_fx_and_eq(tmp_path):
    store=AudioProjects(tmp_path)
    with pytest.raises(AudioProjectError):
        store.save(name='Song',sources=['/Vocal.wav'],controls={'Vocal.wav':{'fx':{'delay':{'enabled':True,'amount':'<svg/onload=alert(1)>'}}}})
    with pytest.raises(AudioProjectError):
        store.save(name='Song',sources=['/Vocal.wav'],controls={'Vocal.wav':{'eq':{'mid':{'db':float('inf')}}}})
    assert store.list()==[]


def test_pan_is_persisted_and_out_of_range_rejected(tmp_path):
    store=AudioProjects(tmp_path)
    entry=store.save(name='Panning',sources=['/Bass.wav'],controls={'Bass.wav':{'pan':-0.35}})
    assert store.get(entry['id'])['controls']['Bass.wav']['pan']==-0.35
    with pytest.raises(AudioProjectError):store.save(name='Panning',sources=['/Bass.wav'],controls={'Bass.wav':{'pan':1.1}},project_id=entry['id'])
