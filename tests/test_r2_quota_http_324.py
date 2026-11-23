"""Quota HTTP contract denies unauthenticated access and owner impersonation."""
import unittest
from flask import Flask, request
from urano.r2_pilot_quota_gate import QuotaGateError, VerifiedPrincipal
from urano.r2_pilot_status import OwnerQuotaStatus
from urano.r2_quota_http import quota_blueprint

class QuotaHttpTests(unittest.TestCase):
    def app(self, principal):
        app=Flask(__name__)
        app.register_blueprint(quota_blueprint(lambda:principal, lambda p: OwnerQuotaStatus('basic',100_000_000_000,10,20,100_000_000_000-30)))
        return app.test_client()
    def test_unauthenticated_denied(self):
        r=self.app(None).get('/api/v1/storage/quota')
        self.assertEqual(r.status_code,403)
        self.assertEqual(r.headers['Cache-Control'],'no-store, private')
    def test_browser_cannot_forge_identity_by_parameters(self):
        r=self.app(VerifiedPrincipal('google','real-sub')).get('/api/v1/storage/quota?tenant_key=t4t&subject=fake',headers={'X-OAuth-Subject':'fake'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json,dict(plan='basic',quota_bytes=100_000_000_000,used_bytes=10,reserved_bytes=20,available_bytes=100_000_000_000-30))
        self.assertNotIn('tenant_key',r.json)
        self.assertNotIn('subject',r.json)
        self.assertIn('Cookie',r.headers['Vary'])
    def test_unapproved_owner_denied(self):
        def deny(_):raise QuotaGateError('no binding')
        app=Flask(__name__)
        app.register_blueprint(quota_blueprint(lambda:VerifiedPrincipal('google','unbound'),deny))
        self.assertEqual(app.test_client().get('/api/v1/storage/quota').status_code,403)

if __name__=='__main__':unittest.main()
