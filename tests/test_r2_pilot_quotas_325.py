"""Portable regressions for the EU D1 pilot quota schema and atomic reservation gate."""
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

SCHEMA=(Path(__file__).resolve().parents[1]/'ops/r2/pilot_quotas_eu.sql').read_text()

class Quotas(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db_path=Path(self.tmp.name)/'quotas.db'
        self.db=sqlite3.connect(self.db_path)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(SCHEMA)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_three_equal_pilot_limits_no_active_auth(self):
        data=self.db.execute('SELECT tenant_key, plan, quota_bytes, state, oauth_subject FROM pilot_tenants ORDER BY tenant_key').fetchall()
        self.assertEqual(data,[('amehc','basic',100_000_000_000,'pending_identity',None),('fergardel','basic',100_000_000_000,'pending_identity',None),('t4t','basic',100_000_000_000,'pending_identity',None)])

    def test_cannot_activate_without_verified_identity(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE pilot_tenants SET state='pilot_active' WHERE tenant_key='amehc'")
        self.db.rollback()
        n=self.db.execute("UPDATE pilot_tenants SET reserved_bytes=1 WHERE tenant_key='amehc' AND state='pilot_active'").rowcount
        self.assertEqual(n,0)

    def test_oversize_and_negative_fail(self):
        for value in (-1,100_000_000_001):
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute('UPDATE pilot_tenants SET reserved_bytes=? WHERE tenant_key=\'fergardel\'',(value,))
            self.db.rollback()
        self.assertEqual(self.db.execute('SELECT reserved_bytes FROM pilot_tenants WHERE tenant_key=\'fergardel\'').fetchone()[0],0)

    def test_concurrent_reservations_not_overbooking(self):
        self.db.execute("UPDATE pilot_tenants SET oauth_issuer='google', oauth_subject='fake-test-sub',state='pilot_active' WHERE tenant_key='fergardel'")
        self.db.commit()
        barrier=threading.Barrier(2)
        wins=[]
        def compete(index):
            connection=sqlite3.connect(self.db_path,timeout=3)
            barrier.wait()
            connection.execute('BEGIN IMMEDIATE')
            cur=connection.execute("UPDATE pilot_tenants SET reserved_bytes=reserved_bytes+60000000000 WHERE tenant_key='fergardel' AND state='pilot_active' AND used_bytes+reserved_bytes+60000000000<=quota_bytes")
            wins.append(cur.rowcount)
            connection.commit()
            connection.close()
        tasks=[threading.Thread(target=compete,args=(n,)) for n in range(2)]
        for t in tasks:t.start()
        for t in tasks:t.join()
        self.assertEqual(sorted(wins),[0,1])
        self.assertEqual(self.db.execute("SELECT reserved_bytes FROM pilot_tenants WHERE tenant_key='fergardel'").fetchone()[0],60_000_000_000)

    def test_no_cross_tenant_subject(self):
        self.db.execute("UPDATE pilot_tenants SET oauth_issuer='google',oauth_subject='same-sub' WHERE tenant_key='amehc'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE pilot_tenants SET oauth_issuer='google',oauth_subject='same-sub' WHERE tenant_key='t4t'")

if __name__=='__main__':unittest.main()
