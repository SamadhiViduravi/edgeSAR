"""
M5 checks for the Shield and the arms (plan section 9, M5): one test per outcome class and per scenario type, with hand-made candidate sets
so that the expected decision is known in advance.  Also: threshold calibration, budget caps, the run counts that are charged as decision time.

Run:  python -m pytest -q tests/test_policy.py
"""
import math
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest                                                        # noqa: E402

from shield import alloc, core                                       # noqa: E402
from shield.cover import build_cover                                 # noqa: E402
from shield.policy import CommitPolicy, Observer, RiskGate, ShieldPolicy, asks, rate_threshold   # noqa: E402
from shield.sim import Decision, Episode, ReportEvent, Sim, SimConfig, apply_record               # noqa: E402

NOOP = {"action": "NO_ACTION"}


def row(i, lm, sensor="ANY", pri=2):
    return {"id": i, "landmark": lm, "sensor": sensor, "priority": pri}


def key_of(n):
    return tuple(n.get(k) for k in ("action", "incident", "landmark", "sensor", "priority"))


def cand(norm, score):
    return {"key": key_of(norm), "norm": norm, "score": score}


def upd(i, lm, s, p):
    return {"action": "UPDATE_INCIDENT", "incident": i, "landmark": lm, "sensor": s, "priority": p}


def create(lm, s, p):
    return {"action": "CREATE_VERIFICATION", "landmark": lm, "sensor": s, "priority": p}


def close(i):
    return {"action": "CLOSE_INCIDENT", "incident": i}


class FakeSvc:
    def __init__(self, cands, pilot=0, conf=0.5):
        self.cands, self.pilot, self.conf = cands, pilot, conf

    def candidates(self, rid):
        return self.cands

    def pilot_record(self, rid):
        return self.cands[self.pilot]

    def confidence(self, rid):
        return self.conf

    def top_score(self, rid):
        return self.cands[0]["score"]


def run_one(policy, open_rows, gold=NOOP, cfg=None, allocator=None, t=0.0):
    sim = Sim(allocator or alloc.BoundedCBBA(), cfg or SimConfig(budget_fraction=1.0))
    e = Episode("E", [ReportEvent(t, "c", "c", [dict(r) for r in open_rows], gold)])
    return sim.run(e, policy, "t")


def outcome(res):
    return res["log"]["reports"][0]["outcome"]


def diag(res):
    return res["log"]["reports"][0]["diag"]


I1 = [row("I1", "Clinic Gate", "RGB", 2)]
Q = 0.75        # conformal threshold: candidates with score >= 0.25 are in the set


# =====================================================================================================================
# outcome classes
# =====================================================================================================================
def test_accept_when_every_candidate_gives_the_same_execution_even_if_the_records_differ():
    """Scenario: harmless record change. Priority 3 versus 2 for the only task: both plans send the same UAV to the same place."""
    cands = [cand(upd("I1", "Clinic Gate", "RGB", 3), 0.6), cand(upd("I1", "Clinic Gate", "RGB", 2), 0.3), cand(close("I1"), 0.1)]
    cands[2]["score"] = 0.1                                         # outside the set (1 - 0.1 = 0.9 > Q)
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), I1)
    assert outcome(res) == "ACCEPT"
    d = diag(res)
    assert d["set_size"] == 2 and d["certified"] and d["distinct_sigs"] == 1 and d["rho"] == 0.0
    assert res["log"]["reports"][0]["runs"] == 2                    # one allocator run per member of the set
    assert res["counts"]["on_time"] == 1


def test_the_confidence_gate_would_not_accept_that_report_but_the_shield_does():
    """Same candidates: the pilot confidence is low (0.5), so a confidence gate with a threshold above 0.5 asks for verification."""
    cands = [cand(upd("I1", "Clinic Gate", "RGB", 3), 0.6), cand(upd("I1", "Clinic Gate", "RGB", 2), 0.3)]
    gate = RiskGate(FakeSvc(cands, conf=0.5), "conf", (0.4,), 1.0)       # ask when 1 - conf = 0.5 > 0.4
    assert outcome(run_one(gate, I1)) == "ESCALATE"
    assert outcome(run_one(ShieldPolicy(FakeSvc(cands, conf=0.5), Q), I1)) == "ACCEPT"


