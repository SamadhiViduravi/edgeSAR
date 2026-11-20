"""PROTOCOL_TEXT_BASELINES.md: the pilot's TF-IDF + logistic-regression classifier and keyword rule engine, run through the SAME mission
simulator, evaluation reports, load levels and arrival seeds as the hidden-vector arms (exploratory, development data, no tuning, no model run).
   python text_baselines_mission.py --root <root2> --ref <dir with the saved records_{L,M,H}_s{1,2,3}.json.gz and mission_results.json> --out out_text_baselines
   (--max-episodes N only for a code check; --no-cache rebuilds the fold split without the saved head probabilities, as needed with the dataset release alone)
<root2> holds edgesar_shield (study code with `shield/`), edgesar_pilot (baselines.py, common.py), edgesar_heads, V1 as in the dataset release `code/`."""
import argparse, gzip, hashlib, json, os, sys, time
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LEVELS, SEEDS = "LMH", (1, 2, 3)
REF_ARMS = ["gold", "f16p", "q4p", "alnp", "recp", "rawp"]
NEW_ARMS = ["tfidf", "rule"]
W = {3: 3.0, 2: 2.0, 1: 1.0}


def by_arm(recs):
    d = {}
    for r in recs: d.setdefault(r["arm"], {})[r["episode"]] = r
    return d


def wvec(by, arm, ids):
    a, b = [], []
    for e in ids:
        x = y = 0.0
        for row in by[arm][e]["inc"]:
            if row[8] == "resolved_external": continue
            w = W[int(row[4])]; y += w
            if row[8] in ("late", "unverified"): x += w
        a.append(x); b.append(y)
    return np.array(a), np.array(b)


def share_w(by, arm, n_boot=2000, seed=11):
    ids = sorted(by[arm]); a, b = wvec(by, arm, ids)
    idx = np.random.RandomState(seed).randint(0, len(ids), size=(n_boot, len(ids)))
    u = a[idx].sum(1) / b[idx].sum(1)
    return a.sum() / b.sum(), float(np.percentile(u, 2.5)), float(np.percentile(u, 97.5))


