"""
Turn the iteration-1 records into tables (docs/ITERATION1_PROTOCOL.md section 3 decides the label; this script only applies it).

    python tools/analyze_iter1.py            -> results/iter1/ITER1_RESULTS.md and ITER1_RESULTS.json
Seeds re-partition the SAME 1,000 reports, so pooled intervals are optimistic; per-seed numbers are shown for the two main comparisons.
"""
import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                                 # noqa: E402

from shield import devrun, paths                                   # noqa: E402

LEVELS = ["L", "M", "H"]
NOT_FLAGGED = ("COMMIT", "ACCEPT", "ACCEPT_INFEASIBLE", "TIMEOUT")
TEXT = {"A0": "Gold records (reference)", "A1": "Q4 head, always commit", "A2": "FP16 head, always commit", "A3": "Q8 head, always commit",
        "A4": "Recentred Q4", "A5": "Frozen FP16 head on raw Q4 (diagnostic)", "A6": "Confidence gate, verification only",
        "A8": "Shield (plan): full cover", "A8c": "Shield + location cover (post-hoc)", "A10": "Shield, no fallback", "A12": "Oracle gate (diagnostic)",
        "B1": "B1 strict candidate check", "B2": "B2 = B1 + mass guard", "B3": "B3 = Shield-2 (B2 + cost-aware fallback)",
        "B4": "B4 = B1 + cost-aware fallback", "G1": "G1 confidence gate with the same fallback (equal footing)"}
COMPARE_ORDER = ["A0", "A1", "A2", "A3", "A4", "A5", "A6", "A8", "A8c", "A10", "A12", "B1", "B2", "B3", "B4", "G1"]
PAIRS = [("B3", "G1", "P1 PRIMARY: Shield-2 vs equal-footing confidence gate"), ("B3", "A1", "P2: Shield-2 vs always commit (no gate)"),
         ("B3", "A8", "P3: Shield-2 vs plan's Shield"), ("B3", "A6", "Shield-2 vs verification-only gate"), ("G1", "A1", "equal-footing gate vs always commit"),
         ("B1", "A8", "strict candidate check alone vs plan's Shield"), ("B2", "B1", "mass guard (full cover)"), ("B3", "B2", "cost-aware fallback (with mass guard)"),
         ("B4", "B1", "cost-aware fallback (no mass guard)"), ("B3", "B4", "mass guard (with cost-aware fallback)"),
         ("A8c", "A6", "reference: location cover vs gate (post-hoc, iteration 0)"), ("A6", "A1", "verification-only gate vs always commit"),
         ("A12", "A1", "headroom: oracle gate vs always commit"), ("A1", "A0", "record-induced misses of the head vs gold"),
         ("A1", "A2", "Q4 vs FP16"), ("A3", "A2", "Q8 vs FP16"), ("A4", "A1", "recentred vs trained-on-Q4")]


def pp(x, d=2):
    return "-" if x != x else "%+.*f" % (d, 100 * x)


def pc(x, d=1):
    return "-" if x != x else "%.*f%%" % (d, 100 * x)


def load(tag):
    d = paths.RESULTS / "iter1" / tag
    recs = {}
    for f in sorted(d.glob("records_*_s*.json.gz")):
        lv, sd = f.stem.split(".")[0].split("_")[1:3]
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            recs[(lv, int(sd[1:]))] = json.load(fh)
    return recs, json.loads((d / "manifest.json").read_text(encoding="utf-8"))


def cls(rep):
    o = rep["o"]
    return "TIMEOUT_LATE" if o.startswith("TIMEOUT_LATE") else o.split(":")[0]


def quality(records, arm):
    """Certified share, certified-and-wrong (plan / table), flagged share, wrong-plan reports left unflagged.  Evaluation side (reads rpg / pg / tg)."""
    n = cert = cert_wrong_plan = cert_wrong_table = flagged = wrong = wrong_unflagged = flagged_wrong = 0
    for r in devrun._by_arm(records)[arm].values():
        for rep in r["reports"]:
            c = cls(rep)
            n += 1
            f = c not in NOT_FLAGGED
            flagged += f
            if c in ("ACCEPT", "ACCEPT_INFEASIBLE"):
                cert += 1
                cert_wrong_plan += rep["pg"] is False
                cert_wrong_table += rep["tg"] is False
            if rep["rpg"] is False:
                wrong += 1
                wrong_unflagged += (not f)
                flagged_wrong += f
    return {"reports": n, "certified": cert / n, "certified_wrong_plan": cert_wrong_plan / n, "certified_wrong_table": cert_wrong_table / n,
            "flagged": flagged / n, "wrong_plan_reports": wrong / n, "wrong_plan_unflagged": wrong_unflagged / n,
            "flagged_precision": (flagged_wrong / flagged) if flagged else float("nan")}


