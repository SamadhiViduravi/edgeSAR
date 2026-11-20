"""
M2 checks for the episode simulator (plan section 9, M2).

  * the hidden-truth wall: truth and gold are closed to everything except the engine and the scorer (guard objects + source scan)
  * the scorer: every real incident is in the denominator and in exactly one class
  * hand-made scenarios: normal case, consequential error (incident dropped), harmless wasted trip, wrong camera, missing candidate that
    needs verification, competing deadlines, impossible coverage, incident resolved by someone else, moved incident (in-flight leg),
    cover task that only the THERMAL UAV can serve
  * time and money: verification delay, budget cap, decision time charged per allocator run, TIMEOUT label
  * determinism, and invariants on random episodes built from the pilot cases (no UAV in two places, travel times, counts add up)

Run:  python -m pytest -q tests/test_sim.py
"""
import ast
import itertools
import json
import math
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest                                                     # noqa: E402

from shield import alloc, core, paths, sim as S               # noqa: E402
from shield.sim import (Decision, Episode, ReportEvent, Sim, SimConfig, TruthLeak, apply_record, canon_table, truth_access)  # noqa: E402

L = core.landmarks()
U = core.uav_specs()
NOOP = {"action": "NO_ACTION"}
CLASSES = {"on_time", "late", "unverified", "resolved_external"}


def row(i, lm, sensor="ANY", pri=2):
    return {"id": i, "landmark": lm, "sensor": sensor, "priority": pri}


def ev(t, ns, open_before, gold):
    return ReportEvent(float(t), ns, ns, open_before, gold)


class Fn:
    def __init__(self, f):
        self.f = f

    def on_report(self, view):
        return self.f(view)


def commit(rec):
    return Fn(lambda v: Decision("COMMIT", "TEST", table=apply_record(v.open_table, rec), record=rec))


def make(cfg=None, allocator=None):
    return Sim(allocator or alloc.BoundedCBBA(), cfg or SimConfig(budget_fraction=1.0))


def travel(uav, a, b):
    return math.dist(a, b) / U[uav].speed


# =====================================================================================================================
# the wall
# =====================================================================================================================
def test_truth_and_gold_are_closed_outside_the_engine():
    t = S.HiddenTruth()
    with pytest.raises(TruthLeak):
        t.incidents()
    with pytest.raises(TruthLeak):
        t.visit("c", "Clinic Gate", frozenset(["RGB"]), 1.0)
    e = ev(0, "c", [], NOOP)
    with pytest.raises(TruthLeak):
        _ = e.gold
    with truth_access():
        assert e.gold == NOOP
    with pytest.raises(TruthLeak):                                # the door closes again afterwards
        _ = e.gold


def test_policy_view_has_no_route_to_the_gold_record():
    """The View offers only belief, UAV state, budget, config and the what-if allocator.  No truth, no gold, no episode object."""
    seen = {}

    def f(view):
        seen["attrs"] = {a for a in dir(view) if not a.startswith("__")}
        return Decision("COMMIT", "TEST", table=view.open_table)

    s = make()
    s.run(Episode("E", [ev(0, "c", [row("I1", "Clinic Gate", "RGB", 3)], NOOP)]), Fn(f), "t")
    public = {a for a in seen["attrs"] if not a.startswith("_")}
    assert public == {"now", "ns", "case_id", "open_table", "budget_left", "cfg", "runs_so_far", "runs_available", "evaluate"}, public
    # a policy that tries to open the gold record through the event or the truth is stopped
    with pytest.raises(TruthLeak):
        Fn(lambda v: v._sim.truth.incidents()).on_report(S.View(s, "c", "c", 0.0))


FORBIDDEN_NAMES = {"HiddenTruth", "truth_access", "TruthLeak", "ReportEvent", "gold", "_gold", "truth", "_sim", "TInc", "verify_now"}


def _policy_files():
    d = Path(__file__).resolve().parent.parent / "shield"
    names = ("policy.py", "shieldpolicy.py", "readout.py", "conformal.py", "cover.py", "gates.py")
    return [d / n for n in names if (d / n).exists()]


def test_source_scan_policy_modules_never_name_the_truth():
    """Runtime modules (readout, conformal, cover, gates, policies) must not mention the hidden truth, the gold record or the engine internals."""
    bad = []
    for f in _policy_files():
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names += [a.name.split(".")[-1] for a in node.names]
            elif isinstance(node, ast.arg):
                names.append(node.arg)
            for n in names:
                if n in FORBIDDEN_NAMES:
                    bad.append("%s:%s uses %s" % (f.name, getattr(node, "lineno", "?"), n))
    assert not bad, bad


