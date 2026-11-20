"""
M4 report: heads, candidate enumeration and conformal coverage on the development set (saved vectors, style A, 5 outer folds).

Acceptance (plan section 9, M4): enumeration gives at most 20 combinations and counts missing candidates; coverage on the hold-out
(EVAL) lies within the binomial 95% band of 1 - alpha.   Run:  python tools/m4_report.py
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                               # noqa: E402

from shield import paths                                         # noqa: E402
from shield.candidates import COMBOS                             # noqa: E402
from shield.devset import ARMS, DevSet                           # noqa: E402

K_MAX = 8
ALPHAS = (0.05, 0.10, 0.20)


def band(p, n):
    h = 1.959964 * math.sqrt(p * (1 - p) / n)
    return p - h, p + h


def main():
    ds = DevSet()
    pc = __import__("shield.candidates", fromlist=["pilot"]).pilot()[0]
    res = {"n_combinations_max": len(COMBOS), "arms": {}, "fit_log": ds.fit_log}
    lines = ["# M4 report: heads, candidates, conformal sets (development set, saved vectors)", "",
             "Style A only; 5 outer folds (EVAL 200, CAL 200, FIT about 515 after removing exact duplicates of CAL/EVAL reports). "
             "Heads: standardise + logistic regression, C by grouped CV inside FIT, tol 1e-6.", ""]
    lines.append("Head fits: %s" % json.dumps(ds.fit_log))
    lines.append("")

    # --- head accuracy per arm (EVAL reports, hierarchical record = what A1-A5 commit)
    lines += ["## Readout accuracy on EVAL (pooled over the 5 folds, n = 1000)", "",
              "| Arm | action correct | whole record correct | gold record expressible by heads+parser |", "|---|---|---|---|"]
    for arm in ARMS:
        a_ok = r_ok = expr = n = 0
        for k, f in ds.folds.items():
            for i in f["eval"]:
                i = int(i)
                e = ds.enum[i]
                h = ds.hier(k, arm, i)
                a_ok += h["action"] == ds.cases[i]["gold"]["action"]
                r_ok += pc.strict_key(h) == ds.label_key[i]
                expr += ds.cands(k, arm, i) and any(c["key"] == ds.label_key[i] for c in ds.cands(k, arm, i))
                n += 1
        res["arms"].setdefault(arm, {})["readout"] = {"n": n, "action_correct": a_ok / n, "record_correct": r_ok / n, "expressible": expr / n}
        lines.append("| %s | %.1f%% | %.1f%% | %.1f%% |" % (arm, 100 * a_ok / n, 100 * r_ok / n, 100 * expr / n))
    lines.append("")

    # --- enumeration facts (q4)
    sizes = Counter()
    missing_cases = []
    for k, f in ds.folds.items():
        for i in list(f["cal"]) + list(f["eval"]):
            i = int(i)
            c = ds.cands(k, "q4", i)
            sizes[len(c)] += 1
            if not any(x["key"] == ds.label_key[i] for x in c):
                missing_cases.append(i)
    tot = sum(sizes.values())
    res["enumeration"] = {"distinct_candidates_per_report": {str(k): v for k, v in sorted(sizes.items())},
                          "reports_with_gold_missing": len(set(missing_cases)), "reports": 2 * 1000}
    lines += ["## Enumeration (Q4 heads)", "",
              "At most %d combinations per report (the plan's 22 counts CREATE and UPDATE twice). Distinct merged candidates per report: %s." %
              (len(COMBOS), dict(sorted(sizes.items()))),
              "Reports (CAL and EVAL roles together, %d rows) whose gold record the heads + parser cannot express: %d unique reports." %
              (tot, len(set(missing_cases))), ""]
    miss_types = Counter(ds.cases[i]["gold"]["action"] for i in set(missing_cases))
    lines.append("By gold action: %s." % dict(miss_types))
    lines.append("")

    # --- top vs hier
    diff = tot_e = 0
    diff_gold = []
    for k, f in ds.folds.items():
        for i in f["eval"]:
            i = int(i)
            c = ds.cands(k, "q4", i)
            h = ds.hier(k, "q4", i)
            tot_e += 1
            if pc.strict_key(h) != c[0]["key"]:
                diff += 1
                diff_gold.append((pc.strict_key(h) == ds.label_key[i], c[0]["key"] == ds.label_key[i]))
    both = Counter(diff_gold)
    res["top_vs_hier"] = {"differ": diff, "n": tot_e, "hier_right_top_wrong": both[(True, False)], "hier_wrong_top_right": both[(False, True)],
                          "both_wrong": both[(False, False)]}
    lines += ["## Two kinds of top record (Q4, EVAL)", "",
              "The hierarchical record (pilot rule, what A1 commits) and the single most probable candidate differ in %d of %d reports "
              "(%.1f%%). Of those: hierarchical right and top wrong %d; hierarchical wrong and top right %d; both wrong %d." %
              (diff, tot_e, 100 * diff / tot_e, both[(True, False)], both[(False, True)], both[(False, False)]), ""]

    # --- conformal sets per alpha, q4
    lines += ["## Conformal sets (Q4 heads; threshold from CAL of each fold; numbers on EVAL, pooled n = 1000)", "",
              "| alpha | target | coverage | 95%% band (binomial, n=1000) | inside? | empty | size 1 | size 2-%d | size > %d | top in set | hier in set | mean size |" % (K_MAX, K_MAX),
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    per_alpha = {}
    for alpha in ALPHAS:
        cov = empty = s1 = smid = sbig = topin = hin = 0
        sizes_ = []
        per_fold = []
        n = 0
        for k, f in ds.folds.items():
            q = ds.q_hat(k, "q4", alpha)
            cal_cov = np.mean([g is not None and (1 - g) <= q + 1e-12 for g in ds.label_scores(k, "q4", f["cal"])])
            fc = 0
            for i in f["eval"]:
                i = int(i)
                S = ds.conformal(k, "q4", i, q)
                keys = {c["key"] for c in S}
                c_all = ds.cands(k, "q4", i)
                ok = ds.label_key[i] in keys
                cov += ok
                fc += ok
                empty += len(S) == 0
                s1 += len(S) == 1
                smid += 2 <= len(S) <= K_MAX
                sbig += len(S) > K_MAX
                topin += c_all[0]["key"] in keys
                hin += pc.strict_key(ds.hier(k, "q4", i)) in keys
                sizes_.append(len(S))
                n += 1
            per_fold.append({"fold": k, "q_hat": q, "cal_coverage": float(cal_cov), "eval_coverage": fc / len(f["eval"])})
        lo, hi = band(1 - alpha, n)
        per_alpha[str(alpha)] = {"coverage": cov / n, "band": [lo, hi], "inside": bool(lo <= cov / n <= hi), "empty": empty, "size1": s1, "size_2_K": smid,
                                 "over_K": sbig, "top_in_set": topin / n, "hier_in_set": hin / n, "mean_size": float(np.mean(sizes_)), "per_fold": per_fold}
        lines.append("| %.2f | %.0f%% | %.1f%% | %.1f%%-%.1f%% | %s | %d | %d | %d | %d | %.1f%% | %.1f%% | %.2f |" %
                     (alpha, 100 * (1 - alpha), 100 * cov / n, 100 * lo, 100 * hi, "yes" if lo <= cov / n <= hi else "NO", empty, s1, smid, sbig,
                      100 * topin / n, 100 * hin / n, float(np.mean(sizes_))))
    res["conformal_q4"] = per_alpha
    lines += ["", "Per fold (coverage on the 200 EVAL reports of each fold; the threshold comes from the 200 CAL reports of that fold):", ""]
    for alpha in ALPHAS:
        pf = per_alpha[str(alpha)]["per_fold"]
        lines.append("* alpha %.2f: %s" % (alpha, "; ".join("fold %d q=%.3f cal %.3f eval %.3f" % (p["fold"], p["q_hat"], p["cal_coverage"], p["eval_coverage"]) for p in pf)))
    lines += ["", "Reading: the band above is the sampling error of the 1000 EVAL reports only. The threshold itself is estimated from 200 reports per fold, so "
              "the true spread is a little wider (about sqrt(2) times).  Coverage is marginal and holds under exchangeability of CAL and EVAL reports; the "
              "reports of one family are NOT independent, so the guarantee is approximate here (plan 4.8).", ""]
    (paths.RESULTS / "M4_readout_report.md").write_text("\n".join(lines), encoding="utf-8")
    (paths.RESULTS / "M4_readout_report.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
