"""Reusable JM quality gate; no portal, credentials or V2 implementation."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import time
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('core_fixture', ROOT / 'tools/core_v2_media_fixture.py')
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)


@pytest.fixture(scope='module')
def bank(tmp_path_factory):
    path = tmp_path_factory.mktemp('core-media') / 'bank'
    media.generate(path)
    return path


def test_bank_has_two_distinct_cameras_and_time_markers(bank):
    manifest = media.verify_inputs(bank)
    assert len(manifest['files']) == 4
    assert media.frame_color(bank / 'camera-a.mp4', .5)[0] == 'red'
    assert media.frame_color(bank / 'camera-a.mp4', 4)[0] == 'green'
    assert media.frame_color(bank / 'camera-b.mp4', .5)[0] == 'blue'
    assert media.frame_color(bank / 'camera-b.mp4', 4)[0] == 'yellow'


def test_existing_destination_never_overwritten(bank):
    before = {p.name: media.sha256(p) for p in bank.iterdir()}
    with pytest.raises(FileExistsError):
        media.generate(bank)
    assert before == {p.name: media.sha256(p) for p in bank.iterdir()}


@pytest.mark.parametrize('damage', ['content', 'symlink', 'recipe'])
def test_integrity_rejects_changed_or_redirected_inputs(bank, tmp_path, damage):
    copy = tmp_path / 'bank'
    shutil.copytree(bank, copy)
    path = copy / 'camera-a.mp4'
    if damage == 'content':
        with path.open('r+b') as target:
            first = target.read(1)
            target.seek(0)
            target.write(bytes([first[0] ^ 1]))
    elif damage == 'symlink':
        path.unlink()
        path.symlink_to(bank / 'camera-a.mp4')
    else:
        recipe = copy / 'recipe.json'
        recipe.write_text('{}')
    with pytest.raises(ValueError):
        media.verify_inputs(copy)


def test_camera_original_is_not_a_correct_montage(bank):
    with pytest.raises(ValueError, match='Wrong camera/source time'):
        media.verify_output(bank, bank / 'camera-a.mp4', width=640, height=360)


@pytest.fixture(scope='module')
def rendered(bank, tmp_path_factory):
    # Explicit opt-in: this imports the pinned Engine from a scratch layout,
    # without touching any installed Companion or starting a listening server.
    if os.environ.get('MONTARA_CORE_FIXTURE_RENDER') != '1':
        pytest.skip('Set MONTARA_CORE_FIXTURE_RENDER=1 for isolated real Engine export')
    from test_local_video import install_layout, fingerprint
    from video_jobs import VideoJobs
    root = tmp_path_factory.mktemp('core-render')
    home = root / 'companion'
    _, sha = install_layout(home)
    recipe = json.loads((bank / 'recipe.json').read_text())
    assert sha == recipe['engine'], 'Fixture and actual Engine must have the same pin'
    project = root / 'project'
    project.mkdir()
    # Existing renderer resolves master within the user-authorized project.
    master = project / f'montara-render-audio-{uuid.uuid4().hex}.audio'
    shutil.copy2(bank / 'master.wav', master)
    sources = [bank / 'camera-a.mp4', bank / 'camera-b.mp4']
    originals = [{'source': key, 'original': {'name': path.name,
                  'size': path.stat().st_size, 'fingerprint': fingerprint(path)}}
                 for key, path in enumerate(sources)]
    manager = VideoJobs(home)
    project_id = 'a' * 16
    payload = {'project': project_id, 'master': master.name,
               'recipe': recipe, 'originals': originals,
               'branding': 'none', 'name': 'CORE-V2-synthetic-acceptance'}
    before = {p.name: media.sha256(p) for p in bank.iterdir()}
    token = manager.start(payload, {project_id: project},
                          lambda original: next((p for p in sources if p.name == original['name']), None))
    deadline = time.monotonic() + 180
    while manager.status(token)['status'] not in ('ready', 'failed') and time.monotonic() < deadline:
        time.sleep(.1)
    status = manager.status(token)
    if status['status'] != 'ready':
        log = project / '.montara-renders' / token / 'render.log'
        manager.cancel(token)
        pytest.fail(f'{status}\n{log.read_text()[-4000:] if log.exists() else "no render log"}')
    output = manager.output(token)
    assert before == {p.name: media.sha256(p) for p in bank.iterdir()}
    manifest = json.loads((project / '.montara-renders' / token / 'render.json').read_text())
    assert manifest['source_files'] == {str(k): str(p.resolve()) for k, p in enumerate(sources)}
    return bank, output, manager, home, token


def test_real_renderer_uses_cuts_source_times_and_selected_master(rendered):
    bank, output, manager, _, token = rendered
    report = media.verify_output(bank, output)
    assert report['status'] == 'PASS'
    assert manager.status(token)['progress'] == 1
    media.write_json_new(output.parent / 'quality-report.json', report)


def test_completed_output_survives_job_manager_reopen(rendered):
    _, output, _, home, token = rendered
    from video_jobs import VideoJobs
    reopened = VideoJobs(home)
    assert reopened.status(token)['status'] == 'ready'
    assert reopened.output(token) == output


def test_oracle_rejects_camera_audio_instead_of_master(rendered, tmp_path):
    bank, output, _, _, _ = rendered
    wrong = tmp_path / 'wrong-master.mp4'
    media.execute(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(output),
                   '-i', str(bank / 'camera-a.mp4'), '-map', '0:v:0', '-map', '1:a:0',
                   '-c', 'copy', '-shortest', str(wrong)])
    with pytest.raises(ValueError, match='Audio does not match'):
        media.verify_output(bank, wrong)
