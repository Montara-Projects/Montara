"""The opt-in H4 queue must stay private and preserve live brokers by default."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from urano.private_broker_service import DemoBroker
from urano.global_owner_admission import GlobalOwnerAdmission
from urano.job_recovery_ledger import JobLease


def key(n):
    return "job-"+format(n,"032x")


def test_existing_running_owners_are_not_redirected_to_unconfigured_queue():
    # Global allocation is explicitly opt-in. No production release
    # silently changes the broker's default admission behavior.
    source=Path("urano/private_broker_service.py").read_text()
    assert "global_admission=None" in source
    assert "if args.global_admission_db else None" in source


def test_broker_ensure_reports_owned_queued_position_without_worker(tmp_path):
    db=GlobalOwnerAdmission(tmp_path/"admission.sqlite3",capacity_gib=6)
    db.ask("first-owner",key(1),"main",6)
    queued=db.ask("second-owner",key(2),"jmlab",6)
    assert queued.state=="queued"
    lease=JobLease("second-owner","project-1",key(2),1,"starting")
    broker=object.__new__(DemoBroker)
    broker.global_admission=db
    broker.resources=SimpleNamespace(memory_mb=6144)
    broker.ledger=SimpleNamespace(
        instance=SimpleNamespace(name="jmlab"),
        unverified_for_owner=lambda _: (lease,),
    )
    broker._launch_reserved_lease=MagicMock(side_effect=AssertionError("queued worker launched"))
    result=broker.ensure_owner("second-owner","project-1")
    assert result=={"ok":True,"project_id":"project-1",
                    "state":"queued","queue_position":1,"generation":1}
    broker._launch_reserved_lease.assert_not_called()


def test_gateway_exposes_position_only_no_job_ids_or_fake_eta():
    source=Path("urano/native_owner_web_gateway.py").read_text()
    block=source[source.index("if (isinstance(result,dict) and result.get(\"ok\") is True"):
                 source.index("if (not isinstance(result,dict)",source.index("if (isinstance(result,dict)"))]
    assert 'response=jsonify(state="queued",position=position)' in block
    assert 'response.status_code=202' in block
    assert 'response.headers["Retry-After"]="5"' in block
    assert "job_id" not in block and "owner_id" not in block


def test_browser_renders_status_for_auth_owner_not_arbitrary_eta():
    source=Path("urano/native_owner_browser_bridge.js").read_text()
    assert "response.status===202 && value.state==='queued'" in source
    assert "queueNote.textContent='Your job is queued · position '" in source
    assert "await new Promise(resolve=>setTimeout(resolve,5000))" in source
    assert "minutes remaining" not in source


def test_broker_restart_keeps_unlaunched_queue_but_fences_running(tmp_path):
    from urano.job_recovery_ledger import JobRecoveryLedger
    from urano.h4_instance import H4Instance
    db=JobRecoveryLedger(tmp_path/"jobs.sqlite3",instance=H4Instance("jmlab"))
    waiting=db.start_trusted("queued-owner","queue-project")
    launched=db.start_trusted("active-owner","active-project")
    db.reserve_target_unit(launched)
    orphaned=db.recover_after_restart(preserve_unlaunched_queued=True)
    assert len(orphaned)==1 and orphaned[0].job_id==launched.job_id
    assert db.get_trusted(waiting.job_id).state=="starting"
    assert db.target_for_trusted(waiting) is None
    assert db.get_trusted(launched.job_id).state=="orphaned"
