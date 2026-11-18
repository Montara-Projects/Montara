#!/usr/bin/env python3
"""MONTARA hybrid benchmark mini: existing code, identical fixture, bounded runs.

Isolated /tmp. No network, product writes, media uploads, main modifications.
Outputs only aggregate metadata, never private absolute paths.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from local_media.proxies import prepare, resolve_recipe

SOURCES = [
    Path("/home/fgardel00/urano-u13e2c-acceptance-20261108/fixtures/camera-A.mp4"),
    Path("/home/fgardel00/urano-u13e2c-acceptance-20261108/fixtures/camera-B.mp4"),
]
STAMP = re.compile(r"@@TIME ([0-9.]+) ([0-9.]+) ([0-9]+)")
def median(nums):
    return round(statistics.median(nums), 4)
def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()
def run(argv, *, timeout=90, output=False):
    start=time.perf_counter()
    p=subprocess.run(["/usr/bin/time","-f","@@TIME %U %S %M",*map(str,argv)],
                     capture_output=True,text=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("command failed (exit %s): %s" %(p.returncode,p.stderr[-500:]))
    m=STAMP.search(p.stderr)
    return dict(wall_s=round(time.perf_counter()-start,4),
                cpu_s=round(float(m[1])+float(m[2]),4) if m else None,
                peak_rss_kb=int(m[3]) if m else None,
                stderr=p.stderr if output else "")
def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-count_frames","-show_entries",
            "stream=codec_name,codec_type,width,height,avg_frame_rate,nb_read_frames,sample_rate,channels:format=duration,size",
            "-of","json",str(path)],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)
def short_probe(p):
    v=next(x for x in p["streams"] if x["codec_type"]=="video")
    a=next((x for x in p["streams"] if x["codec_type"]=="audio"),{})
    return dict(duration_sec=round(float(p["format"]["duration"]),3),
      frames=int(v.get("nb_read_frames") or 0),fps=v.get("avg_frame_rate"),
      width=v["width"],height=v["height"],
      audio_codec=a.get("codec_name"),video_codec=v.get("codec_name"),
      sample_rate=a.get("sample_rate"))
def encode(source,out,crf,affinity=None):
    args=["ffmpeg","-v","error","-nostdin","-y","-copyts","-start_at_zero",
      "-i",str(source),"-map","0:v:0","-map","0:a:0?",
      "-vf","scale=w='min(960,iw)':h=-2","-fps_mode","passthrough",
      "-c:v","libx264","-preset","veryfast","-crf",str(crf),
      "-pix_fmt","yuv420p","-c:a","aac","-b:a","96k",
      "-movflags","+faststart",str(out)]
    if affinity:
        args=["taskset","-c",affinity]+args
    return run(args)
def ssim(source,proxy):
    cmd=["ffmpeg","-hide_banner","-nostdin","-i",str(source),
      "-i",str(proxy),"-filter_complex",
      "[0:v]scale=w='min(960,iw)':h=-2,format=yuv420p[ref];[ref][1:v]ssim",
      "-an","-f","null","-"]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
    if p.returncode:
        raise RuntimeError("SSIM calculation failed: "+p.stderr[-600:])
    m=re.findall(r"All:([0-9.]+)",p.stderr)
    if not m: raise RuntimeError("FFmpeg did not return SSIM")
    return round(float(m[-1]),6)
def seek(path):
    return run(["ffmpeg","-hide_banner","-v","error","-nostdin",
      "-ss","6","-i",str(path),"-frames:v","1","-an","-f","null","-"])["wall_s"]
def validate(out,source):
    a=short_probe(probe(source)); b=short_probe(probe(out))
    assert abs(a["duration_sec"]-b["duration_sec"]) <= .12, (a,b)
    assert a["frames"]==b["frames"],(a,b)
    assert a["fps"]==b["fps"],(a,b)
    assert a["audio_codec"]==b["audio_codec"],(a,b)
    assert b["video_codec"]=="h264" and b["width"]<=960
    return b

def main():
    assert all(x.is_file() for x in SOURCES)
    src_checksums={p.name:digest(p) for p in SOURCES}
    start=time.perf_counter()
    print("PHASE 1: actual Montara proxy cold/warm, two 20s cameras, 3 repeats",flush=True)
    result=dict(version="FER-HYBRID-MINI-20261119-v1",
      baseline_commit="9bd5a8d45d7523a7b383ff411d5c27ce17748959",
      run_utc=datetime.now(timezone.utc).isoformat(),
      ffmpeg=subprocess.run(["ffmpeg","-version"],capture_output=True,text=True).stdout.splitlines()[0],
      host=dict(architecture=os.uname().machine,visible_cpus=len(os.sched_getaffinity(0)),
                affined_cpu_ids=sorted(os.sched_getaffinity(0))),
      scope="two private *synthetic laboratory* 20-second H264/AAC 1280x720 clips; no Chrome, Mac, Companion, 360 or real WAN",
      results={})
    with tempfile.TemporaryDirectory(prefix="montara-hybrid-bench-",dir="/tmp") as folder:
      work=Path(folder)
      first_proxy=None; first_prepared=None
      samples=[]
      for ix,source in enumerate(SOURCES):
        cold=[]; warm=[]; ratios=[]; hashes=[]
        for rep in range(3):
          t0=time.perf_counter()
          rec=prepare(source,work/f"actual-{ix}-{rep}")
          cold.append(time.perf_counter()-t0)
          proxy=Path(rec["proxy"]); hashes.append(digest(proxy))
          ratios.append(proxy.stat().st_size/source.stat().st_size)
          assert proxy.stat().st_size>0
          validate(proxy,source)
          prev_mtime=proxy.stat().st_mtime_ns
          t1=time.perf_counter()
          rec2=prepare(source,work/f"actual-{ix}-{rep}")
          warm.append(time.perf_counter()-t1)
          assert rec2["source_id"]==rec["source_id"]
          assert proxy.stat().st_mtime_ns==prev_mtime
          if ix==0 and rep==0: first_proxy=proxy; first_prepared=rec
        samples.append(dict(source_size_bytes=source.stat().st_size,
              proxy_size_bytes=Path(rec["proxy"]).stat().st_size,
              cold_wall_sec=[round(x,4) for x in cold],
              warm_wall_sec=[round(x,4) for x in warm],
              median_cold_s=median(cold),median_warm_s=median(warm),
              ratio_bytes=round(statistics.median(ratios),4),
              stable_sha256_over_repeats=(len(set(hashes))==1)))
      result["results"]["actual_proxy"]=samples
      print("PROXY",json.dumps(samples),flush=True)

      # Real local_media original resolution -- exactly same source IDs/recipe.
      recipe={"clips":[{"source_id":first_prepared["source_id"],"start":0.5,"end":1.5},
                       {"source_id":first_prepared["source_id"],"start":2.0,"end":3.0}]}
      resolved=resolve_recipe(recipe,first_proxy.parent)
      assert all(c["original"]==str(SOURCES[0].resolve()) for c in resolved)
      target=work/"original-backed-export.mp4"
      export=run(["ffmpeg","-v","error","-nostdin","-y","-i",str(SOURCES[0]),
         "-filter_complex",
         "[0:v]trim=start=0.5:end=1.5,setpts=PTS-STARTPTS[v0];"
         "[0:v]trim=start=2:end=3,setpts=PTS-STARTPTS[v1];"
         "[v0][v1]concat=n=2:v=1:a=0[out]",
         "-map","[out]","-an","-c:v","libx264","-preset","ultrafast",str(target)])
      meta=short_probe(probe(target))
      assert meta["frames"]==50 and abs(meta["duration_sec"]-2.0)<.05,meta
      result["results"]["original_export"]=dict(
           uses_immutable_original=True,nominal_duration_sec=2,
           actual_duration_sec=meta["duration_sec"],frames=meta["frames"],
           bytes=target.stat().st_size,wall_sec=export["wall_s"])
      print("EXPORT",json.dumps(result["results"]["original_export"]),flush=True)

      print("PHASE 2: direct ffmpeg CRF28 control vs CRF30, same scale, audio, encoder, two sources",flush=True)
      recs=[]
      example={}
      for ix,source in enumerate(SOURCES):
        rounds=3 if ix==0 else 1
        for rep in range(rounds):
          codes=[28,30] if rep%2==0 else [30,28]
          for crf in codes:
            out=work/f"direct-{ix}-{rep}-{crf}.mp4"
            timing=encode(source,out,crf)
            m=validate(out,source)
            recs.append(dict(camera=f"fixture-{ix+1}",round=rep,crf=crf,
              wall_s=timing["wall_s"],cpu_s=timing["cpu_s"],
              rss_kb=timing["peak_rss_kb"],size_bytes=out.stat().st_size))
            if rep==0: example[(ix,crf)]=out
      agg={}
      for crf in [28,30]:
        agg[str(crf)]=dict(
            elapsed_median_s=median([x["wall_s"] for x in recs if x["crf"]==crf and x["camera"]=="fixture-1"]),
            filesize_med_bytes=int(statistics.median([x["size_bytes"] for x in recs if x["crf"]==crf and x["camera"]=="fixture-1"])),
            repeated_sha256_stable=len({digest(work/f"direct-0-{r}-{crf}.mp4") for r in range(3)})==1,
            ssim_by_fixture=[ssim(source,example[(ix,crf)]) for ix,source in enumerate(SOURCES)])
      agg["candidate_savings_pct"]=round(100*(1-agg["30"]["filesize_med_bytes"]/agg["28"]["filesize_med_bytes"]),2)
      result["results"]["crf_A_B"]=dict(aggregate=agg,individual=recs)
      print("A_B",json.dumps(agg),flush=True)

      print("PHASE 3: CPU capacity calibration only, not real Windows/Mac",flush=True)
      cpu={}
      for affinity in ["0,1","0-7"]:
        rows=[]
        for rep in range(3):
          out=work/f"cpu-{affinity.replace(',','-')}-{rep}.mp4"
          t=encode(SOURCES[0],out,28,affinity)
          validate(out, SOURCES[0]) # CPU threads can change the MP4 bytes
          rows.append(t)
        cpu[affinity]=dict(median_wall_s=median([x["wall_s"] for x in rows]),
            wall_s=[x["wall_s"] for x in rows],
            cpu_s=[x["cpu_s"] for x in rows],
            max_rss_kb=max(x["peak_rss_kb"] for x in rows))
      result["results"]["cpu_capacity"]=cpu
      result["results"]["seek_original_vs_proxy"]=dict(
         original_wall_s=[seek(SOURCES[0]) for _ in range(3)],
         proxy_wall_s=[seek(first_proxy) for _ in range(3)])
      print("CPU",json.dumps(cpu),flush=True)

      print("PHASE 4: scheduler decision dry-run, historical WAN only",flush=True)
      uplink=3.72*1_000_000 # bits/s, historical 13*4h Opus upload #265
      s0=SOURCES[0].stat().st_size
      proxybytes=first_proxy.stat().st_size
      local_compute=cpu["0,1"]["median_wall_s"]
      remote_compute=cpu["0-7"]["median_wall_s"]
      remote_transfer_original=8*s0/uplink
      remote_transfer_proxy=8*proxybytes/uplink
      local_path=local_compute
      remote_original=remote_compute+remote_transfer_original
      remote_proxy=remote_compute+remote_transfer_proxy
      result["results"]["routing_model"]=dict(
          data_origin="hypothetical, NOT measured Oracle/Windows/Mac or real network",
          historical_uplink_mbit_s=3.72,
          source_original_bytes=s0,proxy_bytes=proxybytes,
          local_like_2cpu_compute_s=local_compute,remote_like_8cpu_compute_s=remote_compute,
          ideal_original_transfer_s=round(remote_transfer_original,4),
          ideal_proxy_transfer_s=round(remote_transfer_proxy,4),
          local_like_total_s=round(local_path,4),
          remote_full_fidelity_total_s_without_queue_return_verify=round(remote_original,4),
          remote_proxy_processing_total_s_without_queue_return_verify=round(remote_proxy,4),
          policy_originals_not_uploaded_by_default=True,
          policy_remote_original_render_eligible=False,
          notes="Proxy-only cannot guarantee final-original fidelity. These are LOWER bounds ignoring RTT, auth, TLS, queue, retries, download and verification.")
      print("PLAN",json.dumps(result["results"]["routing_model"]),flush=True)
    result["overall_wall_s"]=round(time.perf_counter()-start,3)
    result["unchanged_source_sha256"]=all(digest(p)==h for p,h in ((p,src_checksums[p.name]) for p in SOURCES))
    assert result["unchanged_source_sha256"]
    assert result["results"]["original_export"]["uses_immutable_original"]
    output=REPO/"docs/lab/HYBRID_BENCH_MINI_2026-11-19.json"
    output.parent.mkdir(exist_ok=True,parents=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("RESULT_FILE",output,flush=True)
    print("TOTAL_SEC",result["overall_wall_s"],flush=True)
if __name__=="__main__":
    main()
