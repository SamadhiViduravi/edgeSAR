"""
Checks of the FRESH path WITHOUT any fresh outcome: the freeze guard, the fixed-membership episodes, the fresh set (built from a development fold it must
reproduce the cached development probabilities exactly), sharding, and a tiny end-to-end plumbing run on random fake vectors (the numbers mean nothing;
only the plumbing is checked).

Run:  EDGESAR_ROOT=<folder with edgesar_pilot, edgesar_heads, V1, edgesar_audit_2026-11-13> python -m pytest -q tests/test_fresh.py
"""
import copy
import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import numpy as np                                                # noqa: E402
import pytest                                                     # noqa: E402

import gen_episodes_fresh as gen                                  # noqa: E402
import run_fresh                                                  # noqa: E402
from shield import devrun, frozen, paths                          # noqa: E402
from shield.data import DevData                                   # noqa: E402
from shield.devset import DevSet                                  # noqa: E402
from shield.freshset import FreshSet                              # noqa: E402

ARMS = ["A0", "A1", "A6", "A8", "A8c", "A12", "OBS"]


# ---------------------------------------------------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def dev():
    return DevSet()


@pytest.fixture(scope="module")
def dressed(dev):
    """Development fold 0 dressed as a fresh set (same FIT, CAL, EVAL as the cached development run of fold 0)."""
    return FreshSet.from_dev_fold(dev.D, 0)


def norm(records):
    """records without wall-clock fields"""
    out = []
    for r in records:
        r = json.loads(json.dumps(r))
        for rep in r["reports"]:
            rep.pop("ms", None)
        r["cost"].pop("wall_ms", None)
        out.append(r)
    return json.dumps(out, sort_keys=True)


PLAN_TEXT = """# plan
STATUS: %s
<!-- PARAMS-BEGIN -->
%s
<!-- PARAMS-END -->
"""


