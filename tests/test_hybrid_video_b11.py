"""B11 lab contracts: bounded REAL audio, owner gate, no full guide, fail-closed sync.

These cases are intentionally isolated: they do NOT assert that Stage browser,
production Owner, Engine Wizard or Chema's 13-stem Mac session use this code.
"""
from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import wave

import pytest

from hybrid_video_b11 import (
    B11Denied, Window, load_session, prepare_short_guide,
    project_engine_evidence, stage_contract_plan, fail_closed_fallback,
)

SID = "abcdef012345"


def wav(path, seconds=4, rate=8000):
    path.parent.mkdir(parents=True, exist_ok=True)
    count = int(seconds * rate)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        samples = (int(9000 * math.sin(2 * math.pi * 440 * n / rate))
                   for n in range(count))
        out.writeframes(struct.pack("<" + "h" * count, *samples))
    return path


@pytest.fixture
def case(tmp_path):
    root = tmp_path / "private"
    session = root / "Sessions" / SID
    session.mkdir(parents=True)
    first = wav(root / "uploaded" / "guitar.wav")
    second = wav(root / "uploaded" / "perc.wav")
    data = dict(id=SID, video_excerpt=True, status="review", duration=4.,
                tracks=[
                    dict(path=str(first), offset=0., duration=4., samplerate=8000),
                    dict(path=str(second), offset=0., duration=4., samplerate=8000),
                ])
    (session / "session.json").write_text(json.dumps(data), encoding="utf-8")
    def owner(principal, ident):
        return principal == "fer" and ident == SID
    return root, session, first, second, owner


def _good(offset=.25, duration=1.2):
    return dict(source_path="/private/never-publish.mp4",
                offset_sec=offset, duration_sec=duration,
                confidence=32.5, no_audio=False, low_confidence=False,
                unstable_sync=False,
                verification=dict(checked=True, unstable_sync=False,
                                  consensus_count=3))


def test_b11_1_authorized_source_manifest_has_safe_identity(case):
    root, session, first, second, owner = case
    item = load_session(root, SID, "fer", owner)
    public = item.public()
    assert public["session_id"] == SID
    assert public["track_count"] == 2
    assert public["global_duration_sec"] == 4
    assert public["stage_ready"] is False
    assert str(first) not in json.dumps(public)
    assert "guitar.wav" not in json.dumps(public)
    with pytest.raises(B11Denied, match="owner_denied"):
        load_session(root, SID, "chema", owner)
    with pytest.raises(B11Denied, match="owner_authorization_required"):
        load_session(root, SID, "fer", None)
    with pytest.raises(B11Denied, match="invalid_session_id"):
        load_session(root, "../etc/passwd", "fer", owner)


def test_b11_1_audio_only_and_foreign_file_are_denied(case, tmp_path):
    root, session, first, second, owner = case
    manifest = session / "session.json"
    data = json.loads(manifest.read_text())
    data["video_excerpt"] = False
    manifest.write_text(json.dumps(data))
    with pytest.raises(B11Denied, match="audio_only_pipeline_unchanged"):
        load_session(root, SID, "fer", owner)
    data["video_excerpt"] = True
    data["tracks"][0]["path"] = str(wav(tmp_path / "foreign" / "evil.wav"))
    manifest.write_text(json.dumps(data))
    with pytest.raises(B11Denied, match="foreign_track_source"):
        load_session(root, SID, "fer", owner)


@pytest.mark.parametrize("win", [
    Window(-.5, 1), Window(0, 5), Window(2, 2.2),
    Window(float("nan"), 1), Window(.001, 2),
    Window(0, float("inf")),
])
def test_b11_1_invalid_windows_fail_closed(case, win):
    root, session, first, second, owner = case
    with pytest.raises(B11Denied):
        prepare_short_guide(root, SID, "fer", owner, win)


def test_b11_2_real_bounded_ogg_not_full_guide(case, monkeypatch):
    root, session, first, second, owner = case
    import mixer_adapter.session as mixer_session
    def no_full(*args, **kwargs):
        raise AssertionError("B11 must not request listen-all.webm")
    monkeypatch.setattr(mixer_session, "session_listen", no_full)
    guide = prepare_short_guide(root, SID, "fer", owner, Window(.5, 2.5))
    assert guide.path.is_file()
    assert guide.path.stat().st_size > 0
    assert guide.path.suffix == ".ogg"
    assert "b11-cache" in str(guide.path)
    assert not (session / "listen-all.webm").exists()
    public = guide.public()
    assert public["guide_kind"] == "bounded_acoustic_reference_not_master"
    assert public["stage_ready"] is False
    assert str(guide.path) not in json.dumps(public)
    assert "uploaded" not in json.dumps(public)
    second_call = prepare_short_guide(root, SID, "fer", owner, Window(.5, 2.5))
    assert second_call.path == guide.path


