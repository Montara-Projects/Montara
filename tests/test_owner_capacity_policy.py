"""No cgroup mutation: deterministic CPU admission and fairness policy tests."""
import pytest
from urano.owner_capacity_policy import plan_owner_capacity


def test_one_jm_owner_may_borrow_six_of_eight_logical_cpus():
    plan=plan_owner_capacity(["verified-jm"])
    assert plan.quota_percent == {"verified-jm": 600}
    assert plan.queued == ()
    assert plan.available_for_workers == 7


def test_two_owners_share_available_cpu_without_starvation():
    plan=plan_owner_capacity(["jm","fer"])
    assert plan.quota_percent == {"jm": 350,"fer":350}


def test_four_workers_saturate_safe_ram_slots_not_cpus():
    plan=plan_owner_capacity(["a","b","c","d"])
    assert plan.max_concurrent == 4
    assert set(plan.quota_percent.values()) == {175}
    assert sum(plan.quota_percent.values())==700


def test_fifth_worker_is_queued_not_oversubscribed():
    plan=plan_owner_capacity(["a","b","c","d","e"])
    assert plan.queued==("e",)
    assert "e" not in plan.quota_percent


def test_tighter_capacity_and_invalid_settings():
    plan=plan_owner_capacity(["a","b","c"],vcpus=4,ram_gib=16,
                             reserved_vcpus=1,reserved_ram_gib=4)
    assert plan.queued==("c",)
    assert set(plan.quota_percent.values())=={150}
    with pytest.raises(ValueError):
        plan_owner_capacity(["a","a"])
    with pytest.raises(ValueError):
        plan_owner_capacity(["a"],vcpus=1)
    with pytest.raises(ValueError):
        plan_owner_capacity(["a"],max_ram_per_worker_gib=0)
