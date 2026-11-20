"""
Mission-level check of the readout arms (PROTOCOL_MISSION_LADDER.md). Always-commit policies only. Uses the implementation chat's simulator
(edgesar_shield) unchanged: its DevSet, folds, cache, episodes, Sim, CommitPolicy, compact, arm_table, episode_bootstrap_ci and paired.
New readout arms are added in memory to the DevSet object; no file of the package is written.

  python mission_ladder.py --root <folder with edgesar_pilot, edgesar_heads, V1, edgesar_audit_2026-11-13, edgesar_shield> --out out_mission

Writes out_mission/records_<level>_s<seed>.json.gz, MISSION_RESULTS.md, mission_results.json, PROTOCOL_MISSION.sha256.
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np

sys.dont_write_bytecode = True
SEED = 20261113
CACHE_ARMS = ["f16", "q8", "q4", "rec", "raw"]
NEW_ARMS = ["aln", "f16p", "q8p", "q4p", "rawp", "recp", "alnp"]
ARMS = ["gold"] + CACHE_ARMS + NEW_ARMS
TEXT = {"gold": "gold records (reference)", "f16": "FP16 heads, `end` (reference system so far)", "q8": "Q8 heads, `end`", "q4": "Q4 heads refitted on Q4 vectors, `end`",
        "rec": "FP16 heads on recentred Q4, `end`", "raw": "FP16 heads on raw Q4, `end` (frozen)", "aln": "FP16 heads on affine-mapped Q4, `end`",
        "f16p": "FP16 heads, `prefix`", "q8p": "Q8 heads, `prefix`", "q4p": "Q4 heads refitted on Q4 vectors, `prefix`",
        "rawp": "FP16 heads on raw Q4, `prefix` (frozen)", "recp": "FP16 heads on recentred Q4, `prefix`", "alnp": "FP16 heads on affine-mapped Q4, `prefix`"}
PAIRS = [("aln", "q4"), ("aln", "rec"), ("aln", "f16"), ("q4p", "q4"), ("f16p", "f16"), ("alnp", "q4p"), ("alnp", "f16p"), ("q4p", "f16p"),
         ("q4p", "f16"), ("alnp", "f16"), ("rec", "raw"), ("aln", "raw"), ("q4", "f16"), ("q8", "f16"), ("rec", "q4"), ("recp", "q4p"), ("rawp", "f16p"),
         ("q8p", "f16p")]
PKG_ARM = {"gold": "A0", "q4": "A1", "f16": "A2", "q8": "A3", "rec": "A4", "raw": "A5"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--levels", nargs="+", default=["L", "M", "H"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--folds", nargs="+", type=int, default=None)
    ap.add_argument("--max-episodes", type=int, default=None, help="code check only")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    psha = hashlib.sha256((here / "PROTOCOL_MISSION_LADDER.md").read_bytes()).hexdigest()
    (out / "PROTOCOL_MISSION.sha256").write_text(psha + "  PROTOCOL_MISSION_LADDER.md\n", encoding="utf-8")
    os.environ["EDGESAR_ROOT"] = str(root)
    sys.path.insert(0, str(root / "edgesar_shield"))
    from shield import data as sdata, devrun, paths, readout             # noqa: E402
    from shield.alloc import make_allocator                               # noqa: E402
    from shield.candidates import pilot                                   # noqa: E402
    from shield.devset import DevSet, build_service                       # noqa: E402
    from shield.episodes import EPISODE_REPORTS                           # noqa: E402
    from shield.policy import CommitPolicy                                # noqa: E402
    from shield.sim import Sim, SimConfig                                 # noqa: E402
    from ppr_lib import AffineMap, template_key                           # noqa: E402

    t_all = time.time()
    ds = DevSet()
    D = ds.D
    pc = pilot()[0]
    Xe = D.X
    Xp, ids = sdata.load_vectors("prefix")
    assert ids == [c["id"] for c in D.cases]
    tmpl = np.array([template_key(c["text"], pc.LANDMARKS) for c in D.cases])
    log = readout.FitLog()
    folds = a.folds if a.folds is not None else sorted(ds.folds)
    integ = {"refit_vs_cache": {}, "maps": {}}
    # ------------------------------------------------------------------ probabilities of the new arms (FIT only; no labels for the maps)
    for k in folds:
        f = ds.folds[k]
        fit, cal, ev = f["fit"], f["cal"], f["eval"]
        rows = np.concatenate([cal, ev])
        t0 = time.time()
        He = {m: readout.Heads(D.cases, Xe[m], fit, D.group, log) for m in ("f16", "Q4_K_M")}
        chk = {}
        for arm, m in (("f16", "f16"), ("q4", "Q4_K_M")):
            P = He[m].proba(Xe[m][rows])
            chk[arm] = {h: float(np.abs(P[h] - f["P"][arm][h]).max()) for h in P}
            chk[arm]["argmax_changes"] = int(sum((P[h].argmax(1) != f["P"][arm][h].argmax(1)).sum() for h in P))
        integ["refit_vs_cache"][str(k)] = chk
        amap = AffineMap(Xe["f16"][fit], Xe["Q4_K_M"][fit], tmpl[fit], seed=SEED + k)
        f["P"]["aln"] = He["f16"].proba(amap(Xe["Q4_K_M"][rows]))
        Hp = {m: readout.Heads(D.cases, Xp[m], fit, D.group, log) for m in ("f16", "Q8_0", "Q4_K_M")}
        f["P"]["f16p"] = Hp["f16"].proba(Xp["f16"][rows])
        f["P"]["q8p"] = Hp["Q8_0"].proba(Xp["Q8_0"][rows])
        f["P"]["q4p"] = Hp["Q4_K_M"].proba(Xp["Q4_K_M"][rows])
        f["P"]["rawp"] = Hp["f16"].proba(Xp["Q4_K_M"][rows])
        deltap = (Xp["Q4_K_M"][fit] - Xp["f16"][fit]).mean(axis=0)
        f["P"]["recp"] = Hp["f16"].proba(Xp["Q4_K_M"][rows] - deltap)
        amapp = AffineMap(Xp["f16"][fit], Xp["Q4_K_M"][fit], tmpl[fit], seed=SEED + k)
        f["P"]["alnp"] = Hp["f16"].proba(amapp(Xp["Q4_K_M"][rows]))
        integ["maps"][str(k)] = {"n_fit": int(len(fit)), "lambda_end": amap.c, "lambda_prefix": amapp.c,
                                 "err_ratio_end": min(amap.cv_err.values()) / amap.cv_err_recentre_only,
                                 "err_ratio_prefix": min(amapp.cv_err.values()) / amapp.cv_err_recentre_only}
        print("fold %d: heads and maps in %.0f s; refit vs cache max |dP| f16 %.2e q4 %.2e" % (
            k, time.time() - t0, max(chk["f16"][h] for h in ("action", "sensor", "prio")), max(chk["q4"][h] for h in ("action", "sensor", "prio"))), flush=True)
    # ------------------------------------------------------------------ decisions on EVAL (whole-record accuracy; pooled over folds)
    acc = {}
    for arm in CACHE_ARMS + NEW_ARMS:
        ok = n = act = 0
        for k in folds:
            for i in ds.folds[k]["eval"]:
                h = ds.hier(k, arm, int(i))
                n += 1
                ok += pc.strict_key(h) == ds.label_key[int(i)]
                act += h["action"] == ds.label_norm[int(i)]["action"]
        acc[arm] = {"n": n, "record": ok / n, "action": act / n}
    # ------------------------------------------------------------------ missions
    cfg = SimConfig()
    sim = Sim(make_allocator("cbba_bounded"), cfg)
    svc = {k: {arm: build_service(ds, k, arm) for arm in CACHE_ARMS + NEW_ARMS} for k in folds}
    res = {"protocol_sha256": psha, "integrity": integ, "decisions_eval": acc, "levels": {}, "fit_log": log.as_dict()}
    md = ["# Mission-level check of the readout arms: results", "",
          "Exploratory, development data (style A, saved vectors, overlay episodes). Protocol hash `%s`. Always commit; no gate." % psha, ""]
    ref = json.loads((root / "edgesar_shield" / "results" / "dev" / "main" / "DEV_main.json").read_text(encoding="utf-8"))["levels"]
    all_ok = True
    for level in a.levels:
        recs = []
        for seed in a.seeds:
            t0 = time.time()
            srecs = []
            for k in folds:
                eps = ds.make_episodes(ds.folds[k]["eval"], level, seed * 1000 + k, EPISODE_REPORTS)
                if a.max_episodes:
                    eps = eps[:a.max_episodes]
                for e in eps:
                    srecs.append(devrun.compact(sim.run(e, None, "gold", oracle=True), k, level, seed))
                    for arm in CACHE_ARMS + NEW_ARMS:
                        srecs.append(devrun.compact(sim.run(e, CommitPolicy(svc[k][arm]), arm), k, level, seed))
            with gzip.open(out / ("records_%s_s%d.json.gz" % (level, seed)), "wt", encoding="utf-8") as fh:
                json.dump(srecs, fh, separators=(",", ":"))
            recs.extend(srecs)
            print("level %s seed %d: %d records in %.0f s" % (level, seed, len(srecs), time.time() - t0), flush=True)
        table = devrun.arm_table(recs)
        lv = {"arms": {}, "paired": {}, "integrity": {}}
        md.extend(["", "## Level %s" % level, "",
                   "| Arm | What | Missed share (late + unverified) | 95% CI (episodes) | Late | Unverified | Incidents | Wasted trips / report | Distance m / report | Whole record right on EVAL |",
                   "|---|---|---|---|---|---|---|---|---|---|"])
        for arm in ARMS:
            r = table[arm]
            lo, hi = devrun.episode_bootstrap_ci(recs, arm)
            lv["arms"][arm] = {**{kk: r[kk] for kk in ("episodes", "incidents", "late", "unverified", "U_deadline", "wasted_per_report", "distance_per_report_m")}, "ci": [lo, hi]}
            md.append("| %s | %s | %.2f%% | %.2f to %.2f | %d | %d | %d | %.3f | %.0f | %s |" % (
                arm, TEXT[arm], 100 * r["U_deadline"], 100 * lo, 100 * hi, r["late"], r["unverified"], r["incidents"], r["wasted_per_report"],
                r["distance_per_report_m"], "-" if arm == "gold" else "%.1f%%" % (100 * acc[arm]["record"])))
        if not a.max_episodes and a.folds is None and a.seeds == [1, 2, 3] and level in ref:
            for arm, pk in PKG_ARM.items():
                want = ref[level]["arms"][pk]
                same = (table[arm]["late"], table[arm]["unverified"], table[arm]["incidents"]) == (want["late"], want["unverified"], want["incidents"])
                lv["integrity"][arm] = {"package_arm": pk, "identical": bool(same), "here": [table[arm]["late"], table[arm]["unverified"], table[arm]["incidents"]],
                                        "package": [want["late"], want["unverified"], want["incidents"]]}
                all_ok &= same
            md.append("")
            md.append("Integrity against the package's own results (late, unverified, incidents): " + "; ".join(
                "%s=%s %s" % (arm, v["package_arm"], "identical" if v["identical"] else "DIFFERENT %s vs %s" % (v["here"], v["package"])) for arm, v in lv["integrity"].items()))
        md.extend(["", "| Comparison (first minus second, same episodes) | Difference in missed share (pp) | 95% CI | p (sign-flip) | Episodes won first / second / tied |", "|---|---|---|---|---|"])
        for x, y in PAIRS:
            p = devrun.paired(recs, x, y)
            lv["paired"]["%s-%s" % (x, y)] = p
            md.append("| %s minus %s | %+.2f | %+.2f to %+.2f | %.3f | %d / %d / %d |" % (x, y, 100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1], p["p_signflip"],
                                                                                   p["wins_x"], p["wins_y"], p["ties"]))
        res["levels"][level] = lv
    res["integrity"]["package_counts_identical"] = bool(all_ok)
    md.extend(["", "## Integrity and settings", "",
               "* Package counts reproduced for gold, q4, f16, q8, rec, raw at every level: **%s**." % ("PASS" if all_ok else "FAIL - the run is void"),
               "* Heads refitted here against the cache (max absolute probability difference; changed argmax over the three heads): " + "; ".join(
                   "fold %s f16 %.1e / %d, q4 %.1e / %d" % (k, max(v["f16"][h] for h in ("action", "sensor", "prio")), v["f16"]["argmax_changes"],
                                                            max(v["q4"][h] for h in ("action", "sensor", "prio")), v["q4"]["argmax_changes"])
                   for k, v in integ["refit_vs_cache"].items()),
               "* Affine maps (FIT pairs only): " + "; ".join("fold %s n=%d, lambda %s / %s, held-out error ratio %.3f (`end`) / %.3f (`prefix`)" % (
                   k, v["n_fit"], v["lambda_end"], v["lambda_prefix"], v["err_ratio_end"], v["err_ratio_prefix"]) for k, v in integ["maps"].items()),
               "* Head fits: %s" % json.dumps(log.as_dict()),
               "* Total run time: %.0f s." % (time.time() - t_all)])
    (out / "MISSION_RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "mission_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
