import pytest

from urano.session_auth import SessionStore
from urano.session_retention_report import count_eligible


def test_report_counts_boundary_without_changing_either_catalog(tmp_path):
    first = tmp_path / "first.sqlite3"
    second = tmp_path / "second.sqlite3"
    store = SessionStore(first)
    store.issue("owner-a", now=10, ttl_seconds=10)
    current = store.issue("owner-a", now=10, ttl_seconds=11)
    SessionStore(second).issue("owner-b", now=10, ttl_seconds=10)
    previous = [path.read_bytes() for path in (first, second)]

    assert count_eligible(first, cutoff=19) == 0
    assert count_eligible(first, cutoff=20) == 1
    assert store.verify(current.token, now=20) is not None
    assert [path.read_bytes() for path in (first, second)] == previous


def test_report_rejects_snapshot_with_sidecar(tmp_path):
    path = tmp_path / "snapshot.sqlite3"
    SessionStore(path)
    path.with_name(path.name + "-wal").touch()
    with pytest.raises(ValueError, match="offline"):
        count_eligible(path, cutoff=20)
