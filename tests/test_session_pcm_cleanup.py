"""Only finished, trusted server-side decoded PCM may be reclaimed."""
import json
from pathlib import Path

from mixer_adapter.session import original_key, release_finished_song_pcm, save


def test_cleanup_reclaims_verified_decoded_pcm_only(tmp_path):
    home=tmp_path/'Owner'
    work=home/'Sessions'/'abcdefabcdef'
    work.mkdir(parents=True)
    song={'id':3,'start':10.0,'end':20.0,'selected':True}
    data={'tracks':[{'file':'voice.wav','offset':0,'duration':30}],
          'previews':{'voice.wav':{'name':'original.wav'}},
          'songs':[song]}
    key=original_key('voice.wav',[10.0,20.0])
    originals=work/'originals'
    originals.mkdir()
    upload=home/'Uploads'/('a'*32)
    upload.mkdir(parents=True)
    wav=upload/'segment.wav'
    wav.write_bytes(b'RIFF'+b'x'*1024)
    save(upload/'upload.json',{'complete':True,'restored':'segment.wav'})
    save(originals/f'{key}.json',
         {'file':'voice.wav','window':[10.0,20.0],'start':10.0,'path':str(wav)})
    assert release_finished_song_pcm(work,data,song)==1028
    assert not wav.exists()
    assert (upload/'upload.json').is_file()
    assert (originals/f'{key}.json').is_file()


def test_cleanup_refuses_file_outside_owner_uploads(tmp_path):
    home=tmp_path/'Owner'
    work=home/'Sessions'/'abcdefabcdef'
    work.mkdir(parents=True)
    song={'id':3,'start':10.0,'end':20.0,'selected':True}
    data={'tracks':[{'file':'voice.wav','offset':0,'duration':30}],
          'previews':{'voice.wav':{'name':'original.wav'}},'songs':[song]}
    foreign=tmp_path/'foreign.wav'
    foreign.write_bytes(b'ORIGINAL')
    key=original_key('voice.wav',[10.0,20.0])
    originals=work/'originals'
    originals.mkdir()
    save(originals/f'{key}.json',
         {'file':'voice.wav','window':[10.0,20.0],'start':10.0,'path':str(foreign)})
    assert release_finished_song_pcm(work,data,song)==0
    assert foreign.read_bytes()==b'ORIGINAL'
