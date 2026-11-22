"""Pre-deployment gate for a root-owned JM Owner overlay.

Run: python3 tests/test_jm_355_owner_css_asset_pins.py /opt/montara/jmlab-issue355csspin-20261122
The test does NOT need credentials or change project files.
"""
from __future__ import annotations
import hashlib
import pathlib
import re
import sys

def check(path: pathlib.Path) -> None:
    surface = path / "urano/native_owner_browser_surface.py"
    css = path / "web/montara.css"
    js = path / "web/montara.js"
    wsgi = list(path.glob("jmlab_*wsgi.py"))
    assert surface.is_file() and css.is_file() and js.is_file()
    assert len(wsgi) == 1, f"Expected one versioned release WSGI, found {len(wsgi)}"
    source = surface.read_text(encoding="utf-8")
    wsgi_src = wsgi[0].read_text(encoding="utf-8")
    for name, asset in [("montara.css", css), ("montara.js", js)]:
        matches = re.findall(r'"' + re.escape(name) + r'"\s*:\s*"([a-f0-9]{64})"', source)
        assert len(matches) == 1, f"Missing or duplicate Owner static pin for {name}"
        actual = hashlib.sha256(asset.read_bytes()).hexdigest()
        assert matches[0] == actual, f"Owner {name} pin stale: actual={actual}, pinned={matches[0]}"
        assert actual in wsgi_src, f"WSGI does not pin deployed {name}"
    surface_hash = hashlib.sha256(surface.read_bytes()).hexdigest()
    assert surface_hash in wsgi_src, "WSGI must also pin Owner surface source"
    assert "text/css" in source
    assert "abort(503)" in source, "Fail-closed static route contract changed"
    print("JM_355_OWNER_CSS_PIN_PASS stylesheet, javascript, browser surface and WSGI integrity")

if __name__ == "__main__":
    assert len(sys.argv) == 2, "Usage: test_jm_355_owner_css_asset_pins.py <root-owned-overlay>"
    check(pathlib.Path(sys.argv[1]).resolve(strict=True))
