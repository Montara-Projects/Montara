"""Exact allowlist for Chema's per-owner full-session mixer.

No generic /montara/ proxy: every method, session ID, suffix and query has
a fixed contract. The calling Owner gateway still verifies session/CSRF and
broker-issued generation, and the pinned worker sees only its own data root.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode

from urano.native_owner_stage_http import NativeStageTarget

_ID = re.compile(r"[a-f0-9]{12}\Z")
_SONG = re.compile(r"[1-9][0-9]{0,3}\Z")
_SECONDS = re.compile(r"[0-9]{1,9}(?:\.[0-9]{1,6})?\Z")
_PATH = re.compile(r"/montara/session/([a-f0-9]{12})(?:/(.*))?\Z")
_MEDIA = ("audio/webm", "audio/ogg", "audio/mpeg", "application/zip")


def _args(query: str, allowed: frozenset[str], required: frozenset[str]) -> dict[str, str] | None:
    try:
        params = parse_qs(query, strict_parsing=True, keep_blank_values=True,
                          max_num_fields=len(allowed))
    except ValueError:
        return None
    if (not required <= params.keys() or not params.keys() <= allowed or
            any(len(v) != 1 for v in params.values())):
        return None
    return {key: value[0] for key, value in params.items()}


def _song_query(query: str) -> str | None:
    # A browser may request the anonymous window for Mix preview, or a
    # reviewed song ID; never arbitrary paths or unlimited numeric values.
    args = _args(query, frozenset({"song", "start", "end", "name"}),
                 frozenset({"song", "start", "end"}))
    if args is None:
        return None
    if (not _SONG.fullmatch(args["song"]) or
            not all(_SECONDS.fullmatch(args[k]) for k in ("start", "end")) or
            ("name" in args and (len(args["name"]) > 80 or not all(ch.isprintable() for ch in args["name"])))):
        return None
    return urlencode({k: args[k] for k in ("song", "start", "end", "name") if k in args})


def full_session_target(method: str, path: str, query: str = "") -> NativeStageTarget | None:
    """Return bounded private worker target; deny all unknown operations."""
    if (not isinstance(method, str) or not isinstance(path, str) or
            not isinstance(query, str) or len(query) > 2048):
        return None
    if path == "/montara/session":
        return NativeStageTarget(path, "json") if method == "POST" and not query else None
    if path == "/montara/session/latest":
        return NativeStageTarget(path, "json") if method == "GET" and not query else None
    m = _PATH.fullmatch(path)
    if m is None or not _ID.fullmatch(m[1]):
        return None
    suffix = m[2] or ""
    if method == "GET" and not suffix and not query:
        return NativeStageTarget(path, "json")
    if method == "GET" and suffix in {
        "video-source", "waveform",
    } and not query:
        return NativeStageTarget(path, "session-json")
    if method == "GET" and suffix in {"originals", "local-plan"}:
        if not query:
            return NativeStageTarget(path, "json") if suffix == "originals" else None
        if suffix == "originals":
            values = _args(query, frozenset({"song", "start", "end", "name"}), frozenset())
            if values is None or not values:
                return None
            if not set(values) - {"song"}:
                if _SONG.fullmatch(values["song"]):
                    return NativeStageTarget(path + "?" + urlencode(values), "json")
                return None
        normalized = _song_query(query)
        return NativeStageTarget(path + "?" + normalized, "json") if normalized else None
    if suffix == "mix-preview" and method in ("GET", "POST"):
        if method == "POST" and not query:
            return NativeStageTarget(path, "json")
        if method == "GET":
            params = _args(query, frozenset({"song"}), frozenset({"song"}))
            if params and _SONG.fullmatch(params["song"]):
                return NativeStageTarget(path + "?" + urlencode(params), "json")
        return None
    if suffix.startswith("mix-preview/result/") and method == "GET" and not query:
        song = suffix[len("mix-preview/result/"):]
        return NativeStageTarget(path, "session-media") if _SONG.fullmatch(song) else None
    if suffix == "listen" and method in ("GET", "HEAD"):
        if not query:
            return NativeStageTarget(path, "session-media")
        if method != "GET":
            return None
        values = _args(query, frozenset({"start", "end"}), frozenset({"start", "end"}))
        if values and all(_SECONDS.fullmatch(v) for v in values.values()):
            return NativeStageTarget(path + "?" + urlencode(values), "session-media")
        return None
    if method == "GET" and suffix == "results.zip" and not query:
        return NativeStageTarget(path, "session-media")
    if method == "GET" and suffix.startswith("result/"):
        song = suffix[len("result/"):]
        if not _SONG.fullmatch(song):
            return None
        if not query:
            return NativeStageTarget(path, "session-media")
        params = _args(query, frozenset({"v", "download"}), frozenset())
        if params is None or len(params) != 1:
            return None
        key, value = next(iter(params.items()))
        if (key == "download" and value == "1") or (key == "v" and re.fullmatch(r"[0-9]{1,6}", value)):
            return NativeStageTarget(path + "?" + urlencode(params), "session-media")
        return None
    if method == "POST" and not query and suffix in {
        "cancel", "include", "prepare", "render", "songs", "save-mix", "suggest", "video-master",
        "originals", "local-result",
    }:
        return NativeStageTarget(path, "json")
    return None
