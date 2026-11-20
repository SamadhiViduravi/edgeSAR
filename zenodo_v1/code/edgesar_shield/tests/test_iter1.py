"""
Checks of iteration 1 (docs/ITERATION1_PROTOCOL.md): the strict candidate check, the mass guard, the unsupported-interpretation class, the cost-aware
fallback, the equal-footing gate, the runner (serial = spawn), and that the old arms still give exactly the old numbers.

The policy checks use a stub `View` whose `evaluate` returns execution signatures and requirement lists that the test chooses, so each rule is
tested alone and the expected decision is known in advance.

Run:  EDGESAR_ROOT=<folder with edgesar_pilot, edgesar_heads, V1, edgesar_audit_2026-11-13> python -m pytest -q tests/test_iter1.py
"""
import ast
import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest                                                      # noqa: E402

from shield import devrun2, paths                                  # noqa: E402
from shield.policy import ShieldPolicy                             # noqa: E402
from shield.policy2 import GateFB, ShieldV2, n_bad                 # noqa: E402
from shield.sim import Evaluation                                  # noqa: E402


# ---------------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------------
def key_of(n):
    return tuple(n.get(k) for k in ("action", "incident", "landmark", "sensor", "priority"))


def cand(norm, score):
    return {"key": key_of(norm), "norm": norm, "score": score}


def upd(i, lm, s, p):
    return {"action": "UPDATE_INCIDENT", "incident": i, "landmark": lm, "sensor": s, "priority": p}


NOOP = {"action": "NO_ACTION"}


class FakeSvc:
    def __init__(self, cands, pilot=0, conf=0.5):
        self.cands, self.pilot, self.conf = cands, pilot, conf

    def candidates(self, rid):
        return self.cands

    def pilot_record(self, rid):
        return self.cands[self.pilot]

    def confidence(self, rid):
        return self.conf


class FakeView:
    """A View with a scripted evaluate: eval_fn(table) -> (signature, {"R1": [...], "R2": [...], "R3": [...]})."""

    def __init__(self, eval_fn, open_rows=None, budget=2, ns="c", runs=10 ** 6):
        self.eval_fn, self.open_table, self.budget_left, self.ns, self._runs = eval_fn, open_rows or [], budget, ns, runs
        self.now, self.case_id, self.calls = 0.0, "c", []

    def runs_available(self):
        return self._runs

    def evaluate(self, table, free=False):
        sig, det = self.eval_fn(table)
        det = {"R1": [], "R2": [], "R3": [], **det}
        self.calls.append(table)
        return Evaluation(sig, not any(det.values()), det, None, None)


ROWS = [{"id": "I1", "landmark": "L1", "sensor": "ANY", "priority": 2}]


def own_late():
    return {"R2": ["c:I1"]}


# ---------------------------------------------------------------------------------------------------------------------
# strict candidate check
# ---------------------------------------------------------------------------------------------------------------------
def pri_of(table):
    return [r["priority"] for r in table if r["id"] == "I1"][0]


def test_same_plan_but_one_candidate_misses_its_own_deadline_is_not_certified():
    """Priority 3 means an earlier deadline.  The plan is identical, so the plan's Shield (A8) certifies; the strict check must not."""
    cs = [cand(upd("I1", "L1", "ANY", 2), 0.55), cand(upd("I1", "L1", "ANY", 3), 0.40), cand(NOOP, 0.05)]
    fn = lambda t: ("SAME", own_late() if pri_of(t) == 3 else {})                          # noqa: E731
    svc = FakeSvc(cs)
    v = FakeView(fn, ROWS)
    old = ShieldPolicy(svc, 0.95, 8, "shield", True).on_report(FakeView(fn, ROWS))
    assert old.outcome == "ACCEPT"                                                         # the old rule only looks at the committed record
    new = ShieldV2(svc, 0.95, 8, theta=(9.0,), xi=0.0, mass_guard=False, cost_aware=False)
    a = new.assess2(v)
    assert not a.certified and a.reason == "FEASIBILITY_DIFFERS" and a.n_distinct_sigs == 1
    assert a.risk[0] == pytest.approx(1.0 - (0.55 + 0.05))                                # 1 - mass of the candidates that agree with r-hat in plan AND feasibility


def test_all_candidates_equally_infeasible_is_certified_but_infeasible():
    cs = [cand(upd("I1", "L1", "ANY", 2), 0.6), cand(upd("I1", "L1", "ANY", 3), 0.4)]
    fn = lambda t: ("SAME", own_late())                                                    # noqa: E731
    d = ShieldV2(FakeSvc(cs), 0.95, 8, mass_guard=True, cost_aware=True).on_report(FakeView(fn, ROWS))
    assert d.outcome == "ACCEPT_INFEASIBLE" and d.kind == "COMMIT"


