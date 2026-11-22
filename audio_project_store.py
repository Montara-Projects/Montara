"""Private, durable per-Owner audio project metadata (never audio bytes).

The caller selects the Owner's *verified* data root, never a client-supplied
path. Sources are revalidated against Owner upload permissions at reopen time.
Manifests are atomic, revision-gated and share the same identity across saves.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import math
import os
import re
import tempfile
import time
import uuid
from pathlib import Path

_ID = re.compile(r'[a-f0-9]{32}\Z')
_MAX_MANIFEST = 256 * 1024


class AudioProjectError(ValueError):
    pass


class AudioProjectConflict(AudioProjectError):
    pass


def validate_controls(raw: dict, sources: list[str]) -> dict:
    """Reject corrupt or browser-executable mixer state before persistence."""
    if not isinstance(raw, dict) or len(raw)>64:
        raise AudioProjectError('Invalid mixer controls')
    allowed={Path(source).name for source in sources}
    result={}
    for filename, values in raw.items():
        if filename not in allowed or not isinstance(values,dict) or set(values)-{'fader_db','mute','pan','eq','fx'}:
            raise AudioProjectError('Unknown mixer track or control')
        clean={}
        if 'fader_db' in values:
            v=values['fader_db']
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or not -80<=v<=24:
                raise AudioProjectError('Invalid fader level')
            clean['fader_db']=v
        if 'mute' in values:
            if not isinstance(values['mute'],bool):raise AudioProjectError('Invalid mute')
            clean['mute']=values['mute']
        if 'pan' in values:
            v=values['pan']
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or not -1 <= v <= 1:
                raise AudioProjectError('Invalid pan')
            clean['pan']=v
        if 'fx' in values and values['fx'] is not None:
            effects=values['fx']
            if not isinstance(effects,dict) or set(effects)-{'delay','reverb'}:
                raise AudioProjectError('Invalid effects')
            new={}
            for name,item in effects.items():
                if not isinstance(item,dict) or set(item)-{'enabled','amount'}:
                    raise AudioProjectError('Invalid effect settings')
                if 'enabled' in item and not isinstance(item['enabled'],bool):
                    raise AudioProjectError('Invalid effect switch')
                v=item.get('amount',35)
                if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or not 0<=v<=100:
                    raise AudioProjectError('Invalid effect intensity')
                new[name]={'enabled':item.get('enabled',False),'amount':v}
            clean['fx']=new
        if 'eq' in values and values['eq'] is not None:
            eq=values['eq']
            if not isinstance(eq,dict) or set(eq)-{'low','mid','air','high'}:
                raise AudioProjectError('Invalid EQ bands')
            new={}
            for band,item in eq.items():
                if not isinstance(item,dict) or set(item)-{'hz','db','q','type','frequency','gain'}:
                    raise AudioProjectError('Invalid EQ values')
                for key,value in item.items():
                    if key in {'hz','db','q','frequency','gain'} and (not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or abs(value)>25000):
                        raise AudioProjectError('Invalid EQ number')
                    if key=='type' and (not isinstance(value,str) or len(value)>30):
                        raise AudioProjectError('Invalid EQ type')
                new[band]=item
            clean['eq']=new
        result[filename]=clean
    return result


class AudioProjects:
    def __init__(self, data_root: Path):
        self.root = Path(data_root).resolve() / 'AudioProjects'
        if self.root.is_symlink():
            raise AudioProjectError('Untrusted audio project store')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or self.root.stat().st_mode & 0o077:
            raise AudioProjectError('Audio project store must be Owner-private')
        self.lock_path = self.root / '.lock'

    @contextlib.contextmanager
    def _locked(self):
        fd = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'wb') as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                yield
        finally:
            pass

    def _path(self, project_id: str):
        if not isinstance(project_id, str) or not _ID.fullmatch(project_id):
            raise AudioProjectError('Invalid project identifier')
        path = self.root / (project_id + '.json')
        if path.is_symlink():
            raise AudioProjectError('Project record is not trusted')
        return path

    def _read(self, project_id: str):
        path = self._path(project_id)
        if not path.exists():
            raise AudioProjectError('Audio project not found')
        if path.stat().st_size > _MAX_MANIFEST:
            raise AudioProjectError('Audio project record is too large')
        try:
            result = json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise AudioProjectError('Damaged audio project metadata') from exc
        if not isinstance(result,dict) or result.get('id') != project_id or result.get('kind') != 'audio':
            raise AudioProjectError('Invalid audio project record')
        return result

    def list(self):
        with self._locked():
            result = []
            for path in self.root.glob('*.json'):
                if path.is_symlink() or not _ID.fullmatch(path.stem):
                    continue
                try:
                    record = self._read(path.stem)
                except (AudioProjectError, OSError):
                    continue
                result.append({key:record.get(key) for key in ('id','kind','name','updated_at','revision')})
            return sorted(result, key=lambda p:p['updated_at'] or 0, reverse=True)

    def get(self, project_id: str):
        with self._locked():
            return self._read(project_id)

    def save(self, *, name: str, sources: list[str], controls: dict,
             track_types: dict | None = None, project_id: str | None = None,
             revision: int | None = None, master_path: str | None = None):
        if not isinstance(name,str) or not 1 <= len(name.strip()) <= 120 or '\x00' in name:
            raise AudioProjectError('Choose a project name (1–120 characters)')
        name = name.strip()
        if not isinstance(sources,list) or not 1 <= len(sources) <= 64 or not all(isinstance(x,str) and 1 <= len(x) <= 4096 for x in sources):
            raise AudioProjectError('Invalid audio source list')
        if len(set(sources)) != len(sources):
            raise AudioProjectError('Duplicate audio source')
        if not isinstance(track_types or {},dict):
            raise AudioProjectError('Invalid mixer state')
        controls=validate_controls(controls,sources)
        if master_path is not None and (not isinstance(master_path,str) or len(master_path) > 4096):
            raise AudioProjectError('Invalid master reference')
        with self._locked():
            now = time.time()
            if project_id:
                before = self._read(project_id)
            else:
                # Repeated name in this one Owner's audio space updates its slot.
                # Existing *different* audio projects remain untouched.
                matches = []
                for path in self.root.glob('*.json'):
                    if _ID.fullmatch(path.stem) and not path.is_symlink():
                        try:
                            candidate = self._read(path.stem)
                            if candidate['name'].casefold() == name.casefold():
                                matches.append(candidate)
                        except (AudioProjectError,OSError):
                            pass
                before = max(matches,key=lambda p:p.get('updated_at',0)) if matches else None
                project_id = before['id'] if before else uuid.uuid4().hex
            if revision is not None and (not before or before['revision'] != revision):
                raise AudioProjectConflict('Project changed in another tab. Reload before saving.')
            record = dict(kind='audio',id=project_id,name=name,updated_at=now,
                          revision=(before['revision']+1 if before else 1),
                          sources=sources,controls=controls,track_types=track_types or {},
                          master_path=master_path,
                          created_at=before.get('created_at',now) if before else now)
            try:
                raw=json.dumps(record,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf8')
            except (ValueError,TypeError) as exc:
                raise AudioProjectError('Invalid mixer values') from exc
            if len(raw) > _MAX_MANIFEST:
                raise AudioProjectError('Audio project state exceeds safe limit')
            path=self._path(project_id)
            tmp = None
            try:
                with tempfile.NamedTemporaryFile(dir=self.root, prefix='.tmp-', delete=False) as stream:
                    tmp=Path(stream.name)
                    os.fchmod(stream.fileno(),0o600)
                    stream.write(raw)
                    stream.flush();os.fsync(stream.fileno())
                os.replace(tmp,path)
            finally:
                if tmp:tmp.unlink(missing_ok=True)
            return record

    def delete(self, project_id: str, *, revision: int | None = None):
        with self._locked():
            before=self._read(project_id)
            if revision is not None and before['revision']!=revision:
                raise AudioProjectConflict('Project changed in another tab.')
            self._path(project_id).unlink()
            # No audio sources or exports are deleted by this operation.
            return {'deleted':project_id,'kept_media':True}
