"""HTTP project-folder retries cannot create duplicate local projects."""
import importlib.util
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "companion"))
spec = importlib.util.spec_from_file_location("montara_folder_retry_companion", ROOT / "companion" / "companion.py")
companion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(companion)


@pytest.fixture
def folders(tmp_path, monkeypatch):
    home = tmp_path / "state"
    home.mkdir()
    destination = tmp_path / "saved"
    destination.mkdir()
    monkeypatch.setattr(companion, "HOME", home)
    monkeypatch.setattr(companion, "projects", {})
    monkeypatch.setattr(companion, "choose_folder", lambda *_: destination)
    return destination, home


def test_lost_response_retry_reuses_id_and_original_manifest(folders):
    destination, home = folders
    request = {"name": "Session 2026-11-16", "sources": [{"name": "first.mp4"}]}
    status, first = companion.register_project_folder(request)
    assert status == 200
    original = Path(first["folder"]) / "montara-project.json"
    assert original.is_file()
    content = original.read_bytes()
    # The first HTTP response was abandoned; a retry uses the same folder.
    code, repeated = companion.register_project_folder({"name": request["name"], "sources": [{"name": "other.mp4"}]})
    assert code == 200 and repeated == first
    assert original.read_bytes() == content
    assert len(companion.projects) == 1
    assert list(json.loads((home / "projects.json").read_text())) == [first["id"]]


def test_retry_after_process_restart_reuses_persisted_identity(folders):
    destination, home = folders
    _, first = companion.register_project_folder({"name": "Session"})
    companion.projects.clear()
    companion.load_projects()
    status, again = companion.register_project_folder({"name": "Session"})
    assert status == 200 and again == first


def test_unknown_existing_project_is_not_overwritten(folders):
    destination, _ = folders
    existing = destination / "Montara" / "Session"
    existing.mkdir(parents=True)
    original = existing / "montara-project.json"
    original.write_text("private document")
    status, response = companion.register_project_folder({"name": "Session"})
    assert status == 409 and "not registered" in response["error"]
    assert original.read_text() == "private document"


def test_concurrent_folder_dialog_is_rejected_without_opening_second(folders, monkeypatch):
    waiting = threading.Event()
    release = threading.Event()
    called = []
    destination, _ = folders

    def modal(prompt):
        called.append(prompt)
        waiting.set()
        assert release.wait(5)
        return destination

    monkeypatch.setattr(companion, "choose_folder", modal)
    result = []

    def first():
        result.append(companion.register_project_folder({"name": "Session"}))

    thread = threading.Thread(target=first)
    thread.start()
    assert waiting.wait(3)
    try:
        status, response = companion.register_project_folder({"name": "Session"})
        assert status == 409 and "already open" in response["error"]
        assert len(called) == 1
    finally:
        release.set()
        thread.join(5)
    assert result and result[0][0] == 200
