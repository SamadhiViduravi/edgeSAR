"""
Turn the saved development records into tables: outcomes AND costs, paired comparisons, the Shield's decisions, and gate quality.

    python tools/analyze_dev.py --tag main            -> results/dev/main/DEV_main.md, DEV_main.json
Seeds re-partition the SAME 1,000 reports into episodes, so episodes of different seeds are not independent.  The headline numbers are therefore
given per seed as well as pooled; the pooled interval is optimistic and is labelled so.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                                # noqa: E402

from shield import devrun, paths                                  # noqa: E402

LEVELS = ["L", "M", "H"]
PAIRS = [("A8", "A6", "PRIMARY: Shield+cover vs confidence gate (same budget)"), ("A8", "A6b", "Shield+cover vs record-score gate"),
         ("A8", "A7", "Shield+cover vs random gate"), ("A8", "A1", "Shield+cover vs always commit"),
         ("A8c", "A6", "REVISED (post-hoc): Shield+location cover vs confidence gate"), ("A8c", "A1", "Shield+location cover vs always commit"),
         ("A8c", "A8", "location cover vs full cover"), ("A8c", "A10", "location cover vs no fallback"),
         ("A8", "A10", "fallback effect: with cover vs without"), ("A8", "A9", "conformal sets vs singleton sets only"),
         ("A8", "A11", "conformal sets vs top-2 what-if"), ("A10", "A6", "Shield without fallback vs confidence gate"),
         ("A6", "A1", "confidence gate vs always commit"), ("A12", "A1", "HEADROOM: perfect gate vs always commit"),
         ("A1", "A0", "record-induced misses of the Q4 head (vs gold records)"), ("A1", "A2", "Q4 vs FP16 (quantisation effect)"),
         ("A4", "A1", "recentred Q4 vs raw-trained Q4"), ("A5", "A2", "mismatched frozen head vs FP16 (diagnostic)")]


def pct(x, d=1):
    return "-" if x != x else ("%.*f%%" % (d, 100 * x))


def load(tag, base="dev"):
    d = paths.RESULTS / base / tag
    recs = {}
    for f in sorted(d.glob("records_*_s*.json.gz")):
        lv, sd = f.stem.split(".")[0].split("_")[1:3]
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            recs[(lv, int(sd[1:]))] = json.load(fh)
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    return recs, man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--base", default="dev", choices=["dev", "fresh"], help="results/<base>/<tag>")
    ap.add_argument("--levels", nargs="+", default=None)
    a = ap.parse_args()
    recs, man = load(a.tag, a.base)
    fresh = a.base == "fresh"
    levels = a.levels or [l for l in LEVELS if any(k[0] == l for k in recs)]
    seeds = sorted({k[1] for k in recs})
    arms_present = {r["arm"] for v in recs.values() for r in v}
    out, js = [], {"tag": a.tag, "args": man["args"], "levels": {}}
    out.append("# %s results: %s" % ("FRESH (confirmation)" if fresh else "Development", a.tag))
    out.append("")
    if fresh and man.get("eval_set") == "style_b":
        out.append("**EXPLORATORY style-shift check, not a confirmation.** The 400 style-B development reports (wording the heads never saw), in 20 fixed episodes of 20; "
                   "heads fitted on the 1,000 style-A development reports; conformal threshold and gate thresholds from the fresh style-A calibration episodes. "
                   "Style B was used before in the pilot, so nothing here is untouched data. Descriptive only: no test is claimed.")
        out.append("")
    if fresh:
        pl = man.get("plan", {})
        out.append("FRESH reports (inputs generated after the plan was frozen; plan SHA-256 %s). Heads fitted once on the 1,000 development style-A reports; conformal threshold and "
                   "gate thresholds from %s calibration episodes; every number below is from %s evaluation episodes of %d reports sharing one fleet, arrival seed(s) %s. "
                   "Verification budget b = %s of reports (hard cap per episode), delay d_v = %s s; alpha = %s, K = %s, allocator %s, readout %s." % (
                       str(man.get("plan_sha256", "?"))[:16], pl.get("cal_episodes", "?"), pl.get("eval_episodes", "?"), 20, seeds, man["args"]["b"],
                       man["args"]["d_v"], man["args"]["alpha"], man["args"]["K"], man["args"]["allocator"], man["args"]["readout"]))
    else:
        out.append("Saved vectors, 1,000 style-A reports, 5 outer folds, %d seed(s) %s; overlay episodes of %d reports sharing one fleet; verification budget "
                   "b = %s of reports (hard cap per episode), delay d_v = %s s; alpha = %s, K = %s, allocator %s, readout %s. EVAL reports only. "
                   "Style B untouched." % (len(seeds), seeds, 20, man["args"]["b"], man["args"]["d_v"], man["args"]["alpha"], man["args"]["K"],
                                           man["args"]["allocator"], man["args"]["readout"]))
    if man["args"]["readout"] == "raw":
        out.append("")
        out.append("**STRESS TEST: the readout is the deliberately mismatched head (FP16-fitted head applied to raw Q4 vectors).** In this table A1 is therefore a "
                   "mismatched-head commit, and the Shield, the gates and the conformal sets all sit on that mismatched head.")
    out.append("")
    out.append("U_deadline = (late + unverified) / incidents. Lower is better. CI = episode bootstrap, seeds pooled (optimistic: seeds re-use the same reports).")
    out.append("")
    for lv in levels:
        R = [r for (l, s), v in recs.items() if l == lv for r in v]
        js["levels"][lv] = {}
        T = devrun.arm_table(R)
        out.append("## Level %s" % lv)
        out.append("")
        out.append("### Outcomes and costs")
        out.append("")
        out.append("| Arm | System | U_deadline (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | "
                   "hold s / report | allocator runs / report | decision ms median / p99 |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for arm in devrun.ARM_ORDER:
            if arm not in T:
                continue
            t = T[arm]
            lo, hi = devrun.episode_bootstrap_ci(R, arm)
            out.append("| %s | %s | %s (%s to %s) | %d | %d | %.3f | %.3f | %d (%d) | %.0f | %.1f | %.2f | %.2f / %.2f |" % (
                arm, devrun.ARM_TEXT[arm], pct(t["U_deadline"]), pct(lo), pct(hi), t["late"], t["unverified"], t["request_rate"], t["wasted_per_report"],
                t["cover_visits"], t["cover_wasted_visits"], t["distance_per_report_m"], t["hold_s_per_report"], t["allocator_runs_per_report"],
                t["wall_ms_median"], t["wall_ms_p99"]))
        out.append("")
        n_inc = T["A0"]["incidents"] if "A0" in T else T["A1"]["incidents"]
        out.append("Episodes per arm: %d, incidents per arm: %d, reports per arm: %d. Request rates should be near b = %s; the cap is %d request(s) per 20-report episode."
                   % (T["A1"]["episodes"], n_inc, T["A1"]["reports"], man["args"]["b"], int(np.floor(man["args"]["b"] * 20 + 0.5))))
        out.append("")
        js["levels"][lv]["arms"] = T
        # ---- coverage of the conformal sets and missing candidates (evaluation side; identical for every seed, so the first seed is used)
        runs = [r for r in man["runs"] if r["level"] == lv]
        es = [f.get("eval_set") for f in runs[0]["folds"]] if runs else []
        if es and all(es):
            tot = {k: sum(e[k] for e in es) for k in es[0]}
            n_e = tot["reports"]
            out.append("Conformal sets on the %d evaluation reports (target coverage %.0f%%): gold record in the set %d (%s); gold record NOT expressible by the heads + parser "
                       "(missing candidate) %d; empty sets %d; singleton sets %d; sets of 2 to K %d; oversized sets (> K) %d; best-guess record in the set %s." % (
                           n_e, 100 * (1 - man["args"]["alpha"]), tot["covered"], pct(tot["covered"] / n_e), tot["gold_missing"], tot["empty"], tot["size1"],
                           tot["size_2_K"], tot["over_K"], pct(tot["hier_in_set"] / n_e)))
            out.append("")
            js["levels"][lv]["eval_set"] = tot
        # ---- paired
        out.append("### Paired comparisons (same episodes)")
        out.append("")
        out.append("Difference in U_deadline (first minus second); negative = first is better. Per-seed differences in the last column.")
        out.append("")
        out.append("| Comparison | diff (95% CI) | missed incidents: first / second | unverified: first / second | sign-flip p | episodes won / lost / tied | per seed |")
        out.append("|---|---|---|---|---|---|---|")
        js["levels"][lv]["paired"] = []
        for x, y, why in PAIRS:
            if x not in arms_present or y not in arms_present:
                continue
            p = devrun.paired(R, x, y)
            per = []
            for s in seeds:
                Rs = recs.get((lv, s))
                if Rs:
                    per.append("%+.1f" % (100 * devrun.paired(Rs, x, y, n_boot=500)["diff_U"]))
            if fresh and why.startswith("PRIMARY"):
                why = why if lv == "M" else "secondary at this level (the primary comparison is at level M)"
            p["why"] = why
            p["per_seed_pp"] = per
            js["levels"][lv]["paired"].append(p)
            out.append("| %s vs %s: %s | %+.2f pp (%+.2f to %+.2f) | %d / %d | %d / %d | %.3f | %d / %d / %d | %s |" % (
                x, y, why, 100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1], p["miss_x"], p["miss_y"], p["unverified_x"], p["unverified_y"],
                p["p_signflip"], p["wins_x"], p["wins_y"], p["ties"], ", ".join(per)))
        out.append("")
        # ---- Shield decisions
        out.append("### What the Shield decided")
        out.append("")
        out.append("| Outcome class | A8 reports | A8 share | A8c reports | A8c share |")
        out.append("|---|---|---|---|---|")
        c8, c8c = T["A8"]["outcome_classes"], T["A8c"]["outcome_classes"]
        nrep = T["A8"]["reports"]
        for k in ("ACCEPT", "ACCEPT_INFEASIBLE", "ESCALATE", "FALLBACK_COVERED", "FALLBACK_PARTIAL", "FALLBACK_UNRESOLVED", "UNCERTIFIED_COMMIT", "TIMEOUT", "TIMEOUT_LATE"):
            if c8.get(k) or c8c.get(k):
                out.append("| %s | %d | %s | %d | %s |" % (k, c8.get(k, 0), pct(c8.get(k, 0) / nrep), c8c.get(k, 0), pct(c8c.get(k, 0) / nrep)))
        out.append("")
        cert = devrun.certificate_check(R, "A8")
        out.append("Certified (ACCEPT + ACCEPT_INFEASIBLE): %s of reports; certified AND the committed plan differs from the gold plan: %d reports = %s of all reports "
                   "(the marginal guarantee is <= alpha = %s, on exchangeable data). Set sizes of certified reports: %s."
                   % (pct(cert["certified_rate"]), cert["certified_wrong_plan"], pct(cert["certified_wrong_rate"], 2), man["args"]["alpha"], cert["certified_set_sizes"]))
        out.append("")
        js["levels"][lv]["certificate"] = cert
        # ---- gate quality
        out.append("### Which reports does each method flag? (reports whose best-guess record would have given a wrong plan)")
        out.append("")
        out.append("| Arm | flagged (verify or cover) | of which wrong-plan | wrong-plan reports flagged (recall) | flagged that were wrong-plan (precision) | wrong-plan reports left unflagged, share of ALL reports |")
        out.append("|---|---|---|---|---|---|")
        js["levels"][lv]["gate_quality"] = {}
        for arm in ("A1", "A6", "A6b", "A7", "A8", "A8c", "A9", "A10", "A11", "A12"):
            if arm not in arms_present:
                continue
            g = devrun.gate_quality(R, arm)
            js["levels"][lv]["gate_quality"][arm] = g
            out.append("| %s | %d (%s) | %d | %s | %s | %s |" % (arm, g["flagged"], pct(g["flagged"] / max(g["reports"], 1)), g["flagged_wrong"], pct(g["recall"]),
                                                              pct(g["precision"]), pct(g["accepted_wrong_rate"])))
        out.append("")
        if "OBS" in arms_present:
            rq = devrun.ranking_quality(R)
            js["levels"][lv]["ranking"] = rq
            out.append("### Equal-budget ranking: share of the wrong-plan reports caught when each method flags its top f of every episode")
            out.append("")
            out.append("%d reports, %d of them with a wrong plan. The OBS arm behaves exactly like A1 and logs every method's risk score." % (rq["reports"], rq["wrong_plan_reports"]))
            out.append("")
            out.append("| Ranking by | f = 5% | f = 10% | f = 20% | f = 30% | AUROC |")
            out.append("|---|---|---|---|---|---|")
            for name, d in rq["recall_at_flag_rate"].items():
                out.append("| %s | %s | %s | %s | %s | %.3f |" % (name, pct(d["5%"]), pct(d["10%"]), pct(d["20%"]), pct(d["30%"]), d["AUROC"]))
            out.append("")
    text = "\n".join(out)
    d = paths.RESULTS / a.base / a.tag
    stem = ("FRESH_%s" if fresh else "DEV_%s") % a.tag
    (d / (stem + ".md")).write_text(text, encoding="utf-8")
    (d / (stem + ".json")).write_text(json.dumps(js, indent=1, default=float), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
