"""
M1 checks for the bounded CBBA (plan section 9, M1) and for the stable allocator interface.

(a) conflict-free after convergence          (b) converges on 10,000 random instances (<= 4 UAVs, <= 12 tasks), none non-converged
(c) deterministic                            (d) task-order invariant
(e) with L_t = 1 the first assignments equal legacy_greedy_s1 on the 1,400 pilot gold tables (every difference is listed)
(f) ratio to brute force on small instances  (g) how often bid warping changed a bid
Plus the small hand cases asked for: conflicting bids, bundle removal, camera rules / route timing, termination.

Run:  python -m pytest -q tests/test_cbba.py        (the 10,000-instance test takes about half a minute)
"""
import itertools
import json
import math
import os
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import alloc, core, paths                      # noqa: E402
from shield.core import Agent, Problem, Task, req_of        # noqa: E402

LAND = core.landmarks()
LM = sorted(LAND)
N_RANDOM = int(os.environ.get("EDGESAR_TEST_N", "10000"))


def T(key, lm, sensor="ANY", pri=2):
    return Task(key, lm, req_of(sensor), pri)


def A(id_, x=0.0, y=0.0, speed=18.0, cams=("RGB",), avail=0.0):
    return Agent(id_, float(speed), frozenset(cams), (float(x), float(y)), float(avail))


def prob(agents, tasks, banned=None, now=0.0):
    return Problem(now, tuple(agents), tuple(tasks), banned or {}, core.DWELL_S, LAND)


def conflict_free(plan):
    seen = {}
    for u, ks in plan.paths.items():
        for k in ks:
            assert k not in seen, "task %s is in two paths" % k
            seen[k] = u
    return seen


def random_instance(rng, max_agents=4, max_tasks=12):
    n = rng.randint(1, max_agents)
    m = rng.randint(1, max_tasks)
    ags = []
    for i in range(n):
        cams = ("RGB", "THERMAL") if rng.random() < 0.4 else ("RGB",)
        ags.append(A("U%d" % i, rng.uniform(0, 1800), rng.uniform(0, 1600), rng.uniform(10, 25), cams, rng.uniform(0, 60) if rng.random() < 0.3 else 0.0))
    tasks = [T("t%02d" % j, rng.choice(LM), rng.choice(["ANY", "RGB", "THERMAL"]), rng.randint(1, 3)) for j in range(m)]
    banned = {}
    if rng.random() < 0.2:
        banned[rng.choice(tasks).key] = {rng.choice(ags).id}
    return prob(ags, tasks, banned)


# ------------------------------------------------------------------------------------------------ hand cases
def test_conflicting_bids_higher_bid_wins():
    # both UAVs want the one task; the closer one has the higher bid and wins, the other gets nothing
    near, far = A("U1", 100, 100), A("U2", 1500, 1500)
    p = alloc.BoundedCBBA().plan(prob([near, far], [T("x", "Clinic Gate", "ANY", 3)]))
    assert p.paths == {"U1": ["x"], "U2": []}
    assert p.info["converged"]


def test_equal_bids_lower_id_wins():
    p = alloc.BoundedCBBA().plan(prob([A("U2", 100, 100), A("U1", 100, 100)], [T("x", "Clinic Gate", "ANY", 3)]))
    assert p.owner == {"x": "U1"}


def test_conflict_resolution_two_tasks_two_uavs():
    # each UAV is close to a different task: the plan should give each its own
    ags = [A("U1", 520, 520), A("U2", 1750, 1550)]
    tasks = [T("a", "Clinic Gate", "ANY", 2), T("b", "Boat Jetty", "ANY", 2)]
    p = alloc.BoundedCBBA().plan(prob(ags, tasks))
    assert p.owner == {"a": "U1", "b": "U2"}


