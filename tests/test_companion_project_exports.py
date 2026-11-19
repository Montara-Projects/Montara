import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "companion"))
import video_jobs


def test_publish_concurrent_unicode_exports_without_overwrite(tmp_path):
    root = tmp_path.resolve()
    project = root / "Proyecto"
    project.mkdir()
    # Distinct completed jobs have distinct work files. Reusing the same
    # source is not a valid two-render test: Windows publish uses move/rename,
    # whereas POSIX uses hard links and retains the source.
    sources = [project / "finished-1.mp4", project / "finished-2.mp4"]
    for source in sources:
        source.write_bytes(b"complete MP4")
    name = video_jobs.export_name("Canción 日本語.mp4")
    with ThreadPoolExecutor(2) as pool:
        outputs = list(pool.map(lambda src: video_jobs.publish_export(src, project, name), sources))
    assert {p.name for p in outputs} == {"Canción 日本語.mp4", "Canción 日本語 (2).mp4"}
    assert all(path.read_bytes() == b"complete MP4" for path in outputs)
    other = root / "Otro"
    other.mkdir()
    third = project / "finished-3.mp4"
    third.write_bytes(b"complete MP4")
    assert video_jobs.publish_export(third, other, name) == other / "Exports" / f"{name}.mp4"


def test_publish_refuses_linked_export_directory_and_missing_project(tmp_path):
    project = tmp_path.resolve() / "project"
    project.mkdir()
    (project / "Exports").symlink_to(tmp_path, target_is_directory=True)
    source = project / "finished.mp4"
    source.touch()
    with pytest.raises(OSError):
        video_jobs.publish_export(source, project, "Video")
    with pytest.raises(OSError):
        video_jobs.publish_export(source, project / "missing", "Video")
    assert not (tmp_path / "Video.mp4").exists()


def test_reparse_directory_is_rejected():
    path = Mock()
    path.lstat.return_value = Mock(st_mode=0o040700, st_file_attributes=0x400)
    with pytest.raises(OSError):
        video_jobs.real_directory(path)


@pytest.mark.parametrize("outcome", ["ready", "failed", "cancelled"])
def test_job_publication_failure_preserves_download_only_if_complete(tmp_path, monkeypatch, outcome):
    root = tmp_path.resolve()
    jobs = video_jobs.VideoJobs(root / "companion")
    work = root / "work"
    work.mkdir()
    output = work / "finished.mp4"
    job = dict(status="queued", path=output, folder=root, name="Video", project="project",
               work=work, snapshot=work / "progress.json", download_name="Video.mp4")
    jobs.jobs["a" * 32] = job

    def finish(**_):
        output.write_bytes(b"finished" if outcome == "ready" else b"partial")
        if outcome == "cancelled":
            job["status"] = "cancelled"
        return int(outcome == "failed")

    monkeypatch.setattr(video_jobs.subprocess, "Popen", lambda *args, **kwargs: Mock(wait=finish))
    denied = Mock(side_effect=PermissionError("Exports is read-only"))
    monkeypatch.setattr(video_jobs, "publish_export", denied)
    jobs._run("a" * 32)
    assert jobs.status("a" * 32)["status"] == outcome
    if outcome == "ready":
        assert jobs.output("a" * 32) == output
        assert jobs.status("a" * 32)["saved_in_project"] is False
        assert video_jobs.VideoJobs(root / "companion").output("a" * 32) == output
    else:
        denied.assert_not_called()
        assert not output.exists()
        assert jobs.output("a" * 32) is None
    assert not (root / "Exports").exists()


