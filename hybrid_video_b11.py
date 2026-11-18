"""B11 isolated short-guide Stage contract. No routes, workers or production activation.

This module deliberately does not accept a browser-supplied filesystem path, and
does not replace the Stage wizard. A trusted Owner adapter must provide an
authorization callback and a server-selected window; without either it fails.
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Callable


VERSION = "fer-b11-hybrid-lab-v1"
SESSION_ID = re.compile(r"[a-f0-9]{12}\Z")
MAX_WINDOW_SEC = 3600.0
MAX_TRACKS = 128


class B11Denied(ValueError):
    """An explicit fail-closed contract rejection (not a raw path or exception)."""


def deny(reason):
    raise B11Denied(reason)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class Window:
    start_sec: float
    end_sec: float

    def validated(self, duration):
        if (not finite(self.start_sec) or not finite(self.end_sec)
                or self.start_sec < 0 or self.end_sec > duration
                or not .5 <= self.end_sec - self.start_sec <= MAX_WINDOW_SEC):
            deny("invalid_window")
        # Existing listen_range names cached audio with two decimal places.
        # Do not let distinct windows collide on the same cache filename.
        if (abs(self.start_sec - round(self.start_sec, 2)) > 1e-6
                or abs(self.end_sec - round(self.end_sec, 2)) > 1e-6):
            deny("noncanonical_window")
        return self


@dataclass(frozen=True)
class SessionEvidence:
    session_id: str
    duration_sec: float
    recipe_id: str
    work: Path
    tracks: tuple
    manifest: dict

    def public(self):
        return dict(version=VERSION, session_id=self.session_id,
                    global_duration_sec=self.duration_sec,
                    source_identity=self.recipe_id, recipe_version=VERSION,
                    track_count=len(self.tracks), stage_ready=False)


@dataclass(frozen=True)
class ShortGuide:
    session: SessionEvidence
    window: Window
    path: Path   # TRUSTED INTERNAL ONLY: never include in a public response.

    def public(self):
        return dict(self.session.public(), sync_window=dict(
            start_sec=self.window.start_sec, end_sec=self.window.end_sec),
            guide_identity=self.path.parent.parent.name,
            guide_kind="bounded_acoustic_reference_not_master",
            stage_ready=False)


def load_session(data_root, session_id, principal, authorize: Callable | None):
    """Resolve a session from server-owned data_root, after Owner authorization.

    authorize(principal, session_id) MUST consult the actual authenticated
    Owner/project registry in any later integration; no default permissive
    authorization exists. This module has NO HTTP endpoint.
    """
    if not callable(authorize):
        deny("owner_authorization_required")
    if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id):
        deny("invalid_session_id")
    if authorize(principal, session_id) is not True:
        deny("owner_denied")
    root = Path(data_root).resolve(strict=True)
    work = root / "Sessions" / session_id
    if work.is_symlink() or not work.is_dir():
        deny("session_missing")
    manifest_file = work / "session.json"
    if manifest_file.is_symlink() or not manifest_file.is_file():
        deny("session_missing")
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        deny("invalid_session_manifest")
    if not isinstance(data, dict) or data.get("id") != session_id:
        deny("invalid_session_manifest")
    if data.get("video_excerpt") is not True:
        deny("audio_only_pipeline_unchanged")
    if data.get("status") not in ("review", "detecting"):
        deny("session_not_ready_for_lab")
    duration = data.get("duration")
    if not finite(duration) or duration <= 0:
        deny("invalid_global_duration")
    tracks = data.get("tracks")
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= MAX_TRACKS:
        deny("invalid_track_manifest")
    trusted = []
    signatures = []
    for track in tracks:
        if not isinstance(track, dict) or not isinstance(track.get("path"), str):
            deny("invalid_track_manifest")
        source = Path(track["path"])
        if not source.is_absolute():
            deny("invalid_track_path")
        try:
            resolved = source.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                deny("foreign_track_source")
            stat = resolved.stat()
        except (OSError, RuntimeError):
            deny("missing_track_source")
        if (not finite(track.get("offset")) or track["offset"] < 0
                or not finite(track.get("duration")) or track["duration"] <= 0
                or not isinstance(track.get("samplerate"), int)
                or track["samplerate"] <= 0 or stat.st_size <= 0):
            deny("invalid_track_manifest")
        item = dict(track)
        item["path"] = str(resolved)
        trusted.append(item)
        # No user paths leave this method. stat identity is an INVALIDATION
        # hint, not cryptographic proof of original-media equivalence.
        signatures.append(dict(rel=str(resolved.relative_to(root)), size=stat.st_size,
                               mtime_ns=stat.st_mtime_ns, offset=track["offset"],
                               duration=track["duration"], rate=track["samplerate"]))
    payload = dict(session_id=session_id, duration=duration, tracks=signatures,
                   version=VERSION)
    recipe = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()[:24]
    return SessionEvidence(session_id, float(duration), recipe, work,
                           tuple(trusted), data)


def make_owner_csrf_guard(session_store, registered_session_owner):
    """Bridge to EXISTING SessionStore + a trusted session->owner binding.

    A browser cannot supply registered_session_owner; it must be resolved
    by an Owner-scoped catalog during future HTTP integration. No Origin or
    HTTP route is handled here: the Owner gateway must check both.
    """
    if not callable(registered_session_owner):
        deny("session_owner_registry_required")

    def authorized(credentials, session_id):
        if not isinstance(credentials, dict):
            return False
        token, csrf = credentials.get("token"), credentials.get("csrf")
        try:
            session = session_store.verify(token)
            if session is None or not session.matches_csrf(csrf):
                return False
            bound_owner = registered_session_owner(session_id)
            return (isinstance(bound_owner, str) and
                    bound_owner == session.owner_id)
        except (AttributeError, KeyError, TypeError, ValueError):
            return False
    return authorized


def _probe_audio(path, expected_sec):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=15, check=False)
    if result.returncode != 0:
        deny("invalid_guide_audio")
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        deny("invalid_guide_audio")
    if not math.isfinite(duration) or abs(duration - expected_sec) > .25:
        deny("guide_duration_mismatch")


def prepare_short_guide(data_root, session_id, principal, authorize, window: Window):
    """Use EXISTING bounded mixer listen_range, not session_listen/full guide."""
    session = load_session(data_root, session_id, principal, authorize)
    window.validated(session.duration_sec)
    # Versioned isolated cache prevents old listen_range names becoming hits for
    # changed source/offset/recipe. No existing listen-all.webm is touched.
    cache_root = session.work / "b11-cache"
    cache = cache_root / session.recipe_id
    if cache_root.is_symlink() or cache.is_symlink():
        deny("unsafe_lab_cache")
    cache.mkdir(parents=True, exist_ok=True)
    lock_file = cache / ".lock"
    if lock_file.is_symlink():
        deny("unsafe_lab_cache")
    with lock_file.open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        snapshot = cache / "session.json"
        safe = dict(id=session.session_id, duration=session.duration_sec,
                    tracks=list(session.tracks))
        if snapshot.is_symlink() or (cache / "listen").is_symlink():
            deny("unsafe_lab_cache")
        if not snapshot.is_file():
            temp = cache / "session.json.part"
            if temp.is_symlink():
                deny("unsafe_lab_cache")
            temp.write_text(json.dumps(safe, sort_keys=True), encoding="utf-8")
            temp.replace(snapshot)
        else:
            try:
                if json.loads(snapshot.read_text(encoding="utf-8")) != safe:
                    deny("stale_lab_cache_manifest")
            except (OSError, ValueError):
                deny("invalid_lab_cache_manifest")
        from mixer_adapter.session import listen_range
        guide_path = cache / "listen" / (
            f"{window.start_sec:.2f}-{window.end_sec:.2f}.ogg")
        if guide_path.is_symlink():
            deny("unsafe_lab_cache")
        if guide_path.exists() and guide_path.stat().st_size == 0:
            guide_path.unlink()  # only B11's own cache, under lock
        try:
            path = Path(listen_range(cache, window.start_sec, window.end_sec))
        except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            deny("short_guide_generation_failed")
        if not path.is_file() or path.stat().st_size <= 0:
            deny("empty_short_guide")
        _probe_audio(path, window.end_sec - window.start_sec)
        # Refuse a result if a source was replaced DURING guide generation.
        after = load_session(data_root, session_id, principal, authorize)
        if after.recipe_id != session.recipe_id:
            deny("source_changed_during_preparation")
    return ShortGuide(session, window, path)


def _spans_for_clip(clip, window, total):
    offset = clip.get("offset_sec")
    duration = clip.get("duration_sec")
    if not finite(offset) or not finite(duration) or duration <= 0:
        deny("invalid_engine_clip")
    global_offset = window.start_sec + offset
    ranges = clip.get("offset_ranges")
    output = []
    if ranges is not None:
        if not isinstance(ranges, list) or not ranges:
            deny("invalid_offset_ranges")
        for r in ranges:
            if (not isinstance(r, dict) or
                    any(not finite(r.get(k)) for k in (
                        "offset_sec", "clip_start_sec", "clip_end_sec")) or
                    r["clip_start_sec"] < 0 or
                    r["clip_end_sec"] <= r["clip_start_sec"] or
                    r["clip_end_sec"] > duration + .001):
                deny("invalid_offset_ranges")
            global_range_offset = window.start_sec + r["offset_sec"]
            start = global_range_offset + r["clip_start_sec"]
            end = global_range_offset + r["clip_end_sec"]
            output.append(dict(offset_sec=global_range_offset,
                               clip_start_sec=r["clip_start_sec"],
                               clip_end_sec=r["clip_end_sec"]))
    else:
        start = global_offset
        end = global_offset + duration
    spans = [(r["offset_sec"] + r["clip_start_sec"],
              r["offset_sec"] + r["clip_end_sec"]) for r in output] if output else [(start, end)]
    for start, end in spans:
        if not finite(start) or not finite(end) or end <= start:
            deny("invalid_global_span")
    if not any(min(total, b) - max(0, a) >= .5 for a, b in spans):
        deny("no_global_coverage")
    if not any(min(window.end_sec, b) - max(window.start_sec, a) >= .5
               for a, b in spans):
        deny("no_crop_overlap")
    return global_offset, output, spans


def project_engine_evidence(guide: ShortGuide, engine_clips, expected_camera_ids):
    """B11.3: ALL cameras must carry verified native Engine evidence.

    engine_clips MUST come from a trusted Engine invocation, never a browser
    payload; this library only validates/projects it and cannot perform Sync.
    """
    if (not isinstance(engine_clips, dict) or not engine_clips or
            not isinstance(expected_camera_ids, (list, tuple)) or
            not expected_camera_ids or len(set(expected_camera_ids)) != len(expected_camera_ids)
            or set(engine_clips) != set(expected_camera_ids)):
        deny("missing_or_unexpected_camera")
    result = {}
    for camera_id, clip in engine_clips.items():
        if (not isinstance(camera_id, str) or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,80}", camera_id) or not isinstance(clip, dict)):
            deny("invalid_camera_identity")
        verification = clip.get("verification")
        if (clip.get("no_audio") or clip.get("low_confidence") or
                clip.get("unstable_sync") or clip.get("error") or
                not finite(clip.get("confidence")) or clip["confidence"] < 6 or
                not isinstance(verification, dict) or
                verification.get("checked") is not True or
                verification.get("unstable_sync") is not False or
                type(verification.get("consensus_count")) is not int or
                verification["consensus_count"] < 2):
            deny("unproven_engine_sync")
        global_offset, ranges, spans = _spans_for_clip(
            clip, guide.window, guide.session.duration_sec)
        # Deliberately never publish Engine's source_path / local path.
        result[camera_id] = dict(offset_sec=global_offset,
                                 duration_sec=clip["duration_sec"],
                                 confidence=clip["confidence"],
                                 offset_ranges=ranges or None,
                                 verified=True, coverage_spans_global=spans)
    return dict(ok=True, version=VERSION, session_id=guide.session.session_id,
                source_identity=guide.session.recipe_id,
                global_duration_sec=guide.session.duration_sec,
                guide_window=dict(start_sec=guide.window.start_sec,
                                  end_sec=guide.window.end_sec),
                projected_clips=result, stage_ready=False,
                blocker="Wizard/Stage still requires full master and redoes sync")


def run_trusted_engine_window(guide: ShortGuide, camera_ids, engine_runner):
    """B11.3 seam: call the pinned Engine via a trusted, Owner-scoped adapter.

    engine_runner receives an INTERNAL local path and opaque camera IDs. Its
    future implementation must resolve and authorize camera sources server-side,
    then return native Engine evidence. No browser-provided offsets/paths.
    This seam does NOT pretend to be a native Engine invocation in these tests.
    """
    if not callable(engine_runner):
        deny("trusted_engine_runner_required")
    if not isinstance(camera_ids, (tuple, list)) or not camera_ids:
        deny("missing_or_unexpected_camera")
    if not isinstance(guide, ShortGuide) or not guide.path.is_file():
        deny("missing_short_guide")
    try:
        evidence = engine_runner(guide.path, tuple(camera_ids),
                                 guide.window.start_sec)
    except (OSError, ValueError, subprocess.CalledProcessError):
        deny("engine_runner_failed")
    return project_engine_evidence(guide, evidence, camera_ids)


def stage_contract_plan(projected, *, selected_song=None):
    """B11.4: plan only; does not claim Wizard/Cut/Edit/Export compatibility."""
    if not isinstance(projected, dict) or projected.get("ok") is not True:
        deny("unverified_stage_projection")
    total = projected["global_duration_sec"]
    if selected_song is not None:
        if (not isinstance(selected_song, dict) or
                not finite(selected_song.get("start")) or
                not finite(selected_song.get("end")) or
                not 0 <= selected_song["start"] < selected_song["end"] <= total or
                selected_song["end"] - selected_song["start"] > MAX_WINDOW_SEC):
            deny("invalid_global_song")
        if not any(
            min(b, selected_song["end"]) - max(a, selected_song["start"]) >= .5
            for clip in projected["projected_clips"].values()
            for a, b in clip["coverage_spans_global"]):
            deny("no_song_camera_coverage")
    return dict(projected, selected_song_global=selected_song,
                stage_ready=False, required_adapters=[
                    "Owner-verified window source endpoint",
                    "Stage wizard accepts externally verified global offsets",
                    "Global-clock listening and waveform independently of full guide",
                    "Native original-range export compatibility and E2E Mac"],
                fallback="legacy_full_guide_engine")


def fail_closed_fallback(reason):
    """No silent success: actual legacy path is a future Owner/Stage integration."""
    return dict(ok=False, stage_ready=False, fallback_required=True,
                fallback="legacy_full_guide_engine", reason=str(reason))