def test_b11_2_recipe_source_change_invalidates_versioned_cache(case, monkeypatch):
    root, session, first, second, owner = case
    a = prepare_short_guide(root, SID, "fer", owner, Window(0, 2))
    # A modified upload may retain its file size. Its mtime must still
    # invalidate this non-cryptographic cache identity.
    stat = first.stat()
    os.utime(first, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000))
    b = prepare_short_guide(root, SID, "fer", owner, Window(0, 2))
    assert b.session.recipe_id != a.session.recipe_id
    assert b.path != a.path
    assert a.path.exists() and b.path.exists()


def test_b11_3_engine_projection_preserves_global_gaps_two_cameras(case):
    root, session, first, second, owner = case
    guide = prepare_short_guide(root, SID, "fer", owner, Window(.5, 3))
    camera_a = _good(.25, 2)
    camera_a["offset_ranges"] = [
        dict(offset_sec=.25, clip_start_sec=0, clip_end_sec=.5),
        dict(offset_sec=1.0, clip_start_sec=1., clip_end_sec=1.5),
    ]
    camera_b = _good(.4, 1.4)
    projected = project_engine_evidence(
        guide, {"camera_360": camera_a, "camera_phone": camera_b},
        ["camera_360", "camera_phone"])
    assert projected["global_duration_sec"] == 4
    assert projected["guide_window"]["start_sec"] == .5
    assert projected["projected_clips"]["camera_360"]["offset_sec"] == .75
    assert [r["offset_sec"] for r in projected["projected_clips"]["camera_360"]["offset_ranges"]] == [.75, 1.5]
    assert projected["projected_clips"]["camera_360"]["coverage_spans_global"] == [
        (.75, 1.25), (2.5, 3.)
    ]
    assert projected["projected_clips"]["camera_phone"]["offset_sec"] == .9
    assert "/private/" not in json.dumps(projected)
    assert projected["stage_ready"] is False
    plan = stage_contract_plan(projected, selected_song=dict(start=1., end=2.))
    assert plan["selected_song_global"] == dict(start=1., end=2.)
    assert plan["fallback"] == "legacy_full_guide_engine"
    assert plan["stage_ready"] is False


@pytest.mark.parametrize("mutation, reason", [
    ({"confidence": 5.9}, "unproven_engine_sync"),
    ({"low_confidence": True}, "unproven_engine_sync"),
    ({"unstable_sync": True}, "unproven_engine_sync"),
    ({"no_audio": True}, "unproven_engine_sync"),
    ({"verification": {"checked": False, "unstable_sync": False,
                       "consensus_count": 3}}, "unproven_engine_sync"),
    ({"verification": {"checked": True, "unstable_sync": False,
                       "consensus_count": 1}}, "unproven_engine_sync"),
    ({"offset_sec": -100}, "no_global_coverage"),
    ({"offset_ranges": [{"offset_sec": 0, "clip_start_sec": 1.5,
                         "clip_end_sec": .5}]}, "invalid_offset_ranges"),
])
def test_b11_3_rejects_unproven_or_invalid_camera(case, mutation, reason):
    root, session, first, second, owner = case
    guide = prepare_short_guide(root, SID, "fer", owner, Window(.5, 3.))
    bad = dict(_good(), **mutation)
    with pytest.raises(B11Denied, match=reason):
        project_engine_evidence(guide, {"cam": bad}, ["cam"])
    fail = fail_closed_fallback(reason)
    assert fail["fallback_required"] is True
    assert fail["stage_ready"] is False


def test_b11_3_two_camera_atomic_and_negative_offset_handling(case):
    root, session, first, second, owner = case
    guide = prepare_short_guide(root, SID, "fer", owner, Window(1., 3.))
    cam = _good(-.7, 1.5)  # global offset .3; starts before crop
    out = project_engine_evidence(guide, {"cam": cam}, ["cam"])
    assert out["projected_clips"]["cam"]["offset_sec"] == pytest.approx(.3)
    with pytest.raises(B11Denied, match="missing_or_unexpected_camera"):
        project_engine_evidence(guide, {"cam": cam}, ["cam", "other"])
    with pytest.raises(B11Denied, match="unproven_engine_sync"):
        project_engine_evidence(guide, {"cam": cam, "other": dict(_good(), confidence=0)},
                                ["cam", "other"])


