"""Prevent lazy color sampling from changing unedited Stage thumbnail keys.

This is a synthetic backend regression, not an E2E human browser test.
The old LAB-FER engine b867b3c fails this invariant; JM engine 92c7bc3 passes.
"""
from pathlib import Path
import sys

# The engine is a pinned Git submodule and is imported as a Python source tree
# by the end-to-end test environment.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from core.project import atomic_write_json, create_project
from core.shot_review import review_items


def test_late_camera_color_measurement_keeps_stage_thumbnail_asset_keys(tmp_path: Path):
    source = tmp_path / "camera.mp4"
    source.write_bytes(b"synthetic source identity")
    project = create_project("Stage cache keys", str(tmp_path / "review.zuckervid"))
    project.data["inputs"]["videos"] = [{"path": str(source)}]
    project.data["settings"]["wizard"] = {"platform": "youtube"}
    segments = [
        {
            "clip_path": str(source), "source_path": str(source),
            "clip_start_sec": index + 1, "duration_sec": 1,
            "video_light": {"auto": True, "light": 0.0, "shadows": 0.0},
        }
        for index in range(3)
    ]
    atomic_write_json(
        project.artifacts_dir / "edit_plan.json",
        {"platform": "youtube", "segments": segments},
    )
    project.save()

    before = [item["thumbnail_asset"] for item in review_items(project, render_missing=False)]
    assert len(set(before)) == len(segments)

    # The first edit can publish a camera grade after pictures already exist.
    # Subsequent reads must not invalidate untouched shots' image URLs.
    atomic_write_json(
        project.cache_dir / "color_profiles.json",
        {"corrections": {str(source): {"brightness": 1.12}}},
    )
    after = [item["thumbnail_asset"] for item in review_items(project, render_missing=False)]

    assert after == before, (
        "Late camera grading rekeyed untouched Stage thumbnail assets: "
        f"before={before}, after={after}"
    )
