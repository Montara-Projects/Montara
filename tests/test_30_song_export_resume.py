"""Missing Companion audio leaves finished songs resumable, never fatal."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mixer_adapter import session as m


def test_original_timeout_keeps_two_finished_songs():
    from mixer_adapter import single_song
    with tempfile.TemporaryDirectory(prefix='30-song-test-') as tmp:
        work=Path(tmp)/'session'
        work.mkdir()
        songs=[dict(id=i,name=f'Track {i}',start=(i-1)*10.,end=i*10.,selected=True)
               for i in range(1,31)]
        data=dict(status='rendering',started_at=time.time(),duration=300,
                  songs=songs,tracks=[dict(file='bass.wav',offset=0,duration=300)],
                  previews={'bass.wav':{'name':'remote.wav'}},
                  settings={'faders':{},'mutes':{},'per_song':{}},track_types={},
                  empty_tracks=[])
        m.save(work/'session.json',data)
        (work/'exports').mkdir()
        (work/'results').mkdir()
        for song in songs[:2]:
            mp3=work/'exports'/f"song-{song['id']:03d}.mp3"
            mp3.write_bytes(b'ID3'+b'0'*5000)
            m.save(work/'results'/f"{song['id']}.json",dict(
                id=song['id'],start=song['start'],end=song['end'],
                name=song['name'],path=str(mp3),signature=m.render_signature(data,song)))
        def originals(d,work_arg,only_song):
            return [{'received':False}] if only_song>=3 else []
        with patch.object(single_song,'_load_mixer',return_value=(None,SimpleNamespace(PROGRESS_HOOK=None))),\
             patch.object(m,'local_results',return_value={}),\
             patch.object(m,'original_windows',side_effect=originals),\
             patch.object(m,'ORIGINALS_WAIT_SECONDS',-1),\
             patch.object(m.time,'sleep',return_value=None):
            m.execute(work,'render')
        result=m.read(work)
        assert result['status']=='partial',result
        assert len(result['results'])==2
        assert len(result['missing_originals'])==28
        assert [e['id'] for e in result['results']]==[1,2]
        assert 'waiting for original audio' in result['error']
        assert (work/'exports'/'song-001.mp3').is_file()
        assert (work/'exports'/'song-002.mp3').is_file()

def test_exactly_thirty_songs_allowed():
    songs=[dict(start=i*10.,end=(i+1)*10.,selected=True) for i in range(30)]
    assert len(m.validate_songs(songs,300))==30
    try:
        m.validate_songs(songs+[dict(start=300.,end=310.,selected=True)],310)
    except ValueError as error:
        assert '30' in str(error)
    else:
        raise AssertionError('31 songs should be rejected')


if __name__=='__main__':
    test_exactly_thirty_songs_allowed()
    test_original_timeout_keeps_two_finished_songs()
    print('THIRTY_SONG_PAUSE_RESUME_TEST_PASS')