# =====================================================================================================================
# unit: the record semantics
# =====================================================================================================================
def test_apply_record_semantics():
    tb = [row("I1", "Clinic Gate", "RGB", 3), row("I2", "North Bridge", "THERMAL", 1)]
    assert apply_record(tb, NOOP) == tb
    assert [r["id"] for r in apply_record(tb, {"action": "CLOSE_INCIDENT", "incident": "I1"})] == ["I2"]
    up = apply_record(tb, {"action": "UPDATE_INCIDENT", "incident": "I2", "landmark": "Canal Lock", "sensor": "ANY", "priority": 3})
    assert up[1] == row("I2", "Canal Lock", "ANY", 3) and up[0] == tb[0]
    cr = apply_record(tb, {"action": "CREATE_VERIFICATION", "landmark": "Fuel Station", "sensor": "RGB", "priority": 2})
    assert cr[-1] == row("N1", "Fuel Station", "RGB", 2) and len(cr) == 3
    # an incident that is not in the table changes nothing
    assert apply_record(tb, {"action": "CLOSE_INCIDENT", "incident": "I9"}) == tb
    assert apply_record(tb, {"action": "UPDATE_INCIDENT", "incident": "I9", "landmark": "Canal Lock", "sensor": "ANY", "priority": 1}) == tb
    # the input is not changed
    assert tb[0] == row("I1", "Clinic Gate", "RGB", 3)


def test_canon_table_ignores_ids_and_order():
    a = [row("I1", "Clinic Gate", "RGB", 3), row("I2", "North Bridge", "ANY", 1)]
    b = [row("X", "North Bridge", "ANY", 1), row("Y", "Clinic Gate", "RGB", 3)]
    assert canon_table(a) == canon_table(b)
    assert canon_table(a) != canon_table([row("I1", "Clinic Gate", "RGB", 2), row("I2", "North Bridge", "ANY", 1)])


# =====================================================================================================================
# hand-made scenarios
# =====================================================================================================================
def test_normal_case_incident_verified_on_time_by_the_nearest_uav():
    e = Episode("E", [ev(0, "c", [row("I1", "Clinic Gate", "RGB", 3)], NOOP)])
    r = make().run(e, commit(NOOP), "t")
    assert r["counts"] == {"n": 1, "on_time": 1, "late": 0, "unverified": 0, "resolved_external": 0}
    v = r["log"]["visits"]
    assert len(v) == 1 and v[0]["uav"] == "UAV-03" and v[0]["result"] == "verified"
    d = travel("UAV-03", U["UAV-03"].start, L["Clinic Gate"])
    assert abs(v[0]["arrive"] - d) < 1e-9
    assert abs(r["incidents"][0]["verified_at"] - (d + core.DWELL_S)) < 1e-9
    assert r["log"]["wasted"] == 0 and r["requests"] == 0


def test_consequential_error_a_real_incident_is_dropped():
    """The policy commits CLOSE although the gold record keeps the incident: nobody is sent, the incident stays unverified."""
    e = Episode("E", [ev(0, "c", [row("I1", "Clinic Gate", "RGB", 3)], NOOP)])
    r = make().run(e, commit({"action": "CLOSE_INCIDENT", "incident": "I1"}), "t")
    assert r["counts"] == {"n": 1, "on_time": 0, "late": 0, "unverified": 1, "resolved_external": 0}
    assert r["log"]["visits"] == [] and r["log"]["wasted"] == 0
    assert r["log"]["reports"][0]["table_equal_gold"] is False and r["log"]["reports"][0]["plan_equal_gold"] is False


def test_harmless_error_costs_a_wasted_trip_but_no_miss():
    """Gold closes the incident in the same second (it was never real). The stale table sends a UAV for nothing: a cost, not a miss."""
    gold = {"action": "CLOSE_INCIDENT", "incident": "I1"}
    e = Episode("E", [ev(0, "c", [row("I1", "Clinic Gate", "RGB", 3)], gold)])
    r = make().run(e, commit(NOOP), "t")
    assert r["counts"]["n"] == 0 and sum(r["counts"][k] for k in CLASSES) == 0
    assert r["log"]["wasted"] == 1 and r["log"]["empty"] == 1 and r["log"]["visits"][0]["result"] == "empty"
    # and the correct decision costs nothing
    r2 = make().run(e, commit(gold), "t")
    assert r2["log"]["wasted"] == 0 and r2["log"]["visits"] == []


