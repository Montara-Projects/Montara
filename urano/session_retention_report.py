"""Count expired Owner sessions on one offline SQLite snapshot."""
import argparse
import sqlite3
import time
from contextlib import closing
from pathlib import Path


def count_eligible(snapshot: Path, *, cutoff: int) -> int:
    snapshot = snapshot.resolve(strict=True)
    if any(snapshot.with_name(snapshot.name + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError("Use a coherent offline SQLite backup without sidecars")
    with closing(sqlite3.connect(snapshot.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        return db.execute(
            "SELECT count(*) FROM urano_auth_sessions WHERE expires_at <= ?", (cutoff,)
        ).fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--retention-days", required=True, type=int)
    args = parser.parse_args()
    if args.retention_days < 0:
        parser.error("--retention-days must be nonnegative")
    cutoff = int(time.time()) - args.retention_days * 86400
    print(count_eligible(args.snapshot, cutoff=cutoff))


if __name__ == "__main__":
    main()
