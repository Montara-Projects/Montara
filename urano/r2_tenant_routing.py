"""Fail-closed tenant selection for Montara's forthcoming R2 storage adapter.

This is a server-side contract, not a browser API or an active uploader.
The caller must supply:
- the deployment's trusted H4/Workers instance name, never a request parameter;
- an owner_id verified by the current Google/OAuth session;
- a backend-owned owner->tenant mapping, not display names or client JSON.

Actual R2 operations also require atomic quota reservations, authenticated
presigned URLs, integrity checks and project-reference cutover. Nothing here
changes the existing local persistence path until that adapter is integrated.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from uuid import UUID

R2_ACCOUNT_ID = "37db5e5f7ce32628852f0f5abef9fb66"
R2_BUCKET = "montara-media-eu-pilot"
R2_JURISDICTION = "eu"
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.eu.r2.cloudflarestorage.com"

# Operator-controlled deployment identifiers. Never resolve an arbitrary
# browser-supplied label, URL, path or human-readable account name.
_TENANTS = {
    "jmlab": "pilot-amehc",
    "montara-lab-jm": "pilot-amehc",
    "fertrial": "pilot-fergardel",
    "montara-lab-fer": "pilot-fergardel",
    "main": "pilot-t4t",
    "betamain": "pilot-t4t",
    "montara-main": "pilot-t4t",
}
_OWNER_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_ALLOWED_CLASS = frozenset({"originals", "exports", "project-state", "assets"})
_SUFFIX = re.compile(r"[a-z0-9]{1,12}\Z")


class TenantRoutingDenied(PermissionError):
    """Untrusted deployment/owner, unavailable quota or cross-tenant destination."""


@dataclass(frozen=True)
class R2ObjectPlan:
    tenant_id: str
    bucket: str
    endpoint: str
    jurisdiction: str
    key: str


def expected_tenant_for_instance(trusted_instance: str) -> str:
    """Map the *server-configured* instance to its one allowed R2 tenant."""
    if type(trusted_instance) is not str:
        raise TenantRoutingDenied("Untrusted Montara deployment")
    tenant = _TENANTS.get(trusted_instance)
    if tenant is None:
        raise TenantRoutingDenied("Unmapped Montara deployment")
    return tenant


def verified_tenant_for_owner(*, trusted_instance: str, verified_owner_id: str,
                              owner_tenants: Mapping[str, str]) -> str:
    """Fail closed unless a trusted owner registry confirms the same tenant.

    A client parameter such as tenant_id, account label or destination URL
    must never be accepted as the authority for this decision.
    """
    expected = expected_tenant_for_instance(trusted_instance)
    if (type(verified_owner_id) is not str
            or not _OWNER_ID.fullmatch(verified_owner_id)
            or not isinstance(owner_tenants, Mapping)):
        raise TenantRoutingDenied("Unverified R2 owner")
    actual = owner_tenants.get(verified_owner_id)
    if actual != expected:
        raise TenantRoutingDenied("R2 tenant unavailable for this owner")
    return expected


def _canonical_uuid(value: str, label: str) -> str:
    if type(value) is not str:
        raise TenantRoutingDenied(f"Invalid {label}")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise TenantRoutingDenied(f"Invalid {label}") from exc
    if str(parsed) != value:
        raise TenantRoutingDenied(f"Non-canonical {label}")
    return value


def require_cloud_only(mode: str) -> None:
    """Gate for the post-cutover upload adapter; disallow VM persistence."""
    if mode != "r2_eu":
        raise TenantRoutingDenied("Permanent VM storage is forbidden after cutover")


def plan_owner_object(*, trusted_instance: str, verified_owner_id: str,
                      owner_tenants: Mapping[str, str], project_id: str,
                      asset_id: str, asset_class: str, extension: str,
                      persistence_mode: str = "r2_eu") -> R2ObjectPlan:
    """Build a deterministic private R2 key without client-controlled paths.

    Caller MUST verify owner/project membership and reserve tenant quota
    transactionally before issuing an upload, multipart part or download URL.
    """
    require_cloud_only(persistence_mode)
    tenant = verified_tenant_for_owner(
        trusted_instance=trusted_instance,
        verified_owner_id=verified_owner_id,
        owner_tenants=owner_tenants,
    )
    project_id = _canonical_uuid(project_id, "project ID")
    asset_id = _canonical_uuid(asset_id, "asset ID")
    if asset_class not in _ALLOWED_CLASS:
        raise TenantRoutingDenied("Unsupported R2 object class")
    if type(extension) is not str or not _SUFFIX.fullmatch(extension):
        raise TenantRoutingDenied("Untrusted R2 object suffix")
    object_key = (
        f"tenants/{tenant}/projects/{project_id}/"
        f"{asset_class}/{asset_id}.{extension}"
    )
    return R2ObjectPlan(
        tenant_id=tenant, bucket=R2_BUCKET,
        endpoint=R2_ENDPOINT, jurisdiction=R2_JURISDICTION,
        key=object_key,
    )
