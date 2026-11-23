"""Fail-closed quota reservation gate for R2 pilot (OAuth identity from server only).

This is a server-side, unexposed component; no upload credentials are issued here.
The caller must pass issuer+subject validated by an OAuth provider, never browser JSON.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
import uuid

MAX_ASSET_BYTES = 25_000_000_000

class QuotaGateError(ValueError):
    pass

@dataclass(frozen=True)
class VerifiedPrincipal:
    issuer: str
    subject: str

    def __post_init__(self):
        if not self.issuer or not self.subject or len(self.issuer)>256 or len(self.subject)>256:
            raise QuotaGateError('verified identity required')


def _owner(db:sqlite3.Connection, principal:VerifiedPrincipal) -> tuple[str,int,int,int]:
    if not isinstance(principal, VerifiedPrincipal):
        raise QuotaGateError('verified principal is required')
    result=db.execute('''SELECT tenant_key,quota_bytes,used_bytes,reserved_bytes
                       FROM pilot_tenants WHERE oauth_issuer=? AND oauth_subject=? AND state='pilot_active' ''',
                       (principal.issuer,principal.subject)).fetchone()
    if result is None:
        raise QuotaGateError('account unavailable or not authorized')
    return result


def activate_verified(db:sqlite3.Connection, tenant_key:str, principal:VerifiedPrincipal) -> None:
    """Administrative only. Never use route params for tenant_key or unverified identity."""
    if not isinstance(principal, VerifiedPrincipal):
        raise QuotaGateError('verified principal is required')
    with db:
        updated=db.execute('''UPDATE pilot_tenants SET oauth_issuer=?, oauth_subject=?, state='pilot_active'
           WHERE tenant_key=? AND state='pending_identity' AND oauth_subject IS NULL''',
           (principal.issuer,principal.subject,tenant_key)).rowcount
        if updated != 1:
            raise QuotaGateError('tenant not found, already bound or revoked')


def reserve_upload(db:sqlite3.Connection, principal:VerifiedPrincipal, asset_id:str, length:int,
                   *, expires_at:str) -> str:
    """Allocate a unique reservation before an upload; atomic per SQLite writer.

    The caller is responsible for commit/abort after verified R2 checksum and for
    expiring abandoned reservations. No R2 object can be considered billed until
    its verified final length matches reservation length.
    """
    if not isinstance(length,int) or isinstance(length,bool) or not 0<length<=MAX_ASSET_BYTES:
        raise QuotaGateError('invalid upload size')
    if not isinstance(asset_id,str) or not asset_id or len(asset_id)>200:
        raise QuotaGateError('invalid asset')
    try:
        deadline=datetime.fromisoformat(expires_at.replace('Z','+00:00'))
    except (ValueError,AttributeError):
        raise QuotaGateError('invalid expiration') from None
    if deadline.tzinfo is None or deadline<=datetime.now(timezone.utc):
        raise QuotaGateError('expiration must be in the future')
    # BEGIN IMMEDIATE ensures other concurrent SQLite writers wait.
    db.execute('BEGIN IMMEDIATE')
    try:
        tenant,_,_,_ = _owner(db,principal)
        # The quota guard and reservation row are committed together.
        updated=db.execute('''UPDATE pilot_tenants SET reserved_bytes=reserved_bytes+?
            WHERE tenant_key=? AND state='pilot_active'
            AND used_bytes+reserved_bytes+?<=quota_bytes''', (length,tenant,length)).rowcount
        if updated!=1:
            raise QuotaGateError('quota exceeded')
        reservation_id=uuid.uuid4().hex
        db.execute('''INSERT INTO quota_reservations
            (reservation_id,tenant_key,asset_id,bytes,state,expires_at)
            VALUES (?,?,?,?,'reserved',?)''', (reservation_id,tenant,asset_id,length,expires_at))
        db.commit()
        return reservation_id
    except Exception:
        db.rollback()
        raise


def release_upload(db:sqlite3.Connection, principal:VerifiedPrincipal, reservation_id:str) -> bool:
    """Idempotently cancel a reservation, without touching uploaded objects."""
    db.execute('BEGIN IMMEDIATE')
    try:
        tenant,_,_,_=_owner(db,principal)
        found=db.execute('''SELECT bytes,state FROM quota_reservations
            WHERE tenant_key=? AND reservation_id=?''',(tenant,reservation_id)).fetchone()
        if found is None:
            raise QuotaGateError('reservation not found')
        if found[1]=='cancelled':
            db.commit()
            return False
        if found[1]!='reserved':
            raise QuotaGateError('committed reservation cannot be cancelled')
        db.execute('''UPDATE quota_reservations SET state='cancelled'
            WHERE tenant_key=? AND reservation_id=?''',(tenant,reservation_id))
        db.execute('''UPDATE pilot_tenants SET reserved_bytes=reserved_bytes-?
            WHERE tenant_key=?''',(found[0],tenant))
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def commit_upload(db:sqlite3.Connection, principal:VerifiedPrincipal,
                  reservation_id:str, verified_remote_length:int) -> bool:
    """Finalize only after caller verified remote object length/checksum.

    Caller must ensure checksum itself; this function only guards the length.
    """
    db.execute('BEGIN IMMEDIATE')
    try:
        tenant,_,_,_=_owner(db,principal)
        found=db.execute('''SELECT bytes,state FROM quota_reservations
            WHERE tenant_key=? AND reservation_id=?''',(tenant,reservation_id)).fetchone()
        if found is None:
            raise QuotaGateError('reservation not found')
        size,state=found
        if verified_remote_length!=size:
            raise QuotaGateError('remote size mismatch')
        if state=='committed':
            db.commit()
            return False
        if state!='reserved':
            raise QuotaGateError('reservation cannot be committed')
        db.execute('''UPDATE quota_reservations SET state='committed'
            WHERE tenant_key=? AND reservation_id=?''',(tenant,reservation_id))
        db.execute('''UPDATE pilot_tenants SET reserved_bytes=reserved_bytes-?, used_bytes=used_bytes+?
            WHERE tenant_key=?''',(size,size,tenant))
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
