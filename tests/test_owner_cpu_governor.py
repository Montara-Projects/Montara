"""Demand-aware H4 CPU governor safety tests. Never invoke systemd."""
import pytest
from urano import owner_cpu_governor as g


def unit(n,area="jmlab"):
    return f"montara-h4-{area}-job-{n:032x}.service"


def test_single_busy_worker_borrows_six_cores():
    units=[unit(1),unit(2,"main"),unit(3,"main"),unit(4,"main")]
    alloc=g.assign_quotas(units,{units[0]:True})
    assert alloc[units[0]]==570
    assert [alloc[x] for x in units[1:]]==[10,10,10]
    assert sum(alloc.values())<=600


def test_all_four_busy_share_and_no_oversubscription():
    names=[unit(i) for i in range(1,5)]
    alloc=g.assign_quotas(names,dict.fromkeys(names,True))
    assert set(alloc.values())=={150}
    assert sum(alloc.values())==600


def test_two_busy_split_and_zero_busy_floor():
    names=[unit(i) for i in range(1,5)]
    alloc=g.assign_quotas(names,{names[0]:True,names[1]:True})
    assert alloc[names[0]]==alloc[names[1]]==290
    assert alloc[names[2]]==alloc[names[3]]==10
    assert g.assign_quotas(names,{})==dict.fromkeys(names,100)


def test_invalid_unit_cannot_be_throttled():
    with pytest.raises(ValueError):
        g.assign_quotas(["montara-h4-other-job-"+"f"*32+".service"],{})
    with pytest.raises(ValueError):
        g.assign_quotas([unit(1),unit(1)],{})
    with pytest.raises(ValueError):
        g.assign_quotas([unit(1)],{},cores=1)


def test_busy_detection_hold_and_worker_generation_reset():
    u=unit(1)
    snap={u:{"pid":77,"usage":2_000_000,"quota":"1s"}}
    prev={"when":100,"jobs":{u:{"pid":77,"usage":1_000_000,"hold_until":0}}}
    plan,state,busy=g.calculate(snap,prev,110,8)
    assert busy[u] and plan[u]==600 and state["jobs"][u]["hold_until"]==130
    snap[u]["usage"]=2_000_010
    plan,state,busy=g.calculate(snap,state,120,8)
    assert busy[u] and plan[u]==600
    plan,state,busy=g.calculate(snap,state,140,8)
    assert not busy[u] and plan[u]==100
    snap[u]["pid"]=78
    plan,state,busy=g.calculate(snap,state,145,8)
    assert not busy[u]


def test_apply_checks_exact_cgroup_and_pid_and_uses_runtime_only(monkeypatch):
    u=unit(1)
    calls=[]
    def fake(*args):
        calls.append(args)
        if args[1]=="show":
            return "ActiveState=active\nMainPID=123\nControlGroup=/system.slice/"+u+"\n"
        return ""
    monkeypatch.setattr(g,"run",fake)
    result=g.apply_plan({u:{"pid":123,"quota":"1s"}},{u:600})
    assert result==[{"unit":u,"quota_percent":600}]
    assert calls[-1]==("/usr/bin/systemctl","set-property","--runtime",u,"CPUQuota=600%")


def test_six_active_workers_get_one_core_each():
    names=[unit(i, "main" if i%2 else "jmlab") for i in range(1,7)]
    quotas=g.assign_quotas(names,dict.fromkeys(names,True))
    assert set(quotas.values())=={100}
    assert sum(quotas.values())==600


def test_twelve_active_workers_get_half_core_each():
    names=[unit(i, "main" if i%2 else "fertrial") for i in range(1,13)]
    quotas=g.assign_quotas(names,dict.fromkeys(names,True))
    assert set(quotas.values())=={50}
    assert sum(quotas.values())==600


def test_only_one_resident_worker_gets_all_six_cpus():
    names=[unit(1)]
    assert g.assign_quotas(names,{names[0]:True})[names[0]]==600