def test_not_certified_when_candidates_lead_to_different_plans_then_escalate_if_budget_allows():
    """Scenario: consequential error possible. 'nothing happens' versus 'a new incident at Market Square': different task sets, different plans."""
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), I1, gold=create("Market Square", "ANY", 3))
    assert outcome(res) == "ESCALATE" and diag(res)["reason"] == "DIFFERENT_PLANS" and diag(res)["certified"] is False
    assert abs(diag(res)["rho"] - 0.45 / 1.0) < 1e-9                    # mass of the members whose plan differs from the committed one
    assert res["requests"] == 1 and res["log"]["reports"][0]["runs"] == 2
    # the verified record arrives 60 s later, so the new incident is served late relative to the instant commit, but it is served
    assert res["counts"]["n"] == 2 and res["counts"]["unverified"] == 0


def test_fallback_covered_when_no_budget_and_the_cover_is_feasible():
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), I1, gold=create("Market Square", "ANY", 3), cfg=SimConfig(budget_fraction=0.0))
    assert outcome(res) == "FALLBACK_COVERED"
    d = diag(res)
    assert d["cover"]["n_tasks"] == 2 and d["cover"]["n_new"] == 1 and not d["partial_cover"]
    assert res["counts"]["on_time"] == 2 and res["counts"]["unverified"] == 0
    assert res["log"]["reports"][0]["runs"] == 3                      # two members + the cover


def test_cover_costs_a_wasted_trip_when_the_extra_task_was_not_real():
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), I1, gold=NOOP, cfg=SimConfig(budget_fraction=0.0))
    assert outcome(res) == "FALLBACK_COVERED"
    assert res["log"]["empty"] == 1 and res["log"]["wasted"] == 1       # the UAV went to Market Square for nothing
    assert res["counts"]["n"] == 1 and res["counts"]["on_time"] == 1    # but the real incident is untouched


def test_fallback_unresolved_when_the_cover_cannot_meet_the_requirements():
    """Scenario: complete coverage is impossible (here: 20 s deadlines). The cover is committed best-effort and the failure is listed."""
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    cfg = SimConfig(budget_fraction=0.0, deadlines={1: 20.0, 2: 20.0, 3: 20.0})
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), I1, gold=create("Market Square", "ANY", 3), cfg=cfg)
    assert outcome(res) == "FALLBACK_UNRESOLVED"
    assert diag(res)["uncovered"]["R2"]
    assert res["counts"]["late"] == 2                                 # both are served, but not by the 20 s deadlines


def test_accept_infeasible_when_certified_but_the_fleet_cannot_meet_the_deadline():
    cands = [cand(upd("I1", "Clinic Gate", "RGB", 3), 0.9)]
    cfg = SimConfig(budget_fraction=1.0, deadlines={1: 20.0, 2: 20.0, 3: 20.0})
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), I1, cfg=cfg)
    assert outcome(res) == "ACCEPT_INFEASIBLE" and diag(res)["unmet"]["R2"]
    assert res["requests"] == 0                                       # verification would not help, so none is requested


def test_uncertified_commit_in_the_no_fallback_ablation():
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    res = run_one(ShieldPolicy(FakeSvc(cands), Q, cover=False), I1, gold=create("Market Square", "ANY", 3), cfg=SimConfig(budget_fraction=0.0))
    assert outcome(res) == "UNCERTIFIED_COMMIT"
    assert res["counts"]["unverified"] == 1                           # the missed new incident, visible in the results


def test_timeout_when_the_what_if_runs_do_not_fit_into_the_time_limit():
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    cfg = SimConfig(budget_fraction=1.0, alloc_cost_s=2.0, decision_timeout_s=5.0)        # 3 runs would need 6 s
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), I1, cfg=cfg)
    assert outcome(res) == "TIMEOUT" and res["log"]["reports"][0]["runs"] == 0
    assert diag(res)["needed_runs"] == 3


# =====================================================================================================================
# scenario types: sets that cannot be used
# =====================================================================================================================
def test_empty_set_is_uncertified_and_not_truncated():
    cands = [cand(NOOP, 0.2), cand(create("Market Square", "ANY", 3), 0.2)]
    res = run_one(ShieldPolicy(FakeSvc(cands), 0.5), I1, cfg=SimConfig(budget_fraction=0.0))         # both 1-0.2 = 0.8 > 0.5
    assert diag(res)["set_size"] == 0 and diag(res)["reason"] == "EMPTY" and outcome(res) == "FALLBACK_PARTIAL"      # not every plausible record is covered
    assert diag(res)["partial_cover"] is True                         # cover built from the top-K candidates instead
    assert res["log"]["reports"][0]["runs"] == 1                      # no signature runs, only the cover


