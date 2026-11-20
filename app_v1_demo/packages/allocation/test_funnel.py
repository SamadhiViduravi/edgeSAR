"""Step 8 tests: the five fairness checks, run on ALL 1,400 pilot cases (no model is called)."""
import json
import random
from functools import lru_cache

import pytest

from packages.allocation import funnel
from packages.allocation.decisions import PILOT_DIR, apply_decision
from packages.allocation.mission import run_mission
from packages.allocation.world import UAVS
import common

pytestmark = pytest.mark.skipif(not (PILOT_DIR / "data" / "cases.jsonl").exists(), reason="pilot files not found")

CHANGES = ["task_changed", "assignment_changed", "route_changed", "verification_changed"]


@lru_cache(maxsize=1)
def _cases():
    return common.load_cases(PILOT_DIR / "data" / "cases.jsonl")


@lru_cache(maxsize=None)
def _texts(run_name):
    with open(PILOT_DIR / "runs" / (run_name + ".jsonl"), encoding="utf-8") as f:
        return {r["case_id"]: r["text"] for r in map(json.loads, f)}


def _norm(run_name, case):
    obj, _ = common.parse_decision(_texts(run_name)[case["id"]])
    return common.validate(obj, case)[0]


def _truth(case):
    return {t["landmark"]: t["sensor"] for t in apply_decision(case, common.gold_norm(case))}


def _case(case_id):
    return next(c for c in _cases() if c["id"] == case_id)


def _pair(case_id):
    """(truth, FP16 table, FP16 result, Q4 table, Q4 result) for one case."""
    c = _case(case_id)
    truth = _truth(c)
    tf, tq = apply_decision(c, _norm("f16_P1", c)), apply_decision(c, _norm("q4_P1", c))
    return truth, tf, run_mission(UAVS, tf, truth), tq, run_mission(UAVS, tq, truth)


def _same_everywhere(cmp):
    return not any(cmp[k] for k in CHANGES) and not cmp["harmful"] and not cmp["route_only"]


def test_decision_changed_unit():
    a = {"action": "CREATE_VERIFICATION", "landmark": "Clinic Gate", "sensor": "RGB", "priority": 3}
    assert not funnel.decision_changed(a, dict(a))
    assert funnel.decision_changed(a, {**a, "sensor": "THERMAL"})
    assert funnel.decision_changed(a, {"action": "NO_ACTION"})


def test_same_table_run_twice_changes_nothing():
    for c in _cases():
        truth = _truth(c)
        t = apply_decision(c, _norm("f16_P1", c))
        cmp = funnel.compare(t, run_mission(UAVS, t, truth), t, run_mission(UAVS, t, truth), truth)
        assert _same_everywhere(cmp), c["id"]


def test_same_decision_changes_nothing():
    n = 0
    for c in _cases():
        a, b = _norm("f16_P1", c), _norm("q4_P1", c)
        if funnel.decision_changed(a, b):
            continue
        truth = _truth(c)
        ta, tb = apply_decision(c, a), apply_decision(c, b)
        cmp = funnel.compare(ta, run_mission(UAVS, ta, truth), tb, run_mission(UAVS, tb, truth), truth)
        assert _same_everywhere(cmp), c["id"]
        n += 1
    assert n > 500          # there are many cases where both arms agree


def test_no_task_change_means_no_later_change():
    """The hierarchy rule: if L1 did not change, L2, L3 and L4 must not change either."""
    n = 0
    for c in _cases():
        truth, tf, rf, tq, rq = _pair(c["id"])
        cmp = funnel.compare(tf, rf, tq, rq, truth)
        if not cmp["task_changed"]:
            assert _same_everywhere(cmp), c["id"]
            n += 1
    assert n > 900


def test_task_order_does_not_matter():
    rng = random.Random(11)
    for c in _cases():
        truth = _truth(c)
        t = apply_decision(c, _norm("q4_P1", c))
        shuffled = t[:]
        rng.shuffle(shuffled)
        cmp = funnel.compare(t, run_mission(UAVS, t, truth), shuffled, run_mission(UAVS, shuffled, truth), truth)
        assert _same_everywhere(cmp), c["id"]


def test_renaming_task_ids_does_not_matter():
    for c in _cases():
        truth = _truth(c)
        t = apply_decision(c, _norm("f16_P1", c))
        renamed = [{**task, "id": "Z%d" % i} for i, task in enumerate(t)]
        cmp = funnel.compare(t, run_mission(UAVS, t, truth), renamed, run_mission(UAVS, renamed, truth), truth)
        assert _same_everywhere(cmp), c["id"]


def test_c0093_q4_fixes_the_miss():
    truth, tf, rf, tq, rq = _pair("c0093")
    cmp = funnel.compare(tf, rf, tq, rq, truth)          # A = FP16, B = Q4
    assert cmp["task_changed"] and cmp["added_or_removed"] and cmp["verification_changed"]
    assert cmp["fixed_misses"] == ["Rice Field A"] and cmp["new_misses"] == []
    assert cmp["delays"]["Rice Field A"] == pytest.approx(75.33 - 600.0, abs=0.1)
    assert not cmp["harmful"]


def test_c0499_hidden_harm():
    """One victim is saved and another is lost. The mean says 'no change'. The per-incident view says 'harm'."""
    truth, tf, rf, tq, rq = _pair("c0499")
    cmp = funnel.compare(tf, rf, tq, rq, truth)
    assert cmp["new_misses"] == ["Hill Road Bend"] and cmp["fixed_misses"] == ["School Ground"]
    assert abs(cmp["mean_delay"]) < 5
    assert cmp["harmful"] and cmp["hidden_harm"]


def test_harm_threshold_is_a_parameter():
    truth, tf, rf, tq, rq = _pair("c0481")      # no miss; one victim 45 s later, others earlier
    assert funnel.compare(tf, rf, tq, rq, truth, harm_seconds=30)["harmful"]
    assert not funnel.compare(tf, rf, tq, rq, truth, harm_seconds=60)["harmful"]
    assert funnel.compare(tf, rf, tq, rq, truth, harm_seconds=30)["mixed"]


def test_route_can_change_without_assignment_change():
    found = 0
    for c in _cases():
        truth, tf, rf, tq, rq = _pair(c["id"])
        if funnel.compare(tf, rf, tq, rq, truth)["route_only"]:
            found += 1
    assert found >= 1
