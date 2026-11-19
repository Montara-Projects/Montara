"""Original-quality rendering jobs; all filesystem access is resolved locally."""
import hashlib,json,os,re,signal,stat,subprocess,threading,time,uuid,sys
from pathlib import Path
from video_recipe import validate


def stop_process_tree(process):
    """Stop this worker and its FFmpeg descendants, including separate groups."""
    if process.poll() is not None:return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       capture_output=True, timeout=10)
        process.wait(timeout=5)
        return
    rows=subprocess.check_output(['ps','-Ao','pid=,ppid='],text=True).splitlines()
    children={}
    for line in rows:
        pid,parent=map(int,line.split());children.setdefault(parent,[]).append(pid)
    tree=[]
    def collect(pid):
        for child in children.get(pid,[]):collect(child)
        tree.append(pid)
    collect(process.pid)
    for pid in tree:
        try:os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:pass
    try:process.wait(timeout=2)
    except subprocess.TimeoutExpired:pass
    # Children can ignore TERM even after their parent has exited.
    for pid in tree:
        try:os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:pass
    process.wait(timeout=5)


def real_directory(path):
    """Reject symbolic links and Windows reparse points, including junctions."""
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise OSError('The export folder is not a regular directory')
    return info


def export_name(value):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', '-', str(value or ''))
    name = re.sub(r'\.mp4$', '', name.strip(' .'), flags=re.I)
    name = name[:70].strip(' .') or 'Montara video'
    if re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]', name.split('.')[0], re.I):
        name = '_' + name
    return name


def export_directory(project):
    if project.resolve(strict=True) != project:
        raise OSError('The authorized project folder changed')
    real_directory(project)
    folder = project / 'Exports'
    folder.mkdir(exist_ok=True)
    real_directory(folder)
    if folder.resolve(strict=True) != folder:
        raise OSError('Exports must stay inside the authorized project')
    return folder


def publish_export(source, project, name, *, before_publish=None):
    """Publish a complete MP4 without replacing any existing directory entry."""
    folder = export_directory(project)
    initial = real_directory(folder)
    directory_fd = None
    if os.link in os.supports_dir_fd:
        directory_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if directory_fd is not None and not os.path.samestat(initial, os.fstat(directory_fd)):
            raise OSError('The export folder changed')
        suffix = 1
        while True:
            filename = name + (f' ({suffix})' if suffix > 1 else '') + '.mp4'
            target = folder / filename
            if not os.path.samestat(real_directory(folder),
                                   initial):
                raise OSError('The export folder changed')
            if folder.resolve(strict=True) != folder:
                raise OSError('The export folder changed')
            if before_publish is not None:
                # Persist the exact candidate *before* a Windows rename may
                # remove the only surviving work-directory filename.
                before_publish(target)
            try:
                if os.name == 'nt':
                    # Windows rename fails if the name already exists.
                    source.rename(target)
                elif directory_fd is None:
                    os.link(source, target)
                else:
                    os.link(source, filename, dst_dir_fd=directory_fd, follow_symlinks=False)
            except FileExistsError:
                suffix += 1
                continue
            return target
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


def output_fingerprint(path):
    # A bounded content check prevents a stale journal from being recovered
    # against an unrelated file with the same export name.
    with path.open('rb') as handle:
        first = handle.read(65536)
        handle.seek(max(0, path.stat().st_size - 65536))
        last = handle.read(65536)
    return hashlib.sha256(first + last + str(path.stat().st_size).encode()).hexdigest()


