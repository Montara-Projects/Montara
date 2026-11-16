"""O1: conservative one-client, two-host report reduction.

Does not infer WAN bytes, final MP4 quality, OAuth success or physical location
from self-declared PID samples. Never copies media, URLs or process commands.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from o1_hybrid_node_meter import _SCHEMA, _label


def _valid_nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def combine_one_user(reports: list[dict], *, operator_verified: bool = False) -> dict:
    if not isinstance(reports, list) or not 2 <= len(reports) <= 3:
        raise ValueError("Provide one Companion and one VM report; browser is optional")
    seen_roles = set()
    client_hosts = set()
    server_hosts = set()
    run_ids = set()
    normalized = []
    for report in reports:
        if not isinstance(report, dict) or report.get("schema") != _SCHEMA:
            raise ValueError("Unexpected report schema")
        if report.get("no_media_or_secrets_collected") is not True:
            raise ValueError("Unsafe report")
        if report.get("scenario_clients") != 1:
            raise ValueError("This reducer requires a one-client trial")
        run_ids.add(_label(report.get("run_id")))
        role = report.get("role")
        host = _label(report.get("host_label"))
        if role not in ("client_companion", "client_browser", "server") or role in seen_roles:
            raise ValueError("Missing or duplicate report role")
        seen_roles.add(role)
        sample = report.get("sample")
        if not isinstance(sample, dict) or sample.get("method") != "psutil-pid-tree-sampled":
            raise ValueError("Not a genuine PID-tree report")
        if type(sample.get("samples")) is not int or sample["samples"] < 1:
            raise ValueError("No samples")
        for metric in ("observation_seconds", "cpu_seconds_observed_lower_bound",
                       "rss_bytes_sampled_peak"):
            if not _valid_nonnegative(sample.get(metric)):
                raise ValueError("Invalid measured field: " + metric)
        if role == "server":
            server_hosts.add(host)
        else:
            client_hosts.add(host)
        normalized.append({
            "role": role, "host_label": host,
            "cpu_seconds_lower_bound": sample["cpu_seconds_observed_lower_bound"],
            "rss_bytes_sampled_peak": sample["rss_bytes_sampled_peak"],
            "observation_seconds": sample["observation_seconds"],
            "samples": sample["samples"],
        })
    if len(run_ids) != 1 or "server" not in seen_roles or "client_companion" not in seen_roles:
        raise ValueError("One shared run with VM and Companion is required")
    if len(client_hosts) != 1 or len(server_hosts) != 1 or client_hosts == server_hosts:
        raise ValueError("Client/browser and server must declare distinct hosts")
    # Browser and Companion are allowed to share the same client machine.
    return {
        "schema": "o1-orbita-one-user-v1",
        "run_id": next(iter(run_ids)),
        "scenario_clients": 1,
        "reported_hosts_distinct": True,
        "physical_hosts_operator_verified": bool(operator_verified),
        "distributed_performance_verified": False,
        "completed_stage_e2e_verified": False,
        "oauth_verified_by_telemetry": False,
        "original_upload_proven_absent": False,
        "WAN_bytes_measured": None,
        "p50_latency_ms": None,
        "end_to_end_seconds": None,
        "meters": sorted(normalized, key=lambda item: item["role"]),
        "limitations": [
            "Host labels are self-declared, not attested.",
            "PID-tree CPU-s are conservative lower bounds; RSS is sampled, not system peak.",
            "Process samples alone do not prove completed E2E, media quality or WAN transfer.",
            "Independent browser requests and Companion/FFmpeg traffic require separate instrumentation.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Offline O1 one-user PID-tree report reducer")
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--operator-verified", action="store_true")
    args = parser.parse_args()
    reports = [json.loads(file.read_text(encoding="utf-8")) for file in args.input]
    result = combine_one_user(reports, operator_verified=args.operator_verified)
    if args.output.is_symlink():
        raise ValueError("Refusing symlink output")
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print("O1 reports combined; E2E/WAN verification still pending")


if __name__ == "__main__":
    main()
