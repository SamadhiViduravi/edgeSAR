"""
Run all arms on the development set (saved vectors, overlay episodes) and summarise outcomes AND costs.

For every outer fold k and contention level:
  1. CAL reports -> CAL episodes -> the Observer policy commits the pilot-style Q4 record and logs every gate's risk score (free what-if runs);
     thresholds for A6, A6b, A8, A9, A11 are set on those logs so that each gate's expected request rate equals b;
  2. EVAL reports -> EVAL episodes -> every arm runs on exactly the same episodes (paired).
The conformal threshold of fold k comes from the CAL reports of fold k only.

A run returns *compact* records (plain dicts, JSON-ready): counts, costs, one row per report, one row per incident.
"""
import multiprocessing
import time

import numpy as np

from .alloc import make_allocator
from .candidates import pilot
from .devset import ARMS, build_service
from .episodes import EPISODE_REPORTS
from .oracle import ListGate, wrong_table_ids
from .policy import CommitPolicy, Observer, RiskGate, ShieldPolicy, rate_threshold
from .sim import Sim, SimConfig

ARM_ORDER = ["A0", "A1", "A2", "A3", "A4", "A5", "A6", "A6b", "A7", "A8", "A8c", "A9", "A10", "A11", "A12"]
ARM_TEXT = {
    "A0": "Gold records (reference)", "A1": "Q4 heads, always commit", "A2": "FP16 heads, always commit (off-board reference)",
    "A3": "Q8 heads, always commit", "A4": "Recentred Q4 (FP16 head, label-free shift removed)", "A5": "Frozen FP16 head on raw Q4 (diagnostic)",
    "A6": "Confidence gate (min head confidence)", "A6b": "Top-record-score gate", "A7": "Random gate",
    "A8": "Shield + full cover fallback (plan)", "A8c": "Shield + location cover (revised, post-hoc on DEV)", "A9": "Shield, singleton sets only", "A10": "Shield, no fallback",
    "A11": "Top-2 what-if, no conformal", "A12": "Oracle gate (diagnostic upper bound)",
}
GATES = ("A6", "A6b", "A7", "A8", "A8c", "A9", "A10", "A11", "A12")
FLAGGED = ("ESCALATE", "FALLBACK_COVERED", "FALLBACK_PARTIAL", "FALLBACK_UNRESOLVED")


# =====================================================================================================================
# running
# =====================================================================================================================
def compact(res, fold, level, seed, obs_rows=None):
    lg = res["log"]
    reps = []
    for j, r in enumerate(lg["reports"]):
        d = r["diag"] or {}
        cov = d.get("cover") or {}
        reps.append({"id": r["case_id"], "t": round(r["t"], 3), "o": r["outcome"], "runs": r["runs"], "ms": round(r["wall_ms"], 3),
                     "tg": r.get("table_equal_gold"), "pg": r.get("plan_equal_gold"),
                     "rtg": r.get("rhat_table_equal_gold"), "rpg": r.get("rhat_plan_equal_gold"),
                     "sz": d.get("set_size"), "cert": d.get("certified"), "rho": d.get("rho"), "why": d.get("reason"),
                     "nd": d.get("distinct_sigs"), "cov": cov.get("n_tasks"), "cnew": cov.get("n_new"), "part": d.get("partial_cover"),
                     **({"risk": {k: (list(v) if isinstance(v, tuple) else v) for k, v in obs_rows[j].items() if k != "id"}} if obs_rows else {})})
    inc = [[i["ns"], i["iid"], i["landmark"], i["sensor"], i["priority"], round(i["created"], 3), round(i["deadline"], 3),
            None if i["verified_at"] is None else round(i["verified_at"], 3), i["class"]] for i in res["incidents"]]
    cost = {"reports": len(lg["reports"]), "requests": len(lg["requests"]), "wasted": lg["wasted"], "failed": lg["failed"], "empty": lg["empty"],
            "dist": lg["dist"], "hold_s": lg["hold_s"], "decision_s": lg["decision_s"], "policy_runs": lg["policy_runs"],
            "wall_ms": lg["wall_ms_policy"], "engine_runs": lg["engine_runs"], "cover_visits": sum(1 for v in lg["visits"] if v["cover"]),
            "cover_wasted": sum(1 for v in lg["visits"] if v["cover"] and v["result"] != "verified")}
    return {"episode": res["episode"], "arm": res["arm"], "fold": fold, "level": level, "seed": seed, "counts": res["counts"],
            "cap": res["budget_cap"], "cost": cost, "reports": reps, "inc": inc}


