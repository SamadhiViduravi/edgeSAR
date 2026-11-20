"""
EdgeSAR harm test (EXPLORATORY): feed every system's saved record into the SAME allocator and count what happens to the
real incidents. Nothing here trains or loads a model. It reads the per-report answers written by 04_controls.py.

The rules are in HARM_TEST_PLAN.md and harm_config.json (frozen with a hash before any real run).
Setting (as in the existing V1 allocation code, used unchanged and pinned by hash):
  * one report at a time ("single-record fork-and-replay"): the open-incident table of the case + the record the system wrote
  * simplified CBBA (one task per UAV at a time, perfect messages), 3 UAVs, straight-line flight, no random parts
  * a real incident is verified when a UAV with the needed camera finishes a 12 s visit; horizon 600 s
  * hidden truth (the gold table) is used ONLY to decide what a UAV finds when it arrives and to score the run;
    the allocator itself never sees it.
"""
import csv
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from types import SimpleNamespace

import numpy as np

import heads_common as hc
from heads_common import HERE, now_text, pc, sha256_file

HARM_CONFIG_PATH = HERE / "harm_config.json"
OUT_DIR_HARM = HERE / "results_harm"

GOLD_NAME = "GOLD-RECORD (reference)"
GROUPS = ("primary", "secondary", "context")

# additive per-report columns (every statistic is a ratio of sums, so a family bootstrap is exact and cheap)
COLS = ["reports", "n_truth", "ref_unver", "test_unver", "v2u", "u2v", "both_unver", "delay_sum", "delay_n",
        "ref_tsum", "test_tsum", "ref_empty", "ref_failed", "test_empty", "test_failed", "ref_dist", "test_dist",
        "l0", "l1", "l2", "l3", "l4", "harmful", "absorbed", "consequential", "ref_late", "test_late"]
CI = {c: i for i, c in enumerate(COLS)}