def test_wrong_camera_is_found_on_arrival_and_the_task_returns_with_a_ban():
    """Truth needs THERMAL. The table says RGB (wrong). UAV-03 and UAV-01 fly there and fail; UAV-02 (has THERMAL) finishes it."""
    rows = [row("I1", "Hill Road Bend", "THERMAL", 2)]
    wrong = {"action": "UPDATE_INCIDENT", "incident": "I1", "landmark": "Hill Road Bend", "sensor": "RGB", "priority": 2}
    e = Episode("E", [ev(0, "c", rows, NOOP)])
    r = make().run(e, commit(wrong), "t")
    v = r["log"]["visits"]
    assert [x["result"] for x in v] == ["failed", "failed", "verified"], v
    assert [x["uav"] for x in v] == ["UAV-03", "UAV-01", "UAV-02"]
    assert r["log"]["failed"] == 2 and r["log"]["wasted"] == 2
    assert r["counts"]["on_time"] == 1
    # the second try leaves when the first failure is discovered (at its arrival), not when its dwell ends
    t1 = v[0]["arrive"]
    d1 = travel("UAV-01", U["UAV-01"].start, L["Hill Road Bend"])
    assert abs(v[1]["arrive"] - (t1 + d1)) < 1e-9


def test_missing_candidate_is_escalated_and_the_answer_comes_after_the_delay():
    gold = {"action": "CREATE_VERIFICATION", "landmark": "Market Square", "sensor": "ANY", "priority": 3}
    e = Episode("E", [ev(0, "c", [], gold)])
    cfg = SimConfig(budget_fraction=1.0, d_v=60.0)
    r = make(cfg).run(e, Fn(lambda v: Decision("ESCALATE", "ESCALATE")), "t")
    assert r["requests"] == 1 and r["log"]["hold_s"] == 60.0
    d = travel("UAV-03", U["UAV-03"].start, L["Market Square"])
    assert abs(r["log"]["visits"][0]["arrive"] - (60.0 + d)) < 1e-9
    inc = r["incidents"][0]
    assert inc["class"] == "on_time" and abs(inc["verified_at"] - (60.0 + d + core.DWELL_S)) < 1e-9
    assert inc["deadline"] == 240.0                                 # counted from the report, not from the answer
    # the same report committed correctly at once is faster by exactly the hold
    r2 = make(cfg).run(e, commit(gold), "t")
    assert abs(r2["incidents"][0]["verified_at"] + 60.0 - inc["verified_at"]) < 1e-9


def test_escalation_holds_the_old_rows_but_still_dispatches_them():
    """While a report waits for verification the incidents that are already in the table are still planned."""
    rows = [row("I1", "Clinic Gate", "RGB", 3)]
    gold = {"action": "CREATE_VERIFICATION", "landmark": "Market Square", "sensor": "ANY", "priority": 3}
    e = Episode("E", [ev(0, "c", rows, gold)])
    r = make().run(e, Fn(lambda v: Decision("ESCALATE", "ESCALATE")), "t")
    first = r["log"]["visits"][0]
    assert first["landmark"] == "Clinic Gate" and first["arrive"] < 30.0
    assert r["counts"]["on_time"] == 2


def test_budget_cap_is_enforced_and_rounded_per_episode():
    gold = {"action": "CREATE_VERIFICATION", "landmark": "Market Square", "sensor": "ANY", "priority": 3}
    e = Episode("E", [ev(0, "c", [], gold)])
    with pytest.raises(RuntimeError):
        make(SimConfig(budget_fraction=0.0)).run(e, Fn(lambda v: Decision("ESCALATE", "ESCALATE")), "t")
    # cap = floor(b * reports + 0.5)
    caps = {}
    for R in (4, 5, 12, 20):
        evs = [ev(10 * i, "c%d" % i, [], NOOP) for i in range(R)]
        caps[R] = make(SimConfig(budget_fraction=0.10)).run(Episode("E", evs), commit(NOOP), "t")["budget_cap"]
    assert caps == {4: 0, 5: 1, 12: 1, 20: 2}