def eval_set_facts(ds, k, arm, q, K, idx):
    """Facts about the conformal sets on the EVAL reports.  EVALUATION SIDE: it reads the labels, and nothing here is passed to a policy.
    covered = the gold record is in the set; gold_missing = the heads + parser cannot express the gold record at all (a missing candidate)."""
    pc = pilot()[0]
    n = cov = empty = over = s1 = smid = gold_missing = hier_in = top_in = 0
    for i in idx:
        i = int(i)
        cs = ds.cands(k, arm, i)
        S = ds.conformal(k, arm, i, q)
        keys = {c["key"] for c in S}
        n += 1
        cov += ds.label_key[i] in keys
        gold_missing += not any(c["key"] == ds.label_key[i] for c in cs)
        empty += len(S) == 0
        over += len(S) > K
        s1 += len(S) == 1
        smid += 2 <= len(S) <= K
        hier_in += pc.strict_key(ds.hier(k, arm, i)) in keys
        top_in += bool(cs) and cs[0]["key"] in keys
    return {"reports": n, "covered": cov, "gold_missing": gold_missing, "empty": empty, "size1": s1, "size_2_K": smid, "over_K": over,
            "hier_in_set": hier_in, "top_in_set": top_in}


def run_fold(ds, k, level, alpha=0.10, K=8, b=0.10, seed=1, R=EPISODE_REPORTS, allocator="cbba_bounded", cfg=None, arms=None, gap=None,
             max_episodes=None, readout="q4", cover_kw=None, extra_arms=None, shard=None, wrap=None, only_episodes=None, keep=None):
    cfg = cfg or SimConfig()
    cfg = SimConfig(**{**cfg.__dict__, "budget_fraction": b})
    arms = arms or ARM_ORDER
    sim = Sim(make_allocator(allocator), cfg)
    f = ds.folds[k]
    svc = {a: build_service(ds, k, a) for a in ARMS}
    base = svc[readout]                                  # the readout the gates and the Shield sit on (q4 = the competent Q4 head; raw = the mismatched head)
    q = ds.q_hat(k, readout, alpha)
    # ---- thresholds from CAL episodes (observer: commits like A1 and logs every gate's risk; its what-if runs are free)
    obs = Observer(base, q, K)
    for e in ds.make_episodes(f["cal"], level, seed * 1000 + 100 + k, R, gap):
        sim.run(e, obs, "observer")
    th = {}
    for name in ("conf", "topscore", "a8", "a9", "a11"):
        th[name] = rate_threshold([r[name] for r in obs.rows], b)
    info = {"fold": k, "level": level, "seed": seed, "readout": readout, "q_hat": q, "n_cal_reports": len(obs.rows),
            "eval_set": eval_set_facts(ds, k, readout, q, K, f["eval"]),
            "n_fit": int(getattr(ds, "n_fit", len(f["fit"]) if f.get("fit") is not None else 0)),
            "cal_certified_rate": float(np.mean([r["a8_cert"] for r in obs.rows])),
            "cal_set_sizes": {int(s): int(c) for s, c in zip(*np.unique([r["a8_size"] for r in obs.rows], return_counts=True))},
            "thresholds": {n: (None if t[0] is None else list(t[0]), float(t[1])) for n, t in th.items()}}
    pol = {
        "A1": CommitPolicy(base), "A2": CommitPolicy(svc["f16"]), "A3": CommitPolicy(svc["q8"]),
        "A4": CommitPolicy(svc["rec"]), "A5": CommitPolicy(svc["raw"]),
        "A6": RiskGate(base, "conf", *th["conf"], seed=seed), "A6b": RiskGate(base, "topscore", *th["topscore"], seed=seed),
        "A7": RiskGate(base, "random", (1.0 - b,), 0.0, seed=seed),
        "A8": ShieldPolicy(base, q, K, "shield", True, *th["a8"], seed=seed, cover_kw=cover_kw),
        "A8c": ShieldPolicy(base, q, K, "shield", True, *th["a8"], seed=seed, cover_kw={"camera": "rhat", "priority": "rhat"}),
        "A9": ShieldPolicy(base, q, K, "nodown", True, *th["a9"], seed=seed),
        "A10": ShieldPolicy(base, q, K, "shield", False, *th["a8"], seed=seed),
        "A11": ShieldPolicy(base, q, K, "top2", True, *th["a11"], seed=seed),
    }
    for name, kw in (extra_arms or {}).items():             # development variants: name -> cover options of a Shield with the same sets and thresholds
        pol[name] = ShieldPolicy(base, q, K, "shield", True, *th["a8"], seed=seed, cover_kw=kw)
    if "A12" in arms:
        pol["A12"] = ListGate(base, wrong_table_ids(ds, base, f["eval"]))
    out = []
    episodes = ds.make_episodes(f["eval"], level, seed * 1000 + k, R, gap)
    if max_episodes:
        episodes = episodes[:max_episodes]
    if shard:                                                # (j, n): every n-th episode starting at j; thresholds above are identical in every shard
        episodes = episodes[shard[0]::shard[1]]
    if only_episodes is not None:                            # the demo re-runs chosen episodes only (same thresholds as the full run)
        episodes = [e for e in episodes if e.id in only_episodes]
    for e in episodes:
        for a in arms:
            if a == "OBS":                                   # ranking diagnostic: behaves exactly like A1, logs every gate's risk score
                o = Observer(base, q, K)
                res = sim.run(e, o, "OBS")
                out.append(compact(res, k, level, seed, o.rows))
                continue
            p = pol.get(a)
            if wrap is not None and p is not None:           # the demo wraps a policy to record what it saw and decided (the wrapper changes no decision)
                p = wrap(a, p)
            res = sim.run(e, p, a, oracle=(a == "A0"))
            if keep is not None:
                keep[(e.id, a)] = res
            out.append(compact(res, k, level, seed))
    return out, info


