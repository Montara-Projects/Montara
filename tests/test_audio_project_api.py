import json
from pathlib import Path
from flask import Flask
from audio_project_api import register_audio_project_api


def setup(tmp_path):
    root=tmp_path/'owner';root.mkdir()
    folder=root/'Uploads'/('a'*32);folder.mkdir(parents=True)
    audio=folder/'Kick.wav';audio.write_bytes(b'fixture')
    (folder/'upload.json').write_text(json.dumps({'name':'Kick.wav','complete':True}))
    app=Flask(__name__)
    register_audio_project_api(app,root,tmp_path/'fixtures',remote=True)
    return app.test_client(),audio,root


def test_api_create_persist_reopen_save_again_and_delete(tmp_path):
    client,audio,root=setup(tmp_path)
    body={'name':'Jam One','sources':[str(audio)],'track_types':{'Kick.wav':{'type':'kick','side':'','chosen':True}},'controls':{'Kick.wav':{'fader_db':-2,'fx':{'delay':{'enabled':True,'amount':30}}}}}
    first=client.post('/montara/mix/projects',json=body)
    assert first.status_code==200,first.json
    identifier=first.json['id']
    assert client.get('/montara/mix/projects').json['projects'][0]['kind']=='audio'
    reopened=client.get('/montara/mix/projects/'+identifier)
    assert reopened.status_code==200
    assert reopened.json['controls']==body['controls']
    assert reopened.json['track_types']['kick']['type']=='kick'
    body.update(name='jam one',controls={'Kick.wav':{'fader_db':-4}},project_id=identifier,revision=1)
    changed=client.post('/montara/mix/projects',json=body)
    assert changed.status_code==200 and changed.json['revision']==2
    assert len(client.get('/montara/mix/projects').json['projects'])==1
    assert client.post('/montara/mix/projects/'+identifier+'/delete',json={}).status_code==400
    assert client.post('/montara/mix/projects/'+identifier+'/delete',json={'revision':1,'keep_exports':True}).status_code==409
    assert client.post('/montara/mix/projects/'+identifier+'/delete',json={'revision':2,'keep_exports':True}).status_code==200
    assert audio.is_file()
    assert client.get('/montara/mix/projects').json['projects']==[]


def test_missing_sources_and_wrong_owner_are_not_exposed(tmp_path):
    client,audio,root=setup(tmp_path)
    foreign=tmp_path/'other'/'x.wav';foreign.parent.mkdir();foreign.write_bytes(b'private')
    body={'name':'A','sources':[str(foreign)],'controls':{}}
    assert client.post('/montara/mix/projects',json=body).status_code==400
    body['sources']=[str(audio)]
    first=client.post('/montara/mix/projects',json=body)
    assert first.status_code==200
    id=first.json['id']
    audio.unlink()
    assert client.get('/montara/mix/projects/'+id).status_code==409
    assert len(client.get('/montara/mix/projects').json['projects'])==1
    client_other=Flask('other')
    another=tmp_path/'foreign-owner';another.mkdir()
    register_audio_project_api(client_other,another,tmp_path/'fixtures',remote=True)
    assert client_other.test_client().get('/montara/mix/projects/'+id).status_code==404
