"""Remote Mixer source boundaries: isolated unit regressions, no media needed."""
import json
from pathlib import Path

import pytest

from mixer_adapter.source_access import resolve_mix_sources


def _registered(tmp_path, name="bass.wav", complete=True):
    work = tmp_path / "Uploads" / ("a" * 32)
    work.mkdir(parents=True)
    (work / name).write_bytes(b"test")
    (work / "upload.json").write_text(json.dumps({"name": name, "complete": complete}))
    return work / name


def _resolve(paths, tmp_path, remote=True):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir(exist_ok=True)
    return resolve_mix_sources(paths, tmp_path, fixtures, remote=remote)


def test_remote_registered_complete_upload_is_allowed(tmp_path):
    source = _registered(tmp_path)
    assert _resolve([str(source)], tmp_path) == [source.resolve()]


def test_remote_unregistered_private_file_is_rejected(tmp_path):
    private = tmp_path / "private.wav"
    private.write_bytes(b"private")
    with pytest.raises(ValueError, match="registered"):
        _resolve([str(private)], tmp_path)


def test_local_development_path_remains_supported(tmp_path):
    private = tmp_path / "my-music.wav"
    private.write_bytes(b"music")
    assert _resolve([str(private)], tmp_path, remote=False) == [private.resolve()]


def test_remote_unfinished_upload_is_rejected(tmp_path):
    source = _registered(tmp_path, complete=False)
    with pytest.raises(ValueError, match="completed"):
        _resolve([str(source)], tmp_path)


def test_remote_modified_upload_record_is_rejected(tmp_path):
    source = _registered(tmp_path)
    (source.parent / "upload.json").write_text(json.dumps({"name": "other.wav", "complete": True}))
    with pytest.raises(ValueError, match="record"):
        _resolve([str(source)], tmp_path)


def test_remote_symlink_escape_is_rejected(tmp_path):
    private = tmp_path / "secret.wav"
    private.write_bytes(b"secret")
    folder = tmp_path / "Uploads" / ("a" * 32)
    folder.mkdir(parents=True)
    shortcut = folder / "bass.wav"
    shortcut.symlink_to(private)
    (folder / "upload.json").write_text(json.dumps({"name": "bass.wav", "complete": True}))
    with pytest.raises(ValueError, match="registered"):
        _resolve([str(shortcut)], tmp_path)


def test_duplicate_file_names_rejected_before_linking(tmp_path):
    first = tmp_path / "first" / "bass.wav"
    second = tmp_path / "second" / "bass.wav"
    for path in (first, second):
        path.parent.mkdir()
        path.write_bytes(b"test")
    with pytest.raises(ValueError, match="Duplicate"):
        _resolve([str(first), str(second)], tmp_path, remote=False)


def test_remote_bundled_fixture_is_accepted(tmp_path):
    source = tmp_path / "fixtures" / "example.wav"
    source.parent.mkdir()
    source.write_bytes(b"music")
    assert _resolve([str(source)], tmp_path) == [source.resolve()]


def test_invalid_track_payload_is_rejected(tmp_path):
    for payload in (None, [], ["missing.wav"], [4], [""]):
        with pytest.raises(ValueError):
            _resolve(payload, tmp_path)



def _session_preview(tmp_path, *, session_id="b" * 12, song=2, name="bass.wav"):
    work = tmp_path / "Sessions" / session_id
    folder = work / "preview" / str(song) / "tracks"
    folder.mkdir(parents=True)
    track = folder / name
    track.write_bytes(b"RIFF test track")
    data = {"id": session_id, "status": "ready", "preview_song": song,
            "preview_tracks": [str(track)]}
    manifest = work / "session.json"
    manifest.write_text(json.dumps(data))
    return track, manifest


def test_private_remote_current_owner_session_preview_is_allowed(tmp_path):
    track, _ = _session_preview(tmp_path)
    assert _resolve([str(track)], tmp_path) == [track.resolve()]


def test_private_remote_15_registered_preview_tracks_pass(tmp_path):
    track, manifest = _session_preview(tmp_path)
    sources = []
    for n in range(15):
        p = track.with_name(f"stem-{n}.wav")
        p.write_bytes(b"RIFF synthetic")
        sources.append(str(p))
    data = json.loads(manifest.read_text())
    data["preview_tracks"] = sources
    manifest.write_text(json.dumps(data))
    assert _resolve(sources, tmp_path) == [Path(p).resolve() for p in sources]


def test_private_remote_stale_or_different_song_preview_is_rejected(tmp_path):
    track, manifest = _session_preview(tmp_path)
    for key, wrong in (("status", "preparing"), ("preview_song", 3),
                       ("id", "a" * 12), ("preview_tracks", [])):
        previous = manifest.read_text()
        record = json.loads(previous)
        record[key] = wrong
        manifest.write_text(json.dumps(record))
        with pytest.raises(ValueError, match="registered"):
            _resolve([str(track)], tmp_path)
        manifest.write_text(previous)


def test_private_remote_unlisted_file_same_session_is_rejected(tmp_path):
    track, _ = _session_preview(tmp_path)
    rogue = track.with_name("rogue.wav")
    rogue.write_bytes(b"rogue")
    with pytest.raises(ValueError, match="registered"):
        _resolve([str(rogue)], tmp_path)


def test_private_remote_cross_owner_session_preview_rejected(tmp_path):
    track, _ = _session_preview(tmp_path)
    other_owner = tmp_path.parent / "foreign-owner"
    other_owner.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="registered"):
        _resolve([str(track)], other_owner)


def test_private_remote_session_preview_symlink_escape_rejected(tmp_path):
    track, manifest = _session_preview(tmp_path)
    linked = track.with_name("linked.wav")
    linked.symlink_to(track)
    record = json.loads(manifest.read_text())
    record["preview_tracks"] = [str(linked)]
    manifest.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="registered"):
        _resolve([str(linked)], tmp_path)


def test_private_remote_session_preview_fails_closed_on_bad_manifest(tmp_path):
    track, manifest = _session_preview(tmp_path)
    for content in ("{}", "{", " " * 2_000_002):
        manifest.write_text(content)
        with pytest.raises(ValueError, match="registered"):
            _resolve([str(track)], tmp_path)


def test_private_remote_session_preview_outside_allowed_folder_rejected(tmp_path):
    track, manifest = _session_preview(tmp_path)
    wrong = track.parent.parent / "other" / track.name
    wrong.parent.mkdir()
    wrong.write_bytes(b"not an active preview")
    record = json.loads(manifest.read_text())
    record["preview_tracks"] = [str(wrong)]
    manifest.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="registered"):
        _resolve([str(wrong)], tmp_path)
