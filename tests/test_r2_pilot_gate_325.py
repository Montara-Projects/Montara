import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urano.r2_pilot_quota_gate import (
    MAX_ASSET_BYTES,QuotaGateError,VerifiedPrincipal,
    activate_verified,reserve_upload,release_upload,commit_upload,
)

SCHEMA=(Path(__file__).resolve().parents[1]/'ops/r2/pilot_quotas_eu.sql').read_text()

class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'test.db'
        self.db=sqlite3.connect(self.path,timeout=10)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(SCHEMA)
        self.fer=VerifiedPrincipal('https://accounts.google.com','fer-test-sub')
        self.jm=VerifiedPrincipal('https://accounts.google.com','jm-test-sub')
        self.exp=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_unlinked_cannot_reserve(self):
        with self.assertRaises(QuotaGateError):
            reserve_upload(self.db,self.fer,'asset',100,expires_at=self.exp)
        self.assertEqual(self.db.execute("SELECT reserved_bytes FROM pilot_tenants WHERE tenant_key='fergardel'").fetchone()[0],0)

    def test_bound_and_quota(self):
        activate_verified(self.db,'fergardel',self.fer)
        with self.assertRaises(QuotaGateError):
            reserve_upload(self.db,self.fer,'bad',MAX_ASSET_BYTES+1,expires_at=self.exp)
        tokens=[reserve_upload(self.db,self.fer,'asset'+str(i),MAX_ASSET_BYTES,expires_at=self.exp) for i in range(4)]
        with self.assertRaises(QuotaGateError):
            reserve_upload(self.db,self.fer,'over',1,expires_at=self.exp)
        self.assertEqual(len(tokens),len(set(tokens)))
        self.assertTrue(release_upload(self.db,self.fer,tokens[0]))
        self.assertFalse(release_upload(self.db,self.fer,tokens[0]))
        self.assertTrue(commit_upload(self.db,self.fer,tokens[1],MAX_ASSET_BYTES))
        self.assertFalse(commit_upload(self.db,self.fer,tokens[1],MAX_ASSET_BYTES))
        self.assertEqual(self.db.execute("SELECT used_bytes,reserved_bytes FROM pilot_tenants WHERE tenant_key='fergardel'").fetchone(),(MAX_ASSET_BYTES,2*MAX_ASSET_BYTES))

    def test_cross_tenant_cannot_read_reservation(self):
        activate_verified(self.db,'fergardel',self.fer)
        activate_verified(self.db,'amehc',self.jm)
        token=reserve_upload(self.db,self.fer,'fer_asset',123,expires_at=self.exp)
        with self.assertRaises(QuotaGateError): release_upload(self.db,self.jm,token)
        with self.assertRaises(QuotaGateError): commit_upload(self.db,self.jm,token,123)
        with self.assertRaises(QuotaGateError): commit_upload(self.db,self.fer,token,122)
        self.assertTrue(commit_upload(self.db,self.fer,token,123))
        self.assertEqual(self.db.execute("SELECT used_bytes FROM pilot_tenants WHERE tenant_key='amehc'").fetchone()[0],0)

    def test_asset_idempotency_rollback(self):
        activate_verified(self.db,'fergardel',self.fer)
        reserve_upload(self.db,self.fer,'same_asset',100,expires_at=self.exp)
        with self.assertRaises(sqlite3.IntegrityError):
            reserve_upload(self.db,self.fer,'same_asset',100,expires_at=self.exp)
        self.assertEqual(self.db.execute("SELECT reserved_bytes FROM pilot_tenants WHERE tenant_key='fergardel'").fetchone()[0],100)

    def test_two_writers_safely_serialize(self):
        activate_verified(self.db,'fergardel',self.fer)
        self.db.execute("UPDATE pilot_tenants SET used_bytes=90000000000 WHERE tenant_key='fergardel'")
        self.db.commit()
        barrier=threading.Barrier(2)
        results=[]
        def job(i):
            db=sqlite3.connect(self.path,timeout=10)
            barrier.wait()
            try:reserve_upload(db,self.fer,'asset'+str(i),6_000_000_000,expires_at=self.exp);results.append('ok')
            except QuotaGateError:results.append('denied')
            db.close()
        threads=[threading.Thread(target=job,args=(i,)) for i in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertEqual(sorted(results),['denied','ok'])
        self.assertEqual(self.db.execute("SELECT reserved_bytes FROM pilot_tenants WHERE tenant_key='fergardel'").fetchone()[0],6_000_000_000)

    def test_suspended_user_cannot_reserve(self):
        activate_verified(self.db,'fergardel',self.fer)
        self.db.execute("UPDATE pilot_tenants SET state='suspended' WHERE tenant_key='fergardel'")
        self.db.commit()
        with self.assertRaises(QuotaGateError):reserve_upload(self.db,self.fer,'asset',10,expires_at=self.exp)

if __name__=='__main__':unittest.main()