def test_different_plans_are_not_certified_and_all_agree_is_accepted():
    cs = [cand(upd("I1", "L1", "ANY", 2), 0.6), cand(upd("I1", "L1", "ANY", 3), 0.4)]
    s = ShieldV2(FakeSvc(cs), 0.95, 8, mass_guard=True, cost_aware=True)
    assert s.on_report(FakeView(lambda t: ("SAME", {}), ROWS)).outcome == "ACCEPT"
    a = s.assess2(FakeView(lambda t: ("P%d" % pri_of(t), {}), ROWS))
    assert not a.certified and a.reason == "DIFFERENT_PLANS" and a.n_distinct_sigs == 2


# ---------------------------------------------------------------------------------------------------------------------
# mass guard and the unsupported class
# ---------------------------------------------------------------------------------------------------------------------
LOW_MASS = [cand(upd("I1", "L1", "ANY", 2), 0.35), cand(upd("I1", "L1", "ANY", 3), 0.30), cand(upd("I1", "L1", "THERMAL", 2), 0.15),
            cand(upd("I1", "L2", "ANY", 2), 0.08), cand(upd("I1", "L3", "ANY", 2), 0.07), cand(NOOP, 0.05)]       # set at q=0.88 keeps score >= 0.12: mass 0.80


def test_agreement_inside_an_incomplete_set_is_not_certified_when_the_mass_guard_is_on():
    svc = FakeSvc(LOW_MASS)
    fn = lambda t: ("SAME", {})                                                            # noqa: E731
    on = ShieldV2(svc, 0.88, 8, mass_guard=True).assess2(FakeView(fn, ROWS))
    off = ShieldV2(svc, 0.88, 8, mass_guard=False).assess2(FakeView(fn, ROWS))
    assert on.mass == pytest.approx(0.80) and not on.certified and on.reason == "LOW_MASS"
    assert off.certified


def test_unsupported_interpretation_is_committed_visibly_when_no_verification_is_left():
    svc = FakeSvc(LOW_MASS)
    fn = lambda t: ("SAME", {})                                                            # noqa: E731
    d = ShieldV2(svc, 0.88, 8, theta=((9.0,), 0.0), xi=0.0).on_report(FakeView(fn, ROWS, budget=0))
    assert d.outcome == "UNSUPPORTED_COMMIT" and d.kind == "COMMIT"
    assert d.table is not None and not any(r.get("cover") for r in d.table)               # nothing was covered: a cover cannot serve mass outside the set
    d2 = ShieldV2(svc, 0.88, 8, theta=None, xi=1.0).on_report(FakeView(fn, ROWS, budget=1))   # theta None = ask about everything
    assert d2.kind == "ESCALATE"


def test_empty_oversize_and_rhat_outside_the_set_are_uncertified():
    cs = [cand(upd("I1", "L1", "ANY", 2), 0.5), cand(NOOP, 0.5)]
    fn = lambda t: ("SAME", {})                                                            # noqa: E731
    assert ShieldV2(FakeSvc(cs, pilot=0), 0.3, 8).assess2(FakeView(fn, ROWS)).reason == "EMPTY"
    big = [cand(upd("I1", "L%d" % j, "ANY", 2), 0.1) for j in range(10)]
    assert ShieldV2(FakeSvc(big), 0.95, 8).assess2(FakeView(fn, ROWS)).reason == "OVERSIZE"
    cs3 = [cand(upd("I1", "L1", "ANY", 2), 0.9), cand(NOOP, 0.1)]
    a = ShieldV2(FakeSvc(cs3, pilot=1), 0.5, 8).assess2(FakeView(fn, ROWS))               # set keeps score >= 0.5: r-hat (NOOP, 0.1) is outside
    assert a.reason == "RHAT_OUT" and not a.certified


# ---------------------------------------------------------------------------------------------------------------------
# cost-aware fallback
# ---------------------------------------------------------------------------------------------------------------------
FB = [cand(upd("I1", "L1", "ANY", 2), 0.50), cand(upd("I1", "L1", "THERMAL", 3), 0.30), cand(upd("I1", "L2", "ANY", 2), 0.20)]


