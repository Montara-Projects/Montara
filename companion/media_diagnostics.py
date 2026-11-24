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


def virtual_segments(diagnosis, *, target_sec=300.0, max_parts=4096):
    """Non-destructive segment boundaries; spans share the one source file.

    This is a transport/editing plan, not a promise to detect song boundaries.
    """
    if diagnosis.get('status') != 'healthy':
        return {'status':'unavailable','segments':[],'reason':'no_valid_video_metadata'}
    duration=diagnosis.get('duration_sec')
    if not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:
        return {'status':'unavailable','segments':[],'reason':'duration_unknown'}
    size=max(30,min(1800,float(target_sec)))
    count=int(math.ceil(duration/size))
    if count>max_parts:
        return {'status':'unavailable','segments':[],'reason':'too_many_parts'}
    sections=[]
    for index in range(count):
        start=round(index*size,3)
        end=round(min(duration,(index+1)*size),3)
        if end>start:
            sections.append({'index':index+1,'start_sec':start,'end_sec':end,'duration_sec':round(end-start,3)})
    return {'status':'ready','mode':'virtual','original_preserved':True,
            'duration_sec':duration,'segments':sections,'automatic_cut':'technical',
            'song_boundary_detection':'not_performed'}


def repair_remux_copy(source: Path, destination: Path, *, ffmpeg: str, ffprobe: str, timeout: int = 1800):
    """Best-effort remux to a *new* path, without overwriting source.

    Does not claim to reconstruct missing moov metadata or recover lost bytes.
    Never uses shell arguments; caller controls the private destination.
    """
    if source.resolve(strict=True) == destination.resolve(strict=False):
        raise ValueError('source and output must differ')
    if destination.exists():
        raise FileExistsError('recovery target already exists')
    first=diagnose_video(source,ffprobe=ffprobe)
    if first.get('reason')=='missing_index':
        return {'status':'needs_reference','reason':'missing_index',
                'message':'Missing MP4 index requires a compatible recording from the same camera.'}
    if first.get('status') not in {'damaged','inconclusive'}:
        return {'status':'not_needed' if first.get('status')=='healthy' else 'unsupported'}
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=destination.with_name(destination.stem+'.partial'+destination.suffix)
    if temp.exists():raise FileExistsError('temporary target already exists')
    try:
        cmd=[ffmpeg,'-hide_banner','-nostdin','-v','error',
             '-fflags','+genpts+discardcorrupt','-err_detect','ignore_err',
             '-i',str(source),'-map','0:v:0','-map','0:a?',
             '-c','copy','-avoid_negative_ts','make_zero',
             '-movflags','+faststart','-y',str(temp)]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        if p.returncode or not temp.is_file() or temp.stat().st_size<1024:
            return {'status':'failed','reason':'remux_failed'}
        good=diagnose_video(temp,ffprobe=ffprobe)
        if good.get('status')!='healthy':
            return {'status':'failed','reason':'recovered_file_failed_validation'}
        temp.replace(destination)
        return {'status':'recovered','reason':'remux','duration_sec':good.get('duration_sec'),
                'bytes':destination.stat().st_size,'original_preserved':True}
    except (subprocess.TimeoutExpired,OSError,ValueError):
        return {'status':'failed','reason':'repair_timeout_or_io'}
    finally:
        if temp.exists():temp.unlink()


def reference_match(broken: Path, candidate: Path, *, diagnosis: dict):
    """Conservative reference suggestion, never a proof of camera identity.

    Only registered, user-selected sources are considered by the HTTP handler.
    For a missing-moov file, its codec may be unknowable, so avoid claiming
    a match based solely on names.
    """
    import re
    if candidate == broken or candidate.suffix.lower() not in VIDEO_FORMATS:
        return {'suitable':False,'reason':'not_video'}
    if diagnosis.get('status')!='healthy':
        return {'suitable':False,'reason':'unhealthy_reference'}
    same_folder=broken.parent.resolve()==candidate.parent.resolve()
    if not same_folder:
        return {'suitable':False,'reason':'different_folder'}
    def camera_family(name):
        name=Path(name).stem.upper()
        match=re.match(r'^([A-Z]{1,14}[._-]?)([0-9]{3,8})(?:[._-].*)?$',name)
        return (match.group(1),int(match.group(2))) if match else (None,None)
    p,n=camera_family(broken.name)
    q,m=camera_family(candidate.name)
    if not p or p != q:
        return {'suitable':False,'reason':'camera_series_unverified'}
    if diagnosis.get('duration_sec',0)<1:
        return {'suitable':False,'reason':'reference_too_short'}
    # A unique same-folder, same-camera-series candidate is an informed guess,
    # NOT proven compatible; the reconstructed result must still be validated.
    return {'suitable':True,'reason':'same_folder_and_camera_series',
            'confidence':'probable','sequence_distance':abs(n-m),
            'codec':diagnosis.get('codec'), 'width':diagnosis.get('width'),
            'height':diagnosis.get('height')}