def test_decision_time_is_charged_per_allocator_run_and_timeout_is_labelled():
    rows = [row("I1", "Clinic Gate", "RGB", 3)]
    e = Episode("E", [ev(0, "c", rows, NOOP)])

    def two_runs(view):
        view.evaluate(view.open_table)
        view.evaluate(view.open_table)
        return Decision("COMMIT", "TEST", table=view.open_table)

    r = make(SimConfig(budget_fraction=1.0, alloc_cost_s=0.02)).run(e, Fn(two_runs), "t")
    d = travel("UAV-03", U["UAV-03"].start, L["Clinic Gate"])
    assert r["log"]["reports"][0]["runs"] == 2 and abs(r["log"]["decision_s"] - 0.04) < 1e-12
    assert abs(r["log"]["visits"][0]["arrive"] - (0.04 + d)) < 1e-9          # the table is applied 0.04 s late
    assert not r["log"]["reports"][0]["timeout"]
    # a slow machine: 3 s per run, 2 runs = 6 s > 5 s
    r2 = make(SimConfig(budget_fraction=1.0, alloc_cost_s=3.0)).run(e, Fn(two_runs), "t")
    rep = r2["log"]["reports"][0]
    assert rep["timeout"] and rep["outcome"].startswith("TIMEOUT_LATE")
    assert abs(r2["log"]["visits"][0]["arrive"] - (6.0 + d)) < 1e-9
    # what a policy sees of its own time budget
    seen = []

    def ask(view):
        seen.append(view.runs_available())
        view.evaluate(view.open_table)
        seen.append(view.runs_available())
        return Decision("COMMIT", "TEST", table=view.open_table)

    make(SimConfig(budget_fraction=1.0, alloc_cost_s=1.0, decision_timeout_s=5.0)).run(e, Fn(ask), "t")
    assert seen == [5, 4]


def test_competing_deadlines_some_incidents_cannot_be_served_in_time_and_no_policy_can_fix_it():
    """Three reports at the same second, eight urgent incidents each (24 in all), three UAVs, 240 s deadlines.
    One report alone is easy (all 8 on time); three together are not: some are late, also for the gold policy itself."""
    lms = ["Boat Jetty", "Canal Lock", "Rice Field A", "Railway Crossing", "Fuel Station", "North Bridge", "Hill Road Bend", "Rice Field B"]

    def table():
        return [row("I%d" % (k + 1), lm, "ANY", 3) for k, lm in enumerate(lms)]

    alone = make().run(Episode("E1", [ev(0, "c0", table(), NOOP)]), commit(NOOP), "t")
    assert alone["counts"]["on_time"] == 8
    e = Episode("E", [ev(0, "c%d" % n, table(), NOOP) for n in range(3)])
    r = make().run(e, commit(NOOP), "t")
    c = r["counts"]
    assert c["n"] == 24 and c["on_time"] + c["late"] + c["unverified"] + c["resolved_external"] == 24
    assert c["on_time"] < 24 and (c["late"] + c["unverified"]) >= 1
    r_or = make().run(e, commit(NOOP), "gold", oracle=True)
    assert r_or["counts"] == c                                   # the oracle policy is the same here: the misses are the world's, not the model's
    # every UAV works without gaps or overlap
    _check_visit_invariants(r)


def test_impossible_coverage_only_one_uav_has_thermal_so_not_everything_can_be_covered():
    """Four far-apart THERMAL incidents with 240 s deadlines: only UAV-02 can serve them, so some are late. The RGB UAVs are never sent
    (that would only waste trips), and the misses are the same for the gold policy: no fallback can cover what the fleet cannot reach."""
    rows = [row("I1", "Boat Jetty", "THERMAL", 3), row("I2", "Rice Field A", "THERMAL", 3),
            row("I3", "Railway Crossing", "THERMAL", 3), row("I4", "Hill Road Bend", "THERMAL", 3)]
    e = Episode("E", [ev(0, "c", rows, NOOP)])
    r = make().run(e, commit(NOOP), "t")
    assert {v["uav"] for v in r["log"]["visits"]} == {"UAV-02"}
    c = r["counts"]
    assert c["n"] == 4 and c["on_time"] < 4 and c["late"] + c["unverified"] >= 1
    assert r["log"]["wasted"] == 0
    assert make().run(e, commit(NOOP), "gold", oracle=True)["counts"] == c


