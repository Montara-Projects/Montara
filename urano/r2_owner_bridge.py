"""Isolated R2 pilot backend contract. Not a deployed HTTP endpoint.

Only call from an authenticated Google OAuth callback/Owner session. The
caller passes a server-verified principal; never accept issuer, subject, tenant,
object key or quota fields supplied directly by a browser request.

The storage interface is intentionally narrow so a private S3 adapter can be
reviewed and validated separately from tenant access rules. Tests use an
in-memory object store and never access user media or a live bucket.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import sqlite3
import uuid
from typing import Protocol

from urano.r2_pilot_quota_gate import (
    QuotaGateError, VerifiedPrincipal, _owner,
    activate_verified, commit_upload, release_upload, reserve_upload,
)


class PrivateObjectStorage(Protocol):
    def put(self, key: str, content: bytes) -> None: ...
    def get(self, key: str) -> bytes | None: ...
    def delete(self, key: str) -> None: ...


@dataclass(frozen=True)
class SyntheticUploadReceipt:
    asset_id: str
    sha256: str
    bytes_written: int


def ensure_asset_catalog(db: sqlite3.Connection) -> None:
    """Create a metadata-only catalog; no remote media or account grants."""
    db.execute('''CREATE TABLE IF NOT EXISTS pilot_assets (
        asset_id TEXT PRIMARY KEY,
        tenant_key TEXT NOT NULL REFERENCES pilot_tenants(tenant_key),
        object_key TEXT NOT NULL UNIQUE,
        sha256 TEXT NOT NULL,
        size_bytes INTEGER NOT NULL CHECK(size_bytes > 0),
        state TEXT NOT NULL CHECK(state IN ('ready', 'deleted'))
    )''')
    db.commit()


def verified_google_principal(identity) -> VerifiedPrincipal:
    """Adapt ONLY the result of the server's verified OAuth ID-token flow.

    Type checks are defense in depth, not cryptographic authentication. The
    request handler must verify Google JWKS, aud, exp, nonce and PKCE first.
    Never construct GoogleIdentity from user-controlled request JSON here.
    """
    from urano.google_oidc import GoogleIdentity
    if not isinstance(identity, GoogleIdentity):
        raise QuotaGateError('server-verified Google identity required')
    if not isinstance(identity.sub, str) or not re.fullmatch(r'[\x21-\x7e]{1,255}', identity.sub):
        raise QuotaGateError('invalid Google subject')
    return VerifiedPrincipal('https://accounts.google.com', identity.sub)


def bind_approved_google_owner(
    db: sqlite3.Connection, identity, tenant_key: str,
    *, approved_subject_by_tenant: Mapping[str, str],
) -> None:
    """Bind only a provider-verified login matching private operator approval.

    approved_subject_by_tenant comes from privileged configuration, not from
    request JSON, URL parameters or an email/display-name lookup. The actual
    Google subject IDs are never hardcoded in source or written to logs.
    This is a *candidate* adapter, not exposed in production.
    """
    if not isinstance(approved_subject_by_tenant, Mapping):
        raise QuotaGateError('operator-approved mapping required')
    principal = verified_google_principal(identity)
    expected = approved_subject_by_tenant.get(tenant_key)
    if not isinstance(expected, str) or not hmac.compare_digest(expected, principal.subject):
        raise QuotaGateError('pilot account is not approved for this login')
    activate_verified(db, tenant_key, principal)


def upload_synthetic(
    db: sqlite3.Connection, storage: PrivateObjectStorage,
    principal: VerifiedPrincipal, asset_id: str, content: bytes,
) -> SyntheticUploadReceipt:
    """Small fixture-only readback round trip with scoped metadata.

    Does not issue client-facing presigned URLs. A production 25-GB multipart
    adapter must reserve before signing and commit after verified HEAD/hash.
    """
    if not isinstance(principal, VerifiedPrincipal):
        raise QuotaGateError('server verified identity required')
    if not isinstance(content, bytes) or not 0 < len(content) <= 1024 * 1024:
        raise QuotaGateError('synthetic fixture must be at most 1 MiB')
    if not isinstance(asset_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', asset_id):
        raise QuotaGateError('invalid asset id')
    ensure_asset_catalog(db)
    tenant = _owner(db, principal)[0]
    if db.execute('SELECT 1 FROM pilot_assets WHERE asset_id=?', (asset_id,)).fetchone():
        raise QuotaGateError('asset already exists')
    expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    reservation = reserve_upload(db, principal, asset_id, len(content), expires_at=expires)
    object_key = 'pilot/' + tenant + '/' + uuid.uuid4().hex
    expected_hash = hashlib.sha256(content).hexdigest()
    try:
        storage.put(object_key, content)
        saved = storage.get(object_key)
        if saved is None or len(saved) != len(content) or not hmac.compare_digest(
            hashlib.sha256(saved).hexdigest(), expected_hash
        ):
            raise QuotaGateError('private storage readback mismatch')
        # Catalog row is persisted before accounting. On an error remove it
        # and the new remote object; no other tenant can read an unindexed key.
        with db:
            db.execute('''INSERT INTO pilot_assets
                (asset_id, tenant_key, object_key, sha256, size_bytes, state)
                VALUES (?, ?, ?, ?, ?, 'ready')''',
                (asset_id, tenant, object_key, expected_hash, len(content)))
        commit_upload(db, principal, reservation, len(saved))
    except Exception:
        # Best-effort object cleanup. If it fails, the randomly generated key
        # is not exposed to any user; reconciliation must sweep orphan keys.
        try:
            storage.delete(object_key)
        finally:
            with db:
                db.execute('DELETE FROM pilot_assets WHERE asset_id=? AND tenant_key=?', (asset_id, tenant))
            try:
                release_upload(db, principal, reservation)
            except QuotaGateError:
                pass
        raise
    return SyntheticUploadReceipt(asset_id, expected_hash, len(content))


def read_private_asset(
    db: sqlite3.Connection, storage: PrivateObjectStorage,
    principal: VerifiedPrincipal, asset_id: str,
) -> bytes:
    """Resolve storage key from verified owner, never from a browser path."""
    tenant = _owner(db, principal)[0]
    row = db.execute('''SELECT object_key, sha256, size_bytes FROM pilot_assets
        WHERE tenant_key=? AND asset_id=? AND state='ready' ''',
        (tenant, asset_id)).fetchone()
    if row is None:
        raise QuotaGateError('asset not found')
    data = storage.get(row[0])
    if data is None or len(data) != row[2] or not hmac.compare_digest(hashlib.sha256(data).hexdigest(), row[1]):
        raise QuotaGateError('private object integrity check failed')
    return data
