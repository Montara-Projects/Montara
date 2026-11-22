"""Strict root-broker authorization for future per-tab lease IPC messages.

Browser cannot submit Owner identity, PID, systemd unit, project path,
completion proof, idle status or privileged stop. Root independently verifies
Google Owner session+CSRF+canonical project UUID for EVERY request.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re

from urano.owner_tab_lease_guard import OwnerTabLeaseGuard
from urano.private_owner_admission import verify_owner_and_project


_TABOPS = frozenset({
    "tab_open", "tab_heartbeat", "tab_leave",
    "tab_rpc_begin", "tab_rpc_finish",
})
_OPAQUE = re.compile(r"[0-9a-f]{48}\Z")


@dataclass(frozen=True)
class VerifiedTabOperation:
    operation: str
    owner: str
    project: str
    generation: int
    session_hash: str
    lease_id: str | None = None
    operation_id: str | None = None


def verify_tab_operation(raw: bytes, *, owner_db_root) -> VerifiedTabOperation:
    if type(raw) is not bytes or not 0 < len(raw) <= 384:
        raise ValueError("Invalid Owner tab IPC frame")
    try:
        payload=json.loads(raw)
    except (UnicodeError,TypeError,ValueError) as exc:
        raise ValueError("Invalid Owner tab JSON") from exc
    if not isinstance(payload,dict) or payload.get("op") not in _TABOPS:
        raise ValueError("Unsupported Owner tab operation")
    op=payload["op"]
    fields={"op","session","csrf","project_id","generation"}
    if op != "tab_open":
        fields.add("lease_id")
    if op == "tab_rpc_finish":
        fields.add("operation_id")
    if set(payload)!=fields:
        raise ValueError("Unexpected Owner tab fields")
    generation=payload.get("generation")
    if type(generation) is not int or not 1 <= generation <= 2**31-1:
        raise ValueError("Invalid Engine generation")
    for field in ("lease_id","operation_id"):
        if field in fields and (type(payload.get(field)) is not str or
                                not _OPAQUE.fullmatch(payload[field])):
            raise ValueError("Invalid tab operation token")
    # Verify via the EXISTING broker's read-only SQLite session/project
    # authority. The client cannot choose an owner or bypass CSRF.
    proof={field:payload[field] for field in
           ("session","csrf","project_id")}
    proof["op"]="ensure_owner"
    _,owner,project=verify_owner_and_project(
        json.dumps(proof,separators=(",",":")).encode(),
        owner_db_root=owner_db_root)
    return VerifiedTabOperation(
        operation=op,owner=owner,project=project,generation=generation,
        session_hash=OwnerTabLeaseGuard.verified_session_hash(payload["session"]),
        lease_id=payload.get("lease_id"),operation_id=payload.get("operation_id"))
