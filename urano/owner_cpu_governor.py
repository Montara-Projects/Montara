"""Operator-only fair CPU quota governor for H4 isolated Engine workers.

Uses CPU cgroup accounting, not HTTP requests or browser identity. Never
stops/restarts workers or alters MemoryMax, uid, file permissions or cgroups.
Protected operator root service uses fixed unit-name allowlist and verifies
exact systemd ControlGroup before any CPUQuota update. Resource admission
and persistent queue remain the broker responsibility.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

UNIT = re.compile(r"montara-h4-(?:jmlab|main|fertrial|betamain)-job-[a-f0-9]{32}\.service\Z")
CGROOT=Path("/sys/fs/cgroup/system.slice")
STATE=Path("/run/montara-owner-cpu-governor/state.json")
CAP=600
RESERVE=100
MIN_IDLE=25
SAMPLE_BUSY=.07
HOLD_SECONDS=20


def assign_quotas(names, demand, cores=8):
    """Allocate <= cores - one reserved, max 6 per actively working job."""
    names=list(names)
    if len(set(names))!=len(names) or any(not UNIT.fullmatch(u) for u in names):
        raise ValueError("Invalid operator job list")
    if type(cores)!=int or not 2<=cores<=128:
        raise ValueError("Invalid CPU count")
    total=max(100,(cores*100)-RESERVE)
    active=[u for u in names if demand.get(u,False)]
    idle=[u for u in names if not demand.get(u,False)]
    if not active:
        each=min(100,total//max(1,len(names)))
        return {u:each for u in names}
    idle_pct=min(MIN_IDLE,max(0,(total-100*len(active))//max(1,len(idle)))) if idle else 0
    remainder=total-idle_pct*len(idle)
    shared=max(25,min(CAP,remainder//len(active)))
    # Strict global sum (including idle) cannot exceed available vCPU.
    return {**{u:shared for u in active},**{u:idle_pct for u in idle}}


def run(*args):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=10).stdout


def units_snapshot():
    listing=run("/usr/bin/systemctl","list-units","--type=service",
                "--state=running","--no-legend","--plain","--no-pager")
    result={}
    for line in listing.splitlines():
        unit=line.split()[0] if line.split() else ""
        if not UNIT.fullmatch(unit):
            continue
        output=run("/usr/bin/systemctl","show",unit,
                   "-p","ActiveState","-p","LoadState","-p","ControlGroup",
                   "-p","MainPID","-p","CPUQuotaPerSecUSec","--no-pager")
        info=dict(x.split("=",1) for x in output.splitlines() if "=" in x)
        if info.get("ActiveState")!="active" or info.get("LoadState")!="loaded":
            continue
        if info.get("ControlGroup")!="/system.slice/"+unit:
            continue
        try:
            pid=int(info["MainPID"])
            if pid<=1:continue
            stats=(CGROOT/unit/"cpu.stat").read_text()
            usage=int(next(row.split()[1] for row in stats.splitlines()
                           if row.startswith("usage_usec ")))
        except (ValueError,KeyError,StopIteration,FileNotFoundError,PermissionError):
            continue
        result[unit]={"usage":usage,"quota":info.get("CPUQuotaPerSecUSec",""),
                      "pid":pid}
    return result


def load_state():
    try:
        d=json.loads(STATE.read_text())
        if isinstance(d,dict) and isinstance(d.get("jobs"),dict) and type(d.get("when")) in (int,float):
            return d
    except (FileNotFoundError,ValueError,PermissionError):
        pass
    return {"jobs":{},"when":0}


def calculate(snapshot,previous,now,cores):
    prior=previous.get("jobs",{})
    elapsed=now-float(previous.get("when",0))
    active={}
    jobs={}
    for unit,info in snapshot.items():
        old=prior.get(unit,{})
        # A new generation/PID gets its own sample; never reuse old worker
        # accounting after a worker replacement.
        comparable=old.get("pid")==info["pid"] and 0<elapsed<120
        delta=info["usage"]-old.get("usage",0) if comparable else 0
        busy=bool(comparable and delta>0 and delta/(elapsed*1000000)>SAMPLE_BUSY)
        hold_until=now+HOLD_SECONDS if busy else float(old.get("hold_until",0))
        active[unit]=busy or (comparable and now<hold_until)
        jobs[unit]={"pid":info["pid"],"usage":info["usage"],"hold_until":hold_until}
    return assign_quotas(snapshot,active,cores),{"when":now,"jobs":jobs},active


def apply_plan(snapshot,quota):
    results=[]
    for unit,target in quota.items():
        # Reverify unit identity immediately before modifying its live
        # control group. Never trust the previous discovery alone.
        if not UNIT.fullmatch(unit) or not 25<=target<=CAP:
            raise ValueError("Forbidden live quota")
        output=run("/usr/bin/systemctl","show",unit,
                   "-p","ActiveState","-p","MainPID","-p","ControlGroup",
                   "--no-pager")
        actual=dict(row.split("=",1) for row in output.splitlines() if "=" in row)
        if (actual.get("ActiveState")!="active" or
                actual.get("MainPID")!=str(snapshot[unit]["pid"]) or
                actual.get("ControlGroup")!="/system.slice/"+unit):
            results.append({"unit":unit,"skipped":"identity_changed"})
            continue
        current=snapshot[unit].get("quota","")
        # systemd reports CPUQuotaPerSecUSec as 6s for 600% (period 1s).
        try:
            existing=int(float(current[:-1])*100) if current.endswith("s") else -1
        except ValueError:
            existing=-1
        if existing==target:
            continue
        run("/usr/bin/systemctl","set-property","--runtime",unit,
            "CPUQuota="+str(target)+"%")
        results.append({"unit":unit,"quota_percent":target})
    return results


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    snap=units_snapshot()
    now=time.time()
    cores=os.cpu_count() or 8
    quotas,next_state,demand=calculate(snap,load_state(),now,cores)
    print(json.dumps({"cores":cores,"reserve_percent":RESERVE,
                     "busy":[u for u,b in demand.items() if b],
                     "quota_percent":quotas,"mode":"apply" if args.apply else "dry-run"}))
    if args.apply:
        # On any systemd error, do not persist a false snapshot.
        changes=apply_plan(snap,quotas)
        STATE.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        temp=STATE.with_suffix(".tmp")
        temp.write_text(json.dumps(next_state))
        os.chmod(temp,0o600)
        os.replace(temp,STATE)
        print(json.dumps({"changed":changes}))


if __name__=="__main__":
    main()