@pytest.mark.parametrize(("platform", "command", "argument"), [
    ("darwin", "/usr/bin/open", "-R"),
    ("win32", "explorer.exe", "/select,"),
])
def test_open_folder_uses_only_the_completed_authorized_result(tmp_path, monkeypatch, platform, command, argument):
    root = tmp_path.resolve()
    folder = root / "Exports"
    folder.mkdir()
    target = folder / "Música final.mp4"
    target.touch()
    jobs = video_jobs.VideoJobs(root / "companion")
    process = Mock()
    monkeypatch.setattr(video_jobs.subprocess, "Popen", process)
    jobs.jobs["token"] = dict(status="queued", saved_in_project=True, path=target, project="authorized")
    with pytest.raises(ValueError):
        jobs.open_folder("token", {"authorized": root}, platform=platform)
    jobs.jobs["token"]["status"] = "ready"
    with pytest.raises(ValueError):
        jobs.open_folder("token", {}, platform=platform)
    process.assert_not_called()
    jobs.open_folder("token", {"authorized": root}, platform=platform)
    args = process.call_args.args[0]
    assert args[0] == command and args[1].startswith(argument) and args[-1].endswith(str(target))


def test_same_request_reuses_job_but_new_request_can_retry(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    jobs = video_jobs.VideoJobs(root / "companion")
    monkeypatch.setattr(jobs, "runtime", lambda: {"engine": "test"})
    monkeypatch.setattr(video_jobs, "validate", lambda recipe: recipe)
    monkeypatch.setattr(video_jobs.threading, "Thread", lambda **_: Mock())
    master = "montara-render-audio-" + "0" * 32 + ".audio"
    (root / master).write_bytes(b"audio")
    body = dict(request_id="a" * 32, project="p", master=master, originals=[],
                recipe=dict(engine="test", sources=[], segments=[]))
    token = jobs.start(body, {"p": root}, None)
    assert jobs.start(body, {"p": root}, None) == token
    assert len(jobs.jobs) == 1
    jobs.jobs[token]["status"] = "failed"
    assert jobs.start({**body, "request_id": "b" * 32}, {"p": root}, None) != token


def test_open_folder_http_requires_origin_and_rejects_browser_paths(tmp_path, monkeypatch):
    import http.client
    import threading
    from http.server import ThreadingHTTPServer
    import companion

    jobs = video_jobs.VideoJobs(tmp_path)
    open_folder = Mock()
    monkeypatch.setattr(jobs, "open_folder", open_folder)
    monkeypatch.setattr(companion, "video_jobs", jobs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), companion.Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    token = "a" * 32
    route = f"/video-renders/{token}/open-folder"
    try:
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        for origin, payload, expected in (
            ("https://untrusted.example", "{}", 403),
            ("http://127.0.0.1:8101", '{"path":"/tmp"}', 400),
            ("http://127.0.0.1:8101", "{}", 200),
        ):
            connection.request("POST", route, payload, {"Origin": origin, "Content-Type": "application/json"})
            response = connection.getresponse()
            assert response.status == expected
            response.read()
        connection.close()
        open_folder.assert_called_once_with(token, companion.projects)
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_retry_after_restart_keeps_finished_bytes_and_is_idempotent(tmp_path):
    root = tmp_path.resolve()
    token = "c" * 32
    work = root / ".montara-renders" / token
    work.mkdir(parents=True)
    source = work / "finished.mp4"
    source.write_bytes(b"finished video")
    home = root / "companion"
    jobs = video_jobs.VideoJobs(home)
    jobs.jobs[token] = dict(status="ready", progress=1, path=source,
                            work=work, snapshot=work / "progress.json",
                            project="p", download_name="Canción.mp4",
                            saved_in_project=False, save_warning="Exports unavailable")
    jobs._save_completed()
    jobs = video_jobs.VideoJobs(home)
    assert jobs.output(token).read_bytes() == b"finished video"
    exports = root / "Exports"
    exports.symlink_to(root / ".montara-renders", target_is_directory=True)
    with pytest.raises(OSError):
        jobs.retry_publication(token, {"p": root})
    assert source.read_bytes() == b"finished video"
    exports.unlink()
    result = jobs.retry_publication(token, {"p": root})
    assert result["saved_in_project"] is True
    assert jobs.retry_publication(token, {"p": root}) == result
    assert list(exports.iterdir()) == [exports / "Canción.mp4"]
    assert video_jobs.VideoJobs(home).output(token).read_bytes() == b"finished video"
