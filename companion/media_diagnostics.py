"""Read-only first-pass diagnosis of original video files for Montara Companion.

No mutations or writes to the source. The browser receives only allowlisted
categories and media metadata; it never supplies a filesystem path.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

VIDEO_FORMATS = frozenset({'.mp4','.mov','.m4v','.mkv','.avi','.webm','.mts'})
MEDIA_CODECS = frozenset({'h264','hevc','h265','mpeg4','prores','vp8','vp9','av1','mpeg2video'})


def _duration(probe):
    value = (probe.get('format') or {}).get('duration')
    if value is None:
        value = next((s.get('duration') for s in probe.get('streams',[]) if s.get('codec_type')=='video'),None)
    try:
        number=float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return round(number,3) if math.isfinite(number) and number > 0 else None


def classify_probe(*, returncode, stdout, stderr='', timed_out=False):
    """Return a bounded, path-free verdict. Probe failures may be inconclusive."""
    if timed_out:
        return {'status':'inconclusive','reason':'probe_timeout','repair_offer':False}
    try:
        details=json.loads(stdout or '{}')
    except (ValueError, TypeError):
        return {'status':'inconclusive','reason':'invalid_probe_data','repair_offer':False}
    if not isinstance(details,dict):
        return {'status':'inconclusive','reason':'invalid_probe_data','repair_offer':False}
    streams=details.get('streams')
    if not isinstance(streams,list):streams=[]
    video=next((s for s in streams if isinstance(s,dict) and s.get('codec_type')=='video'),None)
    error=(stderr or '').lower()
    structural=('moov atom not found','invalid data found when processing input',
                'error reading header','could not find codec parameters',
                'truncated', 'partial file', 'end of file')
    damage=any(word in error for word in structural)
    if returncode != 0 and damage:
        kind='missing_index' if 'moov atom not found' in error else 'container_damage'
        return {'status':'damaged','reason':kind,'repair_offer':True}
    if returncode != 0:
        return {'status':'inconclusive','reason':'probe_failed','repair_offer':False}
    if video is None:
        return {'status':'unsupported','reason':'no_video_stream','repair_offer':False}
    codec=str(video.get('codec_name') or '').lower()
    if codec not in MEDIA_CODECS:
        return {'status':'unsupported','reason':'unsupported_codec','repair_offer':False}
    duration=_duration(details)
    if duration is None:
        return {'status':'inconclusive','reason':'duration_unknown','repair_offer':False}
    try:
        width=int(video.get('width') or 0);height=int(video.get('height') or 0)
    except (ValueError,TypeError,OverflowError):
        width=height=0
    if width<1 or height<1:
        return {'status':'inconclusive','reason':'dimensions_unknown','repair_offer':False}
    return {'status':'healthy','reason':'short_clip' if duration <= 2 else 'metadata_ok',
            'repair_offer':False,'duration_sec':duration,'width':width,'height':height,
            'codec':codec,'spherical_candidate':width>=2048 and width==height*2,
            'scope':'metadata_only'}


def diagnose_video(path: Path, *, ffprobe: str, timeout: float = 30.0):
    """FFprobe bounded read; never writes or repairs. No absolute paths returned."""
    if path.suffix.lower() not in VIDEO_FORMATS:
        return {'status':'unsupported','reason':'unsupported_extension','repair_offer':False}
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return {'status':'inconclusive','reason':'file_unavailable','repair_offer':False}
        result=subprocess.run([ffprobe,'-v','error','-show_format','-show_streams',
                               '-of','json',str(path)],text=True,capture_output=True,
                              timeout=min(45,max(1,float(timeout))))
    except subprocess.TimeoutExpired:
        return classify_probe(returncode=-1,stdout='',timed_out=True)
    except (OSError,ValueError):
        return {'status':'inconclusive','reason':'file_unavailable','repair_offer':False}
    return classify_probe(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