def good_params(**kw):
    p = {"fresh_seed": 7, "cal_episodes": 2, "eval_episodes": 3, "R": 5, "alpha": 0.10, "K": 8, "b": 0.10, "d_v": 60.0, "alloc_cost_s": 0.02,
         "decision_timeout_s": 5.0, "level_gap_s": {"L": 60.0, "M": 30.0, "H": 8.0}, "deadlines_s": {"1": 480, "2": 360, "3": 240},
         "allocator_default": "cbba_bounded", "primary": {"x": "A8", "y": "A6", "level": "M"},
         "runs": {"t": {"readout": "q4", "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
                  "sb": {"eval_set": "style_b", "readout": "q4", "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]}}}
    p.update(kw)
    return p


def write_plan(path, status="FROZEN-READY", params=None):
    Path(path).write_text(PLAN_TEXT % (status, json.dumps(params or good_params(), indent=1)), encoding="utf-8")


# ---------------------------------------------------------------------------------------------------------------------
# the freeze guard
# ---------------------------------------------------------------------------------------------------------------------
def test_a_draft_plan_cannot_be_frozen(tmp_path):
    p = tmp_path / "plan.md"
    write_plan(p, status="DRAFT")
    with pytest.raises(SystemExit) as e:
        frozen.make_freeze(plan_path=p)
    assert "DRAFT" in str(e.value)


def test_parameter_block_is_validated(tmp_path):
    p = tmp_path / "plan.md"
    prm = good_params()
    del prm["alpha"]
    write_plan(p, params=prm)
    with pytest.raises(SystemExit) as e:
        frozen.plan_params(frozen.plan_text(p))
    assert "alpha" in str(e.value)
    p.write_text("STATUS: FROZEN-READY\nno block here\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        frozen.plan_params(frozen.plan_text(p))


def test_no_run_without_a_freeze_file(tmp_path):
    with pytest.raises(SystemExit) as e:
        frozen.require_freeze(freeze_path=tmp_path / "missing.sha256")
    assert "not frozen" in str(e.value)


def test_freeze_is_intact_then_detects_a_changed_plan_and_changed_code(tmp_path):
    plan = tmp_path / "plan.md"
    write_plan(plan)
    root = tmp_path / "repo"
    (root / "shield").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "shield" / "a.py").write_text("X = 1\n")
    for t in frozen.TOOLS:
        (root / "tools" / t).write_text("# tool\n")
    fz = frozen.make_freeze(plan_path=plan, root=root)
    fz_path = tmp_path / "f.sha256"
    fz_path.write_text(json.dumps(fz))
    probs, _ = frozen.check_freeze(fz_path, plan, root)
    assert probs == []
    # the plan changes by one character
    plan.write_text(plan.read_text() + " ")
    probs, _ = frozen.check_freeze(fz_path, plan, root)
    assert any("EVAL_PLAN_FRESH.md changed" in x for x in probs)
    write_plan(plan)                                                 # restore exactly
    assert frozen.check_freeze(fz_path, plan, root)[0] == []
    # code changes
    (root / "shield" / "a.py").write_text("X = 2\n")
    probs, _ = frozen.check_freeze(fz_path, plan, root)
    assert any("code changed" in x for x in probs)
    (root / "shield" / "a.py").write_text("X = 1\n")
    (root / "tools" / "analyze_dev.py").write_text("# analysis changed\n")
    probs, _ = frozen.check_freeze(fz_path, plan, root)
    assert any("analyze_dev.py" in x for x in probs)


def test_the_real_repository_is_not_frozen_yet():
    """The plan in docs/ is a draft until the main chat approves it: no freeze file may exist in this delivery."""
    assert not frozen.FREEZE.exists()


# ---------------------------------------------------------------------------------------------------------------------
# cases and vectors are verified against the plan and the extraction manifest
# ---------------------------------------------------------------------------------------------------------------------
def make_cases_file(path, P):
    pilot_cases = [json.loads(l) for l in open(paths.PILOT / "data" / "cases.jsonl", encoding="utf-8") if l.strip()]
    cases, _ = gen.generate(P["fresh_seed"], P["cal_episodes"], P["eval_episodes"], P["R"], pilot_cases)
    with open(path, "w", encoding="utf-8") as fh:
        for c in cases:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    return cases


def test_cases_file_must_equal_the_frozen_generator_output(tmp_path):
    P = good_params()
    f = tmp_path / "cases.jsonl"
    cases = make_cases_file(f, P)
    assert run_fresh.verify_cases(f, P) == []
    # one report edited
    bad = copy.deepcopy(cases)
    bad[3]["text"] = bad[3]["text"] + " (edited)"
    with open(f, "w", encoding="utf-8") as fh:
        for c in bad:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    assert run_fresh.verify_cases(f, P)
    # one report dropped
    with open(f, "w", encoding="utf-8") as fh:
        for c in cases[:-1]:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    assert run_fresh.verify_cases(f, P)
    # another seed
    make_cases_file(f, good_params(fresh_seed=8))
    assert run_fresh.verify_cases(f, P)


def fake_vectors(vdir, cases_file, n, dim=2048, result="OK", tamper=None):
    vdir.mkdir(parents=True, exist_ok=True)
    ids = [json.loads(l)["id"] for l in open(cases_file, encoding="utf-8") if l.strip()]
    rng = np.random.RandomState(5)
    models = {}
    for mk in run_fresh.MODELS:
        X = rng.randn(n, dim).astype(np.float32)
        np.save(vdir / ("%s_end.npy" % mk), X)
        models[mk] = {"n": n, "vectors_sha256": paths.sha256_file(vdir / ("%s_end.npy" % mk))}
    (vdir / "case_ids.json").write_text(json.dumps(ids))
    man = {"result": result, "cases_sha256": paths.sha256_file(cases_file), "report_ids_sha256": frozen.sha256_text(",".join(ids)), "models": models, "checks": []}
    if tamper:
        tamper(man)
    (vdir / "extraction_manifest.json").write_text(json.dumps(man))


def test_extraction_manifest_is_checked(tmp_path):
    P = good_params()
    f = tmp_path / "cases.jsonl"
    make_cases_file(f, P)
    n = (P["cal_episodes"] + P["eval_episodes"]) * P["R"]
    v = tmp_path / "v"
    fake_vectors(v, f, n, dim=16)
    assert run_fresh.verify_vectors(f, v) == []
    # FAIL result
    fake_vectors(v, f, n, dim=16, result="FAIL")
    assert any("result" in x for x in run_fresh.verify_vectors(f, v))
    # failed check recorded
    fake_vectors(v, f, n, dim=16, tamper=lambda m: m["checks"].append({"model": "f16", "status": "FAIL", "text": "log order"}))
    assert any("FAILED checks" in x for x in run_fresh.verify_vectors(f, v))
    # vectors changed after the manifest was written
    fake_vectors(v, f, n, dim=16)
    X = np.load(v / "Q4_K_M_end.npy")
    X[0, 0] += 1.0
    np.save(v / "Q4_K_M_end.npy", X)
    assert any("Q4_K_M_end.npy differs" in x for x in run_fresh.verify_vectors(f, v))
    # another cases file
    fake_vectors(v, f, n, dim=16)
    f2 = tmp_path / "cases2.jsonl"
    make_cases_file(f2, good_params(fresh_seed=9))
    assert any("another cases file" in x for x in run_fresh.verify_vectors(f2, v))


# ---------------------------------------------------------------------------------------------------------------------
# episodes with fixed membership
# ---------------------------------------------------------------------------------------------------------------------
def test_fixed_episodes_keep_members_order_and_have_independent_gaps(dressed):
    ev = dressed.folds[0]["eval"]
    eps = dressed.make_episodes(ev, "M", 1)
    assert len(eps) == 10 and all(len(e.events) == 20 for e in eps)
    for e in eps:
        ids = [x.case_id for x in e.events]
        cases = sorted((dressed.cases[i] for i in ev if dressed.cases[i]["episode"] == e.id.split("-", 2)[2]), key=lambda c: c["pos"])
        assert ids == [c["id"] for c in cases]
        ts = [x.t for x in e.events]
        assert ts == sorted(ts) and ts[0] == 0.0
    # an episode's arrival times do not depend on which other episodes are present
    only = dressed.make_episodes([i for i in ev if dressed.cases[i]["episode"] == "X012"], "M", 1)
    full = [e for e in eps if e.id.endswith("X012")][0]
    assert [x.t for x in only[0].events] == [x.t for x in full.events]
    # a different seed gives different gaps, a different level gives different scale
    other = dressed.make_episodes(ev, "M", 2)
    assert [x.t for x in other[0].events] != [x.t for x in eps[0].events]


# ---------------------------------------------------------------------------------------------------------------------
# the fresh set
# ---------------------------------------------------------------------------------------------------------------------
def cache_environment_matches():
    """True when this machine is the one that built results/cache (same Python, numpy, scikit-learn, Linux).  Only then can the cached probabilities
    be compared bit for bit: the heads are fitted by lbfgs with tol 1e-6, and another BLAS or Python build stops at a slightly different point
    (observed on Windows, Python 3.12.6: up to 0.0094 in a probability, no decision changed - results/repro_diagnostic_*/diagnosis.json)."""
    import platform
    import sklearn
    info = json.loads((paths.RESULTS / "cache" / "readout_probs.info.json").read_text(encoding="utf-8"))
    return (info["python"] == platform.python_version() and info["numpy"] == np.__version__ and info["sklearn"] == sklearn.__version__
            and sys.platform.startswith("linux"))


@pytest.fixture(scope="module")
def dev_refit(dev):
    """The development path refitted NOW, in this environment (what readout.cross_fit does for fold 0)."""
    from shield.readout import Heads
    D = dev.D
    fit, cal, ev = D.split(0)
    rows = np.concatenate([cal, ev])
    heads = {m: Heads(D.cases, D.X[m], fit, D.group) for m in ("f16", "Q8_0", "Q4_K_M")}
    delta = (D.X["Q4_K_M"][fit] - D.X["f16"][fit]).mean(axis=0)
    return {"q4": heads["Q4_K_M"].proba(D.X["Q4_K_M"][rows]), "f16": heads["f16"].proba(D.X["f16"][rows]), "q8": heads["Q8_0"].proba(D.X["Q8_0"][rows]),
            "rec": heads["f16"].proba(D.X["Q4_K_M"][rows] - delta), "raw": heads["f16"].proba(D.X["Q4_K_M"][rows]), "delta_norm": float(np.linalg.norm(delta))}


def test_fresh_path_equals_an_independent_refit_of_the_development_path_in_this_environment(dev, dressed, dev_refit):
    """The point of the self-test: the fresh set must run the SAME fitting code as the development path.  Both are fitted now, on this machine."""
    b = dressed.folds[0]
    for arm in ("q4", "f16", "q8", "rec", "raw"):
        for h in ("action", "sensor", "prio"):
            assert dev_refit[arm][h].shape == b["P"][arm][h].shape
            assert np.abs(dev_refit[arm][h] - b["P"][arm][h]).max() < 1e-12, (arm, h)
    assert abs(dev_refit["delta_norm"] - b["delta_norm"]) < 1e-12
    assert dressed.n_fit == len(dev.folds[0]["fit"])


def test_fresh_set_agrees_with_the_cached_development_probabilities_at_decision_level(dev, dressed):
    """Cached (built elsewhere) against refitted here: probabilities may differ in the 3rd decimal (see above); the decisions must not.
    Compared: tolerance on every probability, the pilot-style record, the best candidate, the conformal set and the conformal threshold of every
    CAL and EVAL report (the episodes differ between the two sets by design, so outcome counts are compared in results/repro_diagnostic_*).  The mismatched raw head is a diagnostic arm whose scores sit at the edge of its (very wide)
    set, so one changed set is allowed there and reported."""
    a, b = dev.folds[0], dressed.folds[0]
    for arm in ("q4", "f16", "q8", "rec", "raw"):
        for h in ("action", "sensor", "prio"):
            assert a["P"][arm][h].shape == b["P"][arm][h].shape
            assert np.abs(a["P"][arm][h] - b["P"][arm][h]).max() < 2e-2, (arm, h)
    assert abs(a["delta_norm"] - b["delta_norm"]) < 1e-6
    rows = list(dev.folds[0]["cal"]) + list(dev.folds[0]["eval"])
    for arm in ("q4", "f16", "q8", "rec", "raw"):
        qa, qb = dev.q_hat(0, arm, 0.10), dressed.q_hat(0, arm, 0.10)
        assert abs(qa - qb) < 1e-4, arm
        changed = 0
        for j, i in enumerate(rows):                       # the dressed set numbers its reports 0.. in CAL, EVAL order
            ca, cb = dev.cands(0, arm, i), dressed.cands(0, arm, j)
            assert dev.hier(0, arm, i) == dressed.hier(0, arm, j), (arm, i)
            assert ca[0]["key"] == cb[0]["key"], (arm, i)
            changed += [c["key"] for c in dev.conformal(0, arm, i, qa)] != [c["key"] for c in dressed.conformal(0, arm, j, qb)]
        assert changed <= (1 if arm == "raw" else 0), (arm, changed)


@pytest.mark.skipif(not cache_environment_matches(), reason="bit-for-bit comparison needs the environment that built results/cache (Linux, same Python/numpy/scikit-learn)")
def test_fresh_set_reproduces_the_cached_development_probabilities_bit_for_bit(dev, dressed):
    a, b = dev.folds[0], dressed.folds[0]
    for arm in ("q4", "f16", "q8", "rec", "raw"):
        for h in ("action", "sensor", "prio"):
            assert np.abs(a["P"][arm][h] - b["P"][arm][h]).max() < 1e-12, (arm, h)
    assert abs(a["delta_norm"] - b["delta_norm"]) < 1e-12
    assert dev.q_hat(0, "q4", 0.10) == dressed.q_hat(0, "q4", 0.10)


def test_fresh_set_fits_only_on_the_fit_reports_and_calibrates_only_on_cal(dev, dressed):
    """The heads of the dressed set are fitted on the 523 FIT reports of fold 0 and nothing else; CAL and EVAL are disjoint from each other."""
    ev_ids = {dressed.cases[i]["id"] for i in dressed.folds[0]["eval"]}
    cal_ids = {dressed.cases[i]["id"] for i in dressed.folds[0]["cal"]}
    fit_ids = {dev.cases[int(i)]["id"] for i in dev.folds[0]["fit"]}
    assert not (ev_ids & cal_ids) and not (fit_ids & (ev_ids | cal_ids))
    assert dressed.n_fit == len(fit_ids) == 523
    assert len(cal_ids) == 200 and len(ev_ids) == 200


def test_run_fold_on_the_fresh_set_is_deterministic_and_shards_do_not_change_records(dressed):
    a, ia = devrun.run_fold(dressed, 0, "M", seed=1, arms=ARMS, max_episodes=3)
    b, _ = devrun.run_fold(dressed, 0, "M", seed=1, arms=ARMS, max_episodes=3)
    assert norm(a) == norm(b)
    assert ia["eval_set"]["reports"] == 200 and ia["eval_set"]["gold_missing"] == 0 and ia["n_fit"] == 523
    r2, i2 = devrun.run_level(dressed, "M", folds=[0], processes=2, shards=2, seed=1, arms=["A0", "A1", "A6", "A8"])
    r1, i1 = devrun.run_level(dressed, "M", folds=[0], processes=1, shards=1, seed=1, arms=["A0", "A1", "A6", "A8"])
    order = {x: i for i, x in enumerate(devrun.ARM_ORDER + ["OBS"])}
    r1 = sorted(r1, key=lambda r: (r["episode"], order.get(r["arm"], 99)))
    assert norm(r1) == norm(r2) and len(i2) == 1 and i2[0]["shards"] == 2
    # counts add up in every episode and every arm: on time + late + unverified + resolved externally = incidents
    for r in r2:
        c = r["counts"]
        assert c["on_time"] + c["late"] + c["unverified"] + c["resolved_external"] == c["n"]


def test_the_fresh_run_reads_the_same_runtime_objects_as_the_development_run(dev, dressed):
    """Same policies, same service: the fresh set changes only where probabilities and reports come from."""
    a = devrun.build_service(dev, 0, "q4")
    b = devrun.build_service(dressed, 0, "q4")
    rid = dev.cases[int(dev.folds[0]["eval"][0])]["id"]
    # the dressed set has the same report ids (they are the development ids); compare the candidate lists
    assert [c["key"] for c in a.candidates(rid)] == [c["key"] for c in b.candidates(rid)]
    tol = 1e-12 if cache_environment_matches() else 1e-2          # cached vs refitted: see cache_environment_matches()
    assert [c["score"] for c in a.candidates(rid)] == pytest.approx([c["score"] for c in b.candidates(rid)], abs=tol)


# ---------------------------------------------------------------------------------------------------------------------
# tiny end-to-end plumbing run (fake random vectors: the numbers mean nothing)
# ---------------------------------------------------------------------------------------------------------------------
def test_end_to_end_plumbing_with_fake_vectors(tmp_path, monkeypatch):
    P = good_params()
    plan = tmp_path / "plan.md"
    write_plan(plan, params=P)
    fz_path = tmp_path / "plan.sha256"
    monkeypatch.setattr(frozen, "PLAN", plan)
    monkeypatch.setattr(frozen, "FREEZE", fz_path)
    monkeypatch.setattr(run_fresh, "FRESH", tmp_path / "fresh")
    cases_f = tmp_path / "cases_fresh.jsonl"
    make_cases_file(cases_f, P)
    n = (P["cal_episodes"] + P["eval_episodes"]) * P["R"]
    vdir = tmp_path / "vectors"
    fake_vectors(vdir, cases_f, n)
    argv = ["run_fresh.py", "--cases", str(cases_f), "--vectors", str(vdir), "--tag", "t", "--processes", "1"]

    # 1. not frozen -> stop
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as e:
        run_fresh.main()
    assert "not frozen" in str(e.value)
    # 2. freeze, then a changed plan -> stop
    fz_path.write_text(json.dumps(frozen.make_freeze(plan_path=plan)))
    plan.write_text(plan.read_text() + "\n")
    with pytest.raises(SystemExit) as e:
        run_fresh.main()
    assert "changed after the freeze" in str(e.value)
    write_plan(plan, params=P)
    # 3. edited cases file -> stop
    text = cases_f.read_text(encoding="utf-8")
    cases_f.write_text(text.replace('"pos": 0', '"pos": 1', 1), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        run_fresh.main()
    assert "not what the frozen seed" in str(e.value) or "another cases file" in str(e.value)
    cases_f.write_text(text, encoding="utf-8")
    # 4. everything intact -> runs, writes records and the log
    run_fresh.main()
    out = tmp_path / "fresh" / "t"
    man = json.loads((out / "manifest.json").read_text())
    assert man["kind"] == "fresh" and man["plan_sha256"] == frozen.sha256_text(plan.read_text(encoding="utf-8"))
    recs = json.load(gzip.open(out / "records_M_s1.json.gz", "rt"))
    arms = {r["arm"] for r in recs}
    assert arms == {"A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"}
    assert len({r["episode"] for r in recs}) == P["eval_episodes"]
    for r in recs:
        c = r["counts"]
        assert c["on_time"] + c["late"] + c["unverified"] + c["resolved_external"] == c["n"]
    log = json.loads((tmp_path / "fresh" / "RUN_LOG.json").read_text())
    assert len(log) == 1 and log[0]["tag"] == "t" and log[0]["plan_sha256"] == man["plan_sha256"]
    # 4b. the exploratory style-B check: 400 style-B development reports in 20 episodes of 20, calibrated on the (fake) fresh calibration episodes
    monkeypatch.setattr(sys, "argv", ["run_fresh.py", "--cases", str(cases_f), "--vectors", str(vdir), "--tag", "sb", "--processes", "1"])
    run_fresh.main()
    mb = json.loads((tmp_path / "fresh" / "sb" / "manifest.json").read_text())
    assert mb["eval_set"] == "style_b"
    rb = json.load(gzip.open(tmp_path / "fresh" / "sb" / "records_M_s1.json.gz", "rt"))
    assert len({r["episode"] for r in rb}) == 20 and all(r["counts"]["n"] > 0 for r in rb)
    assert all(rep["id"][0] != "f" for r in rb for rep in r["reports"])        # style-B reports are development reports, not fresh ones
    # 5. a repeat needs a reason, and the old results are kept
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as e:
        run_fresh.main()
    assert "done once" in str(e.value)
    monkeypatch.setattr(sys, "argv", argv + ["--rerun-reason", "test"])
    run_fresh.main()
    kept = [p for p in (tmp_path / "fresh").iterdir() if ".superseded-" in p.name]
    assert len(kept) == 1
    log = json.loads((tmp_path / "fresh" / "RUN_LOG.json").read_text())
    assert [x["tag"] for x in log] == ["t", "sb", "t"]                   # the first run, the style-B check, and the repeat
    assert log[0]["rerun_reason"] is None and log[2]["rerun_reason"] == "test"
    # 6. the analysis script reads the fresh folder
    monkeypatch.setattr(paths, "RESULTS", tmp_path)
    import analyze_dev
    monkeypatch.setattr(sys, "argv", ["analyze_dev.py", "--base", "fresh", "--tag", "t"])
    analyze_dev.main()
    monkeypatch.setattr(sys, "argv", ["analyze_dev.py", "--base", "fresh", "--tag", "sb"])
    analyze_dev.main()
    assert "EXPLORATORY style-shift check" in (tmp_path / "fresh" / "sb" / "FRESH_sb.md").read_text(encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["analyze_dev.py", "--base", "fresh", "--tag", "t"])
    md = (tmp_path / "fresh" / "t" / "FRESH_t.md").read_text(encoding="utf-8")
    assert "FRESH (confirmation)" in md and "Outcomes and costs" in md and "PRIMARY" in md
    assert "gold record NOT expressible" in md                       # missing candidates are always printed, also when zero