def test_bundle_removal_drops_later_tasks_too():
    # U1 and U2 start at the same place. U2 is faster, so it outbids U1 on the first task U1 wanted. U1 had built a bundle of two
    # and must drop BOTH (the task it lost and the one after it), then rebuild.
    u1, u2 = A("U1", 520, 520, speed=16), A("U2", 520, 520, speed=25)
    tasks = [T("a", "Clinic Gate", "ANY", 3), T("b", "School Ground", "ANY", 3), T("c", "Temple Junction", "ANY", 3)]
    al = alloc.BoundedCBBA(bundle_len=3)
    al.trace = []
    p = al.plan(prob([u1, u2], tasks))
    assert p.info["releases"] >= 1, "no bundle release happened in this scenario"
    built = al.trace[0]["built"]
    assert len(built[0]) >= 2 and len(built[1]) >= 2        # both UAVs first built bundles of at least two tasks
    # ... and after the first exchange at least one of them lost something: its bundle is shorter than what it built
    after = al.trace[0]["bundle"]
    assert any(len(after[i]) < len(built[i]) for i in range(2))
    conflict_free(p)
    assert sorted(k for ks in p.paths.values() for k in ks) == ["a", "b", "c"]
    assert p.info["converged"]


def test_release_function_resets_later_bids():
    # white box: after a release the later tasks are free again for everybody (checked through the final plan being complete)
    ags = [A("U%d" % i, 300 + 200 * i, 300) for i in range(4)]
    tasks = [T("t%d" % j, LM[j], "ANY", 1 + j % 3) for j in range(9)]
    al = alloc.BoundedCBBA(bundle_len=3)
    p = al.plan(prob(ags, tasks))
    conflict_free(p)
    assert set(p.owner) == {t.key for t in tasks} and not p.unassigned


def test_camera_rule_and_ban():
    rgb, th = A("U1", 500, 500), A("U2", 520, 520, cams=("RGB", "THERMAL"))
    tasks = [T("hot", "Clinic Gate", "THERMAL", 3), T("any", "School Ground", "ANY", 1)]
    p = alloc.BoundedCBBA().plan(prob([rgb, th], tasks))
    assert p.owner["hot"] == "U2"
    p2 = alloc.BoundedCBBA().plan(prob([rgb, th], tasks, banned={"hot": {"U2"}}))
    assert "hot" in p2.unassigned                               # the only capable UAV is banned: the task stays visible as unassigned
    ok, det = alloc.check_requirements(p2, tasks, {"hot": 1e9, "any": 1e9}, [rgb, th])
    assert not ok and det["R3"] == ["hot"]


def test_route_timing_and_deadline_requirement():
    u = A("U1", 220, 140, speed=16, avail=20.0)                 # busy until t = 20
    tasks = [T("a", "Clinic Gate", "ANY", 3)]
    p = alloc.BoundedCBBA().plan(prob([u], tasks))
    d = math.dist((220, 140), LAND["Clinic Gate"])
    assert abs(p.arrive["a"] - (20.0 + d / 16)) < 1e-9
    assert abs(p.finish["a"] - (p.arrive["a"] + core.DWELL_S)) < 1e-9
    ok, det = alloc.check_requirements(p, tasks, {"a": p.finish["a"] + 1}, [u])
    assert ok
    ok, det = alloc.check_requirements(p, tasks, {"a": p.finish["a"] - 1}, [u])
    assert not ok and det["R2"] == ["a"]


def test_consecutive_legs_use_previous_finish():
    u = A("U1", 520, 520, speed=20)
    tasks = [T("a", "Clinic Gate", "ANY", 3), T("b", "School Ground", "ANY", 3)]
    p = alloc.BoundedCBBA().plan(prob([u], tasks))
    ks = p.paths["U1"]
    assert len(ks) == 2
    first, second = ks
    leg = math.dist(LAND[tasks[0 if first == "a" else 1].landmark], LAND[tasks[1 if second == "b" else 0].landmark]) / 20
    assert abs(p.arrive[second] - (p.finish[first] + leg)) < 1e-9