def table_for(recs, level):
    allr = [r for (lv, s), v in recs.items() if lv == level for r in v]
    return allr


def per_seed(recs, level, x, y):
    out = {}
    for (lv, s), v in sorted(recs.items()):
        if lv == level:
            p = devrun.paired(v, x, y, n_boot=4000)
            out[s] = {"diff_pp": 100 * p["diff_U"], "ci_pp": [100 * p["ci"][0], 100 * p["ci"][1]], "wins_x": p["wins_x"], "wins_y": p["wins_y"], "ties": p["ties"]}
    return out


def analyse(tag):
    recs, man = load(tag)
    res = {"tag": tag, "readout": man["args"]["readout"], "levels": {}}
    for lv in LEVELS:
        allr = table_for(recs, lv)
        if not allr:
            continue
        arms = sorted({r["arm"] for r in allr})
        tab = devrun.arm_table(allr)
        L = {"table": tab, "ci": {}, "pairs": {}, "quality": {}}
        for a in arms:
            if a != "OBS":
                L["ci"][a] = devrun.episode_bootstrap_ci(allr, a)
        for x, y, why in PAIRS:
            if x in arms and y in arms:
                L["pairs"]["%s-%s" % (x, y)] = dict(devrun.paired(allr, x, y), why=why)
        for a in ("A8", "A10", "B1", "B2", "B3", "B4", "G1", "A6"):
            if a in arms:
                L["quality"][a] = quality(allr, a)
        if lv == "M":
            L["per_seed"] = {"B3-G1": per_seed(recs, lv, "B3", "G1"), "B3-A1": per_seed(recs, lv, "B3", "A1")}
        res["levels"][lv] = L
    res["infos"] = {"%s_s%d" % k: None for k in recs}
    res["cal_flag_rates"] = {}
    for run in man["runs"]:
        if run["level"] == "M":
            for f in run["folds"]:
                res["cal_flag_rates"].setdefault(run["seed"], []).append({k: f[k] for k in ("fold", "cal_flag_rate_a8", "cal_flag_rate_s1", "cal_flag_rate_s2", "cal_s2_reasons")})
    return res


def label(res):
    M = res["levels"]["M"]["pairs"]
    p1, p2 = M["B3-G1"], M["B3-A1"]
    pts = []
    for lv in ("L", "H"):
        pr = res["levels"][lv]["pairs"]
        pts.append((lv, pr["B3-G1"]["diff_U"], pr["B3-A1"]["diff_U"]))
    if p2["ci"][0] > 0:
        return "HARMFUL on a competent head", "B3 - A1 is above 0 (CI %s to %s pp)." % (pp(p2["ci"][0]), pp(p2["ci"][1]))
    if p1["ci"][1] < 0 and p2["ci"][1] < 0 and all(a <= 0 and b <= 0 for _, a, b in pts):
        return "SUPPORTED on DEV", "Both CIs are below 0 at level M and the point estimates at L and H are <= 0."
    why = "B3-G1 %s pp (CI %s to %s); B3-A1 %s pp (CI %s to %s); at L/H: %s" % (
        pp(p1["diff_U"]), pp(p1["ci"][0]), pp(p1["ci"][1]), pp(p2["diff_U"]), pp(p2["ci"][0]), pp(p2["ci"][1]),
        ", ".join("%s: G1 %s, A1 %s" % (lv, pp(a), pp(b)) for lv, a, b in pts))
    return "NOT SHOWN", why


