"""Private quota read-model for a server-authenticated Montara Owner.

This module does NOT accept a tenant name or quota from a browser. The caller
must derive VerifiedPrincipal from its verified Google session. Until the OAuth
mapping is approved, this route MUST return authorization denied (not zero GB).
This local SQLite read-model requires a separate Cloudflare D1 implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from urano.r2_pilot_quota_gate import VerifiedPrincipal, _owner

@dataclass(frozen=True)
class OwnerQuotaStatus:
    plan: str
    quota_bytes: int
    used_bytes: int
    reserved_bytes: int
    available_bytes: int

    def as_public_json(self) -> dict[str, str | int]:
        return {
            'plan': self.plan,
            'quota_bytes': self.quota_bytes,
            'used_bytes': self.used_bytes,
            'reserved_bytes': self.reserved_bytes,
            'available_bytes': self.available_bytes,
        }


def owner_quota_status(db: sqlite3.Connection, principal: VerifiedPrincipal) -> OwnerQuotaStatus:
    """Get only this Google identity's active pilot quota; fail closed otherwise."""
    tenant, limit, used, reserved = _owner(db, principal)
    row = db.execute("SELECT plan FROM pilot_tenants WHERE tenant_key=? AND state='pilot_active'", (tenant,)).fetchone()
    if row is None:
        raise RuntimeError('active tenant disappeared during quota read')
    return OwnerQuotaStatus(str(row[0]), limit, used, reserved, limit-used-reserved)