_G = {}


def _job(args):
    k, kw = args
    t0 = time.time()
    kw = dict(kw)
    if kw.get("shard") is None:
        kw.pop("shard", None)
    recs, info = run_fold(_G["ds"], k, **kw)
    info["seconds"] = round(time.time() - t0, 1)
    return recs, info


def run_level(ds, level, folds=None, processes=2, verbose=False, shards=1, **kw):
    """All folds of one level (and one seed). Returns (records, infos).  shards > 1 splits the EVAL episodes of each fold over that many jobs
    (every shard recomputes the same thresholds from the same CAL episodes, so the records do not depend on the number of shards)."""
    folds = list(folds if folds is not None else sorted(ds.folds))
    _G["ds"] = ds
    jobs = [(k, dict(kw, level=level, shard=((j, shards) if shards > 1 else None))) for k in folds for j in range(shards)]
    if processes > 1 and len(jobs) > 1:
        with multiprocessing.get_context("fork").Pool(processes) as pool:
            outs = pool.map(_job, jobs, chunksize=1)
    else:
        outs = [_job(j) for j in jobs]
    records, infos = [], []
    for n, (recs, info) in enumerate(outs):
        records.extend(recs)
        if shards == 1 or n % shards == 0:
            infos.append(dict(info, shards=shards))
        elif shards > 1:
            infos[-1]["seconds"] = round(infos[-1]["seconds"] + info["seconds"], 1)
        if verbose:
            print("   level %s fold %d: %.0f s" % (level, info["fold"], info["seconds"]), flush=True)
    if shards > 1:
        order = {a: i for i, a in enumerate(ARM_ORDER + ["OBS"])}
        records.sort(key=lambda r: (r["episode"], order.get(r["arm"], 99)))
    return records, infos


