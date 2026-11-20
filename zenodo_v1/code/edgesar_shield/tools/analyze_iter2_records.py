"""
Iteration 2, record-level analysis required by docs/ITERATION2_PROTOCOL.md section 4 (secondary outcome: whole-record accuracy, repaired / newly wrong
counts relative to plain Q4) plus correction precision, net change and family-clustered uncertainty.  Same fitting code, models, splits and settings
as tools/analyze_iter2.py (no missions here).  Status of every number: SECONDARY (protocol section 4), not the primary test.

    python tools/analyze_iter2_records.py
Writes results/iter2/ITER2_RECORDS.md/.json and results/iter2/record_correct.npz (per-record right/wrong for every arm).
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tools")); sys.dont_write_bytecode = True
from shield import data as sdata, readout                              # noqa: E402
from shield.candidates import pilot                                    # noqa: E402
from shield.devset import DevSet                                       # noqa: E402
from verify_alignment import MyMap                                     # noqa: E402
from analyze_iter2 import KEYS, SHORT                                  # noqa: E402


def exact_mcnemar(b, c):
    from math import comb
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=str(HERE / "results" / "iter2" / "features"))
    ap.add_argument("--out", default=str(HERE / "results" / "iter2"))
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args()
    out = Path(a.out)
    want = (HERE / "results" / "ITER2_PROTOCOL.sha256").read_text().split()[0]
    psha = hashlib.sha256((HERE / "docs" / "ITERATION2_PROTOCOL.md").read_bytes()).hexdigest()
    assert psha == want, "protocol changed after hashing"
    fdir = Path(a.features); t_all = time.time()
    keys = [k for k in KEYS if (fdir / ("%s_end.npy" % k)).exists() and (fdir / ("%s_prefix.npy" % k)).exists()]
    ds = DevSet(); D = ds.D; pc = pilot()[0]
    Xe = {"f16": D.X["f16"], "q4": D.X["Q4_K_M"]}
    Xp_all, ids = sdata.load_vectors("prefix"); assert ids == [c["id"] for c in D.cases]
    Xp = {"f16": Xp_all["f16"], "q4": Xp_all["Q4_K_M"]}
    for k in keys:
        for pos, X in (("end", Xe), ("prefix", Xp)):
            X[k] = np.load(fdir / ("%s_%s.npy" % (k, pos))).astype(np.float64)
    log = readout.FitLog(); folds = sorted(ds.folds)
    ARMS = ["f16p", "q4p", "q4a", "q4ap"]
    for k in keys:
        s = SHORT[k]; ARMS += [s + "m", s + "mp", s + "a", s + "ap"]
    for fk in folds:
        f = ds.folds[fk]; fit = f["fit"]; rows = np.concatenate([f["cal"], f["eval"]])
        grp = np.array([D.group[i] for i in fit]); t0 = time.time()
        H = {"e": readout.Heads(D.cases, Xe["f16"], fit, D.group, log), "p": readout.Heads(D.cases, Xp["f16"], fit, D.group, log)}
        f["P"]["f16p"] = H["p"].proba(Xp["f16"][rows])
        for name, src in [("q4", "q4")] + [(SHORT[k], k) for k in keys]:
            mm = readout.Heads(D.cases, Xe[src], fit, D.group, log); mp = readout.Heads(D.cases, Xp[src], fit, D.group, log)
            ae = MyMap(Xe["f16"][fit], Xe[src][fit], grp); ap_ = MyMap(Xp["f16"][fit], Xp[src][fit], grp)
            if name == "q4":
                f["P"]["q4p"] = mp.proba(Xp[src][rows]); f["P"]["q4a"] = H["e"].proba(ae(Xe[src][rows])); f["P"]["q4ap"] = H["p"].proba(ap_(Xp[src][rows]))
            else:
                f["P"][name + "m"] = mm.proba(Xe[src][rows]); f["P"][name + "mp"] = mp.proba(Xp[src][rows])
                f["P"][name + "a"] = H["e"].proba(ae(Xe[src][rows])); f["P"][name + "ap"] = H["p"].proba(ap_(Xp[src][rows]))
        print("fold %d fitted in %.0f s" % (fk, time.time() - t0), flush=True)
    ALL = ["f16", "q4"] + ARMS
    idx, grp_of, correct = [], [], {arm: [] for arm in ALL}
    for fk in folds:
        for i in ds.folds[fk]["eval"]:
            i = int(i); idx.append(i); grp_of.append(D.group[i])
            for arm in ALL:
                correct[arm].append(bool(pc.strict_key(ds.hier(fk, arm, i)) == ds.label_key[i]))
    idx = np.array(idx); grp_of = np.array(grp_of); C = {k: np.array(v, bool) for k, v in correct.items()}
    n = len(idx); assert n == len(set(idx.tolist()))
    np.savez_compressed(out / "record_correct.npz", idx=idx, group=grp_of, **C)
    # integrity: same whole-record accuracies as ITER2_RESULTS.json
    prev = json.loads((out / "ITER2_RESULTS.json").read_text())["decisions_eval"]
    integ = {k: (abs(C[k].mean() - prev[k]) < 1e-9) for k in ALL}
    print("integrity (accuracies equal to the mission run):", all(integ.values()), flush=True)
    ug = np.unique(grp_of); gi = {g: np.where(grp_of == g)[0] for g in ug}
    rng = np.random.default_rng(20261114)
    boots = [rng.integers(0, len(ug), len(ug)) for _ in range(a.boot)]

    def cluster_ci(delta):
        s = np.array([delta[gi[g]].sum() for g in ug], float); m = np.array([len(gi[g]) for g in ug], float)
        est = s.sum() / m.sum()
        bs = np.array([s[b].sum() / m[b].sum() for b in boots])
        return est, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

    def cmp(x, y):
        cx, cy = C[x], C[y]
        rep = int((~cy & cx).sum()); nw = int((cy & ~cx).sum())
        est, lo, hi = cluster_ci(cx.astype(float) - cy.astype(float))
        return {"x": x, "ref": y, "acc_x": float(cx.mean()), "acc_ref": float(cy.mean()), "repaired": rep, "newly_wrong": nw, "net": rep - nw,
                "precision_repaired_over_changed": (rep / (rep + nw)) if rep + nw else None, "diff_pp": 100 * est, "ci_pp_cluster": [100 * lo, 100 * hi],
                "p_mcnemar_exact": exact_mcnemar(rep, nw)}
    rows = []
    for k in keys:
        s = SHORT[k]
        rows += [cmp(s + "mp", "q4p"), cmp(s + "ap", "q4ap"), cmp(s + "m", "q4"), cmp(s + "a", "q4a")]
    rows += [cmp("q4ap", "q4p"), cmp("q4a", "q4"), cmp("q4p", "f16p"), cmp("q4", "f16"),
             cmp("dommp", "genmp"), cmp("dxmp", "genmp"), cmp("dommp", "dxmp"), cmp("domm", "genm"), cmp("dxm", "genm"), cmp("domm", "dxm"),
             cmp("dommp", "f16p"), cmp("genmp", "f16p"), cmp("dxmp", "f16p"), cmp("q5mp", "f16p"), cmp("q5ap", "f16p")]
    res = {"protocol_sha256": psha, "n_records": n, "n_family_groups": int(len(ug)), "integrity_equal_to_mission_run": bool(all(integ.values())),
           "bootstrap": "cluster bootstrap over families (D.group), 10000 resamples, seed 20261114", "comparisons": rows, "seconds": round(time.time() - t_all)}
    (out / "ITER2_RECORDS.json").write_text(json.dumps(res, indent=1))
    md = ["# Iteration 2: whole-record results (secondary outcome, protocol section 4)", "",
          "Status: SECONDARY. The primary mission-level verdict stays NOT SHOWN. %d records, %d family clusters. Intervals: cluster bootstrap over families (records of one family are not independent). "
          "McNemar p is exact and treats records as independent, so it is optimistic. Precision = repaired / (repaired + newly wrong). Reference = plain Q4 at the same position and readout unless the second name says otherwise. "
          "Integrity (accuracies equal to the mission run): %s." % (n, len(ug), res["integrity_equal_to_mission_run"]), "",
          "| arm | ref | acc arm | acc ref | repaired | newly wrong | net | precision | diff pp | 95% CI (cluster) | McNemar p |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append("| %s | %s | %.1f | %.1f | %d | %d | %+d | %s | %+.2f | %+.2f to %+.2f | %.3f |" % (r["x"], r["ref"], 100 * r["acc_x"], 100 * r["acc_ref"], r["repaired"], r["newly_wrong"], r["net"],
              ("%.2f" % r["precision_repaired_over_changed"]) if r["precision_repaired_over_changed"] is not None else "-", r["diff_pp"], r["ci_pp_cluster"][0], r["ci_pp_cluster"][1], r["p_mcnemar_exact"]))
    (out / "ITER2_RECORDS.md").write_text("\n".join(md) + "\n")
    print("done", res["seconds"], "s")


if __name__ == "__main__":
    main()
