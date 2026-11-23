"""Owner authorization, synthetic object readback and denial contract."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from urano.r2_pilot_quota_gate import QuotaGateError, VerifiedPrincipal, activate_verified
from urano.r2_owner_bridge import upload_synthetic, read_private_asset, verified_google_principal, ensure_asset_catalog, bind_approved_google_owner
from urano.google_oidc import GoogleIdentity

SCHEMA=(Path(__file__).resolve().parents[1]/'ops/r2/pilot_quotas_eu.sql').read_text()

class FakePrivateR2:
    def __init__(self): self.data={}
    def put(self,key,content): self.data[key]=content
    def get(self,key):return self.data.get(key)
    def delete(self,key):self.data.pop(key,None)

class OwnerIsolation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=sqlite3.connect(Path(self.tmp.name)/'test.db')
        self.db.executescript(SCHEMA)
        ensure_asset_catalog(self.db)
        self.store=FakePrivateR2()
        self.fer=VerifiedPrincipal('https://accounts.google.com','verified-fer-test')
        self.jm=VerifiedPrincipal('https://accounts.google.com','verified-jm-test')
        self.t4t=VerifiedPrincipal('https://accounts.google.com','verified-t4t-test')
    def tearDown(self): self.db.close();self.tmp.cleanup()
    def activate(self):
        for tenant,principal in [('fergardel',self.fer),('amehc',self.jm),('t4t',self.t4t)]:
            activate_verified(self.db,tenant,principal)
    def test_verified_google_adapter_rejects_client_dict(self):
        with self.assertRaises(QuotaGateError): verified_google_principal({'sub':'forged'})
        self.assertEqual(verified_google_principal(GoogleIdentity('trusted-test','verified@example.com')).subject,'trusted-test')
    def test_operator_approved_oauth_binding_not_name_based(self):
        approved={'fergardel':'trusted-fer-sub'}
        login=GoogleIdentity('trusted-fer-sub','any_verified_email@example.com')
        with self.assertRaises(QuotaGateError):
            bind_approved_google_owner(self.db,login,'amehc',approved_subject_by_tenant=approved)
        with self.assertRaises(QuotaGateError):
            bind_approved_google_owner(self.db,GoogleIdentity('attacker','fer@example.com'),
                                       'fergardel',approved_subject_by_tenant=approved)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM pilot_tenants WHERE state='pilot_active'").fetchone()[0],0)
        bind_approved_google_owner(self.db,login,'fergardel',approved_subject_by_tenant=approved)
        self.assertEqual(self.db.execute("SELECT state FROM pilot_tenants WHERE tenant_key='fergardel'").fetchone()[0],'pilot_active')
        with self.assertRaises(QuotaGateError):
            bind_approved_google_owner(self.db,login,'fergardel',approved_subject_by_tenant=approved)

    def test_three_tenants_byte_exact_and_cross_read_denied(self):
        self.activate()
        principals=[self.fer,self.jm,self.t4t]
        for i,principal in enumerate(principals):
            content=(f'montara-synthetic-{i}-'.encode()*100)
            receipt=upload_synthetic(self.db,self.store,principal,'test'+str(i),content)
            self.assertEqual(receipt.bytes_written,len(content))
            self.assertEqual(read_private_asset(self.db,self.store,principal,receipt.asset_id),content)
            for other in principals:
                if other==principal:continue
                with self.assertRaises(QuotaGateError):read_private_asset(self.db,self.store,other,receipt.asset_id)
        self.assertEqual(len(self.store.data),3)
        self.assertEqual(self.db.execute("SELECT SUM(used_bytes), SUM(reserved_bytes) FROM pilot_tenants").fetchone(),(sum(len((f'montara-synthetic-{i}-'.encode()*100)) for i in range(3)),0))
    def test_no_login_no_upload(self):
        with self.assertRaises(QuotaGateError):upload_synthetic(self.db,self.store,self.fer,'a',b'a')
        self.assertEqual(self.store.data,{})
    def test_wrong_issuer_denied(self):
        self.activate()
        with self.assertRaises(QuotaGateError):upload_synthetic(self.db,self.store,VerifiedPrincipal('https://evil.example','verified-fer-test'),'bad',b'a')
    def test_corrupt_readback_cleans_reservation(self):
        self.activate()
        class Corrupt(FakePrivateR2):
            def get(self,key):return b'corrupted' if key in self.data else None
        store=Corrupt()
        with self.assertRaises(QuotaGateError):upload_synthetic(self.db,store,self.fer,'bad',b'original')
        self.assertEqual(store.data,{})
        self.assertEqual(self.db.execute("SELECT reserved_bytes,used_bytes FROM pilot_tenants WHERE tenant_key='fergardel'").fetchone(),(0,0))
    def test_untrusted_object_key_not_accessible(self):
        self.activate()
        self.store.put('pilot/fergardel/directly-guessed',b'secret')
        with self.assertRaises(QuotaGateError):read_private_asset(self.db,self.store,self.fer,'directly-guessed')
    def test_replay_asset_id_is_denied(self):
        self.activate()
        upload_synthetic(self.db,self.store,self.fer,'same',b'first')
        with self.assertRaises(QuotaGateError):upload_synthetic(self.db,self.store,self.fer,'same',b'second')
        self.assertEqual(read_private_asset(self.db,self.store,self.fer,'same'),b'first')

if __name__=='__main__':unittest.main()