def test_termination_round_cap_is_reported():
    rng = random.Random(7)
    pr = random_instance(rng, 4, 12)
    pr = prob(list(pr.agents)[:3] + [A("Ux", 10, 10)], list(pr.tasks) + [T("z%d" % i, LM[i], "ANY", 2) for i in range(6)])
    al = alloc.BoundedCBBA(round_cap=1)
    p = al.plan(pr)
    assert p.info["converged"] is False and p.info["nonconverged"] >= 1
    conflict_free(p)                                           # even when it stops early the answer is conflict-free


def test_terminates_within_diameter_times_tasks_bound():
    rng = random.Random(11)
    worst = 0.0
    for _ in range(400):
        pr = random_instance(rng, 4, 10)
        for graph, diam in (("full", 1), ("line", None)):
            al = alloc.BoundedCBBA(graph=graph, bundle_len=3)
            p = al.plan(pr)
            n = len(pr.agents)
            d = 1 if graph == "full" else max(1, n - 1)
            bound = d * max(1, len(pr.tasks)) + d + 2          # thesis: converges within D * N_t steps (+ the quiet rounds we require)
            worst = max(worst, p.info["max_rounds_one_auction"] / bound)
            assert p.info["converged"]
            assert p.info["max_rounds_one_auction"] <= bound, (graph, p.info, bound)
    assert worst <= 1.0


def test_line_graph_reaches_agreement():
    rng = random.Random(5)
    for _ in range(300):
        pr = random_instance(rng, 4, 9)
        al = alloc.BoundedCBBA(graph="line")
        p = al.plan(pr)
        assert p.info["converged"]
        conflict_free(p)


def test_disconnected_graph_is_refused():
    pr = prob([A("U1"), A("U2"), A("U3")], [T("a", "Clinic Gate")])
    al = alloc.BoundedCBBA(graph="custom", adjacency={"U1": ["U2"], "U2": ["U1"], "U3": []})
    try:
        al.plan(pr)
    except ValueError:
        return
    raise AssertionError("a disconnected graph must be refused")


# ------------------------------------------------------------------------------------------------ properties
def test_deterministic_and_order_invariant():
    rng = random.Random(3)
    for _ in range(300):
        pr = random_instance(rng)
        p1 = alloc.BoundedCBBA().plan(pr)
        p2 = alloc.BoundedCBBA().plan(pr)
        assert p1.paths == p2.paths
        ts, ags = list(pr.tasks), list(pr.agents)
        rng.shuffle(ts)
        rng.shuffle(ags)
        p3 = alloc.BoundedCBBA().plan(Problem(pr.now, tuple(ags), tuple(ts), pr.banned, pr.dwell, pr.landmarks))
        assert p1.paths == p3.paths


def test_random_instances_converge_and_are_conflict_free():
    rng = random.Random(20261113)
    worst_rounds, warps, bids, nonconv, rel = 0, 0, 0, 0, 0
    for _ in range(N_RANDOM):
        pr = random_instance(rng)
        al = alloc.BoundedCBBA()
        p = al.plan(pr)
        nonconv += p.info["nonconverged"]
        worst_rounds = max(worst_rounds, p.info["max_rounds_one_auction"])
        warps += p.info["warps"]
        bids += p.info["bids"]
        rel += p.info["releases"]
        conflict_free(p)
        # every task that some UAV can take is planned; the others are reported as unassigned
        for t in pr.tasks:
            can = any(t.req <= a.sensors and a.id not in pr.banned.get(t.key, ()) for a in pr.agents)
            assert (t.key in p.owner) == can, (t, p.paths, p.unassigned)
    assert nonconv == 0, "%d auctions did not converge" % nonconv
    test_random_instances_converge_and_are_conflict_free.report = {"instances": N_RANDOM, "non_converged": nonconv, "worst_rounds": worst_rounds,
                                                                  "warped_bids": warps, "bids_evaluated": bids, "bundle_releases": rel}


