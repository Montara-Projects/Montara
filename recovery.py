"""Chronological recovery of managed work, independent of browser/device memory."""
from pathlib import Path
import json
import re


def register_recovery(app, data_root):
    from flask import jsonify
    root = Path(data_root).resolve()

    @app.get('/montara/recovery/latest')
    def latest():
        candidates = []
        for kind, folder, filename in [('project', 'Projects', 'project.json'), ('session', 'Sessions', 'session.json')]:
            for path in (root / folder).glob('*/' + filename):
                if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(root / folder):
                    continue
                try:
                    data = json.loads(path.read_text())
                    if not isinstance(data, dict):
                        continue
                    if kind == 'session':
                        if not re.fullmatch('[a-f0-9]{12}', path.parent.name) or data.get('id') != path.parent.name:
                            continue
                        item = dict(kind=kind, id=data['id'])
                        # A failed startup before detection has no recoverable
                        # work. It must not hide the last finished concert in
                        # Latest after a corrected MAIN worker is installed.
                        empty_import_failure = (
                            data.get('status') == 'failed'
                            and data.get('error') == "No module named 'resumable_upload'"
                            and not data.get('results')
                        )
                        completed = bool(data.get('results')) and data.get('status') in ('done', 'partial')
                    else:
                        inputs = data.get('inputs') or {}
                        if not any(inputs.get(k) for k in ('videos', 'audio', 'master')):
                            continue  # Empty drafts must not hide the last real work.
                        item = dict(kind=kind, path=str(path.parent), name=data.get('name', path.parent.stem),
                                    platform=(data.get('settings', {}).get('wizard') or {}).get('platform', 'youtube'))
                    candidates.append((path.stat().st_mtime_ns, item,
                                       empty_import_failure if kind == 'session' else False,
                                       completed if kind == 'session' else False))
                except (OSError, ValueError, TypeError, AttributeError):
                    continue
        if not candidates:
            return jsonify(error=dict(message='No saved work.')), 404
        latest = max(candidates, key=lambda row: row[0])
        if latest[2]:
            finished = [row for row in candidates if row[3]]
            if finished:
                latest = max(finished, key=lambda row: row[0])
        return jsonify(latest[1])