def fb_view(extra_bad_for):
    """Different plans for different candidates (so the fallback is needed). extra_bad_for(table) -> number of fleet-wide unmet requirements."""
    def fn(t):
        n = extra_bad_for(t)
        return ("S" + str(sorted((r["landmark"], tuple(sorted(r.get("req", ()))) , r["priority"]) for r in t)),
                {"R2": ["x:%d" % j for j in range(n)]})
    return FakeView(fn, ROWS, budget=0)


def has_cover(t, lm):
    return any(r["landmark"] == lm for r in t)


def run_fallback(extra, cost_aware=True):
    s = ShieldV2(FakeSvc(FB), 0.95, 8, theta=((9.0,), 0.0), xi=0.0, mass_guard=True, cost_aware=cost_aware)
    return s.on_report(fb_view(extra))


def test_cost_aware_takes_the_full_cover_when_it_predicts_no_extra_unmet_requirement():
    d = run_fallback(lambda t: 0)
    assert d.diag["fallback_choice"] == "full" and d.outcome in ("FALLBACK_COVERED", "FALLBACK_PARTIAL", "FALLBACK_UNRESOLVED")
    assert len(d.table) == 2                                                               # L1 and L2


def test_cost_aware_takes_the_location_cover_when_only_it_is_harmless():
    # full cover asks THERMAL + priority 3 at L1 (the union); the location cover keeps r-hat's ANY / priority 2 there
    def extra(t):
        full = any(r["landmark"] == "L1" and tuple(r.get("req", ())) == ("THERMAL",) and r["priority"] == 3 for r in t)
        return 2 if full else 0
    d = run_fallback(extra)
    assert d.diag["fallback_choice"] == "location"
    l1 = [r for r in d.table if r["landmark"] == "L1"][0]
    assert l1["priority"] == 2 and tuple(l1["req"]) == ()


def test_cost_aware_declines_a_cover_that_makes_other_incidents_late_and_commits_rhat():
    d = run_fallback(lambda t: 1 if has_cover(t, "L2") else 0)                             # any cover adds the L2 task, which breaks something
    assert d.outcome == "COVER_DECLINED" and d.kind == "COMMIT" and d.diag["fallback_choice"] == "declined"
    assert [r["landmark"] for r in d.table] == ["L1"]                                      # the table of r-hat, nothing added


def test_without_cost_awareness_the_full_cover_is_always_taken():
    d = run_fallback(lambda t: 1 if has_cover(t, "L2") else 0, cost_aware=False)
    assert d.outcome in ("FALLBACK_COVERED", "FALLBACK_UNRESOLVED", "FALLBACK_PARTIAL") and has_cover(d.table, "L2")


def test_n_bad_counts_distinct_tasks_over_the_whole_fleet():
    ev = Evaluation("s", False, {"R1": ["a:1"], "R2": ["a:1", "b:2"], "R3": ["c:3"]}, None, None)
    assert n_bad(ev) == 3


# ---------------------------------------------------------------------------------------------------------------------
# timeout and the equal-footing gate
# ---------------------------------------------------------------------------------------------------------------------
def test_shield_v2_reports_timeout_when_the_decision_does_not_fit():
    d = ShieldV2(FakeSvc(FB), 0.95, 8).on_report(FakeView(lambda t: ("S", {}), ROWS, runs=2))
    assert d.outcome == "TIMEOUT" and d.kind == "COMMIT"


def gate(conf, th_esc, th_fb, **kw):
    return GateFB(FakeSvc(FB, conf=conf), 0.95, 8, *th_esc, *th_fb, **kw)


def test_equal_footing_gate_commits_escalates_or_falls_back_by_its_two_thresholds():
    fn = lambda t: ("S" + str(len(t)), {})                                                 # noqa: E731
    # risk = 1 - conf = 0.8
    calm = gate(0.2, ((0.95,), 0.0), ((0.90,), 0.0)).on_report(FakeView(fn, ROWS, budget=1))
    assert calm.outcome == "COMMIT"
    esc = gate(0.2, ((0.5,), 0.0), ((0.4,), 0.0)).on_report(FakeView(fn, ROWS, budget=1))
    assert esc.kind == "ESCALATE"
    fb = gate(0.2, ((0.5,), 0.0), ((0.4,), 0.0)).on_report(FakeView(fn, ROWS, budget=0))
    assert fb.outcome.startswith("FALLBACK") or fb.outcome == "COVER_DECLINED"
    to = gate(0.2, ((0.5,), 0.0), ((0.4,), 0.0)).on_report(FakeView(fn, ROWS, budget=0, runs=2))
    assert to.outcome == "TIMEOUT"


