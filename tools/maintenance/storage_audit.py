#!/usr/bin/env python3
"""Conservative read-only storage inventory. Never yields deletion authorizations."""
import argparse
import collections
import json
import os
import stat
from pathlib import Path


def audit(root: Path, max_depth: int = 4) -> dict:
    result = {'files': 0, 'bytes': 0, 'symlinks_skipped': 0, 'scan_errors': 0,
              'protected_files': 0, 'protected_bytes': 0, 'categories': {}}
    counts = collections.defaultdict(lambda: {'files': 0, 'bytes': 0})
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Audit root must be an existing non-symlink directory')
    def walk(directory: Path, depth: int):
        if depth > max_depth:
            result['scan_errors'] += 1  # Never imply complete inspection.
            return
        try:
            with os.scandir(directory) as it:
                for entry in it:
                    try:
                        attrs = entry.stat(follow_symlinks=False)
                        if stat.S_ISLNK(attrs.st_mode):
                            result['symlinks_skipped'] += 1
                            continue
                        if stat.S_ISDIR(attrs.st_mode):
                            walk(Path(entry.path), depth + 1)
                        elif stat.S_ISREG(attrs.st_mode):
                            category = Path(entry.path).relative_to(root).parts[0]
                            counts[category]['files'] += 1
                            counts[category]['bytes'] += attrs.st_size
                            result['files'] += 1
                            result['bytes'] += attrs.st_size
                    except (OSError, ValueError):
                        result['scan_errors'] += 1
        except (OSError, PermissionError):
            result['scan_errors'] += 1
    walk(root, 0)
    result['categories'] = dict(sorted(counts.items()))
    result['protected_files'] = result['files']
    result['protected_bytes'] = result['bytes']
    result['candidate_for_deletion_files'] = 0
    result['candidate_for_deletion_bytes'] = 0
    result['mode'] = 'READ_ONLY; nothing is authorized for deletion'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--max-depth', type=int, default=4)
    args = parser.parse_args()
    if args.max_depth < 0:
        parser.error('--max-depth must be nonnegative')
    print(json.dumps(audit(args.root, args.max_depth), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
