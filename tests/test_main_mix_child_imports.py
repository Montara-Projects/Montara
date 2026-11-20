"""Ensure the isolated -P child has the complete MAIN mix adapter package."""
import os
import subprocess
import sys
from pathlib import Path


def test_preview_child_modules_import_without_current_working_directory(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    script = (
        "from mixer_adapter.session import render_song, prepare_tracks; "
        "from mixer_adapter.single_song import SingleSongMix; "
        "from mixer_adapter.extract import window_command; "
        "from mixer_adapter.render_progress import SongProgress; "
        "from mixer_adapter import source_access; "
        "print('MAIN_MIX_CHILD_IMPORTS_OK')"
    )
    result = subprocess.run(
        [sys.executable, "-P", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "MAIN_MIX_CHILD_IMPORTS_OK" in result.stdout
