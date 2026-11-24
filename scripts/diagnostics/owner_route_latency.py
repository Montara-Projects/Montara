#!/usr/bin/env python3
"""Privacy-preserving summaries of Owner worker access/slow-request logs.

Run on redacted/authorized journal stream, e.g.:
  journalctl -u <OWNER_JOB> --since '30 minutes ago' -o cat |
    python3 scripts/diagnostics/owner_route_latency.py --label JM

This does not benchmark the browser/Cloudflare. Counts of access log requests
and slow-request measurements are separate and MUST NOT be added together.
Only explicitly allowlisted route identifiers reach stdout.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import re
import statistics
import sys
from typing import Iterable

SLOW = re.compile(
    r"Slow request\s+([A-Z]+)\s+(/\S+?):\s+(\d+(?:\.\d+)?)\s+ms\s+\(HTTP\s+(\d{3})\)"
)
ACCESS = re.compile(r'"([A-Z]+)\s+(/\S+)\s+HTTP/\d+(?:\.\d+)?"\s+(\d{3})\b')
ALLOWED = {
    "/api/v1/wizard/prepare": "prepare",
    "/api/v1/wizard/start": "start",
    "/api/v1/wizard/review": "review",
    "/api/v1/wizard/review/replace": "swap",
    "/api/v1/wizard/spherical-preview": "spherical_preview",
    "/api/v1/edit/shot": "edit_shot",
    "/api/v1/edit/shot/frame": "edit_frame",
    "/api/v1/edit/timeline": "timeline",
}
PREFIX = (
    (re.compile(r"^/api/v1/wizard/review/preview/\d+$"), "hover_preview"),
    (re.compile(r"^/api/v1/wizard/review/thumbnail/[^/]+/[^/]+$"), "thumbnail"),
)


def route_id(method: str, raw_path: str) -> str | None:
    if method not in {"GET", "POST", "PATCH", "PUT"}:
        return None
    # Do not preserve query values, source paths, tokens, filenames or shot IDs.
    path = raw_path.partition("?")[0]
    name = ALLOWED.get(path)
    if name is None:
        name = next((alias for regex, alias in PREFIX if regex.fullmatch(path)), None)
    return f"{method} {name}" if name is not None else None


def aggregate(lines: Iterable[str], label: str) -> dict:
    counts: dict[str, Counter] = defaultdict(Counter)
    slow_ms: dict[str, list[float]] = defaultdict(list)
    for line in lines:
        match = ACCESS.search(line)
        if match:
            method, path, status = match.groups()
            route = route_id(method, path)
            if route:
                counts[route][status] += 1
        match = SLOW.search(line)
        if match:
            method, path, ms, status = match.groups()
            route = route_id(method, path)
            if route:
                slow_ms[route].append(float(ms))
    all_keys = sorted(set(counts) | set(slow_ms))
    result = {}
    for key in all_keys:
        measurements = sorted(slow_ms.get(key, []))
        data = {
            "access_status_counts": dict(sorted(counts.get(key, {}).items())),
            "slow_samples_only": len(measurements),
        }
        if measurements:
            data["slow_sample_min_ms"] = round(measurements[0], 1)
            data["slow_sample_median_ms"] = round(statistics.median(measurements), 1)
            data["slow_sample_max_ms"] = round(measurements[-1], 1)
            # A p95 of a handful of slow-only samples is misleading.
            if len(measurements) >= 20:
                data["slow_sample_p95_ms"] = round(
                    measurements[(95 * (len(measurements) - 1) + 99) // 100], 1
                )
        result[key] = data
    return {
        "environment": label,
        "source": "Owner worker logs, NOT browser-to-MP4 E2E",
        "limitations": (
            "Access counts and slow samples are distinct; the latter are "
            "thresholded, incomplete and cannot estimate E2E percentiles."
        ),
        "routes": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, choices=("JM", "FER", "MAIN"))
    args = parser.parse_args()
    print(json.dumps(aggregate(sys.stdin, args.label), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