def test_b11_4_not_ready_without_actual_stage_adapter(case):
    root, session, first, second, owner = case
    guide = prepare_short_guide(root, SID, "fer", owner, Window(.5, 3.))
    out = project_engine_evidence(guide, {"cam": _good()}, ["cam"])
    plan = stage_contract_plan(out, selected_song={"start": 1., "end": 2.})
    assert plan["stage_ready"] is False
    assert any("Wizard" in item or "wizard" in item.lower()
               for item in plan["required_adapters"])
    with pytest.raises(B11Denied, match="invalid_global_song"):
        stage_contract_plan(out, selected_song={"start": 2., "end": 5.})
    with pytest.raises(B11Denied, match="no_song_camera_coverage"):
        stage_contract_plan(out, selected_song={"start": 3., "end": 3.5})


def test_b11_5_no_http_route_or_original_modification(case):
    root, session, first, second, owner = case
    before = [x.read_bytes() for x in (first, second)]
    guide = prepare_short_guide(root, SID, "fer", owner, Window(.5, 2.5))
    assert [x.read_bytes() for x in (first, second)] == before
    # Lab module deliberately has no Flask registration or production endpoint.
    import hybrid_video_b11 as lab
    assert not hasattr(lab, "register_full_session")
    assert not hasattr(lab, "register_blueprint")
    assert not hasattr(lab, "create_public_route")
    assert not (session / "listen-all.webm").exists()


def test_b11_1_real_owner_session_csrf_and_registry_binding(case, tmp_path):
    from urano.session_auth import SessionStore
    from hybrid_video_b11 import make_owner_csrf_guard
    root, session, first, second, owner = case
    session_store = SessionStore(tmp_path / "sessions.sqlite3")
    creds = session_store.issue("verified-fer-owner")
    bound_owner = {SID: "verified-fer-owner"}
    guard = make_owner_csrf_guard(session_store, bound_owner.get)
    principal = {"token": creds.token, "csrf": creds.csrf}
    assert load_session(root, SID, principal, guard).session_id == SID
    with pytest.raises(B11Denied, match="owner_denied"):
        load_session(root, SID, {"token": creds.token, "csrf": "0" * 64}, guard)
    bound_owner[SID] = "other-owner"
    with pytest.raises(B11Denied, match="owner_denied"):
        load_session(root, SID, principal, guard)
    bound_owner[SID] = "verified-fer-owner"
    rotated = session_store.rotate_csrf(creds.token)
    assert rotated
    with pytest.raises(B11Denied, match="owner_denied"):
        load_session(root, SID, principal, guard)
    assert load_session(root, SID,
        {"token": creds.token, "csrf": rotated}, guard).session_id == SID
    session_store.revoke(creds.token)
    with pytest.raises(B11Denied, match="owner_denied"):
        load_session(root, SID,
            {"token": creds.token, "csrf": rotated}, guard)


def test_b11_5_rejects_symlinked_lab_cache(case, tmp_path):
    root, session, first, second, owner = case
    outside = tmp_path / "outside"
    outside.mkdir()
    (session / "b11-cache").symlink_to(outside, target_is_directory=True)
    with pytest.raises(B11Denied, match="unsafe_lab_cache"):
        prepare_short_guide(root, SID, "fer", owner, Window(.5, 2.5))
    assert not list(outside.iterdir())


def test_b11_5_detects_source_change_during_generation(case, monkeypatch):
    root, session, first, second, owner = case
    import mixer_adapter.session as mixer_session
    original = mixer_session.listen_range
    def changed(work, start, end):
        result = original(work, start, end)
        st = first.stat()
        os.utime(first, ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000))
        return result
    monkeypatch.setattr(mixer_session, "listen_range", changed)
    with pytest.raises(B11Denied, match="source_changed_during_preparation"):
        prepare_short_guide(root, SID, "fer", owner, Window(.5, 2.5))


def test_b11_3_trusted_engine_seam_invokes_only_bounded_guide(case):
    from hybrid_video_b11 import run_trusted_engine_window
    root, session, first, second, owner = case
    guide = prepare_short_guide(root, SID, "fer", owner, Window(.5, 3.))
    invoked = []
    def actual_engine_adapter_to_be_supplied_by_owner(path, ids, origin):
        invoked.append((path, ids, origin))
        assert path.suffix == ".ogg"
        assert "b11-cache" in str(path)
        assert origin == .5
        return {"cam": _good()}
    result = run_trusted_engine_window(
        guide, ["cam"], actual_engine_adapter_to_be_supplied_by_owner)
    assert len(invoked) == 1
    assert result["stage_ready"] is False
    with pytest.raises(B11Denied, match="trusted_engine_runner_required"):
        run_trusted_engine_window(guide, ["cam"], None)
