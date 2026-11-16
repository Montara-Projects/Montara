"""Verify the dedicated H4 broker sees the same private Owner filesystem."""
import json
import os
import socket
import stat
import struct
from pathlib import Path

from urano.h4_instance import H4Instance

OWNER_SOCKET = H4Instance().owner_socket
OWNER_MOUNT = H4Instance().mount
PROBE = {"op": "h4_preflight"}


def owner_identity(root, uid, gid):
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700
            or (info.st_uid, info.st_gid) != (uid, gid)):
        raise ValueError("H4 Owner directory must have mode 0700 and the web UID/GID")
    for name in ("projects.sqlite3", "sessions.sqlite3", "owners.sqlite3", "pending.sqlite3"):
        try:
            db = (root / name).lstat()
        except FileNotFoundError:
            continue  # Owner initializes new databases after preflight.
        if (not stat.S_ISREG(db.st_mode) or db.st_uid != uid or db.st_mode & 0o022):
            raise ValueError("H4 Owner SQLite file has unsafe ownership, permissions or type")
    return [info.st_dev, info.st_ino]


def broker_identity(root, uid, gid):
    if not os.statvfs(root).f_flag & os.ST_RDONLY:
        raise ValueError("H4 broker Owner mount must be read-only")
    return owner_identity(root, uid, gid)


def require_matching_broker(root, control_socket=None):
    control_socket = OWNER_SOCKET if control_socket is None else control_socket
    uid, gid = os.getuid(), os.getgid()
    expected = owner_identity(root, uid, gid)
    try:
        info = control_socket.lstat()
        parent = control_socket.parent.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0
                or parent.st_gid != gid or stat.S_IMODE(parent.st_mode) != 0o710
                or not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0
                or info.st_gid != gid or stat.S_IMODE(info.st_mode) != 0o660):
            raise ValueError("H4 admission socket has unsafe ownership or permissions")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(3)
            conn.connect(str(control_socket))
            _, peer_uid, _ = struct.unpack("3i", conn.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
            if peer_uid != 0:
                raise ValueError("H4 admission socket peer must be the root broker")
            conn.sendall(json.dumps(PROBE).encode())
            with conn.makefile("rb") as response:
                reply = json.loads(response.readline(512))
    except FileNotFoundError as exc:
        raise ValueError("H4 admission socket is missing; start the dedicated broker first") from exc
    except OSError as exc:
        raise ValueError("H4 admission broker is unreachable") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("H4 admission broker returned an invalid preflight response") from exc
    if reply != {"ok": True, "owner_identity": expected}:
        raise ValueError("H4 admission broker does not read this Owner directory")