def repair_missing_index_copy(source: Path, reference: Path, destination: Path, *,
                              untrunc: str, ffprobe: str, timeout: int=2400):
    """Repair using independently copied damaged footage and unchanged reference.

    Untrunc can create a recovered MP4 inside a private work directory.
    Copy/clone avoids any risk of modifying the broken original. Validate
    before atomically publishing the finished copy; never claim full recovery.
    """
    import shutil
    import tempfile
    if not source.is_file() or not reference.is_file() or source.resolve()==reference.resolve():
        return {'status':'failed','reason':'invalid_reference_or_source'}
    if destination.exists() or destination.resolve(strict=False)==source.resolve():
        return {'status':'failed','reason':'target_exists_or_overlaps_original'}
    ref_diag=diagnose_video(reference,ffprobe=ffprobe)
    if ref_diag.get('status')!='healthy':
        return {'status':'failed','reason':'reference_unreadable'}
    if diagnose_video(source,ffprobe=ffprobe).get('reason')!='missing_index':
        return {'status':'not_needed','reason':'not_missing_index'}
    tool=Path(untrunc)
    if not tool.is_file():
        return {'status':'needs_repair_engine','reason':'untrunc_not_installed'}
    space=shutil.disk_usage(destination.parent)
    size=source.stat().st_size
    required=max(512*1024*1024,size*2+32*1024*1024)
    if space.free < required:
        return {'status':'failed','reason':'insufficient_space',
                'required_gib':round(required/2**30,1),
                'available_gib':round(space.free/2**30,1)}
    with tempfile.TemporaryDirectory(prefix='montara-repair-',dir=str(destination.parent)) as dirname:
        temporary=Path(dirname)
        shadow=temporary/'source.mp4'
        # macOS clonefile (copy-on-write) is faster when both paths share APFS.
        if __import__('sys').platform=='darwin':
            cloned=subprocess.run(['/bin/cp','-c',str(source),str(shadow)],capture_output=True)
            if cloned.returncode:shutil.copyfile(source,shadow)
        else:shutil.copyfile(source,shadow)
        original_size=source.stat().st_size
        original_edge=(source.open('rb').read(65536),)
        try:
            result=subprocess.run([str(tool),'-n',str(reference),str(shadow)],
                        capture_output=True,text=True,timeout=timeout,cwd=str(temporary))
        except (subprocess.TimeoutExpired,OSError):
            return {'status':'failed','reason':'repair_timeout_or_tool_error'}
        # untrunc output naming differs by build: common variants include
        # source.mp4_fixed.mp4 and source.mp4_fixed-dyn.MP4. Discover the
        # produced file instead of assuming one version-specific filename.
        candidates=[p for p in temporary.iterdir()
                    if p.is_file() and p != shadow
                    and p.name.lower().startswith(shadow.name.lower() + '_fixed')
                    and p.suffix.lower()=='.mp4' and p.stat().st_size>=1024]
        fixed=max(candidates,key=lambda p:p.stat().st_size) if candidates else None
        if fixed is None:
            return {'status':'failed','reason':'untrunc_no_recovery'}
        recovered=diagnose_video(fixed,ffprobe=ffprobe)
        if recovered.get('status')!='healthy':
            return {'status':'failed','reason':'recovered_file_failed_validation'}
        # Original content must not be modified by any child process.
        if source.stat().st_size!=original_size or source.open('rb').read(65536)!=original_edge[0]:
            return {'status':'failed','reason':'original_changed_unexpectedly'}
        fixed.replace(destination)
        return {'status':'recovered','reason':'untrunc_reference',
                'duration_sec':recovered.get('duration_sec'),'bytes':destination.stat().st_size,
                'reference_used':True,'original_preserved':True,
                'scope':'structure_and_metadata_checked_not_full_decode'}



def validate_recovered_video(source: Path, *, ffmpeg: str, ffprobe: str, timeout=24):
    """Check metadata and decode brief samples of video/audio; no writes."""
    data=diagnose_video(source,ffprobe=ffprobe)
    if data.get('status')!='healthy':return {'status':'unusable','reason':'metadata_invalid'}
    duration=data['duration_sec']
    stamps=sorted(set(round(t,3) for t in (0.0,max(0.0,duration*0.5-0.5),max(0.0,duration-3))))
    for second in stamps:
        cmd=[ffmpeg,'-hide_banner','-nostdin','-v','error','-ss',str(second),'-i',str(source),'-map','0:v:0','-frames:v','4','-f','null','-']
        try:
            result=subprocess.run(cmd,capture_output=True,timeout=timeout)
        except (OSError,subprocess.TimeoutExpired):return {'status':'unusable','reason':'sample_timeout'}
        if result.returncode:return {'status':'unusable','reason':'video_sample_failed'}
    audio_verified=False
    try:
        details=subprocess.run([ffprobe,'-v','error','-show_entries','stream=codec_type','-of','json',str(source)],capture_output=True,text=True,timeout=timeout)
        streams=json.loads(details.stdout).get('streams',[]) if details.returncode==0 else []
        has_audio=any(v.get('codec_type')=='audio' for v in streams)
        if has_audio:
            cmd=[ffmpeg,'-hide_banner','-nostdin','-v','error','-ss',str(max(0.0,duration*0.5-0.5)),'-i',str(source),'-map','0:a:0','-t','0.5','-f','null','-']
            output=subprocess.run(cmd,capture_output=True,timeout=timeout)
            if output.returncode:return {'status':'unusable','reason':'audio_sample_failed'}
            audio_verified=True
    except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):return {'status':'unusable','reason':'audio_check_failed'}
    return {'status':'healthy','duration_sec':duration,'audio_sample_verified':audio_verified,
            'video_samples_verified':len(stamps),'scope':'sampled_decode_not_full_scan'}
