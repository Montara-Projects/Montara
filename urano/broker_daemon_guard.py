"""Exclusive, local daemon startup guard for a single Owner broker ledger.

Only the systemd-managed root broker entrypoint should call this guard.
Creating an operator/helper DemoBroker instance must never acquire the lock,
unlink another daemon's live sockets or perform crash reconciliation.
"""
from __future__ import annotations

from contextlib import contextmanager
import errno
import fcntl
import os
from pathlib import Path
import socket
import stat


class BrokerAlreadyActive(RuntimeError):
    """Another authoritative broker already owns this ledger or socket."""


@contextmanager
def exclusive_broker_daemon(ledger_path: Path):
    ledger_path = Path(ledger_path)
    directory = ledger_path.parent
    if (not ledger_path.is_absolute() or directory.is_symlink()
            or not directory.is_dir() or directory.stat().st_mode & 0o022):
        raise RuntimeError("Untrusted broker ledger directory")
    lock_path = directory / "authoritative-daemon.lock"
    flags = os.O_CREAT | os.O_RDWR | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(lock_path, flags, 0o600)
    try:
        state = os.fstat(fd)
        if (not stat.S_ISREG(state.st_mode) or state.st_nlink != 1 or
                state.st_uid != os.geteuid() or state.st_mode & 0o077):
            raise RuntimeError("Untrusted broker daemon lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BrokerAlreadyActive("Authoritative broker daemon already active") from exc
        yield
    finally:
        os.close(fd)


def refuse_live_broker_socket(path: Path) -> None:
    """Refuse a second daemon even if the previous version lacked our lock."""
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError("Broker socket symlink forbidden")
    if not path.exists():
        return
    if not stat.S_ISSOCK(path.lstat().st_mode):
        raise RuntimeError("Broker socket path is not a socket")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(0.3)
        status = client.connect_ex(str(path))
    if status == 0:
        raise BrokerAlreadyActive("Another broker is accepting connections")
    if status != errno.ECONNREFUSED:
        raise RuntimeError("Unable to prove broker socket is stale")