def test_oversized_set_is_uncertified_and_counted():
    cands = [cand(create(lm, "ANY", 3), 0.1) for lm in ("Market Square", "Fuel Station", "Canal Lock", "Boat Jetty")]
    res = run_one(ShieldPolicy(FakeSvc(cands), 0.95, K=3), I1, cfg=SimConfig(budget_fraction=0.0))
    assert diag(res)["set_size"] == 4 and diag(res)["reason"] == "OVERSIZE" and outcome(res) == "FALLBACK_PARTIAL"
    assert diag(res)["cover"]["n_members"] == 3                       # partial cover: top-K only


def test_committed_record_outside_the_set_is_uncertified():
    cands = [cand(NOOP, 0.5), cand(create("Market Square", "ANY", 3), 0.5)]
    svc = FakeSvc(cands, pilot=1)
    svc.cands = [dict(cands[0], score=0.9), dict(cands[1], score=0.05)]
    res = run_one(ShieldPolicy(svc, 0.3), I1, cfg=SimConfig(budget_fraction=0.0))                    # only the first is in the set; pilot record is the second
    assert diag(res)["r_in_set"] is False and diag(res)["reason"] == "RHAT_OUT"


def test_missing_candidate_the_shield_accepts_a_wrong_record_and_the_incident_is_missed():
    """Scenario: missing candidate (parser miss). The gold record is not among the candidates, the set is a confident singleton, the Shield accepts,
    and the real incident is never verified. The guarantee does not cover this case: it is counted as a coverage failure and shows up as a miss."""
    cands = [cand(NOOP, 0.97), cand(create("Fuel Station", "ANY", 3), 0.03)]
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), I1, gold=create("Market Square", "ANY", 3))
    assert outcome(res) == "ACCEPT" and diag(res)["set_size"] == 1
    assert res["counts"]["unverified"] == 1


def test_competing_deadlines_two_thermal_needs_with_a_single_thermal_uav():
    """Scenario: competing deadlines. Two priority-3 THERMAL tasks, only UAV-02 can serve them: the cover is feasible only if both fit."""
    rows = [row("I1", "Clinic Gate", "THERMAL", 3), row("I2", "Railway Crossing", "THERMAL", 3)]
    cands = [cand(NOOP, 0.5), cand(upd("I1", "Clinic Gate", "THERMAL", 2), 0.5)]
    res = run_one(ShieldPolicy(FakeSvc(cands), Q), rows, cfg=SimConfig(budget_fraction=1.0))
    assert {v["uav"] for v in res["log"]["visits"]} == {"UAV-02"}
    assert outcome(res) in ("ACCEPT", "ACCEPT_INFEASIBLE")             # a priority change does not change the plan with two tasks on one UAV


def test_singleton_only_ablation_rejects_what_the_full_shield_certifies():
    cands = [cand(upd("I1", "Clinic Gate", "RGB", 3), 0.6), cand(upd("I1", "Clinic Gate", "RGB", 2), 0.3)]
    full = run_one(ShieldPolicy(FakeSvc(cands), Q), I1)
    nodown = run_one(ShieldPolicy(FakeSvc(cands), Q, mode="nodown"), I1)
    assert outcome(full) == "ACCEPT" and outcome(nodown) in ("ESCALATE", "FALLBACK_COVERED")
    assert diag(nodown)["reason"] == "SINGLETON_ONLY"


def test_top2_ablation_has_no_calibration_and_uses_the_top_two_candidates_only():
    cands = [cand(upd("I1", "Clinic Gate", "RGB", 3), 0.5), cand(upd("I1", "Clinic Gate", "RGB", 2), 0.3), cand(create("Fuel Station", "ANY", 1), 0.2)]
    res = run_one(ShieldPolicy(FakeSvc(cands), 0.0, mode="top2"), I1)          # q = 0 would give an empty conformal set; top2 ignores it
    assert outcome(res) == "ACCEPT" and diag(res)["set_size"] == 2