def md_main(res):
    o = []
    A = o.append
    A("## Readout `%s`  (%s)" % (res["tag"], res["readout"]))
    A("")
    for lv in LEVELS:
        if lv not in res["levels"]:
            continue
        L = res["levels"][lv]
        A("### Level %s: missed share (late + unverified), all outcomes and costs" % lv)
        A("")
        A("| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |")
        A("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for a in COMPARE_ORDER:
            if a not in L["table"]:
                continue
            t = L["table"][a]
            ci = L["ci"][a]
            A("| %s | %s | %s | %s to %s | %.3f | %.3f | %d | %d | %.0f | %.1f | %.3f | %.2f |" % (
                a, TEXT.get(a, ""), pc(t["U_deadline"], 2), pc(ci[0], 2), pc(ci[1], 2), t["request_rate"], t["wasted_per_report"], t["cover_visits"],
                t["cover_wasted_visits"], t["distance_per_report_m"], t["hold_s_per_report"], t["decision_s_per_report"], t["allocator_runs_per_report"]))
        A("")
        A("Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:")
        A("")
        A("| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |")
        A("|---|---|---|---|---|---|")
        for k, v in L["pairs"].items():
            A("| %s | %s | %s | %s to %s | %.3f | %d / %d / %d |" % (k, v["why"], pp(v["diff_U"]), pp(v["ci"][0]), pp(v["ci"][1]), v["p_signflip"], v["wins_x"], v["wins_y"], v["ties"]))
        A("")
        if "per_seed" in L:
            A("Per arrival seed (each seed re-partitions the same reports, so seeds are not independent):")
            A("")
            A("| seed | B3 - G1 (pp) | CI | B3 - A1 (pp) | CI |")
            A("|---|---|---|---|---|")
            for s in sorted(L["per_seed"]["B3-G1"]):
                g, a1 = L["per_seed"]["B3-G1"][s], L["per_seed"]["B3-A1"][s]
                A("| %s | %+.2f | %+.2f to %+.2f | %+.2f | %+.2f to %+.2f |" % (s, g["diff_pp"], g["ci_pp"][0], g["ci_pp"][1], a1["diff_pp"], a1["ci_pp"][0], a1["ci_pp"][1]))
            A("")
        A("Decisions of the Shield-type arms (share of reports):")
        A("")
        A("| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |")
        A("|---|---|---|---|---|---|---|---|")
        for a, q in L["quality"].items():
            A("| %s | %s | %s | %s | %s | %s | %s | %s |" % (a, pc(q["certified"]), pc(q["certified_wrong_plan"], 2), pc(q["certified_wrong_table"], 2), pc(q["flagged"]),
                                                           pc(q["wrong_plan_reports"]), pc(q["wrong_plan_unflagged"], 2), pc(q["flagged_precision"])))
        A("")
        A("Outcome classes (reports):")
        A("")
        A("| arm | " + " | ".join(sorted({c for a in ("A8", "B1", "B2", "B3", "B4", "G1") if a in L["table"] for c in L["table"][a]["outcome_classes"]})) + " |")
        cl = sorted({c for a in ("A8", "B1", "B2", "B3", "B4", "G1") if a in L["table"] for c in L["table"][a]["outcome_classes"]})
        A("|---|" + "---|" * len(cl))
        for a in ("A8", "B1", "B2", "B3", "B4", "G1"):
            if a in L["table"]:
                A("| %s | %s |" % (a, " | ".join(str(L["table"][a]["outcome_classes"].get(c, 0)) for c in cl)))
        A("")
    return o


def main():
    results = {}
    out = ["# Iteration 1: development results", "",
           "Protocol: `docs/ITERATION1_PROTOCOL.md` (SHA-256 %s). Development data only (1,000 style-A reports, saved vectors, 5 family folds, overlay episodes of 20 reports, 3 arrival seeds pooled). "
           "Nothing here is a confirmation. Pooled intervals are optimistic because seeds reuse the same reports." % (paths.RESULTS / "iter1" / "PROTOCOL.sha256").read_text().split()[0], ""]
    for tag in ("q4", "f16", "q8", "raw"):
        if not (paths.RESULTS / "iter1" / tag / "manifest.json").exists():
            continue
        r = analyse(tag)
        results[tag] = r
    if "q4" in results:
        lab, why = label(results["q4"])
        results["label"] = {"label": lab, "why": why}
        out += ["## Label by the fixed rule (protocol section 3)", "", "**%s.** %s" % (lab, why), ""]
    for tag, r in results.items():
        if tag == "label":
            continue
        out += md_main(r)
    (paths.RESULTS / "iter1" / "ITER1_RESULTS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (paths.RESULTS / "iter1" / "ITER1_RESULTS.json").write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")
    print("\n".join(out[:12]))


if __name__ == "__main__":
    main()