# =====================================================================================================================
# summaries (all work on compact records)
# =====================================================================================================================
def _by_arm(records):
    out = {}
    for r in records:
        out.setdefault(r["arm"], {})[r["episode"] + "|" + str(r["seed"]) + "|" + str(r["level"])] = r
    return out


def arm_table(records):
    """One row per arm: outcomes and costs, pooled over episodes."""
    rows = {}
    for arm, eps in _by_arm(records).items():
        n = on = late = unv = ext = 0
        reports = req = wasted = failed = empty = cv = cvw = 0
        dist = hold = dec = runs = wall = 0.0
        cls, wl = {}, []
        for r in eps.values():
            c, k = r["counts"], r["cost"]
            n += c["n"]; on += c["on_time"]; late += c["late"]; unv += c["unverified"]; ext += c["resolved_external"]
            reports += k["reports"]; req += k["requests"]; wasted += k["wasted"]; failed += k["failed"]; empty += k["empty"]
            dist += k["dist"]; hold += k["hold_s"]; dec += k["decision_s"]; runs += k["policy_runs"]; wall += k["wall_ms"]
            cv += k["cover_visits"]; cvw += k["cover_wasted"]
            for rep in r["reports"]:
                key = rep["o"].split(":")[0] if not rep["o"].startswith("TIMEOUT_LATE") else "TIMEOUT_LATE"
                cls[key] = cls.get(key, 0) + 1
                if rep["ms"] > 0:
                    wl.append(rep["ms"])
        nz = max(reports, 1)
        rows[arm] = {"episodes": len(eps), "reports": reports, "incidents": n, "on_time": on, "late": late, "unverified": unv, "resolved_external": ext,
                     "U_deadline": (late + unv) / n if n else float("nan"), "U_unverified": unv / n if n else float("nan"),
                     "requests": req, "request_rate": req / nz, "wasted_trips": wasted, "wasted_per_report": wasted / nz,
                     "failed_visits": failed, "empty_visits": empty, "cover_visits": cv, "cover_wasted_visits": cvw,
                     "distance_per_report_m": dist / nz, "hold_s_per_report": hold / nz, "decision_s_per_report": dec / nz,
                     "allocator_runs_per_report": runs / nz, "outcome_classes": cls,
                     "wall_ms_median": float(np.median(wl)) if wl else 0.0, "wall_ms_p99": float(np.percentile(wl, 99)) if wl else 0.0}
    return rows


def episode_bootstrap_ci(records, arm, n_boot=2000, seed=11):
    eps = list(_by_arm(records)[arm].values())
    m = np.array([e["counts"]["late"] + e["counts"]["unverified"] for e in eps], dtype=float)
    n = np.array([e["counts"]["n"] for e in eps], dtype=float)
    rng = np.random.RandomState(seed)
    idx = rng.randint(0, len(eps), size=(n_boot, len(eps)))
    u = m[idx].sum(1) / n[idx].sum(1)
    return float(np.percentile(u, 2.5)), float(np.percentile(u, 97.5))