def load_harm_config(path=None):
    with open(path or HARM_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =================================================================== the existing allocation code (pinned by hash)
def v1_dir(cfg):
    from pathlib import Path
    return Path(os.environ.get("EDGESAR_V1_DIR") or (HERE / cfg["v1_dir"])).resolve()


def check_allocator_frozen(cfg):
    """Return the list of allocator files whose bytes are not the ones named in the plan."""
    base = v1_dir(cfg)
    bad = []
    for rel, want in cfg["allocator_sha256"].items():
        p = base / rel
        if not p.exists():
            bad.append("%s: file not found" % rel)
        elif sha256_file(p) != want:
            bad.append("%s: not the frozen version" % rel)
    return bad


def load_allocator(cfg):
    base = v1_dir(cfg)
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    from packages.allocation import mission, world, funnel, cbba          # noqa: E402
    if abs(mission.HORIZON - cfg["horizon_s"]) > 1e-9 or abs(mission.DWELL - cfg["dwell_s"]) > 1e-9:
        raise SystemExit("mission.py HORIZON/DWELL are not the values in harm_config.json. Stop.")
    if abs(funnel.EPS - cfg["eps_s"]) > 1e-9 or abs(funnel.HARM_SECONDS - cfg["harm_seconds_exploratory"]) > 1e-9:
        raise SystemExit("funnel.py EPS/HARM_SECONDS are not the values in harm_config.json. Stop.")
    return SimpleNamespace(mission=mission, world=world, funnel=funnel, cbba=cbba, UAVS=world.UAVS, LANDMARKS=world.LANDMARKS,
                           H=mission.HORIZON)


def apply_decision(case, norm):
    """Same as V1 packages/allocation/decisions.py (a test compares them): the task table after the record."""
    table = [dict(t) for t in case["open"]]
    action = norm["action"]
    if action == "CLOSE_INCIDENT":
        table = [t for t in table if t["id"] != norm["incident"]]
    elif action == "UPDATE_INCIDENT":
        for t in table:
            if t["id"] == norm["incident"]:
                t["landmark"] = norm["landmark"]
                t["sensor"] = norm["sensor"]
                t["priority"] = norm["priority"]
    elif action == "CREATE_VERIFICATION":
        table.append({"id": "NEW", "landmark": norm["landmark"], "sensor": norm["sensor"], "priority": norm["priority"]})
    return table


# =================================================================== reading the saved answers
def norm_from_row(r):
    a = r["pred_action"]
    n = {"action": a}
    if a in ("UPDATE_INCIDENT", "CLOSE_INCIDENT"):
        n["incident"] = r["pred_link"]
    if a in ("CREATE_VERIFICATION", "UPDATE_INCIDENT"):
        n["landmark"], n["sensor"], n["priority"] = r["pred_location"], r["pred_sensor"], int(r["pred_priority"])
    return n


def _read_rows(path, key_cols):
    with open(path, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            yield tuple(r[k] for k in key_cols), r


def load_predictions(path, cases):
    """{system: {case_id: norm}} from predictions_end.csv. Also checks every row against the gold answer: the rebuilt record must
    equal the gold record exactly when the file says record_ok = 1. Returns (data, number_of_rows, number_of_mismatches)."""
    gold = {c["id"]: pc.gold_norm(c) for c in cases}
    out, n_rows, bad = defaultdict(dict), 0, 0
    for (system,), r in _read_rows(path, ["system"]):
        norm = norm_from_row(r)
        out[system][r["case_id"]] = norm
        n_rows += 1
        if (norm == gold[r["case_id"]]) != bool(int(r["record_ok"])):
            bad += 1
    return dict(out), n_rows, bad


def load_bootstrap(path, cases):
    """{(head_id, vector): {case_id: norm}} and {head_id: seed} from bootstrap_predictions_end.csv."""
    gold = {c["id"]: pc.gold_norm(c) for c in cases}
    out, seeds, n_rows, bad = defaultdict(dict), {}, 0, 0
    for (head, vec), r in _read_rows(path, ["head_id", "vector"]):
        norm = norm_from_row(r)
        out[(head, vec)][r["case_id"]] = norm
        seeds[head] = r["seed"]
        n_rows += 1
        if (norm == gold[r["case_id"]]) != bool(int(r["record_ok"])):
            bad += 1
    return dict(out), seeds, n_rows, bad


# =================================================================== one mission
class Run:
    __slots__ = ("norm", "table", "res", "ms")

    def __init__(self, norm, table, res, ms):
        self.norm, self.table, self.res, self.ms = norm, table, res, ms


def truth_of(case):
    """The real incidents of this case = the gold table: {landmark: camera really needed}."""
    return {t["landmark"]: t["sensor"] for t in apply_decision(case, pc.gold_norm(case))}


def fly(A, case, norm, truth):
    table = apply_decision(case, norm)
    t0 = time.perf_counter()
    res = A.mission.run_mission(A.UAVS, table, truth)
    return Run(norm, table, res, (time.perf_counter() - t0) * 1000.0)


def run_arm(A, cases, truths, norms_by_id):
    return {c["id"]: fly(A, c, norms_by_id[c["id"]], truths[c["id"]]) for c in cases}


def flight_distance(A, res):
    pos = {u.id: u.start for u in A.UAVS}
    d = 0.0
    for v in sorted(res["visits"], key=lambda v: (v["start"], v["uav"])):
        p = A.LANDMARKS[v["landmark"]]
        d += math.dist(pos[v["uav"]], p)
        pos[v["uav"]] = p
    return d


def _verified(res, landmark, H):
    t = res["verify_time"].get(landmark)
    return t is not None and t <= H


def _trips(res):
    c = Counter(v["result"] for v in res["visits"])
    return c.get("empty", 0), c.get("failed", 0)


def pair_vector(A, cfg, ref, test, truth):
    """All additive numbers for ONE report: reference run vs test run. Reference = the gold-record run, or another system."""
    H = A.H
    n = len(truth)
    ru = tu = v2u = u2v = bu = 0
    dsum, dn, rt, tt, rl, tl = 0.0, 0, 0.0, 0.0, 0, 0
    for l in truth:
        rv, tv = _verified(ref.res, l, H), _verified(test.res, l, H)
        ru += not rv
        tu += not tv
        v2u += rv and not tv
        u2v += (not rv) and tv
        bu += (not rv) and (not tv)
        if rv and tv:
            dsum += test.res["verify_time"][l] - ref.res["verify_time"][l]
            dn += 1
        a, b = ref.res["verify_time"].get(l), test.res["verify_time"].get(l)
        rt += H if a is None else a
        tt += H if b is None else b
        rl += a is not None and a > H
        tl += b is not None and b > H
    cmp = A.funnel.compare(ref.table, ref.res, test.table, test.res, truth,
                           harm_seconds=cfg["harm_seconds_exploratory"], eps=cfg["eps_s"])
    l0 = A.funnel.decision_changed(ref.norm, test.norm)
    l1 = cmp["task_changed"]
    l4 = cmp["verification_changed"]
    re_, rf_ = _trips(ref.res)
    te_, tf_ = _trips(test.res)
    vec = {"reports": 1, "n_truth": n, "ref_unver": ru, "test_unver": tu, "v2u": v2u, "u2v": u2v, "both_unver": bu,
           "delay_sum": dsum, "delay_n": dn, "ref_tsum": rt, "test_tsum": tt, "ref_empty": re_, "ref_failed": rf_,
           "test_empty": te_, "test_failed": tf_, "ref_dist": flight_distance(A, ref.res), "test_dist": flight_distance(A, test.res),
           "l0": int(l0), "l1": int(l1), "l2": int(cmp["assignment_changed"]), "l3": int(cmp["route_changed"]), "l4": int(l4),
           "harmful": int(cmp["harmful"]), "absorbed": int(l1 and not l4), "consequential": int(l1 and l4),
           "ref_late": rl, "test_late": tl}
    return [float(vec[c]) for c in COLS], cmp


# =================================================================== family bootstrap (paired: the same families are drawn for both)
def _div(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return np.where(b > 0, a / np.where(b > 0, b, 1.0), np.nan)


STATS = {
    "U_test": lambda S: _div(S[:, CI["test_unver"]], S[:, CI["n_truth"]]),
    "U_ref": lambda S: _div(S[:, CI["ref_unver"]], S[:, CI["n_truth"]]),
    "dU": lambda S: _div(S[:, CI["test_unver"]] - S[:, CI["ref_unver"]], S[:, CI["n_truth"]]),
    "v2u_per100": lambda S: 100.0 * _div(S[:, CI["v2u"]], S[:, CI["reports"]]),
    "u2v_per100": lambda S: 100.0 * _div(S[:, CI["u2v"]], S[:, CI["reports"]]),
    "delay_mean": lambda S: _div(S[:, CI["delay_sum"]], S[:, CI["delay_n"]]),
    "rmivt_test": lambda S: _div(S[:, CI["test_tsum"]], S[:, CI["n_truth"]]),
    "rmivt_ref": lambda S: _div(S[:, CI["ref_tsum"]], S[:, CI["n_truth"]]),
    "trips_test": lambda S: _div(S[:, CI["test_empty"]] + S[:, CI["test_failed"]], S[:, CI["reports"]]),
    "trips_ref": lambda S: _div(S[:, CI["ref_empty"]] + S[:, CI["ref_failed"]], S[:, CI["reports"]]),
    "dist_test": lambda S: _div(S[:, CI["test_dist"]], S[:, CI["reports"]]),
    "dist_ref": lambda S: _div(S[:, CI["ref_dist"]], S[:, CI["reports"]]),
    "absorbed_share": lambda S: _div(S[:, CI["absorbed"]], S[:, CI["l1"]]),
}


def cluster_boot(fams, M, stat_fn, B, seed, level=0.95):
    """Resample whole families with replacement. Returns (point, low, high, number_of_families)."""
    fams = np.asarray(fams)
    uniq, inv = np.unique(fams, return_inverse=True)
    F = len(uniq)
    S = np.zeros((F, M.shape[1]))
    np.add.at(S, inv, M)
    point = float(stat_fn(S.sum(0, keepdims=True))[0])
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(F, np.full(F, 1.0 / F), size=B)
    vals = stat_fn(counts @ S)
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return point, float("nan"), float("nan"), F
    lo, hi = np.percentile(vals, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return point, float(lo), float(hi), F


def summarize(M, fams, cfg, names=None):
    """Point value and 95% family-bootstrap interval for every statistic, plus plain totals."""
    M = np.asarray(M, dtype=float)
    out = {}
    for k in (names or STATS):
        p, lo, hi, F = cluster_boot(fams, M, STATS[k], cfg["bootstrap_resamples"], cfg["bootstrap_seed"], cfg["ci_level"])
        out[k] = {"point": p, "low": lo, "high": hi}
    tot = M.sum(0)
    out["totals"] = {c: float(tot[CI[c]]) for c in COLS}
    out["n_families"] = int(len(np.unique(np.asarray(fams))))
    return out


# =================================================================== run everything for one split
def split_index(cases, split):
    if split == "all":
        return list(range(len(cases)))
    return [i for i, c in enumerate(cases) if c["split"] == split]


def pair_matrix(A, cfg, cases, truths, ref_runs, test_runs, idx):
    rows, cmps = [], []
    for i in idx:
        cid = cases[i]["id"]
        v, cmp = pair_vector(A, cfg, ref_runs[cid], test_runs[cid], truths[cid])
        rows.append(v)
        cmps.append(cmp)
    return np.array(rows, dtype=float).reshape(len(rows), len(COLS)), cmps


def per_report_rows(arm, group, cases, idx, M, cmps, ref_runs, test_runs):
    out = []
    for k, i in enumerate(idx):
        c = cases[i]
        v = dict(zip(COLS, M[k]))
        cls = "table unchanged" if not v["l1"] else ("consequential" if v["l4"] else "absorbed")
        out.append({"arm": arm, "group": group, "case_id": c["id"], "split": c["split"], "family": c["family"],
                    "n_truth": int(v["n_truth"]), "unverified_arm": int(v["test_unver"]), "unverified_reference": int(v["ref_unver"]),
                    "verified_to_unverified": int(v["v2u"]), "unverified_to_verified": int(v["u2v"]),
                    "delay_sum_both_verified_s": round(v["delay_sum"], 3), "delay_n": int(v["delay_n"]),
                    "empty_trips": int(v["test_empty"]), "failed_trips": int(v["test_failed"]),
                    "distance_m": round(v["test_dist"], 1), "compute_ms": round(test_runs[c["id"]].ms, 3),
                    "record_differs_from_reference": int(v["l0"]), "task_table_differs": int(v["l1"]),
                    "assignment_changed": int(v["l2"]), "route_changed": int(v["l3"]), "verification_changed": int(v["l4"]),
                    "class": cls, "harmful_exploratory_30s": int(v["harmful"])})
    return out


def per_incident_rows(arm, cases, idx, truths, ref_runs, test_runs, H):
    out = []
    for i in idx:
        c = cases[i]
        r, t = ref_runs[c["id"]], test_runs[c["id"]]
        for l, need in sorted(truths[c["id"]].items()):
            rv, tv = _verified(r.res, l, H), _verified(t.res, l, H)
            a, b = r.res["verify_time"].get(l), t.res["verify_time"].get(l)
            out.append({"arm": arm, "case_id": c["id"], "split": c["split"], "family": c["family"], "landmark": l,
                        "camera_needed": need, "reference_verified": int(rv), "reference_time_s": "" if a is None else round(a, 2),
                        "arm_verified": int(tv), "arm_time_s": "" if b is None else round(b, 2),
                        "transition": ("V" if rv else "U") + "->" + ("V" if tv else "U"),
                        "delay_diff_s": round(b - a, 2) if (rv and tv) else ""})
    return out


def write_csv(path, rows, columns=None):
    columns = columns or (list(rows[0]) if rows else [])
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def extras(A, cases, truths, runs, idx):
    """Absolute (not paired) numbers for one arm: verification time of the incidents that WERE verified, and compute time."""
    H = A.H
    times, ms = [], []
    n_inc = 0
    for i in idx:
        cid = cases[i]["id"]
        r = runs[cid]
        ms.append(r.ms)
        for l in truths[cid]:
            n_inc += 1
            t = r.res["verify_time"].get(l)
            if t is not None and t <= H:
                times.append(t)
    q = lambda a, p: float(np.percentile(a, p)) if len(a) else None
    return {"incidents": n_inc, "verified": len(times), "verified_median_s": q(times, 50), "verified_p90_s": q(times, 90),
            "compute_ms_median": q(ms, 50), "compute_ms_p90": q(ms, 90)}


def compute_summary(A, cfg, cases, truths, gold_runs, arm_runs, bootstrap_runs=None, say=print):
    """arm_runs = {group: {arm: runs}}. Returns the summary dict and the long result tables."""
    fam = lambda idx: [cases[i]["family"] for i in idx]
    S = {"vs_gold": {}, "pairs": {}, "bootstrap": None, "extras": {}}
    rep_rows, inc_rows = [], []
    splits = [cfg["primary_split"]] + [s for s in cfg["secondary_splits"] if s != cfg["primary_split"]]
    for group in GROUPS:
        for arm, runs in arm_runs.get(group, {}).items():
            S["vs_gold"][arm] = {"group": group}
            S["extras"][arm] = {}
            for sp in splits:
                idx = split_index(cases, sp)
                S["extras"][arm][sp] = extras(A, cases, truths, runs, idx)
                M, cmps = pair_matrix(A, cfg, cases, truths, gold_runs, runs, idx)
                S["vs_gold"][arm][sp] = summarize(M, fam(idx), cfg)
                if sp == "all":
                    rep_rows += per_report_rows(arm, group, cases, idx, M, cmps, gold_runs, runs)
                    inc_rows += per_incident_rows(arm, cases, idx, truths, gold_runs, runs, A.H)
    S["extras"][GOLD_NAME] = {sp: extras(A, cases, truths, gold_runs, split_index(cases, sp)) for sp in splits}
    # pairs between heads precisions (the quantization question), and shared/offset vs separate Q4
    for ref, test in cfg["arm_pairs"]:
        S["pairs"]["%s -> %s" % (ref, test)] = {}
        pool = {**arm_runs.get("primary", {}), **arm_runs.get("secondary", {}), **arm_runs.get("context", {})}
        for sp in splits:
            idx = split_index(cases, sp)
            M, _ = pair_matrix(A, cfg, cases, truths, pool[ref], pool[test], idx)
            S["pairs"]["%s -> %s" % (ref, test)][sp] = summarize(M, fam(idx), cfg)
    S["miss_reasons"] = miss_reasons(A, cases, truths, gold_runs, arm_runs, cfg["primary_split"])
    if bootstrap_runs:
        S["bootstrap"] = summarize_bootstrap(A, cfg, cases, truths, gold_runs, bootstrap_runs)
    return S, rep_rows, inc_rows


def miss_reasons(A, cases, truths, gold_runs, arm_runs, split):
    """POST-RUN DESCRIPTIVE LOOK (not in the frozen plan): for every real incident that was verified with the gold record but not with
    the arm's record (V->U), which kind of record change was it? Key = 'gold action -> system action'. The counts add up to V->U."""
    idx = split_index(cases, split)
    out = {}
    for group, arms in arm_runs.items():
        for arm, runs in arms.items():
            c = Counter()
            for i in idx:
                cid = cases[i]["id"]
                for l in truths[cid]:
                    if _verified(gold_runs[cid].res, l, A.H) and not _verified(runs[cid].res, l, A.H):
                        c["%s -> %s" % (gold_runs[cid].norm["action"], runs[cid].norm["action"])] += 1
            out[arm] = dict(c)
    return out


def summarize_bootstrap(A, cfg, cases, truths, gold_runs, bootstrap_runs):
    """For each vector set: the spread over the bootstrap heads of U and dU on the primary split (point values only).
    The heads are trained on resampled data and tested on the SAME reports. They are NOT independent datasets."""
    idx = split_index(cases, cfg["primary_split"])
    out = {}
    for vec in cfg["bootstrap_vectors"]:
        us, dus, v2us, u2vs = [], [], [], []
        for (head, v), runs in sorted(bootstrap_runs.items()):
            if v != vec:
                continue
            M, _ = pair_matrix(A, cfg, cases, truths, gold_runs, runs, idx)
            t = M.sum(0)
            us.append(t[CI["test_unver"]] / t[CI["n_truth"]])
            dus.append((t[CI["test_unver"]] - t[CI["ref_unver"]]) / t[CI["n_truth"]])
            v2us.append(t[CI["v2u"]])
            u2vs.append(t[CI["u2v"]])
        if us:
            f = lambda a: {"mean": float(np.mean(a)), "min": float(np.min(a)), "max": float(np.max(a))}
            out[vec] = {"heads": len(us), "U": f(us), "dU": f(dus), "v2u": f(v2us), "u2v": f(u2vs)}
    return out