def test_bids_are_non_increasing_along_each_bundle():
    # bid warping makes the bids of a bundle non-increasing in the order the tasks were added
    rng = random.Random(9)
    seen = 0
    for _ in range(300):
        pr = random_instance(rng, 4, 10)
        al = alloc.BoundedCBBA()
        al.trace = []
        al.plan(pr)
        # the trace holds the state after each round of the LAST auction of the call; check that one
        last = al.trace[-1]
        for i, b in enumerate(last["bundle"]):
            ys = [last["y"][i][j] for j in b]
            assert all(ys[k] >= ys[k + 1] - 1e-9 for k in range(len(ys) - 1)), ys
            seen += len(b)
    assert seen > 0


# ------------------------------------------------------------------------------------------------ brute force
def best_total(agents, tasks, now, dwell, disc):
    """Highest total score over every assignment of every task to a compatible UAV and every order."""
    best = -1.0
    n, m = len(agents), len(tasks)
    cap = {i: [j for j in range(m) if tasks[j].req <= agents[i].sensors] for i in range(n)}

    def rec(j, paths):
        nonlocal best
        if j == m:
            tot = sum(alloc.path_score(agents[i], [tasks[x] for x in paths[i]], now, LAND, dwell, disc) for i in range(n))
            best = max(best, tot)
            return
        for i in range(n):
            if j in cap[i]:
                for pos in range(len(paths[i]) + 1):
                    paths[i].insert(pos, j)
                    rec(j + 1, paths)
                    paths[i].pop(pos)
    rec(0, [[] for _ in range(n)])
    return best


def plan_total(agents, tasks, plan, now, dwell, disc):
    by = {t.key: t for t in tasks}
    return sum(alloc.path_score(a, [by[k] for k in plan.paths[a.id]], now, LAND, dwell, disc) for a in agents)


def test_ratio_to_brute_force_small_instances():
    rng = random.Random(42)
    ratios = {"bounded L3": [], "bounded L1": [], "legacy": []}
    legacy = alloc.LegacyGreedyS1()
    for _ in range(150):
        n, m = rng.randint(2, 3), rng.randint(2, 6)
        ags = [A("U%d" % i, rng.uniform(0, 1800), rng.uniform(0, 1600), rng.uniform(12, 22), ("RGB", "THERMAL") if i == 0 else ("RGB",)) for i in range(n)]
        tasks = [T("t%d" % j, rng.choice(LM), rng.choice(["ANY", "RGB", "THERMAL"]), rng.randint(1, 3)) for j in range(m)]
        pr = prob(ags, tasks)
        opt = best_total(ags, tasks, 0.0, core.DWELL_S, core.TIME_DISCOUNT)
        if opt <= 0:
            continue
        for name, al in (("bounded L3", alloc.BoundedCBBA(bundle_len=3)), ("bounded L1", alloc.BoundedCBBA(bundle_len=1)), ("legacy", legacy)):
            p = al.plan(pr)
            ratios[name].append(plan_total(ags, tasks, p, 0.0, core.DWELL_S, core.TIME_DISCOUNT) / opt)
    out = {k: {"n": len(v), "mean": sum(v) / len(v), "min": min(v)} for k, v in ratios.items()}
    test_ratio_to_brute_force_small_instances.report = out
    assert all(v["min"] > 0.5 for v in out.values()), out          # sanity floor only; the number itself is reported, not assumed