def paired(records, x, y, n_boot=10000, seed=7):
    """Arm x against arm y on the same episodes: difference in pooled U_deadline (x - y), episode bootstrap 95% CI, and a paired sign-flip
    permutation test on the per-episode difference in missed incidents (late + unverified)."""
    by = _by_arm(records)
    ids = sorted(set(by[x]) & set(by[y]))
    mx = np.array([by[x][e]["counts"]["late"] + by[x][e]["counts"]["unverified"] for e in ids], dtype=float)
    my = np.array([by[y][e]["counts"]["late"] + by[y][e]["counts"]["unverified"] for e in ids], dtype=float)
    ux = sum(by[x][e]["counts"]["unverified"] for e in ids)
    uy = sum(by[y][e]["counts"]["unverified"] for e in ids)
    nn = np.array([by[x][e]["counts"]["n"] for e in ids], dtype=float)
    if not np.array_equal(nn, np.array([by[y][e]["counts"]["n"] for e in ids], dtype=float)):
        raise RuntimeError("the two arms have different incident counts: the episodes are not paired")
    rng = np.random.RandomState(seed)
    E = len(ids)
    idx = rng.randint(0, E, size=(n_boot, E))
    diff = (mx[idx].sum(1) - my[idx].sum(1)) / nn[idx].sum(1)
    d = mx - my
    obs = d.sum()
    signs = rng.choice([-1.0, 1.0], size=(n_boot, E))
    perm = np.abs((signs * d).sum(1))
    p = (np.sum(perm >= abs(obs) - 1e-12) + 1) / (n_boot + 1)
    return {"x": x, "y": y, "episodes": E, "incidents": int(nn.sum()), "diff_U": float((mx.sum() - my.sum()) / nn.sum()),
            "ci": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))],
            "miss_x": int(mx.sum()), "miss_y": int(my.sum()), "unverified_x": int(ux), "unverified_y": int(uy),
            "p_signflip": float(p), "wins_x": int((d < 0).sum()), "wins_y": int((d > 0).sum()), "ties": int((d == 0).sum()),
            "sd_episode_diff": float(np.std(d, ddof=1)) if E > 1 else float("nan"), "mean_n_per_episode": float(nn.mean())}


def gate_quality(records, arm):
    """How well does the arm pick the reports whose best-guess record would have given the wrong plan?  (rpg = r_hat plan equals the gold plan,
    computed from the state at the decision, evaluation only.)  recall = wrong-plan reports that were flagged / wrong-plan reports;
    precision = flagged reports with a wrong plan / flagged reports; accepted_wrong = wrong-plan reports that were committed unflagged."""
    tot = wrong = flagged = flagged_wrong = acc_wrong = n = 0
    for r in _by_arm(records)[arm].values():
        for rep in r["reports"]:
            if rep["rpg"] is None:
                continue
            n += 1
            w = not rep["rpg"]
            f = rep["o"].split(":")[0] in FLAGGED
            wrong += w
            flagged += f
            flagged_wrong += (w and f)
            acc_wrong += (w and not f)
    return {"reports": n, "wrong_plan": wrong, "flagged": flagged, "flagged_wrong": flagged_wrong, "accepted_wrong": acc_wrong,
            "recall": flagged_wrong / wrong if wrong else float("nan"), "precision": flagged_wrong / flagged if flagged else float("nan"),
            "wrong_rate": wrong / n if n else float("nan"), "accepted_wrong_rate": acc_wrong / n if n else float("nan")}


def certificate_check(records, arm="A8"):
    """The Shield's marginal guarantee: P(certified and the committed plan is not the gold plan) <= alpha.  Counted on reports the Shield
    certified (ACCEPT and ACCEPT_INFEASIBLE) with `pg` = plan of the committed record equals the gold plan."""
    n = cert = bad = 0
    sizes = {}
    for r in _by_arm(records)[arm].values():
        for rep in r["reports"]:
            n += 1
            if rep["o"].split(":")[0] in ("ACCEPT", "ACCEPT_INFEASIBLE"):
                cert += 1
                bad += (rep["pg"] is False)
                s = rep["sz"]
                sizes[s] = sizes.get(s, 0) + 1
    return {"reports": n, "certified": cert, "certified_rate": cert / n if n else float("nan"), "certified_wrong_plan": bad,
            "certified_wrong_rate": bad / n if n else float("nan"), "certified_set_sizes": dict(sorted(sizes.items(), key=lambda kv: str(kv[0])))}