def test_a_late_incident_is_late_and_not_unverified():
    """Deadlines shortened to 20 s: the UAV still gets there, so the incident is verified late (a different class from never verified)."""
    e = Episode("E", [ev(0, "c", [row("I1", "Clinic Gate", "RGB", 3)], NOOP)])
    r = make(SimConfig(budget_fraction=1.0, deadlines={1: 20.0, 2: 20.0, 3: 20.0})).run(e, commit(NOOP), "t")
    assert r["counts"]["late"] == 1 and r["counts"]["unverified"] == 0 and r["counts"]["on_time"] == 0


def test_incident_resolved_by_someone_else_is_counted_and_the_trip_is_wasted():
    far = {"action": "CREATE_VERIFICATION", "landmark": "Boat Jetty", "sensor": "ANY", "priority": 1}
    close = {"action": "CLOSE_INCIDENT", "incident": "N1"}
    e = Episode("E", [ev(0, "c", None, far), ev(5, "c", None, close)])
    r = make().run(e, commit(NOOP), "gold", oracle=True)
    assert r["counts"] == {"n": 1, "on_time": 0, "late": 0, "unverified": 0, "resolved_external": 1}
    assert r["log"]["wasted"] == 1 and r["log"]["visits"][0]["result"] == "empty"
    assert r["incidents"][0]["class"] == "resolved_external"


def test_moved_incident_the_leg_in_progress_is_not_recalled():
    """The incident moves while a UAV is flying to the old place. The UAV finds nothing there; the task is then flown to the new place."""
    upd = {"action": "UPDATE_INCIDENT", "incident": "I1", "landmark": "Rice Field B", "sensor": "RGB", "priority": 3}
    e = Episode("E", [ev(0, "c", [row("I1", "Clinic Gate", "RGB", 3)], NOOP), ev(10, "c", None, upd)])
    r = make().run(e, commit(NOOP), "gold", oracle=True)
    v = r["log"]["visits"]
    assert [(x["landmark"], x["result"]) for x in v] == [("Clinic Gate", "empty"), ("Rice Field B", "verified")], v
    assert r["counts"]["on_time"] == 1 and r["log"]["wasted"] == 1


def test_cover_task_with_two_cameras_goes_to_the_only_uav_that_has_both():
    rows = [row("I1", "Hill Road Bend", "THERMAL", 2)]
    cover = {"id": "C1", "landmark": "Hill Road Bend", "sensor": "RGB+THERMAL", "req": ("RGB", "THERMAL"), "priority": 2, "cover": True}
    e = Episode("E", [ev(0, "c", rows, NOOP)])
    r = make().run(e, Fn(lambda v: Decision("COMMIT", "FALLBACK_COVERED", table=[cover])), "t")
    v = r["log"]["visits"]
    assert len(v) == 1 and v[0]["uav"] == "UAV-02" and v[0]["cover"] and v[0]["result"] == "verified"
    assert r["counts"]["on_time"] == 1
    # cover rows are the system's own tasks: a later report never sees them in the open table
    seen = {}

    def later(view):
        seen["tb"] = view.open_table
        return Decision("COMMIT", "TEST", table=view.open_table)

    e2 = Episode("E", [ev(0, "c", rows, NOOP), ev(1, "c", None, NOOP)])
    pol = Fn(lambda v: Decision("COMMIT", "FALLBACK_COVERED", table=[cover]) if v.now == 0 else later(v))
    make().run(e2, pol, "t")
    assert seen["tb"] == []


def test_what_if_does_not_change_the_world_and_matches_the_real_plan():
    """view.evaluate() on the table that is then committed predicts the first assignments that really happen."""
    rows = [row("I1", "Clinic Gate", "RGB", 3), row("I2", "Rice Field B", "ANY", 2)]
    box = {}

    def f(view):
        tb = view.open_table
        box["ev"] = view.evaluate(tb)
        return Decision("COMMIT", "TEST", table=tb)

    s = make()
    r = s.run(Episode("E", [ev(0, "c", rows, NOOP)]), Fn(f), "t")
    plan = box["ev"].plan
    first = {u: ks[0] for u, ks in plan.paths.items() if ks}
    started = {v["uav"]: v["key"] for v in r["log"]["visits"]}
    for u, k in first.items():
        assert started[u] == k
    ok, det = alloc.check_requirements(plan, box["ev"].prob.tasks, {"c:I1": 240.0, "c:I2": 360.0}, box["ev"].prob.agents)
    assert box["ev"].ok == ok