# =====================================================================================================================
# budget, thresholds, caps
# =====================================================================================================================
def test_escalation_stops_when_the_budget_is_used_up():
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    sim = Sim(alloc.BoundedCBBA(), SimConfig(budget_fraction=0.2))                   # 5 reports -> cap 1
    evs = [ReportEvent(100.0 * j, "c%d" % j, "c%d" % j, [dict(r) for r in I1], NOOP) for j in range(5)]
    res = sim.run(Episode("E", evs), ShieldPolicy(FakeSvc(cands), Q), "t")
    outs = [r["outcome"] for r in res["log"]["reports"]]
    assert outs.count("ESCALATE") == 1 and outs.count("FALLBACK_COVERED") == 4 and res["requests"] == 1 == res["budget_cap"]


def test_rate_threshold_hits_the_target_rate_including_ties():
    rng = random.Random(3)
    for risks in ([(rng.random(),) for _ in range(500)],
                  [(1.0, 0.3)] * 100 + [(0.0, rng.random()) for _ in range(400)],          # a big mass point
                  [(float(rng.randint(0, 3)),) for _ in range(500)]):
        for b in (0.05, 0.1, 0.3):
            theta, xi = rate_threshold(risks, b)
            u = [rng.random() for _ in risks]
            exact = sum(1 for r in risks if r > theta) + xi * sum(1 for r in risks if r == theta)
            assert abs(exact / len(risks) - b) < 1e-9
            # realised with random tie-breaking
            hits = sum(asks(r, ui, theta, xi) for r, ui in zip(risks, u))
            assert abs(hits / len(risks) - b) < 0.06
    assert rate_threshold([(0.1,), (0.2,)], 1.0)[0] is None


def test_every_arm_commits_the_same_record_when_nothing_is_asked():
    """With a threshold that never fires, the gates behave exactly like A1 (same table, same outcome)."""
    cands = [cand(upd("I1", "Clinic Gate", "RGB", 3), 0.6), cand(upd("I1", "Clinic Gate", "RGB", 2), 0.3)]
    base = run_one(CommitPolicy(FakeSvc(cands)), I1)
    for pol in (RiskGate(FakeSvc(cands), "conf", (2.0,), 0.0), RiskGate(FakeSvc(cands), "topscore", (2.0,), 0.0),
                ShieldPolicy(FakeSvc(cands), Q)):
        r = run_one(pol, I1)
        assert r["counts"] == base["counts"] and r["incidents"][0]["verified_at"] == pytest.approx(base["incidents"][0]["verified_at"], abs=0.1)


def test_observer_is_free_and_commits_like_a1():
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    obs = Observer(FakeSvc(cands), Q)
    r_obs = run_one(obs, I1, cfg=SimConfig(budget_fraction=0.0))
    r_a1 = run_one(CommitPolicy(FakeSvc(cands)), I1, cfg=SimConfig(budget_fraction=0.0))
    assert r_obs["log"]["reports"][0]["runs"] == 0 and r_obs["counts"] == r_a1["counts"]
    assert obs.rows[0]["a8"][0] > 0 and not obs.rows[0]["a8_cert"]
    assert r_obs["log"]["decision_s"] == 0.0 and r_obs["log"]["engine_runs"] > 0


# =====================================================================================================================
# the cover builder
# =====================================================================================================================
def test_cover_rules_union_max_priority_one_task_per_location_and_closing_only_if_all_candidates_close():
    base = [row("I1", "Clinic Gate", "RGB", 1), row("I2", "North Bridge", "THERMAL", 2)]
    members = [cand(close("I2"), 0.4),                                     # closes I2
               cand(upd("I1", "Clinic Gate", "THERMAL", 3), 0.3),         # makes I1 thermal and urgent
               cand(create("Clinic Gate", "ANY", 2), 0.3)]                 # a second task at the same place
    rows, info = build_cover(base, members, tag="x")
    by = {r["landmark"]: r for r in rows}
    assert set(by) == {"Clinic Gate", "North Bridge"}                  # one task per location; I2 kept because two candidates keep it
    assert by["Clinic Gate"]["priority"] == 3 and set(by["Clinic Gate"]["req"]) == {"RGB", "THERMAL"}
    assert by["Clinic Gate"]["id"] == "I1" and not by["Clinic Gate"]["cover"]        # existing incident keeps its id and clock
    assert by["North Bridge"]["id"] == "I2"
    # if every candidate closes I2 it disappears
    rows2, info2 = build_cover(base, [cand(close("I2"), 0.5), cand(close("I2"), 0.5)], tag="y")
    assert {r["landmark"] for r in rows2} == {"Clinic Gate"} and info2["closed"] == ["I2"]
    # a task that exists in no open row gets a new cover id
    rows3, _ = build_cover(base, [cand(create("Fuel Station", "RGB", 2), 1.0)], tag="z")
    new = [r for r in rows3 if r["landmark"] == "Fuel Station"]
    assert new[0]["cover"] and new[0]["id"].startswith("Cz_")


