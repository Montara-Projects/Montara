"""Track types the person can choose for each audio track, and the mixer role each one uses.

The page pre-fills the type from the file name (same rules as the mixer) and the person can
change it. A type the person chose themselves also tells the mixer the track is music: it is
never muted as empty or noisy. Types without a mixer role of their own yet use the nearest
one (until ZuckerMixer's instrument dictionary has them).
"""
from __future__ import annotations

from pathlib import Path
import re

# value: (label shown in the page, ZuckerMixer role)
TYPES: dict[str, tuple[str, str]] = {
    "kick": ("Kick", "kick"),
    "snare": ("Snare", "snare"),
    "hh": ("Hi-hat", "hh"),
    "overhead": ("Overhead", "overhead"),
    "drums": ("Drums (other)", "drums"),
    "percussion": ("Percussion", "drums"),
    "bass": ("Bass", "bass"),
    "guitar_electric": ("Electric guitar", "guitar"),
    "guitar_acoustic": ("Acoustic guitar", "guitar"),
    "keys": ("Piano / keys", "keys"),
    "synth": ("Synth", "synth"),
    "sax": ("Saxophone", "sax"),
    "trumpet": ("Trumpet", "horn"),
    "trombone": ("Trombone", "horn"),
    "flute": ("Flute", "horn"),
    "violin": ("Violin", "horn"),
    "strings": ("Strings", "synth"),
    "vocal": ("Lead vocal", "vocal"),
    "backing_vocal": ("Backing vocal", "vocal"),
    "podcast_voice": ("Podcast voice", "vocal"),
    "narration": ("Narration voice", "vocal"),
    "room": ("Room / audience", "room"),
    "other": ("Other", "other"),
}
SIDES = {"", "L", "R"}


AUDIO_SUFFIXES = {".wav", ".flac", ".wv", ".opus", ".aif", ".aiff", ".mp3", ".m4a", ".ogg"}


def track_key(name) -> str:
    """'Bass.wav', 'Bass.wav.opus' (a preview) and 'Bass.wav.flac' are the same track: 'bass'."""
    path = Path(str(name)).name
    while Path(path).suffix.lower() in AUDIO_SUFFIXES:
        path = path[: -len(Path(path).suffix)]
    return path.lower()


def validate(raw) -> dict[str, dict]:
    """{track key: {type, side, chosen}}; unknown types are dropped."""
    result = {}
    if not isinstance(raw, dict):
        return result
    for name, item in list(raw.items())[:200]:
        if not isinstance(item, dict) or item.get("type") not in TYPES:
            continue
        side = item.get("side") if item.get("side") in SIDES else ""
        result[track_key(name)] = {"type": item["type"], "side": side, "chosen": item.get("chosen") is True}
    return result


def infer_recording_type(name: str) -> str:
    """Conservative role inference for structured concert-recorder file names.

    Only improves existing unconfirmed Other choices. Explicit manual choices
    always win. Never renames a track, changes Owner data, or classifies
    non-concert personal names as voice mics.
    """
    stem = track_key(name)
    stem = re.sub(r"\.tracks$", "", stem, flags=re.I)
    stem = re.sub(r"^[0-9]{8,14}(?=[a-z])", "", stem, flags=re.I)
    from_concert = stem.endswith("t4tinsel")
    if from_concert:
        stem = stem[:-len("t4tinsel")]
    stem = stem.strip(" ._-").replace("_", " ").lower()
    if not stem:
        return "other"
    if re.search(r"kick|bass drum|\bbd\b|bombo", stem): return "kick"
    if re.search(r"snare|\bsnr\b", stem): return "snare"
    if re.search(r"hi.?hat|\bhh\b", stem): return "hh"
    if re.search(r"overhead|\bov\b|\boh\b", stem): return "overhead"
    if re.search(r"tom(?:\s*\d+)?|drum|\bkit\b", stem): return "drums"
    if re.search(r"\bbass\b", stem): return "bass"
    if re.search(r"acoustic.*guit|acoustic guitar", stem): return "guitar_acoustic"
    if re.search(r"guit|guitar|\bgtr\b", stem): return "guitar_electric"
    if re.search(r"keys|keyboard|piano|rhodes|organ", stem): return "keys"
    if re.search(r"synth|moog|juno|novation|nord|korg", stem): return "synth"
    if re.search(r"sax", stem): return "sax"
    if re.search(r"trumpet|trump|trompeta", stem): return "trumpet"
    if re.search(r"\bvocal\b|\bvox\b|\bvoice\b", stem): return "vocal"
    if from_concert and re.fullmatch(r"[a-zà-ÿ]{3,}", stem):
        return "vocal"  # tentative personal-mic name, not confirmed identity
    return "other"


def for_files(types, files) -> dict[str, dict]:
    """Type for DSP by original filename; manual choices always win.

    Historic MAIN sessions contain 'other'/chosen=False despite obvious
    instrument names. Correct those on use, without rewriting session.json.
    """
    types = types or {}
    result = {}
    for raw in files:
        name = Path(str(raw)).name
        selected = types.get(track_key(raw))
        if selected is None:
            continue
        chosen = dict(selected)
        if chosen["type"] == "other" and chosen.get("chosen") is not True:
            guessed = infer_recording_type(name)
            if guessed != "other":
                chosen["type"] = guessed
        result[name] = chosen
    return result


def mixer_roles(types: dict[str, dict]) -> dict[str, str]:
    """Mixer role per file. Keys with a side become keys_l / keys_r (the mixer's stereo keys)."""
    roles = {}
    for name, item in (types or {}).items():
        role = TYPES[item["type"]][1]
        if role == "keys" and item.get("side") in {"L", "R"}:
            role = "keys_l" if item["side"] == "L" else "keys_r"
        roles[name] = role
    return roles


def stereo_sides(types: dict[str, dict]) -> dict[str, str]:
    return {name: item["side"] for name, item in (types or {}).items() if item.get("side") in {"L", "R"}}


def noise_exempt(types: dict[str, dict]) -> set[str]:
    """Tracks whose type the person chose: they are music, never muted as noise."""
    return {name for name, item in (types or {}).items() if item.get("chosen") and item["type"] != "other"}


def apply(pipeline, stems, types):
    """Give the mixer the person's types: roles on the stems, stereo sides, noise exemptions.

    `types` is keyed by file name (see for_files). Returns the stems with their roles replaced.
    """
    from dataclasses import replace
    roles = mixer_roles(types)
    pipeline.STEREO_SIDES = stereo_sides(types)
    pipeline.NOISE_EXEMPT_STEMS = noise_exempt(types)
    # The instrument dictionary refines each track's processing (EQ, compressor, pan, level, sends).
    pipeline.STEM_INSTRUMENTS = {name: item["type"] for name, item in (types or {}).items()}
    return [replace(s, role=roles[s.path.name]) if s.path.name in roles else s for s in stems]
