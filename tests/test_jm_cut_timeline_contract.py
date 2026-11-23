"""LAB-JM-only music cut transport and zoom-timeline regression gate.

These tests are synthetic: they do not touch real Owners or claim E2E drag.
"""
from pathlib import Path
import re
import pytest
from urano.native_owner_stage_http import native_stage_route

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("method,path,query,accepted,kind", [
    ("GET", "/api/v1/edit/timeline", "kind=music", True, "json"),
    ("PATCH", "/api/v1/edit/timeline", "", True, "timeline-patch"),
    ("PATCH", "/api/v1/edit/timeline", "kind=music", False, None),
    ("POST", "/api/v1/edit/timeline", "", False, None),
    ("POST", "/api/v1/edit/timeline/save", "", False, None),
    ("GET", "/api/v1/edit/timeline", "kind=show", False, None),
    ("GET", "/api/v1/edit/timeline", "", False, None),
    ("DELETE", "/api/v1/edit/timeline", "", False, None),
])
def test_only_reviewed_music_timeline_routes(method,path,query,accepted,kind):
    target=native_stage_route(method,path,query)
    assert bool(target)==accepted
    if accepted:
        assert target.upstream==path+('?' + query if query else '')
        assert target.kind==kind


def test_browser_uses_dedicated_owner_post_alias():
    js=(ROOT/"urano/native_owner_browser_bridge.js").read_text()
    assert "const timelineWrite = operation==='api/v1/edit/timeline'" in js
    assert "method==='PATCH' && !address.search" in js
    assert "timelineSave ? nativePrefix+'api/v1/edit/timeline/save'" in js
    assert "const wireMethod=(shotSave||timelineSave)?'POST':method" in js
    assert "montara/mix/projects" in js


def test_gateway_constrains_music_roll_and_preserves_engine_errors():
    gateway=(ROOT/"urano/native_owner_web_gateway.py").read_text()
    assert 'path=="/api/v1/edit/timeline/save" and not query' in gateway
    assert 'upstream_path=("/api/v1/edit/shot" if shot_tunnel else' in gateway
    assert 'if kind=="timeline-patch":' in gateway
    assert 'set(value)!={"kind","project_id","revision","index","at"}' in gateway
    assert 'value.get("kind")!="music"' in gateway
    assert 'not math.isfinite(value["at"])' in gateway
    assert 'X-Montara-Stage-Origin' in gateway


def test_edit_shows_zoomed_same_cut_bar_without_frame_thumbnails():
    cut=(ROOT/"web/cut-editor.js").read_text()
    assert 'function makeCutTrack(doc,scene,label,onSelect,options={})' in cut
    assert "if(options.pxPerSecond)bed.style.width=" in cut
    assert "const zoomArea=document.createElement('section')" in cut
    assert "className='music-cut-zoom'" in cut
    assert "const track=makeCutTrack(currentCutDocument" in cut
    assert "options.onSaved?.(saved)" in cut
    assert 'rollPreview(next)' in cut
    assert re.search(r"onpointerup=.*save\(next\)",cut)
    assert "onpointercancel" in cut
    assert "reviewBlob" not in cut  # No new 360 or preview implementation