def ranking_quality(records, rates=(0.05, 0.10, 0.20, 0.30)):
    """Same budget, who picks the risky reports better?  Uses the OBS arm (behaves like A1: always commits the best-guess record, and logs the risk
    score of every gate).  In every episode each ranker flags its top ceil(f R) reports; we count how many of the reports whose best-guess record would
    give a WRONG PLAN (rpg False) are among them.  Ties are broken by the report id hash (fixed), so no ranker gains from the order of the data.
    Also AUROC over all reports (ties count half)."""
    import hashlib
    from math import ceil
    eps = list(_by_arm(records)["OBS"].values())
    rankers = {"A8 Shield (rho, 1-score)": "a8", "A9 singleton-only": "a9", "A11 top-2 what-if": "a11", "A6 confidence": "conf", "A6b record score": "topscore"}
    out = {}
    wrong_total = sum(1 for e in eps for r in e["reports"] if r["rpg"] is False)
    n_total = sum(len(e["reports"]) for e in eps)
    tie = lambda rid: int(hashlib.sha256(("rank|" + rid).encode()).hexdigest()[:8], 16)
    for name, key in list(rankers.items()) + [("random", None)]:
        rec = {}
        for f in rates:
            hit = 0
            for e in eps:
                reps = e["reports"]
                if key is None:
                    order = sorted(range(len(reps)), key=lambda j: tie(reps[j]["id"]))
                else:
                    order = sorted(range(len(reps)), key=lambda j: (tuple(reps[j]["risk"][key]), tie(reps[j]["id"])), reverse=True)
                top = order[:int(ceil(f * len(reps) - 1e-9))]
                hit += sum(1 for j in top if reps[j]["rpg"] is False)
            rec["%d%%" % round(100 * f)] = hit / wrong_total if wrong_total else float("nan")
        # AUROC
        if key is None:
            auc = 0.5
        else:
            pos, neg = [], []
            for e in eps:
                for r in e["reports"]:
                    (pos if r["rpg"] is False else neg).append(tuple(r["risk"][key]))
            allv = sorted(set(pos + neg))
            rank = {v: i for i, v in enumerate(allv)}
            import numpy as _np
            pr = _np.array([rank[v] for v in pos]); nr = _np.array([rank[v] for v in neg])
            if len(pr) and len(nr):
                srt = _np.sort(nr)
                lt = _np.searchsorted(srt, pr, side="left"); le = _np.searchsorted(srt, pr, side="right")
                auc = float(((lt + 0.5 * (le - lt)).sum()) / (len(pr) * len(nr)))
            else:
                auc = float("nan")
        rec["AUROC"] = auc
        out[name] = rec
    return {"reports": n_total, "wrong_plan_reports": wrong_total, "recall_at_flag_rate": out}


def auroc_diff_ci(records, key_a, key_b, n_boot=2000, seed=5):
    """Paired episode bootstrap of  AUROC(ranking by key_a) - AUROC(ranking by key_b)  for finding the reports whose best-guess record gives a
    wrong plan.  Uses the OBS arm.  Positive = key_a ranks better."""
    from scipy.stats import rankdata
    eps = list(_by_arm(records)["OBS"].values())
    cols = {}
    for key in (key_a, key_b):
        allv = sorted({tuple(r["risk"][key]) for e in eps for r in e["reports"]})
        pos = {v: j for j, v in enumerate(allv)}
        cols[key] = [np.array([pos[tuple(r["risk"][key])] for r in e["reports"]], dtype=float) for e in eps]
    lab = [np.array([r["rpg"] is False for r in e["reports"]]) for e in eps]

    def auc(score_list, lab_list, sel):
        s = np.concatenate([score_list[i] for i in sel])
        y = np.concatenate([lab_list[i] for i in sel])
        n1, n0 = int(y.sum()), int((~y).sum())
        if n1 == 0 or n0 == 0:
            return float("nan")
        rk = rankdata(s)
        return (rk[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)

    rng = np.random.RandomState(seed)
    E = len(eps)
    full = np.arange(E)
    point = (auc(cols[key_a], lab, full), auc(cols[key_b], lab, full))
    d = []
    for _ in range(n_boot):
        sel = rng.randint(0, E, size=E)
        d.append(auc(cols[key_a], lab, sel) - auc(cols[key_b], lab, sel))
    d = np.array(d)
    return {"auroc_a": float(point[0]), "auroc_b": float(point[1]), "diff": float(point[0] - point[1]),
            "ci": [float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))], "episodes": E}
