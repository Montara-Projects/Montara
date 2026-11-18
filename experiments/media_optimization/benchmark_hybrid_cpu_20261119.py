#!/usr/bin/env python3
"""Continuation of mini hybrid benchmark, focused on CPU and routing dry-run."""
import json
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO=Path("/home/fgardel00/montara-hybrid-bench-20261119")
sys.path.insert(0, str(REPO))
from experiments.media_optimization.benchmark_hybrid_mini_20261119 import encode, probe, short_probe, ssim, digest, seek, median
SRC=Path("/home/fgardel00/urano-u13e2c-acceptance-20261108/fixtures/camera-A.mp4")

def main():
    before=digest(SRC)
    result=dict(version="FER-HYBRID-MINI-20261119-CPU-v2",
                run_utc=datetime.now(timezone.utc).isoformat(),
                source_kind="synthetic 20-second lab camera, not Chema original",
                host_cpus=len(os.sched_getaffinity(0)),
                caution="2 CPUs and 8 CPUs are both on SAME GCP host, not two real executors")
    with tempfile.TemporaryDirectory(prefix="montara-hybrid-cpu-",dir="/tmp") as folder:
        root=Path(folder)
        sets={}
        for affinity in ("0,1","0-7"):
            rows=[]
            for rep in range(3):
                dest=root/f"{affinity.replace(',','-')}-{rep}.mp4"
                timings=encode(SRC,dest,28,affinity)
                data=short_probe(probe(dest))
                assert data["frames"]==500 and data["fps"]=="25/1" and abs(data["duration_sec"]-20.0)<.1
                assert data["audio_codec"]=="aac" and data["width"]==960 and data["height"]==540
                row=dict(run=rep+1,wall_s=timings["wall_s"],cpu_s=timings["cpu_s"],
                         peak_rss_kb=timings["peak_rss_kb"],bytes=dest.stat().st_size,
                         sha256=digest(dest))
                if rep==0: row["ssim_vs_original"]=ssim(SRC,dest)
                rows.append(row)
                print("CAPACITY",affinity,rep+1,json.dumps(row),flush=True)
            sets[affinity]=dict(wall_median_s=median([x["wall_s"] for x in rows]),
                 wall_samples_s=[x["wall_s"] for x in rows],
                 cpu_samples_s=[x["cpu_s"] for x in rows],
                 size_samples_bytes=[x["bytes"] for x in rows],
                 max_rss_kb=max(x["peak_rss_kb"] for x in rows),
                 sha_stable_within_affinity=len(set(x["sha256"] for x in rows))==1,
                 ssim_vs_original=rows[0]["ssim_vs_original"])
        result["cpu_capacity"]=sets
        # Actual seek operations, but no network transfer measurement.
        result["original_seek_s"]=[seek(SRC) for _ in range(3)]
        reference_size=946091 # actual Montara proxy bytes from phase 1, camera-A
        bitrate=3.72e6 # bits/s, historic 13*4h WAN throughput; not current.
        local_compute=sets["0,1"]["wall_median_s"]
        remote_compute=sets["0-7"]["wall_median_s"]
        original_transfer=SRC.stat().st_size*8/bitrate
        proxy_transfer=reference_size*8/bitrate
        result["scheduling_dry_run"]=dict(
            known_historical_uplink_mbps=3.72,
            data_type="idealized lower bounds, no real WAN",
            local_like_2cpu_compute_s=local_compute,
            gcp_like_8cpu_compute_s=remote_compute,
            source_original_bytes=SRC.stat().st_size,
            proxy_bytes=reference_size,
            remote_original_transfer_lower_bound_s=round(original_transfer,4),
            remote_proxy_transfer_lower_bound_s=round(proxy_transfer,4),
            local_like_compute_only_s=local_compute,
            remote_original_total_lower_bound_s=round(remote_compute+original_transfer,4),
            remote_proxy_total_lower_bound_s=round(remote_compute+proxy_transfer,4),
            remote_high_quality_export_permitted_without_original=False,
            decision_with_policy="Keep final original-backed export local; remote proxy-only analysis eligible where permitted; defer scheduler integration",
            missing=["local Windows/Mac timings","real upload RTT, TLS, retry and queue",
                     "real network bandwidth", "actual 360/HDR input", "real Stage E2E"])
    assert digest(SRC)==before
    result["source_unchanged"]=True
    dest=REPO/"docs/lab/HYBRID_BENCH_MINI_CPU_2026-11-19.json"
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("CPU_REPORT",dest,flush=True)
    print("CAPACITY_SUMMARY",json.dumps(result["cpu_capacity"]),flush=True)
    print("ROUTING",json.dumps(result["scheduling_dry_run"]),flush=True)

if __name__=="__main__":
    main()