def test_cover_with_both_cameras_goes_to_the_thermal_uav():
    cands = [cand(upd("I1", "Hill Road Bend", "THERMAL", 2), 0.5), cand(upd("I1", "Hill Road Bend", "RGB", 2), 0.5)]
    rows = [row("I1", "Hill Road Bend", "THERMAL", 2)]
    res = run_one(ShieldPolicy(FakeSvc(cands, pilot=1), Q), rows, cfg=SimConfig(budget_fraction=0.0))
    assert outcome(res) == "FALLBACK_COVERED"
    v = res["log"]["visits"]
    assert len(v) == 1 and v[0]["uav"] == "UAV-02" and v[0]["result"] == "verified"


def test_location_cover_keeps_the_committed_camera_and_says_so():
    """Development variant A8c: the cover adds the other candidates' LOCATIONS but keeps r_hat's cameras and priority. A candidate that needs the
    other camera is then not served by the cover, and the outcome is FALLBACK_PARTIAL, not FALLBACK_COVERED. The plan's full cover serves both."""
    cands = [cand(upd("I1", "Clinic Gate", "RGB", 2), 0.55), cand(upd("I1", "Clinic Gate", "THERMAL", 2), 0.45)]
    cfg = SimConfig(budget_fraction=0.0)
    loc = run_one(ShieldPolicy(FakeSvc(cands), Q, cover_kw={"camera": "rhat", "priority": "rhat"}), I1, cfg=cfg)
    assert outcome(loc) == "FALLBACK_PARTIAL" and diag(loc)["cover_unserved_candidates"] == 1 and diag(loc)["cover_complete"] is False
    full = run_one(ShieldPolicy(FakeSvc(cands), Q), I1, cfg=cfg)
    assert outcome(full) == "FALLBACK_COVERED" and diag(full)["cover_complete"] is True


def test_location_cover_still_covers_a_new_location():
    cands = [cand(NOOP, 0.55), cand(create("Market Square", "ANY", 3), 0.45)]
    res = run_one(ShieldPolicy(FakeSvc(cands), Q, cover_kw={"camera": "rhat", "priority": "rhat"}), I1, gold=create("Market Square", "ANY", 3),
                  cfg=SimConfig(budget_fraction=0.0))
    assert outcome(res) == "FALLBACK_COVERED" and res["counts"]["unverified"] == 0 and res["counts"]["on_time"] == 2


def test_uncovered_rows_rules():
    from shield.cover import uncovered_rows
    cover = [{"id": "I1", "landmark": "A", "sensor": "RGB", "req": ("RGB",), "priority": 2, "cover": False}]
    assert uncovered_rows(cover, [row("X", "A", "RGB", 2)]) == []                      # same
    assert uncovered_rows(cover, [row("X", "A", "RGB", 1)]) == []                      # lower priority is served by a higher one
    assert uncovered_rows(cover, [row("X", "A", "RGB", 3)]) == ["X"]                   # higher priority is not
    assert uncovered_rows(cover, [row("X", "A", "THERMAL", 2)]) == ["X"]               # other camera is not
    assert uncovered_rows(cover, [row("X", "A", "ANY", 2)]) == []                      # any UAV can do an ANY task, so an RGB UAV can
    assert uncovered_rows(cover, [row("X", "B", "RGB", 2)]) == ["X"]                   # other place is not


def test_policy_modules_do_not_import_the_truth():
    import ast
    d = Path(__file__).resolve().parent.parent / "shield"
    bad = []
    for name in ("policy.py", "cover.py", "service.py", "candidates.py", "readout.py"):
        src = (d / name).read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(src)):
            ids = []
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                ids = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
            elif isinstance(node, ast.Name):
                ids = [node.id]
            elif isinstance(node, ast.Attribute):
                ids = [node.attr]
            for i in ids:
                if any(w in i for w in ("HiddenTruth", "truth_access", "TruthLeak", "ReportEvent", "_gold", "label_norm", "label_key")) or i in ("gold", "truth", "_sim"):
                    bad.append((name, getattr(node, "lineno", 0), i))
    assert not bad, bad


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
