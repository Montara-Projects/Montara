"""Validate source paths offered to the Stage mixer.

A web browser cannot grant a remote server direct access to the visitor's disk.
In remote/private mode this boundary allows only completed uploads, pinned
fixtures, or song-specific WAV previews listed in the current Owner-local
Session manifest. The caller must already be isolated to that Owner's root.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


_UPLOAD_ID = re.compile(r"[a-f0-9]{32}\Z")
_SESSION_ID = re.compile(r"[a-f0-9]{12}\Z")
_SONG_ID = re.compile(r"[1-9][0-9]{0,3}\Z")


def _verified_session_preview(path: Path, owner_root: Path) -> bool:
    """Accept only a current, server-created song excerpt in this Owner root.

    A browser path string is never authority. The private server-created
    session.json enumerates precisely the currently valid preview tracks.
    Earlier previews, another song, symlinks, or another Owner are denied.
    """
    sessions = owner_root / "Sessions"
    if not path.is_relative_to(sessions) or path.suffix.lower() != ".wav":
        return False
    rel = path.relative_to(sessions)
    if (len(rel.parts) != 5 or not _SESSION_ID.fullmatch(rel.parts[0]) or
            rel.parts[1] != "preview" or
            not _SONG_ID.fullmatch(rel.parts[2]) or
            rel.parts[3] != "tracks" or
            not rel.parts[4].lower().endswith(".wav")):
        return False
    work = sessions / rel.parts[0]
    if any(part.is_symlink() for part in (
            sessions, work, work / "preview", work / "preview" / rel.parts[2],
            path.parent, path)):
        return False
    manifest = work / "session.json"
    try:
        if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 2_000_000:
            return False
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return False
    if (not isinstance(data, dict) or data.get("id") != rel.parts[0] or
            data.get("status") not in ("ready", "done") or
            type(data.get("preview_song")) is not int or
            data["preview_song"] != int(rel.parts[2])):
        return False
    current = data.get("preview_tracks")
    if (not isinstance(current, list) or not 1 <= len(current) <= 64 or
            not all(isinstance(value, str) for value in current)):
        return False
    return str(path) in current


def resolve_mix_sources(raw_tracks, data_root: Path, fixtures_root: Path, *, remote: bool):
    """Return authorised Paths; raise ValueError on invalid or unregistered input.

    Local development retains explicitly supplied local paths for compatibility.
    Private remote mode also accepts exact Owner-local current song excerpts.
    """
    if not isinstance(raw_tracks, list) or not raw_tracks or len(raw_tracks) > 64:
        raise ValueError("Choose between 1 and 64 audio tracks.")
    if any(not isinstance(item, str) or not item or len(item) > 4096 for item in raw_tracks):
        raise ValueError("Invalid audio track.")
    paths = [Path(item).resolve() for item in raw_tracks]
    if any(not path.is_file() for path in paths):
        raise ValueError("One or more audio tracks are unavailable.")
    if len(set(paths)) != len(paths) or len({p.name.casefold() for p in paths}) != len(paths):
        raise ValueError("Duplicate audio tracks or filenames.")

    if not remote:
        return paths

    owner_root = Path(data_root).resolve()
    uploads = (owner_root / "Uploads").resolve()
    fixtures = Path(fixtures_root).resolve()
    for path in paths:
        if path.is_relative_to(fixtures):
            # Fixtures are shipped by Montara itself, not uploaded by visitors.
            continue
        if _verified_session_preview(path, owner_root):
            continue
        if not path.is_relative_to(uploads):
            raise ValueError("Track is not a registered upload.")
        relative = path.relative_to(uploads)
        if len(relative.parts) != 2 or not _UPLOAD_ID.fullmatch(relative.parts[0]):
            raise ValueError("Track is not a registered upload.")
        folder = uploads / relative.parts[0]
        try:
            record = json.loads((folder / "upload.json").read_text())
        except (OSError, ValueError, TypeError):
            raise ValueError("Track upload record is unavailable.") from None
        if record.get("complete") is not True or record.get("name") != relative.parts[1]:
            raise ValueError("Track upload is not completed or does not match the record.")
    return paths
