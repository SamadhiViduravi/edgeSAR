"""
Iteration 2 analysis (docs/ITERATION2_PROTOCOL.md): do the importance-matrix Q4 files and Q5 reduce the remaining Q4 decision gap?

    python tools/analyze_iter2.py --features results/iter2/features
Reads vectors for KEYS (Q4_IMX_DOMAIN, Q4_IMX_GENERIC, Q5) at `end` and `prefix`, fits MATCHED and ALIGNED readouts per outer fold on FIT reports only,
runs always-commit missions (levels L/M/H, seeds 1-3) and applies the decision rule of the protocol. Writes results/iter2/ITER2_RESULTS.md/.json.
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tools")); sys.dont_write_bytecode = True
from shield import data as sdata, devrun, readout                    # noqa: E402
from shield.alloc import make_allocator                                # noqa: E402
from shield.candidates import pilot                                    # noqa: E402
from shield.devset import DevSet, build_service                        # noqa: E402
from shield.episodes import EPISODE_REPORTS                            # noqa: E402
from shield.policy import CommitPolicy                                 # noqa: E402
from shield.sim import Sim, SimConfig                                  # noqa: E402
from verify_alignment import MyMap                                     # noqa: E402

KEYS = ["Q4_IMX_DOMAIN", "Q4_IMX_GENERIC", "Q5", "Q4_IMX_DOMAIN_M"]
SHORT = {"Q4_IMX_DOMAIN": "dom", "Q4_IMX_GENERIC": "gen", "Q5": "q5", "Q4_IMX_DOMAIN_M": "dx"}   # dx = Amendment 1 control (matched chunk budget)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=str(HERE / "results" / "iter2" / "features"))
    ap.add_argument("--out", default=str(HERE / "results" / "iter2"))
    ap.add_argument("--levels", nargs="+", default=["L", "M", "H"]); ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--folds", nargs="+", type=int, default=None); ap.add_argument("--max-episodes", type=int, default=None)
    ap.add_argument("--no-protocol-check", action="store_true", help="tests only")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    psha = hashlib.sha256((HERE / "docs" / "ITERATION2_PROTOCOL.md").read_bytes()).hexdigest()
    if not a.no_protocol_check:
        want = (HERE / "results" / "ITER2_PROTOCOL.sha256").read_text().split()[0]
        if psha != want:
            sys.exit("protocol changed after hashing. Stop.")
        ah = hashlib.sha256((HERE / "docs" / "ITERATION2_AMENDMENT1.md").read_bytes()).hexdigest()
        if ah != (HERE / "results" / "ITER2_AMENDMENT1.sha256").read_text().split()[0]:
            sys.exit("amendment 1 changed after hashing. Stop.")
    fdir = Path(a.features); t_all = time.time()
    keys = [k for k in KEYS if (fdir / ("%s_end.npy" % k)).exists() and (fdir / ("%s_prefix.npy" % k)).exists()]
    print("variants found:", keys, flush=True)
    ds = DevSet(); D = ds.D; pc = pilot()[0]
    Xe = {"f16": D.X["f16"], "q4": D.X["Q4_K_M"]}
    Xp_all, ids = sdata.load_vectors("prefix"); assert ids == [c["id"] for c in D.cases]
    Xp = {"f16": Xp_all["f16"], "q4": Xp_all["Q4_K_M"]}
    for k in keys:
        for pos, X in (("end", Xe), ("prefix", Xp)):
            v = np.load(fdir / ("%s_%s.npy" % (k, pos))).astype(np.float64)
            assert v.shape == (len(D.cases), 2048) and np.isfinite(v).all(), (k, pos, v.shape)
            X[k] = v
    log = readout.FitLog(); folds = a.folds if a.folds is not None else sorted(ds.folds)
    ARMS = ["f16p", "q4p", "q4a", "q4ap"]            # f16 end = cache 'f16', q4 end = cache 'q4'
    for k in keys:
        s = SHORT[k]; ARMS += [s + "m", s + "mp", s + "a", s + "ap"]
    check = {}
    for fk in folds:
        f = ds.folds[fk]; fit = f["fit"]; rows = np.concatenate([f["cal"], f["eval"]])
        grp = np.array([D.group[i] for i in fit]); t0 = time.time()
        H = {"e": readout.Heads(D.cases, Xe["f16"], fit, D.group, log), "p": readout.Heads(D.cases, Xp["f16"], fit, D.group, log)}
        f["P"]["f16p"] = H["p"].proba(Xp["f16"][rows])
        for name, src in [("q4", "q4")] + [(SHORT[k], k) for k in keys]:
            pre = "q4" if name == "q4" else name
            mm = readout.Heads(D.cases, Xe[src], fit, D.group, log); mp = readout.Heads(D.cases, Xp[src], fit, D.group, log)
            ae = MyMap(Xe["f16"][fit], Xe[src][fit], grp); ap_ = MyMap(Xp["f16"][fit], Xp[src][fit], grp)
            if name == "q4":
                f["P"]["q4p"] = mp.proba(Xp[src][rows]); f["P"]["q4a"] = H["e"].proba(ae(Xe[src][rows])); f["P"]["q4ap"] = H["p"].proba(ap_(Xp[src][rows]))
            else:
                f["P"][name + "m"] = mm.proba(Xe[src][rows]); f["P"][name + "mp"] = mp.proba(Xp[src][rows])
                f["P"][name + "a"] = H["e"].proba(ae(Xe[src][rows])); f["P"][name + "ap"] = H["p"].proba(ap_(Xp[src][rows]))
        print("fold %d fitted in %.0f s" % (fk, time.time() - t0), flush=True)
    acc = {}
    for arm in ["f16", "q4"] + ARMS:
        ok = n = 0
        for fk in folds:
            for i in ds.folds[fk]["eval"]:
                n += 1; ok += pc.strict_key(ds.hier(fk, arm, int(i))) == ds.label_key[int(i)]
        acc[arm] = ok / n
    MA = ["f16", "q4"] + ARMS
    sim = Sim(make_allocator("cbba_bounded"), SimConfig())
    svc = {fk: {arm: build_service(ds, fk, arm) for arm in MA} for fk in folds}
    ref = json.loads((HERE / "results" / "dev" / "main" / "DEV_main.json").read_text())["levels"]
    res = {"protocol_sha256": psha, "variants": keys, "decisions_eval": acc, "levels": {}, "fit_log": log.as_dict()}
    full = a.folds is None and a.max_episodes is None and a.seeds == [1, 2, 3]
    ok_int = True
    for level in a.levels:
        recs = []
        for seed in a.seeds:
            for fk in folds:
                eps = ds.make_episodes(ds.folds[fk]["eval"], level, seed * 1000 + fk, EPISODE_REPORTS)
                if a.max_episodes: eps = eps[:a.max_episodes]
                for e in eps:
                    recs.append(devrun.compact(sim.run(e, None, "gold", oracle=True), fk, level, seed))
                    for arm in MA: recs.append(devrun.compact(sim.run(e, CommitPolicy(svc[fk][arm]), arm), fk, level, seed))
        table = devrun.arm_table(recs); lv = {"arms": {}, "paired": {}}
        for arm in ["gold"] + MA:
            r = table[arm]; lo, hi = devrun.episode_bootstrap_ci(recs, arm)
            lv["arms"][arm] = {"missed": r["U_deadline"], "ci": [lo, hi], "late": r["late"], "unverified": r["unverified"], "incidents": r["incidents"]}
        if full and level in ref:
            for arm, pk in {"gold": "A0", "q4": "A1", "f16": "A2"}.items():
                w = ref[level]["arms"][pk]; ok_int &= (table[arm]["late"], table[arm]["unverified"], table[arm]["incidents"]) == (w["late"], w["unverified"], w["incidents"])
        pairs = [("q4p", "f16p"), ("q4", "f16"), ("q4a", "q4"), ("q4ap", "q4p")]
        for k in keys:
            s = SHORT[k]
            pairs += [(s + "mp", "q4p"), (s + "m", "q4"), (s + "ap", "q4ap"), (s + "a", "q4a"), (s + "mp", "f16p"), (s + "ap", "f16p"), (s + "m", "f16"), (s + "a", "f16")]
        if "dom" in [SHORT[k] for k in keys] and "gen" in [SHORT[k] for k in keys]:
            pairs += [("dommp", "genmp"), ("domm", "genm"), ("domap", "genap")]
        if "dx" in [SHORT[k] for k in keys] and "gen" in [SHORT[k] for k in keys]:
            pairs += [("dxmp", "genmp"), ("dxm", "genm"), ("dxap", "genap")]
        if "dx" in [SHORT[k] for k in keys] and "dom" in [SHORT[k] for k in keys]:
            pairs += [("dommp", "dxmp"), ("domm", "dxm")]
        if "q5" in [SHORT[k] for k in keys]:
            pairs += [("q5mp", "q4p"), ("q5m", "q4")]
        for x, y in pairs:
            if x in table and y in table: lv["paired"]["%s-%s" % (x, y)] = devrun.paired(recs, x, y)
        res["levels"][level] = lv
        print(level, {k_: round(100 * v["missed"], 2) for k_, v in lv["arms"].items()}, flush=True)
    res["integrity_package_counts"] = bool(ok_int) if full else "not checked (partial run)"
    # decision rule (protocol section 5)
    L = res["levels"]
    if "dom" in [SHORT[k] for k in keys] and all(l in L for l in ("L", "M", "H")):
        pM = L["M"]["paired"]["dommp-q4p"]; gap = L["M"]["paired"]["q4p-f16p"]["diff_U"]
        cond = [pM["ci"][1] < 0, L["L"]["paired"]["dommp-q4p"]["diff_U"] <= 0, L["H"]["paired"]["dommp-q4p"]["diff_U"] <= 0, gap > 0 and -pM["diff_U"] >= 0.5 * gap]
        res["rule"] = {"conditions": {"ci_upper_below_0_at_M": cond[0], "point_le_0_at_L": cond[1], "point_le_0_at_H": cond[2], "at_least_half_of_gap": cond[3]},
                       "diff_M_pp": 100 * pM["diff_U"], "ci_M_pp": [100 * pM["ci"][0], 100 * pM["ci"][1]], "gap_q4p_minus_f16p_M_pp": 100 * gap, "label": "SUPPORTED on DEV" if all(cond) else "NOT SHOWN"}
        if "gen" in [SHORT[k] for k in keys]:
            pg = L["M"]["paired"]["dommp-genmp"]; res["rule"]["in_domain_vs_generic_M_budgets_differ"] = {"diff_pp": 100 * pg["diff_U"], "ci_pp": [100 * pg["ci"][0], 100 * pg["ci"][1]], "note": "in-domain text is about 2.7x longer than generic; not enough alone to claim 'in-domain'"}
            if "dx" in [SHORT[k] for k in keys]:
                pm = L["M"]["paired"]["dxmp-genmp"]; res["rule"]["in_domain_vs_generic_M_matched"] = {"diff_pp": 100 * pm["diff_U"], "ci_pp": [100 * pm["ci"][0], 100 * pm["ci"][1]], "in_domain_matters": bool(pm["ci"][1] < 0)}
                pt = L["M"]["paired"]["dommp-dxmp"]; res["rule"]["more_text_effect_M"] = {"diff_pp": 100 * pt["diff_U"], "ci_pp": [100 * pt["ci"][0], 100 * pt["ci"][1]]}
            else:
                res["rule"]["in_domain_vs_generic_M_matched"] = "control file missing: comparison incomplete"
    res["seconds"] = round(time.time() - t_all)
    (out / "ITER2_RESULTS.json").write_text(json.dumps(res, indent=1, default=float))
    md = ["# Iteration 2 results (development data, model-side round)", "", "Protocol hash `%s`. Always commit; no gate. Pooled intervals are optimistic (seeds reuse reports)." % psha, ""]
    for level in a.levels:
        md += ["## Level %s" % level, "", "| arm | missed share | 95% CI | late | unverified |", "|---|---|---|---|---|"]
        for arm, v in res["levels"][level]["arms"].items():
            md.append("| %s | %.2f%% | %.2f to %.2f | %d | %d |" % (arm, 100 * v["missed"], 100 * v["ci"][0], 100 * v["ci"][1], v["late"], v["unverified"]))
        md += ["", "| paired (first minus second) | pp | 95% CI | p |", "|---|---|---|---|"]
        for kx, p in res["levels"][level]["paired"].items():
            md.append("| %s | %+.2f | %+.2f to %+.2f | %.3f |" % (kx, 100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1], p["p_signflip"]))
        md.append("")
    md += ["## Whole-record accuracy on EVAL", ""] + ["* %s: %.1f%%" % (k, 100 * v) for k, v in acc.items()]
    if "rule" in res: md += ["", "## Decision rule", "", "```", json.dumps(res["rule"], indent=1), "```"]
    (out / "ITER2_RESULTS.md").write_text("\n".join(md) + "\n")
    print(json.dumps(res.get("rule", {}), indent=1)); print("done", res["seconds"], "s")


if __name__ == "__main__":
    main()
