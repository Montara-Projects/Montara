"""Run with JM private Owner overlay on PYTHONPATH."""
import importlib.util
from pathlib import Path
import pytest


def test_restrict_owner_audio_project_rpc():
    file=Path(__file__).resolve().parents[1]/'ops/jm/audio-projects-379/native_owner_mix_http.py'
    spec=importlib.util.spec_from_file_location('test_private_audio_mix_route',file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    route=module.native_mix_target
    valid='a'*32
    for method,p in [('GET','/montara/mix/projects'),('POST','/montara/mix/projects'),
                     ('GET',f'/montara/mix/projects/{valid}'),('POST',f'/montara/mix/projects/{valid}/delete')]:
        assert route(method,p) is not None,(method,p)
    for method,p in [('DELETE',f'/montara/mix/projects/{valid}/delete'),('GET','/montara/mix/projects/../../etc/passwd'),
                     ('POST','/montara/mix/projects/notanid/delete'),('POST',f'/montara/mix/projects/{valid}'),
                     ('GET',f'/montara/mix/projects/{valid}/delete')]:
        assert route(method,p) is None,(method,p)
    assert route('GET','/montara/mix/projects','owner=other') is None
