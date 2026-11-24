"""Non-destructive canonical identity lookup for verified Owner project shelves.

A name can resolve to precisely one stored project, never arbitrary newest.
Historic duplicates remain accessible and are reported for manual selection.
"""
from __future__ import annotations
import re
import unicodedata
from pathlib import Path


class AmbiguousProject(ValueError):
    pass


def canonical_name(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError('Invalid project name')
    name = unicodedata.normalize('NFKC', raw)
    name = ' '.join(name.split()).casefold()
    if not name or len(name) > 120 or any(ord(char) < 32 for char in name):
        raise ValueError('Project title must be 1–120 characters')
    return name


def match_projects(entries: list[dict], title: str, *, kind: str = 'video') -> dict:
    """Resolve titles of one kind after the caller fetches Owner-scoped entries.

    Never silently discard historical duplicate paths or pick newest.
    """
    if kind not in {'video', 'audio'}:
        raise ValueError('Invalid project kind')
    key = canonical_name(title)
    matches = [row for row in entries
               if row.get('kind', 'video') == kind and
               isinstance(row.get('name'), str) and
               canonical_name(row['name']) == key]
    # An older record may be exposed twice by multiple storage locations.
    unique = {}
    for row in matches:
        path = row.get('path') if kind == 'video' else row.get('id')
        if not isinstance(path,str) or not path:
            raise ValueError('Untrusted project entry')
        unique[path] = row
    if len(unique) > 1:
        raise AmbiguousProject('Multiple historic projects have this title. Open the intended one from Your Projects; no files have been changed.')
    if unique:
        return {'action':'open', 'kind':kind, 'project':next(iter(unique.values()))}
    return {'action':'new', 'kind':kind}
