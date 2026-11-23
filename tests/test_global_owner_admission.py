"""Cross-broker atomic owner-wide FIFO RAM admission security tests."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest
from urano.global_owner_admission import GlobalOwnerAdmission,GlobalAdmissionDenied


def key(n):
    return "job-"+format(n,"032x")


@pytest.fixture
def store(tmp_path):
    return GlobalOwnerAdmission(tmp_path/"shared.sqlite3",capacity_gib=24)


def test_single_and_multiple_brokers_one_shared_budget(store):
    first=store.ask("owner-a",key(1),"jmlab",6)
    second=store.ask("owner-b",key(2),"main",8)
    third=store.ask("owner-c",key(3),"fertrial",8)
    fourth=store.ask("owner-d",key(4),"main",8)
    assert [x.state for x in (first,second,third,fourth)] == [
        "reserved","reserved","reserved","queued"]
    assert fourth.position==1
    assert store.status(key(4),"owner-d").position==1
    assert store.mark_running(key(1),"owner-a")=="running"
    with pytest.raises(GlobalAdmissionDenied):
        store.release_verified(key(1),"owner-a")
    store.mark_stopping(key(1),"owner-a")
    store.release_verified(key(1),"owner-a",cgroup_verified_empty=True)
    assert store.status(key(4),"owner-d").state=="reserved"


def test_fifo_does_not_bypass_older_large_job(store):
    assert store.ask("a",key(1),"main",20).state=="reserved"
    assert store.ask("b",key(2),"jmlab",8).state=="queued"
    assert store.ask("c",key(3),"main",2).position==2
    assert store.status(key(3),"c").state=="queued"
    store.release_verified(key(1),"a",cgroup_verified_empty=True)
    assert store.status(key(2),"b").state=="reserved"
    assert store.status(key(3),"c").state=="reserved"


def test_same_owner_cannot_overallocate_with_two_brokers(store):
    store.ask("person",key(1),"jmlab",6)
    assert store.ask("person",key(2),"main",8).state=="queued"
    # A second render by the same person waits instead of taking another
    # reservation, even when started through a different trusted broker.
    assert store.status(key(2),"person").position==1
    # Idempotent from same broker, different requested RAM disallowed.
    assert store.ask("person",key(1),"jmlab",6).state=="reserved"
    with pytest.raises(GlobalAdmissionDenied):
        store.ask("person",key(1),"jmlab",12)


def test_queue_owner_visibility_and_cancellation(store):
    store.ask("a",key(1),"main",24)
    store.ask("b",key(2),"jmlab",6)
    assert store.status(key(2),"b").position==1
    with pytest.raises(GlobalAdmissionDenied):
        store.status(key(2),"a")
    assert store.cancel_queued(key(2),"b")=="cancelled"
    with pytest.raises(GlobalAdmissionDenied):
        store.mark_running(key(2),"b")
    assert store.ask("b",key(3),"jmlab",6).position==1


def test_reserved_cgroup_still_counts_when_orphaned(store):
    store.ask("a",key(1),"main",20)
    store.mark_orphaned(key(1),"a")
    assert store.ask("b",key(2),"jmlab",6).state=="queued"
    with pytest.raises(GlobalAdmissionDenied):
        store.release_verified(key(1),"a",cgroup_verified_empty=False)
    assert store.status(key(2),"b").state=="queued"
    store.release_verified(key(1),"a",cgroup_verified_empty=True)
    assert store.status(key(2),"b").state=="reserved"


def test_atomic_requests_from_multiple_broker_processes(store):
    def request(i):
        local=GlobalOwnerAdmission(store.path,capacity_gib=24)
        return local.ask("owner-"+str(i),key(i+1),
                         ("jmlab","main","fertrial")[i%3],6)
    with ThreadPoolExecutor(max_workers=12) as pool:
        rows=list(pool.map(request,range(12)))
    assert sum(row.state=="reserved" for row in rows)==4
    assert sum(row.state=="queued" for row in rows)==8
    with sqlite3.connect(store.path) as db:
        used=db.execute("""SELECT COALESCE(SUM(requested_gib),0)
            FROM global_owner_admission WHERE state='reserved'""").fetchone()[0]
    assert used<=24


def test_rejects_malformed_operator_identity_and_oversized_memory(store):
    with pytest.raises(GlobalAdmissionDenied):
        store.ask("../foreign",key(1),"jmlab",6)
    with pytest.raises(GlobalAdmissionDenied):
        store.ask("person","job-a","main",6)
    with pytest.raises(GlobalAdmissionDenied):
        store.ask("person",key(1),"other",6)
    with pytest.raises(GlobalAdmissionDenied):
        store.ask("person",key(1),"main",25)


def test_owner_multiple_pending_does_not_block_another_owner(store):
    assert store.ask("owner-a",key(1),"jmlab",6).state=="reserved"
    assert store.ask("owner-a",key(2),"main",8).state=="queued"
    # Other owners can use the spare RAM even though A has queued again.
    assert store.ask("owner-b",key(3),"main",8).state=="reserved"
    assert store.ask("owner-c",key(4),"main",8).state=="reserved"
    assert store.status(key(2),"owner-a").state=="queued"
    store.release_verified(key(1),"owner-a",cgroup_verified_empty=True)
    assert store.status(key(2),"owner-a").state=="reserved"


def test_same_owner_pending_queue_limit(store):
    assert store.ask("person",key(1),"main",6).state=="reserved"
    for i in range(2,10):
        assert store.ask("person",key(i),"jmlab",6).state=="queued"
    with pytest.raises(GlobalAdmissionDenied):
        store.ask("person",key(10),"main",6)