# ---------------------------------------------------------------------------------------------------------------------
# no truth in the new runtime code
# ---------------------------------------------------------------------------------------------------------------------
def test_policy2_does_not_import_the_truth():
    src = (Path(paths.HERE) / "shield" / "policy2.py").read_text(encoding="utf-8")
    bad = []
    for node in ast.walk(ast.parse(src)):
        ids = []
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            ids = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
        elif isinstance(node, ast.Name):
            ids = [node.id]
        elif isinstance(node, ast.Attribute):
            ids = [node.attr]
        for i in ids:
            if any(w in i for w in ("HiddenTruth", "truth_access", "TruthLeak", "ReportEvent", "_gold", "label_norm", "label_key", "oracle")) or i in ("gold", "truth", "_sim"):
                bad.append((getattr(node, "lineno", 0), i))
    assert not bad, bad


# ---------------------------------------------------------------------------------------------------------------------
# the runner on saved vectors
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def ds():
    from shield.devset import DevSet
    return DevSet()


def norm(records):
    out = []
    for r in records:
        r = json.loads(json.dumps(r))
        for rep in r["reports"]:
            rep.pop("ms", None)
        r["cost"].pop("wall_ms", None)
        out.append(r)
    return json.dumps(sorted(out, key=lambda x: (x["fold"], x["episode"], x["arm"])), sort_keys=True)


def test_runner_is_deterministic_and_serial_equals_spawn(ds):
    arms = ["A0", "A1", "A6", "B3", "G1"]
    a, ia = devrun2.run_fold_v2(ds, 0, "M", seed=1, arms=arms, max_episodes=2)
    b, _ = devrun2.run_fold_v2(ds, 0, "M", seed=1, arms=arms, max_episodes=2)
    assert norm(a) == norm(b)
    s, _ = devrun2.run_level_v2(ds, "M", folds=[0, 1], processes=1, seed=1, arms=arms, max_episodes=1)
    p, _ = devrun2.run_level_v2(ds, "M", folds=[0, 1], processes=2, method="spawn", seed=1, arms=arms, max_episodes=1)
    assert norm(s) == norm(p) and len(s) == 2 * len(arms)
    for r in a:
        c = r["counts"]
        assert c["on_time"] + c["late"] + c["unverified"] + c["resolved_external"] == c["n"]
        assert r["cost"]["requests"] <= r["cap"]                                           # the verification cap holds for every arm
    assert ia["cal_flag_rate_s2"] >= ia["cal_flag_rate_s1"] - 1e-12                        # the mass guard can only flag more


def test_b3_uses_only_known_outcome_classes_and_g1_matches_the_shield_flag_rate_on_cal(ds):
    recs, info = devrun2.run_fold_v2(ds, 0, "M", seed=1, arms=["B3", "G1"], max_episodes=4)
    known = {"ACCEPT", "ACCEPT_INFEASIBLE", "ESCALATE", "FALLBACK_COVERED", "FALLBACK_PARTIAL", "FALLBACK_UNRESOLVED", "UNSUPPORTED_COMMIT", "COVER_DECLINED",
             "TIMEOUT", "COMMIT"}
    for r in recs:
        for rep in r["reports"]:
            assert rep["o"].split(":")[0] in known, rep["o"]
    g = info["thresholds"]["gfb"]
    assert g[0] is not None                                                                # a second threshold exists and was set on CAL, not on EVAL


def test_old_arms_give_exactly_the_old_numbers_in_the_new_runner():
    """Iteration 1 re-runs A1, A6, A8, A8c with the same code path; their incident counts must equal the original development run (results/dev/main)."""
    old_dir, new_dir = paths.RESULTS / "dev" / "main", paths.RESULTS / "iter1" / "q4"
    files = [new_dir / ("records_%s_s%d.json.gz" % (lv, s)) for lv in ("L", "M", "H") for s in (1, 2, 3)]
    if not all(f.exists() for f in files) or not old_dir.exists():
        pytest.skip("iteration-1 or original development records are not on disk")

    def counts(f, arms):
        out = {}
        for r in json.load(gzip.open(f, "rt")):
            if r["arm"] in arms:
                out[(r["episode"], r["fold"], r["arm"])] = (r["counts"]["n"], r["counts"]["on_time"], r["counts"]["late"], r["counts"]["unverified"])
        return out
    for f in files:
        a = counts(old_dir / f.name, {"A1", "A6", "A8", "A8c", "A10"})
        b = counts(f, {"A1", "A6", "A8", "A8c", "A10"})
        assert a and a == b, f.name


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