class VideoJobs:
    def __init__(self,home):
        self.home=Path(home)/'video';self.jobs={};self.lock=threading.Lock();self.slot=threading.Semaphore(1)
        try:
            saved=json.loads((self.home/'completed-jobs.json').read_text())
            if not isinstance(saved,dict):saved={}
            for token,row in saved.items():
                if not re.fullmatch('[a-f0-9]{32}',token) or not isinstance(row,dict):continue
                path=Path(row['path'])
                work=Path(row['work'])
                pending=row.get('pending_path')
                recovered=False
                if (isinstance(pending, str) and isinstance(row.get('pending_fingerprint'), str)
                        and work.name == token and work.parent.name == '.montara-renders'):
                    candidate=Path(pending)
                    project=work.parent.parent
                    try:
                        if (candidate.parent == project/'Exports'
                                and candidate.resolve(strict=True) == candidate
                                and stat.S_ISREG(candidate.lstat().st_mode)
                                and candidate.stat().st_size > 0
                                and output_fingerprint(candidate) == row['pending_fingerprint']):
                            path=candidate
                            recovered=True
                    except OSError:
                        pass
                if path.is_file() and path.stat().st_size>0:
                    self.jobs[token]={'status':'ready','progress':1.,'path':path,'work':work,
                                      'snapshot':Path(row['snapshot']),'download_name':path.name if recovered else row['download_name'],
                                      'diagnostics':row.get('diagnostics',[]), 'project':row.get('project'),
                                      'saved_in_project':True if recovered else row.get('saved_in_project',False),
                                      'save_warning':None if recovered else row.get('save_warning'),
                                      'request_hash':row.get('request_hash')}
        except (OSError,ValueError,KeyError,TypeError):pass

    def _save_completed(self):
        rows={token:{k:str(job[k]) for k in ('path','work','snapshot','download_name')}
              for token,job in self.jobs.items() if job['status']=='ready'}
        for token,row in rows.items():
            for key in ('diagnostics','project','saved_in_project','save_warning','request_hash',
                        'pending_path','pending_fingerprint'):
                if key in self.jobs[token]:row[key]=self.jobs[token][key]
        self.home.mkdir(parents=True,exist_ok=True)
        temporary=self.home/'completed-jobs.tmp'
        with temporary.open('w') as handle:
            handle.write(json.dumps(dict(list(rows.items())[-30:])))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(self.home/'completed-jobs.json')

    def renderer_python(self, *, platform=None):
        # The renderer is installed independently from the native MSIX tray.
        # Preserve POSIX runtimes while using the Windows venv convention.
        if (os.name if platform is None else platform) == 'nt':
            return self.home / 'venv' / 'Scripts' / 'python.exe'
        return self.home / 'venv' / 'bin' / 'python'

    def runtime(self):
        python=self.renderer_python();marker=self.home/'ENGINE_COMMIT'
        if (self.home/'INSTALLING').exists():return None
        if not os.access(python, os.X_OK) or not (self.home/'local_video.py').is_file():return None
        if not (self.home/'engine/core/stages/export.py').is_file():return None
        try:sha=marker.read_text().strip()
        except (OSError, UnicodeError):return None
        return {'engine':sha} if re.fullmatch('[a-f0-9]{40}',sha) else None

    def start(self,body,projects,find_original):
        request_id = body.get('request_id')
        if request_id is not None and (not isinstance(request_id, str)
                                      or not re.fullmatch(r'[a-f0-9]{32}', request_id)):
            raise ValueError('Invalid export request ID')
        request_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if request_id:
            with self.lock:
                previous = self.jobs.get(request_id)
                if previous is not None:
                    if previous.get('request_hash') != request_hash:
                        raise ValueError('The export request ID is already in use')
                    return request_id
        locate_started=time.monotonic()
        runtime=self.runtime()
        if not runtime:raise ValueError('Install the companion video renderer before exporting originals')
        recipe=validate(body.get('recipe'))
        if recipe['engine']!=runtime['engine']:raise ValueError('Update the companion to the editor version on this page')
        folder=projects.get(body.get('project'))
        if folder is None or not folder.is_dir():raise ValueError('Choose the project folder on this computer')
        master=body.get('master')
        if not isinstance(master,str) or not re.fullmatch(r'montara-render-audio-[a-f0-9]{32}\.audio',master):raise ValueError('Choose the exported master')
        master=folder/master
        if not master.is_file() or not 0<master.stat().st_size<=1024**3:raise ValueError('Send the master audio before rendering')
        mapping=body.get('originals')
        if not isinstance(mapping,list) or len(mapping)!=len(recipe['sources']):raise ValueError('Locate every original video')
        source_files={};verified={}
        for item in mapping:
            key=item.get('source') if isinstance(item,dict) else None
            if isinstance(key,bool) or not isinstance(key,int) or key in source_files or key not in [s['key'] for s in recipe['sources']]:raise ValueError('Invalid original source mapping')
            if item.get('original'):
                # Companion validates name, size and edge fingerprint before lookup.
                original=item['original']
                if not isinstance(original,dict) or not isinstance(original.get('name'),str) or '/' in original['name'] or '\\' in original['name'] or not isinstance(original.get('size'),int) or isinstance(original['size'],bool) or not isinstance(original.get('fingerprint'),str) or not re.fullmatch('[a-f0-9]{64}',original['fingerprint']):raise ValueError('Invalid original identity')
                path=find_original(original)
                if path:
                    path=Path(path)
                    with path.open('rb') as handle:
                        first=handle.read(65536);handle.seek(max(0,path.stat().st_size-65536));last=handle.read(65536)
                    if path.stat().st_size!=original['size'] or hashlib.sha256(first+last).hexdigest()!=original['fingerprint']:raise ValueError('Source '+str(key)+' · '+original['name']+': original changed. Reconnect it before exporting.')
            else:
                name=item.get('asset')
                if not isinstance(name,str) or not re.fullmatch(r'montara-render-source-[a-f0-9]{32}\.(mp4|mov|mkv|webm|mts)',name):raise ValueError('Invalid source asset')
                path=folder/name
            if not path or not Path(path).is_file() or Path(path).suffix.lower() not in {'.mp4','.mov','.m4v','.mts','.mkv','.avi','.webm'}:raise ValueError('Source '+str(key)+' · '+str((item.get('original') or {}).get('name') or item.get('asset') or 'video')+': original unavailable. Reconnect its drive and retry.')
            source_files[key]=str(Path(path).resolve())
            if item.get('original'):verified[key]=item['original']
        branding=body.get('branding','none')
        if branding not in ('none','montara','mine'):raise ValueError('Choose a logo option')
        personal_logo=None
        if branding=='mine':
            name=body.get('logo')
            if not isinstance(name,str) or not re.fullmatch(r'montara-render-logo-[a-f0-9]{32}\.png',name):raise ValueError('Send your logo before rendering')
            logo=folder/name
            if logo.is_symlink() or not logo.is_file() or not 0<logo.stat().st_size<=10*1024*1024:raise ValueError('The logo is unavailable')
            import struct
            with logo.open('rb') as handle:header=handle.read(24)
            if len(header)!=24 or header[:8]!=b'\x89PNG\r\n\x1a\n' or header[12:16]!=b'IHDR':raise ValueError('Choose a PNG logo')
            width,height=struct.unpack('>II',header[16:24])
            if not 1<=width<=1600 or not 1<=height<=1600:raise ValueError('Resize your logo before rendering')
            personal_logo=str(logo.resolve())
        with self.lock:
            if request_id in self.jobs:
                previous = self.jobs[request_id]
                if previous.get('request_hash') != request_hash:
                    raise ValueError('The export request ID is already in use')
                return request_id
            if sum(j['status'] in ('queued','rendering') for j in self.jobs.values())>=2:raise ValueError('Wait for the current video export')
            real_directory(folder)
            folder = folder.resolve(strict=True)
            folder_info = real_directory(folder)
            token = request_id or uuid.uuid4().hex
            work_root = folder / '.montara-renders'
            work_root.mkdir(exist_ok=True)
            real_directory(work_root)
            if work_root.resolve(strict=True) != work_root:
                raise ValueError('The local render folder is not inside the project')
            work = work_root / token
            work.mkdir()
            name = export_name(body.get('name'))
            output = work / 'finished.mp4'
            progress=work/'progress.json'
            manifest={'verified_originals':verified,'personal_logo':personal_logo,'recipe':recipe,'source_files':source_files,'master':str(master),'branding':branding,'work':str(work),'output':str(output),'progress':str(progress),'source_lookup_sec':round(time.monotonic()-locate_started,3),
                      'spherical_cache':str(self.home/'spherical-cache'/runtime['engine'])}
            (work/'render.json').write_text(json.dumps(manifest))
            for key in [k for k,j in self.jobs.items() if j['status'] in ('ready','failed','cancelled')][:-30]:self.jobs.pop(key)
            self.jobs[token]={'diagnostics':recipe.get('diagnostics',[]),'status':'queued','progress':0,'path':output,'work':work,'snapshot':progress,'download_name':name+'.mp4', 'name':name, 'project':body.get('project'), 'folder':folder, 'folder_info':folder_info, 'request_hash':request_hash,
                              'tasks':[{'id':f'segment-{i+1}','label':f'Shot {i+1}/{len(recipe["segments"])}','percent':0} for i in range(len(recipe['segments']))]}
        threading.Thread(target=self._run,args=(token,),daemon=True).start()
        return token

    def _run(self,token):
        job=self.jobs[token]
        with self.slot:
            with self.lock:
                if job['status']=='cancelled':return
                job['status']='rendering'
                job['started_monotonic']=time.monotonic()
            try:
                with (job['work']/'render.log').open('wb') as log:
                    with self.lock:
                        if job['status']=='cancelled':return
                        process=subprocess.Popen([str(self.renderer_python()),str(self.home/'local_video.py'),str(job['work']/'render.json')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                        job['process']=process
                    try:code=process.wait(timeout=21600)
                    except subprocess.TimeoutExpired:
                        self.cancel(token);raise RuntimeError('The video render exceeded its time limit')
                job.pop('process',None)
                with self.lock:
                    if job['status']=='cancelled' or code:
                        job['path'].unlink(missing_ok=True)
                        if job['status']=='cancelled':return
                    if code or not job['path'].is_file() or job['path'].stat().st_size == 0:
                        raise RuntimeError('The original-quality render failed. The diagnostic is saved in the project folder.')
                    # First make the finished work copy discoverable on a
                    # process restart, before publication can move it on NTFS.
                    job.update(status='ready', progress=1., saved_in_project=False)
                    try:
                        self._save_completed()
                        folder_info = job.get('folder_info')
                        if folder_info is not None and not os.path.samestat(folder_info, real_directory(job['folder'])):
                            raise OSError('The authorized project folder changed')
                        published = publish_export(job['path'], job['folder'], job['name'],
                                                   before_publish=lambda path: self._prepare_publication(job, path))
                    except OSError:
                        job.update(saved_in_project=False, save_warning=
                                   'Could not save to Exports. Check the project drive and folder permissions, or download the finished video.')
                    else:
                        source=job['path']
                        job.update(path=published, download_name=published.name, saved_in_project=True)
                        job.pop('save_warning', None)
                        try:
                            self._save_completed()
                        except OSError:
                            pass  # Journal can recover the moved Windows output.
                        else:
                            try:
                                source.unlink(missing_ok=True)
                            except OSError:
                                pass
                    job.pop('pending_path', None)
                    job.pop('pending_fingerprint', None)
            except Exception as exc:
                if job['status']!='cancelled':job.update(status='failed',error=str(exc)[:250])

    def _prepare_publication(self, job, target):
        # Called under self.lock. Persist intent for each collision candidate
        # before Windows moves finished.mp4; recovery verifies the bytes.
        job['pending_path'] = str(target)
        job['pending_fingerprint'] = output_fingerprint(job['path'])
        self._save_completed()

    def cancel(self,token):
        job=self.jobs.get(token)
        if not job:return False
        with self.lock:
            if job['status'] in ('ready','failed'):return True
            job['status']='cancelled'
            process=job.get('process')
        if process and process.poll() is None:
            stop_process_tree(process)
        return True

    def status(self,token):
        job=self.jobs.get(token)
        if not job:return None
        result={k:job[k] for k in ('status','progress','error','tasks','diagnostics') if k in job}
        if job['status']=='ready':
            result.update(filename=job['download_name'], saved_in_project=job.get('saved_in_project',False))
            if job.get('save_warning'):result['save_warning']=job['save_warning']
        if job['status']=='rendering' and 'started_monotonic' in job:
            result['elapsed_sec']=round(max(0.,time.monotonic()-job['started_monotonic']),1)
        if job['status']=='rendering':
            try:
                snap=json.loads(job['snapshot'].read_text())
                result.update(progress=min(.99,float(snap.get('progress') or 0)),message=str(snap.get('message') or '')[:200])
                if isinstance(snap.get('tasks'),list):result['tasks']=snap['tasks']
            except (OSError,ValueError,TypeError):pass
        return result

    def output(self,token):
        job=self.jobs.get(token)
        return job['path'] if job and job['status']=='ready' else None

    def retry_publication(self, token, projects):
        with self.lock:
            job = self.jobs.get(token)
            if not job or job['status'] != 'ready':
                raise ValueError('The finished render is unavailable')
            if job.get('saved_in_project'):
                return self.status(token)
            registered = projects.get(job.get('project'))
            if registered is None:
                raise ValueError('Reconnect the authorized project folder')
            real_directory(registered)
            project = registered.resolve(strict=True)
            source = job['path']
            if (source != project / '.montara-renders' / token / 'finished.mp4'
                    or source.resolve(strict=True) != source
                    or not stat.S_ISREG(source.lstat().st_mode)
                    or source.stat().st_size == 0):
                raise ValueError('The finished video is unavailable in the authorized project')
            published = publish_export(
                source, project, export_name(job['download_name']),
                before_publish=lambda path: self._prepare_publication(job, path))
            job.update(path=published, download_name=published.name, saved_in_project=True)
            job.pop('save_warning', None)
            try:
                self._save_completed()
            except OSError:
                pass  # Journal recovers the Windows move if the update fails.
            else:
                try:
                    source.unlink(missing_ok=True)
                except OSError:
                    pass
            job.pop('pending_path', None)
            job.pop('pending_fingerprint', None)
            return self.status(token)

    def open_folder(self, token, projects, *, platform=None):
        job = self.jobs.get(token)
        if not job or job['status'] != 'ready' or not job.get('saved_in_project'):
            raise ValueError('This export is not available in the project folder')
        project = projects.get(job.get('project'))
        if project is None:
            raise ValueError('Reconnect the authorized project folder')
        real_directory(project)
        project = project.resolve(strict=True)
        path = job['path']
        folder = project / 'Exports'
        real_directory(folder)
        if (path.parent != folder or path.resolve(strict=True) != path
                or not stat.S_ISREG(path.lstat().st_mode)
                or getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('The export is no longer in the authorized project folder')
        platform = sys.platform if platform is None else platform
        if platform == 'darwin':
            command = ['/usr/bin/open', '-R', str(path)]
        elif platform == 'win32':
            command = ['explorer.exe', '/select,' + str(path)]
        else:
            raise ValueError('Opening the export folder is available on Mac and Windows')
        subprocess.Popen(command)
