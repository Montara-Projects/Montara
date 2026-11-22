"""#359: distinguish Engine HTTP 409/503 from the Owner gateway, safely.

Uses real Google-Owner session/CSRF/project registry and the real Flask Owner
gateway; only the downstream Unix descriptor transport is a test double.
This DOES NOT substitute for Linux SO_PEERCRED or browser E2E.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flask import Flask

from urano.native_owner_web_gateway import native_owner_gateway_blueprint
from urano.native_owner_workspace_registry import NativeOwnerWorkspaceRegistry
from urano.project_catalog import ProjectCatalog
from urano.session_auth import SESSION_COOKIE, SessionStore

ORIGIN="https://montara.test"


class StubReply:
    def __init__(self,status):
        self.status=status
        self.body=json.dumps({
            "error":{"code":"stale_edit" if status==409 else "worker_busy",
                     "message":"Render is still running"}
        } if status!=200 else {"index":3,"revision":"a"*20}).encode()

    def getheader(self,header,default=None):
        return {"Content-Type":"application/json"}.get(header,default)

    def read(self,size):
        return self.body[:size]


class StubSocket:
    def __init__(self,status,requests):
        self.status=status
        self.requests=requests
        self.timeout=0
        self.sock=None

    def request(self,method,path,body=None,headers=None):
        self.requests.append((method,path,headers))

    def getresponse(self):
        return StubReply(self.status)

    def close(self):
        pass


class StageErrorOriginTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="s359-",dir="/tmp")
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        sessions=SessionStore(root/"sessions.sqlite3")
        registry=NativeOwnerWorkspaceRegistry(ProjectCatalog(root/"projects.sqlite3"))
        self.issued=sessions.issue("owner-test")
        self.status=200
        self.connect_fails=False
        self.requests=[]
        self.ensure_calls=[]

        def ensure_worker(operation,token,csrf,workspace_id):
            self.ensure_calls.append(operation)
            if self.connect_fails:
                raise TimeoutError("private socket path SHOULD NEVER BE ECHOED")
            return {"ok":True,"state":"ready","project_id":workspace_id,"generation":1}

        def connect_worker(token,csrf,workspace_id,generation):
            if self.connect_fails or generation!=1:
                raise TimeoutError("private descriptor timed out / DO NOT ECHO")
            return StubSocket(self.status,self.requests)

        app=Flask("stage-error-source-359")
        app.register_blueprint(native_owner_gateway_blueprint(
            sessions,registry,https_origin=ORIGIN,
            ensure_worker=ensure_worker,connect_worker=connect_worker))
        self.client=app.test_client()
        self.client.set_cookie(SESSION_COOKIE,self.issued.token,domain="montara.test")
        self.auth={"Origin":ORIGIN,"X-Urano-CSRF":self.issued.csrf}
        self.assertEqual(self.client.post("/urano/v1/native/ensure",headers=self.auth,
             base_url=ORIGIN).status_code,200)

    def call(self,headers=None):
        return self.client.get(
            "/urano/v1/native/rpc/api/v1/edit/shot?index=3",
            headers=self.auth if headers is None else headers,
            base_url=ORIGIN)

    def test_engine_upstream_409_and_503_keep_body_and_origin(self):
        for code in (409,503):
            with self.subTest(code=code):
                self.status=code
                r=self.call({**self.auth,"X-Montara-Engine-Generation":"1"})
                self.assertEqual(r.status_code,code)
                self.assertEqual(r.headers["X-Montara-Stage-Origin"],"engine")
                self.assertIn("owner;dur=",r.headers["Server-Timing"])
                self.assertIn("broker;dur=",r.headers["Server-Timing"])
                self.assertIn("engine;dur=",r.headers["Server-Timing"])
                self.assertEqual(r.json["error"]["code"],
                                 "stale_edit" if code==409 else "worker_busy")
                self.assertEqual(self.requests[-1][:2],
                                 ("GET","/api/v1/edit/shot?index=3"))
                exposed=str(r.headers)+r.get_data(as_text=True)
                for secret in (self.issued.token,self.issued.csrf,
                               "DO NOT ECHO"):
                    if secret:self.assertNotIn(secret,exposed)

    def test_save_conflict_preserves_engine_409_without_any_replay(self):
        self.status=409
        scope={**self.auth,"X-Montara-Engine-Generation":"1"}
        data={"project_id":"/private/Projects/test.zuckervid",
              "revision":"a"*20,"index":3,"choice":0,
              "edit_component":"movement","apply_to_source":False}
        outcome=self.client.post(
            "/urano/v1/native/rpc/api/v1/edit/shot/save",
            headers=scope,base_url=ORIGIN,json=data)
        self.assertEqual(outcome.status_code,409,outcome.get_data(as_text=True))
        self.assertEqual(outcome.headers["X-Montara-Stage-Origin"],"engine")
        self.assertEqual(outcome.json["error"]["code"],"stale_edit")
        self.assertEqual(len(self.requests),1,"A stale Save must never replay")
        self.assertEqual(self.requests[0][:2],("PATCH","/api/v1/edit/shot"))

    def test_owner_broker_timeout_503_not_misattributed_to_engine(self):
        self.connect_fails=True
        before=len(self.requests)
        r=self.call({**self.auth,"X-Montara-Engine-Generation":"1"})
        self.assertEqual(r.status_code,503)
        self.assertEqual(r.headers["X-Montara-Stage-Origin"],"owner-gateway")
        self.assertIn("owner;dur=",r.headers["Server-Timing"])
        self.assertNotIn("engine;dur=",r.headers["Server-Timing"])
        self.assertNotIn("private descriptor",r.get_data(as_text=True))
        self.assertEqual(len(self.requests),before)

    def test_owner_generation_409_not_misattributed_to_cloudflare(self):
        r=self.call()
        self.assertEqual(r.status_code,409)
        self.assertEqual(r.headers["X-Montara-Stage-Origin"],"owner-gateway")
        self.assertIn("owner;dur=",r.headers["Server-Timing"])

    def test_authentication_and_csrf_required_before_any_worker_request(self):
        before=len(self.requests)
        r=self.call({"Origin":ORIGIN,"X-Urano-CSRF":"f"*64,
                     "X-Montara-Engine-Generation":"1"})
        self.assertEqual(r.status_code,403)
        self.assertEqual(len(self.requests),before)

    def test_success_has_timing_and_no_error_origin(self):
        r=self.call({**self.auth,"X-Montara-Engine-Generation":"1"})
        self.assertEqual(r.status_code,200)
        self.assertIn("engine;dur=",r.headers["Server-Timing"])
        self.assertNotIn("X-Montara-Stage-Origin",r.headers)


if __name__=="__main__":
    unittest.main()