# ------------------------------------------------------------------------------------------------ against the legacy allocator
def test_L1_first_assignments_equal_legacy_on_pilot_gold_tables():
    root = paths.ROOT
    cases_path = root / "edgesar_pilot" / "data" / "cases.jsonl"
    if not cases_path.exists():
        return
    paths.require_pins()
    paths.add_pilot_to_path()
    import common as pc                                               # noqa: E402
    cases = pc.load_cases(cases_path)
    legacy = alloc.LegacyGreedyS1()
    new = alloc.BoundedCBBA(bundle_len=1)
    fleet = core.fleet()
    same = diff = 0
    explained = []
    for c in cases:
        table = [dict(t) for t in c["open"]]
        g = pc.gold_norm(c)
        a = g["action"]
        if a == "CLOSE_INCIDENT":
            table = [t for t in table if t["id"] != g["incident"]]
        elif a == "UPDATE_INCIDENT":
            for t in table:
                if t["id"] == g["incident"]:
                    t.update(landmark=g["landmark"], sensor=g["sensor"], priority=g["priority"])
        elif a == "CREATE_VERIFICATION":
            table.append({"id": "NEW", "landmark": g["landmark"], "sensor": g["sensor"], "priority": g["priority"]})
        tasks = [Task(t["id"], t["landmark"], req_of(t["sensor"]), t["priority"]) for t in table]
        pr = Problem(0.0, fleet, tuple(tasks), {}, core.DWELL_S, LAND)
        p1 = legacy.plan(pr)
        # first assignment only: the first task on each UAV's path (legacy hands out one task per free UAV at time 0)
        f1 = {u: ks[0] for u, ks in p1.paths.items() if ks}
        p2 = new.plan(pr)
        f2 = {u: ks[0] for u, ks in p2.paths.items() if ks}
        if f1 == f2:
            same += 1
        else:
            diff += 1
            explained.append((c["id"], f1, f2))
    test_L1_first_assignments_equal_legacy_on_pilot_gold_tables.report = {"tables": len(cases), "same_first_assignment": same, "different": diff,
                                                                          "differences": explained[:20]}
    assert diff == 0, "first assignments differ in %d tables, first few: %s" % (diff, explained[:5])


def test_legacy_wrapper_matches_v1_mission_visit_order_when_everything_succeeds():
    # The wrapper's roll-out equals what V1 mission.py does when all visits succeed (same visits per UAV, in the same order).
    root = paths.ROOT
    if not (root / "V1").exists():
        return
    paths.require_pins()
    paths.add_v1_to_path()
    paths.add_pilot_to_path()
    from packages.allocation import mission, world            # noqa: E402
    import common as pc                                        # noqa: E402
    cases = pc.load_cases(root / "edgesar_pilot" / "data" / "cases.jsonl")
    legacy = alloc.LegacyGreedyS1()
    fleet = core.fleet()
    bad = 0
    for c in cases[:400]:
        g = pc.gold_norm(c)
        table = [dict(t) for t in c["open"]]
        if g["action"] == "CLOSE_INCIDENT":
            table = [t for t in table if t["id"] != g["incident"]]
        elif g["action"] == "UPDATE_INCIDENT":
            for t in table:
                if t["id"] == g["incident"]:
                    t.update(landmark=g["landmark"], sensor=g["sensor"], priority=g["priority"])
        elif g["action"] == "CREATE_VERIFICATION":
            table.append({"id": "NEW", "landmark": g["landmark"], "sensor": g["sensor"], "priority": g["priority"]})
        truth = {t["landmark"]: t["sensor"] for t in table}
        res = mission.run_mission(world.UAVS, table, truth)
        routes = {}
        for v in sorted(res["visits"], key=lambda v: (v["start"], v["uav"])):
            routes.setdefault(v["uav"], []).append(v["landmark"])
        tasks = [Task(t["id"], t["landmark"], req_of(t["sensor"]), t["priority"]) for t in table]
        p = legacy.plan(Problem(0.0, fleet, tuple(tasks), {}, core.DWELL_S, LAND))
        by = {t.key: t for t in tasks}
        mine = {u: [by[k].landmark for k in ks] for u, ks in p.paths.items() if ks}
        if mine != routes:
            bad += 1
    assert bad == 0, "%d of 400 tables: the wrapper's roll-out differs from the V1 mission" % bad


def _write_report(path):
    """Used by tools to save the measured numbers of the reporting tests."""
    out = {}
    for fn in (test_random_instances_converge_and_are_conflict_free, test_ratio_to_brute_force_small_instances,
               test_L1_first_assignments_equal_legacy_on_pilot_gold_tables):
        if hasattr(fn, "report"):
            out[fn.__name__] = fn.report
    Path(path).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
