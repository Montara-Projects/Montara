"""Isolated quota-view and R2 S3 adapter tests. No real keys or network."""
import io
import sqlite3
import unittest
from pathlib import Path
from urano.r2_pilot_quota_gate import QuotaGateError, VerifiedPrincipal, activate_verified
from urano.r2_pilot_status import owner_quota_status
from urano.r2_owner_bridge import upload_synthetic, read_private_asset
from urano.r2_private_s3 import PrivateR2S3Storage, R2StorageConfigurationError

SCHEMA=(Path(__file__).resolve().parents[1]/'ops/r2/pilot_quotas_eu.sql').read_text()

class FakeS3:
    def __init__(self):self.items={};self.calls=[]
    def put_object(self,**kw):
        self.calls.append(('put',kw['Key']));self.items[(kw['Bucket'],kw['Key'])]=kw['Body']
    def get_object(self,**kw):
        self.calls.append(('get',kw['Key']))
        data=self.items[(kw['Bucket'],kw['Key'])]
        return {'ContentLength':len(data),'Body':io.BytesIO(data)}
    def delete_object(self,**kw):
        self.calls.append(('delete',kw['Key']))
        self.items.pop((kw['Bucket'],kw['Key']),None)

class PilotStatusS3Tests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript(SCHEMA)
        self.jm=VerifiedPrincipal('https://accounts.google.com','jm-verified-sub')
        self.t4t=VerifiedPrincipal('https://accounts.google.com','t4t-verified-sub')
        self.fer=VerifiedPrincipal('https://accounts.google.com','fer-verified-sub')
    def tearDown(self):self.db.close()
    def test_unmapped_or_unactivated_quota_denied(self):
        with self.assertRaises(QuotaGateError):owner_quota_status(self.db,self.jm)
    def test_each_active_owner_gets_only_own_basic_100gb(self):
        for name,identity in [('amehc',self.jm),('t4t',self.t4t),('fergardel',self.fer)]:
            activate_verified(self.db,name,identity)
        self.db.execute("UPDATE pilot_tenants SET used_bytes=3000,reserved_bytes=2000 WHERE tenant_key='amehc'")
        for p in (self.jm,self.t4t,self.fer):
            status=owner_quota_status(self.db,p).as_public_json()
            self.assertEqual(status['quota_bytes'],100_000_000_000)
            self.assertEqual(status['available_bytes'],status['quota_bytes']-status['used_bytes']-status['reserved_bytes'])
            self.assertNotIn('tenant_key',status)
            self.assertNotIn('oauth_subject',status)
        self.assertEqual(owner_quota_status(self.db,self.jm).used_bytes,3000)
        self.assertEqual(owner_quota_status(self.db,self.t4t).used_bytes,0)
    def test_s3_transport_with_isolated_owner_access_and_sha(self):
        for name,p in [('amehc',self.jm),('t4t',self.t4t)]:activate_verified(self.db,name,p)
        fake=FakeS3();s3=PrivateR2S3Storage(fake,'montara-media-eu-pilot')
        receipt=upload_synthetic(self.db,s3,self.jm,'smoke',b'synthetic-only\0'*40)
        self.assertEqual(read_private_asset(self.db,s3,self.jm,'smoke'),b'synthetic-only\0'*40)
        with self.assertRaises(QuotaGateError):read_private_asset(self.db,s3,self.t4t,'smoke')
        self.assertEqual(receipt.bytes_written,len(b'synthetic-only\0'*40))
        self.assertTrue(all(k.startswith('pilot/amehc/') for _,k in fake.calls))
    def test_private_transport_rejects_arbitrary_paths_and_big_fixture(self):
        fake=FakeS3();s3=PrivateR2S3Storage(fake,'montara-media-eu-pilot')
        for key in ('../private', 'pilot/t4t/evil', 'pilot/amehc/'+'a'*31):
            with self.assertRaises(R2StorageConfigurationError):s3.get(key)
        with self.assertRaises(R2StorageConfigurationError):s3.put('pilot/amehc/'+'a'*32,b'a'*(1024*1024+1))
        self.assertFalse(fake.calls)
    def test_no_missing_credentials_in_client_factory(self):
        from urano.r2_private_s3 import build_private_r2_s3_client
        with self.assertRaises(R2StorageConfigurationError):build_private_r2_s3_client(account_id='bad',access_key_id='x',secret_access_key='x')
        with self.assertRaises(R2StorageConfigurationError):build_private_r2_s3_client(account_id='a'*32,access_key_id='',secret_access_key='')

if __name__=='__main__':unittest.main()
