"""Parts B and C of PROTOCOL_PRACTICAL_ADVANTAGE.md (exploratory, development data, level M, prefix, always commit).
   python mission_gold_trace.py --root <root2> --out out_trace [--max-episodes N]  (N only for a code check)"""
import argparse, gzip, hashlib, json, os, sys, time
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PKG = next((p for p in (HERE.parent / "repair_package", HERE.parent / "repair_pkg" / "edgesar_repair_2026-11-14") if p.exists()), HERE.parent / "repair_package")   # path fix only (supplement layout: repair_package/)
SEED = 20261113
LEVEL, SEEDS = "M", [1, 2, 3]
BASES = ["q4p", "alnp"]
VARS = ["a", "s", "p", "as", "ap", "sp", "asp"]
SCARCE = [100, 300]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--max-episodes", type=int, default=None); a = ap.parse_args()
    root = Path(a.root).resolve(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    psha = hashlib.sha256((HERE / "PROTOCOL_PRACTICAL_ADVANTAGE.md").read_bytes()).hexdigest()
    (out / "PROTOCOL.sha256").write_text(psha + "  PROTOCOL_PRACTICAL_ADVANTAGE.md\n")
    os.environ["EDGESAR_ROOT"] = str(root)
    sys.path.insert(0, str(root / "edgesar_shield")); sys.path.insert(0, str(PKG))
    from shield import data as sdata, devrun, readout
    from shield.alloc import make_allocator
    from shield.candidates import pilot
    from shield.devset import DevSet, build_service
    from shield.episodes import EPISODE_REPORTS
    from shield.policy import CommitPolicy
    from shield.sim import Sim, SimConfig
    from ppr_lib import AffineMap, template_key
    t_all = time.time()
    ds = DevSet(); D = ds.D; pc = pilot()[0]
    Xp, ids = sdata.load_vectors("prefix"); assert ids == [c["id"] for c in D.cases]
    tmpl = np.array([template_key(c["text"], pc.LANDMARKS) for c in D.cases])
    id2i = {c["id"]: i for i, c in enumerate(D.cases)}
    log = readout.FitLog(); folds = sorted(ds.folds)
    CL = readout.CLASSES
    SC_ARMS = ["q4p_n%d" % n for n in SCARCE]
    GV = ["%s_g%s" % (b, v) for b in BASES for v in VARS]
    ARMS = ["gold", "f16p", "q4p", "alnp", "recp", "rawp"] + SC_ARMS + GV
    fitsizes = {}
    for k in folds:
        f = ds.folds[k]; fit, cal, ev = np.asarray(f["fit"]), f["cal"], f["eval"]; rows = np.concatenate([cal, ev]); fitsizes[k] = int(len(fit))
        Hp = {m: readout.Heads(D.cases, Xp[m], fit, D.group, log) for m in ("f16", "Q4_K_M")}
        f["P"]["f16p"] = Hp["f16"].proba(Xp["f16"][rows]); f["P"]["q4p"] = Hp["Q4_K_M"].proba(Xp["Q4_K_M"][rows])
        f["P"]["rawp"] = Hp["f16"].proba(Xp["Q4_K_M"][rows])
        delta = (Xp["Q4_K_M"][fit] - Xp["f16"][fit]).mean(axis=0)
        f["P"]["recp"] = Hp["f16"].proba(Xp["Q4_K_M"][rows] - delta)
        amap = AffineMap(Xp["f16"][fit], Xp["Q4_K_M"][fit], tmpl[fit], seed=SEED + k)
        f["P"]["alnp"] = Hp["f16"].proba(amap(Xp["Q4_K_M"][rows]))
        perm = np.random.default_rng(20261114 + k).permutation(fit)
        for n in SCARCE:
            sub = np.sort(perm[:n])
            f["P"]["q4p_n%d" % n] = readout.Heads(D.cases, Xp["Q4_K_M"], sub, D.group, log).proba(Xp["Q4_K_M"][rows])
        for b in BASES:
            for v in VARS:
                Q = {h: f["P"][b][h].copy() for h in f["P"][b]}
                for j, i in enumerate(rows):
                    g = D.cases[int(i)]["gold"]
                    for letter, head, val in (("a", "action", g["action"]), ("s", "sensor", g.get("sensor", "")), ("p", "prio", str(g.get("priority", "")))):
                        if letter in v and val in CL[head]:
                            Q[head][j] = 0.0; Q[head][j][CL[head].index(val)] = 1.0
                f["P"]["%s_g%s" % (b, v)] = Q
        print("fold %d: heads, map and variants ready (n_fit %d)" % (k, len(fit)), flush=True)
    sim = Sim(make_allocator("cbba_bounded"), SimConfig())
    svc = {k: {arm: build_service(ds, k, arm) for arm in ARMS if arm != "gold"} for k in folds}
    print("services built in %.0f s" % (time.time() - t_all), flush=True)
    recs = []
    for seed in SEEDS:
        t0 = time.time()
        for k in folds:
            eps = ds.make_episodes(ds.folds[k]["eval"], LEVEL, seed * 1000 + k, EPISODE_REPORTS)
            if a.max_episodes: eps = eps[:a.max_episodes]
            for e in eps:
                recs.append(devrun.compact(sim.run(e, None, "gold", oracle=True), k, LEVEL, seed))
                for arm in ARMS[1:]:
                    recs.append(devrun.compact(sim.run(e, CommitPolicy(svc[k][arm]), arm), k, LEVEL, seed))
        print("seed %d done in %.0f s" % (seed, time.time() - t0), flush=True)
    with gzip.open(out / "records_M.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(recs, fh, separators=(",", ":"))
    table = devrun.arm_table(recs)
    # ------------------------------------------------ integrity against the earlier prefix mission run
    ref = json.loads((PKG / "out_mission" / "mission_results.json").read_text())["levels"][LEVEL]["arms"]
    integ = {}
    if not a.max_episodes:
        for arm in ("gold", "f16p", "q4p", "alnp", "recp", "rawp"):
            integ[arm] = {"here": [table[arm]["late"], table[arm]["unverified"], table[arm]["incidents"]],
                          "earlier": [ref[arm]["late"], ref[arm]["unverified"], ref[arm]["incidents"]]}
            integ[arm]["identical"] = integ[arm]["here"] == integ[arm]["earlier"]
    # ------------------------------------------------ field errors per report
    def fields_wrong(k, arm, i):
        h = ds.hier(k, arm, i); g = ds.label_norm[int(i)]; w = []
        if h.get("action") != g.get("action"): w.append("A")
        elif g.get("action") in ("CREATE_VERIFICATION", "UPDATE_INCIDENT"):
            if h.get("sensor") != g.get("sensor"): w.append("S")
            if str(h.get("priority")) != str(g.get("priority")): w.append("P")
        return "".join(w) or "-"
    trace = {}
    for base in BASES:
        pat = {}
        for r in recs:
            if r["arm"] != base: continue
            for rep in r["reports"]:
                i = id2i[rep["id"]]
                p = fields_wrong(r["fold"], base, i)
                d = pat.setdefault(p, {"reports": 0, "plan_not_gold": 0, "table_not_gold": 0})
                d["reports"] += 1; d["plan_not_gold"] += rep["pg"] is False; d["table_not_gold"] += rep["tg"] is False
        trace[base] = pat
    # ------------------------------------------------ report
    pairs = [("alnp", "q4p_n100"), ("alnp", "q4p_n300"), ("alnp", "q4p"), ("recp", "q4p_n100"), ("alnp", "recp"), ("q4p", "f16p"), ("alnp", "f16p"),
             ("q4p_n100", "q4p"), ("q4p_n300", "q4p")]
    for b in BASES:
        pairs += [("%s_g%s" % (b, v), b) for v in VARS] + [("%s_g%s" % (b, v), "gold") for v in ("a", "s", "p", "asp")]
    pairs += [(b, "gold") for b in BASES]
    res = {"protocol_sha256": psha, "arms": {}, "paired": {}, "integrity": integ, "fit_sizes": fitsizes, "trace": trace, "fit_log": log.as_dict()}
    md = ["# Practical-advantage check, Parts B and C: results", "",
          "Exploratory, development data (style A, saved vectors, `prefix`), level M, 3 arrival seeds, 5 folds, always commit. Protocol hash `%s`. Cloud run." % psha, "",
          "| Arm | What | Missed share | 95% CI (episodes) | Late | Unverified | Incidents |", "|---|---|---|---|---|---|---|"]
    TXT = {"gold": "gold records", "f16p": "FP16 heads", "q4p": "Q4 heads retrained, all FIT labels", "alnp": "FP16 heads on mapped Q4 (no labels for the map)",
           "recp": "FP16 heads on recentred Q4", "rawp": "FP16 heads on raw Q4 (diagnostic)", "q4p_n100": "Q4 heads retrained on 100 labels", "q4p_n300": "Q4 heads retrained on 300 labels"}
    for b in BASES:
        for v in VARS: TXT["%s_g%s" % (b, v)] = "%s with gold %s" % (b, "+".join({"a": "action", "s": "sensor", "p": "priority"}[c] for c in v))
    for arm in ARMS:
        r = table[arm]; lo, hi = devrun.episode_bootstrap_ci(recs, arm)
        res["arms"][arm] = {**{kk: r[kk] for kk in ("episodes", "incidents", "late", "unverified", "U_deadline")}, "ci": [lo, hi]}
        md.append("| %s | %s | %.2f%% | %.2f to %.2f | %d | %d | %d |" % (arm, TXT[arm], 100 * r["U_deadline"], 100 * lo, 100 * hi, r["late"], r["unverified"], r["incidents"]))
    md += ["", "Integrity against the earlier prefix mission run (late, unverified, incidents): " + ("; ".join("%s %s" % (k, "identical" if v["identical"] else "DIFFERENT %s vs %s" % (v["here"], v["earlier"])) for k, v in integ.items()) or "not run (code check)"), "",
           "| Comparison (first minus second, same episodes) | Difference in missed share (pp) | 95% CI | p (sign-flip) | Episodes first better / worse / tied | sd of per-episode difference (missed incidents) |", "|---|---|---|---|---|---|"]
    for x, y in pairs:
        p = devrun.paired(recs, x, y); res["paired"]["%s-%s" % (x, y)] = p
        md.append("| %s minus %s | %+.2f | %+.2f to %+.2f | %.3f | %d / %d / %d | %.2f |" % (x, y, 100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1], p["p_signflip"], p["wins_x"], p["wins_y"], p["ties"], p["sd_episode_diff"]))
    md += ["", "## Which fields are wrong, and does the committed plan differ from the gold plan? (reports counted once per arrival seed)", ""]
    for b in BASES:
        n = sum(v["reports"] for v in trace[b].values())
        md += ["**%s** (%d report decisions)" % (b, n), "", "| Wrong fields (A action, S sensor, P priority; - none) | Reports | Plan differs from gold plan | Table differs from gold table |", "|---|---|---|---|"]
        for p, v in sorted(trace[b].items(), key=lambda kv: -kv[1]["reports"]):
            md.append("| %s | %d | %d (%.0f%%) | %d |" % (p, v["reports"], v["plan_not_gold"], 100 * v["plan_not_gold"] / v["reports"], v["table_not_gold"]))
        md.append("")
    md += ["Fit sizes (reports used to fit maps and heads, per fold): %s." % json.dumps(fitsizes), "Head fits: %s" % json.dumps(log.as_dict()), "Total run time: %.0f s." % (time.time() - t_all)]
    (out / "TRACE_RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
