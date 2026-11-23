"""Pure, operator-only JM worker CPU admission plan.

No network-facing user value may choose quota or influence the target unit.
The trusted owner broker must validate ledger, cgroup, and owner identity before
applying any systemd property to a running process. This module does NOT apply
changes, touch systemd, or interrupt active work.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Iterable


@dataclass(frozen=True)
class CapacityPlan:
    quota_percent: dict[str, int]
    queued: tuple[str, ...]
    vcpus: int
    available_for_workers: int
    max_concurrent: int


def plan_owner_capacity(
        job_ids: Iterable[str], *,
        vcpus: int = 8,
        ram_gib: int = 31,
        reserved_vcpus: int = 1,
        reserved_ram_gib: int = 5,
        max_ram_per_worker_gib: int = 6,
        max_worker_percent: int = 600,
) -> CapacityPlan:
    """Plan fair per-worker CPUQuota values, conservatively queueing overflow.

    Identifiers must already be trusted broker/ledger job identifiers. Sorting
    here is deterministic for a *snapshot*; a real scheduler must preserve
    the ledger's admission/FIFO order to avoid starving older requests.
    """
    if (type(vcpus) is not int or not 2 <= vcpus <= 128 or
            type(ram_gib) is not int or not 4 <= ram_gib <= 1024 or
            type(reserved_vcpus) is not int or not 1 <= reserved_vcpus < vcpus or
            type(reserved_ram_gib) is not int or not 1 <= reserved_ram_gib < ram_gib or
            type(max_ram_per_worker_gib) is not int or not 1 <= max_ram_per_worker_gib <= 64 or
            type(max_worker_percent) is not int or not 100 <= max_worker_percent <= 3200):
        raise ValueError("Invalid trusted resource policy")
    entries=list(job_ids)
    if len(set(entries)) != len(entries) or len(entries)>2048 or any(
            not isinstance(j,str) or not 1<=len(j)<=128 for j in entries):
        raise ValueError("Untrusted or duplicate worker identity")
    usable=vcpus-reserved_vcpus
    ram_slots=floor((ram_gib-reserved_ram_gib)/max_ram_per_worker_gib)
    slots=min(usable,ram_slots)
    if slots<1:
        raise ValueError("No safe worker admission capacity")
    admitted=entries[:slots]
    # Integer percentages retain deterministic aggregate <= available CPU.
    per_worker=min(max_worker_percent, usable*100//len(admitted)) if admitted else 0
    quotas={job:per_worker for job in admitted}
    assert sum(quotas.values())<=usable*100
    return CapacityPlan(quotas,tuple(entries[slots:]),vcpus,usable,slots)