# =====================================================================================================================
# determinism and invariants
# =====================================================================================================================
def _cases():
    import json as _j
    p = paths.PILOT / "data" / "cases.jsonl"
    return [_j.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def _random_episode(cases, rng, R, gap, eid):
    pick = rng.sample(cases, R)
    t, evs = 0.0, []
    for c in pick:
        evs.append(ReportEvent(t, c["id"], c["id"], [dict(x) for x in c["open"]], dict(c["gold"])))
        t += rng.expovariate(1.0 / gap)
    return Episode(eid, evs)


def _check_visit_invariants(res):
    """Per UAV: visits in time order, a visit starts after the previous one ended, flight time is at least distance / speed."""
    by_uav = {}
    for v in res["log"]["visits"]:
        by_uav.setdefault(v["uav"], []).append(v)
    for u, vs in by_uav.items():
        vs.sort(key=lambda v: v["arrive"])
        pos, free = U[u].start, 0.0
        for v in vs:
            need = travel(u, pos, L[v["landmark"]])
            assert v["arrive"] - need >= free - 1e-6, (u, v, "started before it was free")
            assert abs(v["finish"] - v["arrive"] - core.DWELL_S) < 1e-9
            pos, free = L[v["landmark"]], v["finish"]


def test_random_episodes_counts_add_up_and_uavs_obey_physics():
    if not (paths.PILOT / "data" / "cases.jsonl").exists():
        pytest.skip("pilot data not found")
    cases = [c for c in _cases() if c["style"] == "A"]
    rng = random.Random(7)
    s = make(SimConfig(budget_fraction=0.2))
    flips = 0
    for k in range(12):
        e = _random_episode(cases, rng, 14, 40.0, "r%d" % k)
        # a messy policy: accept the gold record most of the time, otherwise drop/close something or escalate
        def pol(view, rng=random.Random(k)):
            tb = view.open_table
            x = rng.random()
            if x < 0.15 and view.budget_left > 0:
                return Decision("ESCALATE", "ESCALATE")
            if x < 0.30 and tb:
                return Decision("COMMIT", "TEST", table=[r for r in tb if r is not tb[0]])
            return Decision("COMMIT", "TEST", table=tb)
        res = s.run(e, Fn(pol), "t")
        c = res["counts"]
        assert c["on_time"] + c["late"] + c["unverified"] + c["resolved_external"] == c["n"] == len(res["incidents"])
        assert all(i["class"] in CLASSES for i in res["incidents"])
        assert res["requests"] <= res["budget_cap"]
        _check_visit_invariants(res)
        # wasted trips = failed + empty
        assert res["log"]["wasted"] == res["log"]["failed"] + res["log"]["empty"]
        # total real incidents does not depend on the policy
        ref = s.run(e, commit(NOOP), "gold", oracle=True)
        assert ref["counts"]["n"] == c["n"]
        flips += ref["counts"]["unverified"]
    assert flips >= 0


def test_runs_are_deterministic():
    if not (paths.PILOT / "data" / "cases.jsonl").exists():
        pytest.skip("pilot data not found")
    cases = [c for c in _cases() if c["style"] == "A"]
    e = _random_episode(cases, random.Random(3), 14, 40.0, "d")
    a = make().run(e, commit(NOOP), "x", oracle=True)
    b = make().run(e, commit(NOOP), "x", oracle=True)
    ka = json.dumps([a["counts"], a["incidents"], a["log"]["visits"]], sort_keys=True)
    kb = json.dumps([b["counts"], b["incidents"], b["log"]["visits"]], sort_keys=True)
    assert ka == kb


def test_legacy_and_bounded_allocator_both_run_inside_the_same_engine():
    if not (paths.PILOT / "data" / "cases.jsonl").exists():
        pytest.skip("pilot data not found")
    cases = [c for c in _cases() if c["style"] == "A"]
    e = _random_episode(cases, random.Random(5), 10, 40.0, "l")
    out = {}
    for name in ("cbba_bounded", "legacy_greedy_s1"):
        r = Sim(alloc.make_allocator(name), SimConfig(budget_fraction=0.2)).run(e, commit(NOOP), name, oracle=True)
        _check_visit_invariants(r)
        out[name] = r["counts"]
    assert out["cbba_bounded"]["n"] == out["legacy_greedy_s1"]["n"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
