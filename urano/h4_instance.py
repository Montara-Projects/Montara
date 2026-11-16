"""Operator-selected namespaces for isolated native Owner instances."""
import re
from dataclasses import dataclass
from pathlib import Path

INSTANCE = r"[a-z][a-z0-9]{0,11}"
UNIT = re.compile(rf"montara-(?:i24|h4-{INSTANCE})-job-[a-f0-9]{{32}}\Z")


@dataclass(frozen=True)
class H4Instance:
    name: str = ""

    def __post_init__(self):
        if self.name and not re.fullmatch(INSTANCE, self.name):
            raise ValueError("Invalid H4 instance identifier")

    @property
    def prefix(self):
        return "montara-h4" + ("-" + self.name if self.name else "")

    @property
    def worker_script(self):
        return f"/opt/montara/broker-{self.prefix.removeprefix('montara-')}-native/native_owner_systemd_worker.py"

    @property
    def broker_socket(self):
        return Path("/run") / (self.prefix + "-broker") / "control.sock"

    @property
    def owner_socket(self):
        return Path("/run") / (self.prefix + "-owner-admission") / "control.sock"

    @property
    def ledger(self):
        return Path("/var/lib") / (self.prefix + "-broker") / "jobs.sqlite3"

    @property
    def private_root(self):
        return Path("/var/lib") / (self.prefix + "-owner")

    @property
    def mount(self):
        return Path("/run") / (self.prefix + "-owner-ro")

    @property
    def unit_prefix(self):
        return self.prefix + "-job-" if self.name else "montara-i24-job-"

    @property
    def state_prefix(self):
        return self.prefix + "-owner-" if self.name else "montara-owner-"

    @staticmethod
    def from_unit(unit):
        if not UNIT.fullmatch(unit):
            raise ValueError("Invalid Owner worker unit")
        return H4Instance(unit[len("montara-h4-"):].rsplit("-job-", 1)[0]
                          if unit.startswith("montara-h4-") else "")


def validate_private_root(instance, root):
    if instance.name and root != instance.private_root:
        raise ValueError("H4 instance must use its dedicated private Owner directory")
