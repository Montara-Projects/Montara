"""Isolated route-contract test for the MAIN Owner logo overlay.

Usage: python ops/main/logo-340/test_stage_contract.py /path/to/overlay
No live service, Owner data or production project is accessed.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: test_stage_contract.py PATH_TO_STAGED_MAIN_OVERLAY")
target = Path(sys.argv[1]) / "urano/native_owner_stage_http.py"
assert target.is_file()
spec = spec_from_file_location("_main_logo_stage_contract", target)
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
route = module.native_stage_route
positive = [
    ("GET", "/montara/branding", "", "json"),
    ("POST", "/montara/branding", "", "branding"),
    ("POST", "/montara/logo", "", "logo-upload"),
    ("GET", "/montara/logo", "", "review-media"),
    ("GET", "/montara/logo", "t=123456", "review-media"),
]
negative = [
    ("POST", "/montara/logo", "t=1"),
    ("GET", "/montara/logo", "t=bogus"),
    ("GET", "/montara/logo", "t=1&t=2"),
    ("GET", "/montara/logo", "file=../../project"),
    ("DELETE", "/montara/logo", ""),
    ("GET", "/montara/branding", "x=1"),
    ("GET", "/montara/logos", ""),
]
for method, path, query, kind in positive:
    result = route(method, path, query)
    assert result is not None and result.kind == kind, (method, path, query)
for case in negative:
    assert route(*case) is None, case
print(f"MAIN_LOGO_STAGE_CONTRACT_PASS {len(positive)+len(negative)} cases")