def paired_w(by, x, y, n_boot=10000, seed=7):
    ids = sorted(set(by[x]) & set(by[y])); ax, bx = wvec(by, x, ids); ay, by_ = wvec(by, y, ids)
    assert np.allclose(bx, by_), "weighted denominators differ: the episodes are not paired"
    idx = np.random.RandomState(seed).randint(0, len(ids), size=(n_boot, len(ids)))
    d = (ax[idx].sum(1) - ay[idx].sum(1)) / bx[idx].sum(1)
    dd = ax - ay
    return {"diff": float((ax.sum() - ay.sum()) / bx.sum()), "ci": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "wins_x": int((dd < 0).sum()), "wins_y": int((dd > 0).sum()), "ties": int((dd == 0).sum())}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--ref", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--max-episodes", type=int, default=None); ap.add_argument("--no-cache", action="store_true"); a = ap.parse_args()
    root = Path(a.root).resolve(); ref = Path(a.ref).resolve(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    psha = hashlib.sha256((HERE / "PROTOCOL_TEXT_BASELINES.md").read_bytes()).hexdigest()
    (out / "PROTOCOL.sha256").write_text(psha + "  PROTOCOL_TEXT_BASELINES.md\n")
    os.environ["EDGESAR_ROOT"] = str(root); sys.path.insert(0, str(root / "edgesar_shield"))
    from shield import devrun, readout
    from shield.alloc import make_allocator
    from shield.candidates import pilot
    from shield.devset import DevSet, build_service
    from shield.episodes import EPISODE_REPORTS
    from shield.policy import CommitPolicy
    from shield.sim import Sim, SimConfig
    t_all = time.time()
    from shield import paths
    if a.no_cache or not (paths.RESULTS / "cache" / "readout_probs.npz").exists():
        # the baselines need no saved vectors or head probabilities: only the report texts and the fold split (DevData.split), which the cache merely stores
        from shield.candidates import Enumerator
        from shield.data import DevData, N_FOLDS
        ds = DevSet.__new__(DevSet); ds.D = DevData(); ds.folds = {}
        for k in range(N_FOLDS):
            fit, cal, ev = ds.D.split(k); ds.folds[k] = {"fit": fit, "cal": cal, "eval": ev, "P": {}}
        ds.fit_log = None; ds.cases = ds.D.cases; ds.enum = {int(i): Enumerator(ds.cases[i]) for i in ds.D.A}
        pc0 = pilot()[0]; ds.label_norm = {int(i): pc0.gold_norm(ds.cases[i]) for i in ds.D.A}; ds.label_key = {i: pc0.strict_key(n) for i, n in ds.label_norm.items()}
        ds._pos = {k: {int(i): r for r, i in enumerate(np.concatenate([f["cal"], f["eval"]]))} for k, f in ds.folds.items()}; ds._cand_cache = {}
        print("running WITHOUT the head-probability cache (fold split rebuilt from DevData.split)", flush=True)
    else:
        ds = DevSet()
    D = ds.D; pc, pb = pilot(); CL = readout.CLASSES; folds = sorted(ds.folds)
    id2i = {c["id"]: i for i, c in enumerate(D.cases)}
    fitinfo = {}
    for k in folds:
        f = ds.folds[k]; fit = np.asarray(f["fit"]); rows = np.concatenate([f["cal"], f["eval"]])
        # ---- tfidf: the pilot's LRBaseline, unchanged, fitted on the FIT reports of this fold
        t0 = time.time(); base = pb.LRBaseline().fit([D.cases[int(i)] for i in fit]); X = [pb.lr_text(D.cases[int(i)]) for i in rows]
        f["P"]["tfidf"] = {"action": readout.proba_fixed(base.action, X, CL["action"]), "sensor": readout.proba_fixed(base.sensor, X, CL["sensor"]),
                           "prio": readout.proba_fixed(base.prio, X, CL["prio"])}
        # ---- rule: the pilot's rule_decision, unchanged; one-hot where it speaks, uniform where it does not
        pa = np.zeros((len(rows), 4)); ps = np.full((len(rows), 3), 1 / 3); pp = np.full((len(rows), 3), 1 / 3)
        for r, i in enumerate(rows):
            d = pb.rule_decision(D.cases[int(i)]); pa[r, CL["action"].index(d["action"])] = 1.0
            if d.get("sensor") in CL["sensor"]: ps[r] = 0.0; ps[r, CL["sensor"].index(d["sensor"])] = 1.0
            if d.get("priority") is not None and str(d["priority"]) in CL["prio"]: pp[r] = 0.0; pp[r, CL["prio"].index(str(d["priority"]))] = 1.0
        f["P"]["rule"] = {"action": pa, "sensor": ps, "prio": pp}
        fitinfo[k] = {"n_fit": int(len(fit)), "seconds_tfidf": round(time.time() - t0, 1)}
        print("fold %d: tfidf fitted on %d reports, rule ready" % (k, len(fit)), flush=True)
    # ---------------------------------------------------------------- decision accuracy on EVAL and wrong fields
    acc = {}
    for arm in NEW_ARMS:
        ok = n = act = 0
        for k in folds:
            for i in ds.folds[k]["eval"]:
                h = ds.hier(k, arm, int(i)); n += 1; ok += pc.strict_key(h) == ds.label_key[int(i)]; act += h["action"] == ds.label_norm[int(i)]["action"]
        acc[arm] = {"n": n, "record": ok / n, "action": act / n}
    refres = json.loads((ref / "mission_results.json").read_text(encoding="utf-8"))
    ref_acc = {arm: refres["decisions_eval"][arm] for arm in ("f16p", "q4p", "alnp", "recp", "rawp") if arm in refres["decisions_eval"]}

    def fields_wrong(k, arm, i):
        h = ds.hier(k, arm, i); g = ds.label_norm[int(i)]; w = []
        if h.get("action") != g.get("action"): w.append("A")
        elif g.get("action") in ("CREATE_VERIFICATION", "UPDATE_INCIDENT"):
            if h.get("sensor") != g.get("sensor"): w.append("S")
            if str(h.get("priority")) != str(g.get("priority")): w.append("P")
        return "".join(w) or "-"
    # ---------------------------------------------------------------- missions
    sim = Sim(make_allocator("cbba_bounded"), SimConfig())
    svc = {k: {arm: build_service(ds, k, arm) for arm in NEW_ARMS} for k in folds}
    print("services built in %.0f s" % (time.time() - t_all), flush=True)
    new = {lev: [] for lev in LEVELS}
    for lev in LEVELS:
        for seed in SEEDS:
            t0 = time.time(); srecs = []
            for k in folds:
                eps = ds.make_episodes(ds.folds[k]["eval"], lev, seed * 1000 + k, EPISODE_REPORTS)
                if a.max_episodes: eps = eps[:a.max_episodes]
                for e in eps:
                    srecs.append(devrun.compact(sim.run(e, None, "gold", oracle=True), k, lev, seed))
                    for arm in NEW_ARMS: srecs.append(devrun.compact(sim.run(e, CommitPolicy(svc[k][arm]), arm), k, lev, seed))
            with gzip.open(out / ("records_%s_s%d.json.gz" % (lev, seed)), "wt", encoding="utf-8") as fh: json.dump(srecs, fh, separators=(",", ":"))
            new[lev] += srecs; print("level %s seed %d: %d records in %.0f s" % (lev, seed, len(srecs), time.time() - t0), flush=True)
    # ---------------------------------------------------------------- integrity against the saved gold records, then the tables
    res = {"protocol_sha256": psha, "fit": fitinfo, "decisions_eval": {**acc, **{"ref_" + k: v for k, v in ref_acc.items()}}, "levels": {}, "integrity": {}}
    NAMES = {"gold": "Gold records", "f16p": "F16 reader", "q4p": "Q4 retrained, all labels", "alnp": "Q4 label-free map", "recp": "Q4 recentred",
             "rawp": "Q4 unchanged transfer", "tfidf": "TF-IDF + LR (text)", "rule": "Keyword rule engine (text)"}
    md = ["# Conventional text baselines in the mission simulator: results", "",
          "Exploratory, development data (style A wording), reading position `prefix` for the hidden-vector arms, always commit, bounded CBBA. Protocol hash `%s`." % psha,
          "No tuning, no model run. The TF-IDF classifier and the rule engine are the pilot's own code. Pooled intervals are optimistic (the arrival seeds reuse the same reports).", ""]
    all_ok = True
    for lev in LEVELS:
        refrecs = []
        for s in SEEDS: refrecs += json.load(gzip.open(ref / ("records_%s_s%d.json.gz" % (lev, s))))
        refby = by_arm([r for r in refrecs if r["arm"] in REF_ARMS]); newby = by_arm(new[lev])
        ids = sorted(newby["gold"]); bad = 0
        for e in ids:
            g1, g2 = newby["gold"][e]["counts"], refby["gold"][e]["counts"]
            if any(g1[kk] != g2[kk] for kk in ("n", "late", "unverified")): bad += 1
        res["integrity"][lev] = {"episodes": len(ids), "gold_mismatches": bad}; all_ok &= bad == 0
        recs = [r for r in refrecs if r["arm"] in REF_ARMS and r["episode"] in set(ids)] + [r for r in new[lev] if r["arm"] in NEW_ARMS]
        by = by_arm(recs); res["levels"][lev] = {"arms": {}, "paired": {}}
        md += ["## Level %s" % lev, "", "Integrity: the re-run gold arm reproduces the saved late / unverified / incident counts in %d of %d episodes (%s)." %
               (len(ids) - bad, len(ids), "PASS" if bad == 0 else "FAIL"), "",
               "| Arm | Missed share, every incident once | 95% CI | Missed share, priority-weighted 3/2/1 | 95% CI |", "|---|---|---|---|---|"]
        for arm in REF_ARMS + NEW_ARMS:
            eps = list(by[arm].values()); m = sum(r["counts"]["late"] + r["counts"]["unverified"] for r in eps); n = sum(r["counts"]["n"] for r in eps)
            lo, hi = devrun.episode_bootstrap_ci(recs, arm); w, wlo, whi = share_w(by, arm)
            res["levels"][lev]["arms"][arm] = {"missed": m, "incidents": n, "share": m / n, "ci": [lo, hi], "w_share": w, "w_ci": [wlo, whi], "episodes": len(eps)}
            md.append("| %s | %.2f%% | %.2f to %.2f | %.2f%% | %.2f to %.2f |" % (NAMES[arm], 100 * m / n, 100 * lo, 100 * hi, 100 * w, 100 * wlo, 100 * whi))
        md += ["", "| First minus second (pp) | Every incident once (95% CI) | First better / worse / tied | Priority-weighted (95% CI) |", "|---|---|---|---|"]
        for x in NEW_ARMS:
            for y in ("f16p", "q4p", "alnp", "recp", "gold"):
                p = devrun.paired(recs, x, y); pw = paired_w(by, x, y); res["levels"][lev]["paired"]["%s-%s" % (x, y)] = {"ordinary": p, "weighted": pw}
                md.append("| %s minus %s | %+.2f (%+.2f to %+.2f) | %d / %d / %d | %+.2f (%+.2f to %+.2f) |" % (x, y, 100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1], p["wins_x"], p["wins_y"], p["ties"],
                         100 * pw["diff"], 100 * pw["ci"][0], 100 * pw["ci"][1]))
        md.append("")
    md += ["## Decision accuracy on the EVAL reports (development wording; pooled over the 5 folds)", "", "| System | Whole record right | Action right |", "|---|---|---|"]
    for arm in NEW_ARMS: md.append("| %s | %.1f%% | %.1f%% |" % (NAMES[arm], 100 * acc[arm]["record"], 100 * acc[arm]["action"]))
    for arm, v in ref_acc.items(): md.append("| %s (saved) | %.1f%% | %.1f%% |" % (NAMES[arm], 100 * v["record"], 100 * v["action"]))
    md += ["", "## Which fields are wrong (reports counted once per arrival seed and level)", ""]
    for arm in NEW_ARMS:
        pat = {}
        for lev in LEVELS:
            for r in new[lev]:
                if r["arm"] != arm: continue
                for rep in r["reports"]:
                    p = fields_wrong(r["fold"], arm, id2i[rep["id"]]); d = pat.setdefault(p, {"reports": 0, "plan_not_gold": 0}); d["reports"] += 1; d["plan_not_gold"] += rep["pg"] is False
        res["fields_wrong_" + arm] = pat; tot = sum(v["reports"] for v in pat.values())
        md += ["**%s** (%d report decisions over L, M, H)" % (NAMES[arm], tot), "", "| Wrong fields (A action, S sensor, P priority; - none) | Reports | Plan differs from gold plan |", "|---|---|---|"]
        for p, v in sorted(pat.items(), key=lambda kv: -kv[1]["reports"]): md.append("| %s | %d | %d (%.0f%%) |" % (p, v["reports"], v["plan_not_gold"], 100 * v["plan_not_gold"] / v["reports"]))
        md.append("")
    md += ["Integrity overall: %s. Fit sizes and times: %s. Total run time %.0f s." % ("PASS" if all_ok else "FAIL (do not use the paired lines)", json.dumps(fitinfo), time.time() - t_all)]
    (out / "TEXT_BASELINES_RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("\n".join(md))
    if not all_ok: sys.exit(2)


if __name__ == "__main__":
    main()
