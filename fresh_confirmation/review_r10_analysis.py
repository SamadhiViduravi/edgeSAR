"""
R10 analysis (exploratory; 25 Nov 2026): summaries of the label-free mission check written by review_r10.py.

Reads out_review/review_results_r10.json (one row per candidate, set and load) and out_review/review_results_r10_episodes.json
(per-episode missed and incident counts of every arm under gold truth and under the referee truth) and writes
out_review/review_results_r10_analysis.json with:
  1. per condition (set x load): rank correlation with the true penalty of the referee and of three record-level proxies
     (disagreement with the old records in any field, in the sensor field, and the whole-record accuracy drop against gold labels),
     for all 36 candidates and for the 34 hidden-state candidates, by candidate family, and pairwise ordering
     (share of candidate pairs whose true penalties differ by more than 0.5 pp that each measure orders correctly);
  2. the referee's overestimate (referee minus true penalty);
  3. selection: the candidate with the smallest referee penalty among the label-free options (unchanged, recentering, map) and among
     all hidden-state candidates, against the candidate with the smallest true penalty;
  4. an episode bootstrap (2,000 resamples) of the referee's rank correlation;
  5. how many unlabeled reports the check needs: the referee computed on random subsets of k episodes (about 20 reports each) of
     set A, compared with the true penalties on all 300 episodes (1,000 subsets per k and load).

    python review_r10_analysis.py --out out_review
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

LEVELS = ("L", "M", "H")
PAIR_PP = 0.5
LABEL_FREE = ("rawp", "recp", "alnp")
TEXT = ("tfidf", "rule")


def family(arm):
    if arm in TEXT:
        return "text"
    if arm.startswith("q4p"):
        return "retrained"
    return "fp16_derived"          # unchanged, recentred, map, bias recalibration, vector scaling


def rho(x, y):
    return float(spearmanr(x, y)[0])


def concordance(sel, key):
    ok = tot = 0
    for i in range(len(sel)):
        for j in range(i + 1, len(sel)):
            dt = sel[i]["true_pp"] - sel[j]["true_pp"]
            if abs(dt) <= PAIR_PP:
                continue
            tot += 1
            ok += (dt * (sel[i][key] - sel[j][key]) > 0)
    return {"correct": ok, "pairs": tot, "share": ok / tot if tot else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out_review")
    a = ap.parse_args()
    out = Path(a.out)
    res = json.loads((out / "review_results_r10.json").read_text())
    eps = json.loads((out / "review_results_r10_episodes.json").read_text())["levels"]
    for t in eps.values():
        t["missed"] = {k: np.asarray(v, dtype=float) for k, v in t["missed"].items()}
        t["n"] = np.asarray(t["n"], dtype=float)
    cands = res["candidates"]
    rows = res["rows"]
    hs = [c for c in cands if c not in TEXT]

    def pen(st, lev, idx=None):
        g, r = eps["%s_%s_gold" % (st, lev)], eps["%s_%s_referee" % (st, lev)]

        def sh(t, arm):
            m, n = np.asarray(t["missed"][arm]), np.asarray(t["n"])
            if idx is not None:
                m, n = m[idx], n[idx]
            return 100.0 * m.sum() / n.sum()
        bt, br = sh(g, "f16p"), sh(r, "f16p")
        return {c: sh(g, c) - bt for c in cands}, {c: sh(r, c) - br for c in cands}

    # sanity: the per-episode counts reproduce the rows
    for x in rows:
        tp, rp = pen(x["set"], x["level"])
        assert abs(tp[x["arm"]] - x["true_pp"]) < 1e-9 and abs(rp[x["arm"]] - x["referee_pp"]) < 1e-9

    keys = ("referee_pp", "disagree_any", "disagree_sensor", "accuracy_drop")
    A = {"note": "R10 analysis, exploratory, 25 Nov 2026", "pair_threshold_pp": PAIR_PP, "conditions": {}}
    rng = np.random.default_rng(20261125)
    for st in ("A", "B"):
        for lev in LEVELS:
            sel = [x for x in rows if x["set"] == st and x["level"] == lev]
            byarm = {x["arm"]: x for x in sel}
            c = {"n_candidates": len(sel), "episodes": len(eps["%s_%s_gold" % (st, lev)]["n"]),
                 "incidents_gold": float(np.sum(eps["%s_%s_gold" % (st, lev)]["n"]))}
            t_all = [x["true_pp"] for x in sel]
            c["spearman_all"] = {k: rho([x[k] for x in sel], t_all) for k in keys}
            hsel = [byarm[h] for h in hs]
            c["spearman_hidden_state"] = {k: rho([x[k] for x in hsel], [x["true_pp"] for x in hsel]) for k in keys}
            for fam in ("fp16_derived", "retrained"):
                fs = [x for x in sel if family(x["arm"]) == fam]
                c["spearman_" + fam] = {"n": len(fs), **{k: rho([x[k] for x in fs], [x["true_pp"] for x in fs]) for k in keys}}
            c["pairwise_all"] = {k: concordance(sel, k) for k in keys}
            over = np.array([x["referee_pp"] - x["true_pp"] for x in sel])
            over_hs = np.array([x["referee_pp"] - x["true_pp"] for x in hsel])
            c["overestimate_pp"] = {"mean": float(over.mean()), "min": float(over.min()), "max": float(over.max()),
                                    "mean_hidden_state": float(over_hs.mean()), "min_hidden_state": float(over_hs.min()),
                                    "max_hidden_state": float(over_hs.max()), "rows_referee_below_true": int((over < 0).sum())}
            pick_lf = min(LABEL_FREE, key=lambda h: byarm[h]["referee_pp"])
            best_lf = min(LABEL_FREE, key=lambda h: byarm[h]["true_pp"])
            pick_hs = min(hs, key=lambda h: byarm[h]["referee_pp"])
            best_hs = min(hs, key=lambda h: byarm[h]["true_pp"])
            c["selection"] = {"label_free_pick": pick_lf, "label_free_best": best_lf,
                              "hidden_state_pick": pick_hs, "hidden_state_pick_true_pp": byarm[pick_hs]["true_pp"],
                              "hidden_state_best": best_hs, "hidden_state_best_true_pp": byarm[best_hs]["true_pp"],
                              "hidden_state_regret_pp": byarm[pick_hs]["true_pp"] - byarm[best_hs]["true_pp"]}
            # episode bootstrap of the referee's rank correlation (true and referee penalties recomputed on the same resample)
            ne = c["episodes"]
            boots = []
            for _ in range(2000):
                idx = rng.integers(0, ne, ne)
                tp, rp = pen(st, lev, idx)
                boots.append(rho([rp[h] for h in cands], [tp[h] for h in cands]))
            c["referee_spearman_bootstrap95"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
            A["conditions"]["%s_%s" % (st, lev)] = c

    # how many unlabeled reports: referee on k random episodes of set A against the true penalties on all episodes
    sub = {}
    for lev in LEVELS:
        tp_full, _ = pen("A", lev)
        ne = len(eps["A_%s_gold" % lev]["n"])
        for k in (5, 10, 25, 50, 100):
            rs, lf_ok, regret = [], 0, []
            for _ in range(1000):
                idx = rng.choice(ne, k, replace=False)
                _, rp = pen("A", lev, idx)
                rs.append(rho([rp[h] for h in cands], [tp_full[h] for h in cands]))
                lf_ok += min(LABEL_FREE, key=lambda h: rp[h]) == min(LABEL_FREE, key=lambda h: tp_full[h])
                ph = min(hs, key=lambda h: rp[h])
                regret.append(tp_full[ph] - min(tp_full[h] for h in hs))
            sub["%s_k%d" % (lev, k)] = {"episodes": k, "reports_approx": 20 * k, "spearman_median": float(np.median(rs)),
                                        "spearman_p05": float(np.percentile(rs, 5)), "label_free_pick_correct": lf_ok / 1000,
                                        "hidden_state_regret_median_pp": float(np.median(regret)),
                                        "hidden_state_regret_p95_pp": float(np.percentile(regret, 95)),
                                        "hidden_state_regret_le_025pp": float(np.mean(np.array(regret) <= 0.25))}
    A["subsets_set_A"] = sub
    (out / "review_results_r10_analysis.json").write_text(json.dumps(A, indent=1), encoding="utf-8")
    for k, c in A["conditions"].items():
        print(k, {kk: round(v, 3) for kk, v in c["spearman_all"].items()}, "boot", [round(x, 3) for x in c["referee_spearman_bootstrap95"]],
              "over", round(c["overestimate_pp"]["mean"], 2), c["selection"]["label_free_pick"], c["selection"]["hidden_state_pick"],
              round(c["selection"]["hidden_state_regret_pp"], 2))
    for k, v in sub.items():
        print(k, round(v["spearman_median"], 3), round(v["spearman_p05"], 3), v["label_free_pick_correct"], round(v["hidden_state_regret_median_pp"], 2),
              round(v["hidden_state_regret_p95_pp"], 2), v["hidden_state_regret_le_025pp"])


if __name__ == "__main__":
    main()
