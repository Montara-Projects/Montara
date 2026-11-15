import json
import os
import socket
import stat
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from urano import h4_owner_preflight as preflight
from urano.private_broker_service import dispatch_owner


class H4PreflightTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.uid, self.gid = os.getuid(), os.getgid()
        os.chown(self.root, -1, self.gid)

    def test_no_listener_fails_with_actionable_diagnostic(self):
        with patch.object(preflight, "OWNER_SOCKET", self.root / "missing.sock"):
            with self.assertRaisesRegex(ValueError, "socket is missing"):
                preflight.require_matching_broker(self.root)

    def test_linked_catalog_is_rejected(self):
        (self.root / "projects.sqlite3").symlink_to("/dev/null")
        with self.assertRaisesRegex(ValueError, "SQLite file"):
            preflight.owner_identity(self.root, self.uid, self.gid)

    def test_broker_refuses_writeable_owner_mount(self):
        with patch.object(preflight.os, "statvfs", return_value=SimpleNamespace(f_flag=0)):
            with self.assertRaisesRegex(ValueError, "read-only"):
                preflight.broker_identity(self.root, self.uid, self.gid)

    def test_portal_rejects_other_owner_root_at_correct_socket(self):
        conn = MagicMock()
        conn.getsockopt.return_value = struct.pack("3i", 42, 0, 0)
        response = conn.makefile.return_value.__enter__.return_value
        socket_path = MagicMock()
        socket_path.lstat.return_value = SimpleNamespace(
            st_uid=0, st_gid=self.gid, st_mode=stat.S_IFSOCK | 0o660)
        socket_path.parent.lstat.return_value = SimpleNamespace(
            st_uid=0, st_gid=self.gid, st_mode=stat.S_IFDIR | 0o710)
        with patch.object(preflight, "OWNER_SOCKET", socket_path), patch.object(
            socket, "socket"
        ) as factory, patch.object(socket, "SO_PEERCRED", 17, create=True):
            factory.return_value.__enter__.return_value = conn
            identity = preflight.owner_identity(self.root, self.uid, self.gid)
            response.readline.return_value = json.dumps(
                {"ok": True, "owner_identity": [identity[0], identity[1] + 1]}
            ).encode()
            with self.assertRaisesRegex(ValueError, "does not read this Owner directory"):
                preflight.require_matching_broker(self.root)
            response.readline.return_value = json.dumps(
                {"ok": True, "owner_identity": identity}
            ).encode()
            preflight.require_matching_broker(self.root)

    def test_probe_requires_authenticated_web_uid_and_h4_mode(self):
        conn = MagicMock()
        conn.getsockopt.return_value = struct.pack("3i", 42, 1001, 1002)
        conn.recv.return_value = json.dumps(preflight.PROBE).encode()
        with patch.object(socket, "SO_PEERCRED", 17, create=True), patch(
            "urano.private_broker_service.broker_identity", return_value=[1, 2]
        ) as identity:
            with self.assertRaises(PermissionError):
                dispatch_owner(conn, 999, self.root, None, h4_gid=1002)
            identity.assert_not_called()
            with self.assertRaises(ValueError):
                dispatch_owner(conn, 1001, self.root, None)
            identity.assert_not_called()
            self.assertEqual(dispatch_owner(conn, 1001, self.root, None, h4_gid=1002),
                             {"ok": True, "owner_identity": [1, 2]})
