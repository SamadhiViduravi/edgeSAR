"""
EdgeSAR harm test: write harm_report.md, harm_table.csv and harm_outcome.png from the summary made by harm_lib.compute_summary.
Plain words on purpose. Every number in the report is also in harm_summary.json.
"""
import csv
import json
import math

import numpy as np

import harm_lib as hl
import heads_report as hr

TABLE = hr.table


def pct(x, d=1):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else "%.*f%%" % (d, 100 * x)


def pp(x, d=1):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else "%+.*f" % (d, 100 * x)


def ci_pct(s, d=1):
    return "%s (%s to %s)" % (pct(s["point"], d), pct(s["low"], d), pct(s["high"], d))


def ci_pp(s, d=1):
    return "%s (%s to %s)" % (pp(s["point"], d), pp(s["low"], d), pp(s["high"], d))


def ci_num(s, d=1, unit=""):
    f = lambda v: "-" if v is None or math.isnan(v) else "%.*f" % (d, v)
    return "%s%s (%s to %s)" % (f(s["point"]), unit, f(s["low"]), f(s["high"]))


def n_(x):
    return "%d" % round(x)


def f_needed(s, target=0.02):
    hw = (s["high"] - s["low"]) / 2
    return None if not hw or math.isnan(hw) else int(math.ceil(s["n_fam"] * (hw / target) ** 2))


# ------------------------------------------------------------------ the report
def write_report(path, S, cfg, ctx):
    sp = cfg["primary_split"]
    W = []
    add = W.append
    V = S["vs_gold"]
    arms = {g: [a for a in cfg["arms"][g] if a in V] for g in hl.GROUPS}
    sample = V[arms["primary"][0]][sp]
    nF = sample["n_families"]
    nrep = int(sample["totals"]["reports"])
    ninc = int(sample["totals"]["n_truth"])
    refU = sample["U_ref"]

    add("# EdgeSAR harm test: results (EXPLORATORY)")
    add("")
    add("Made: %s. Run folder: `%s`. Plan: `HARM_TEST_PLAN.md` (%s). Main split: held-out style B = %d reports, %d families, %d real incidents."
        % (ctx["created"], ctx["run_name"], ctx["plan_status"], nrep, nF, ninc))
    add("")
    add("**What this is.** Every system's saved record for a report is given to the same allocator (simplified CBBA, 3 UAVs). "
        "A simulator then says which real incidents get verified by the 600 s horizon. The reference is a run with the "
        "**correct (gold) record** for the same report. The reference is not an optimal planner. "
        "**What this is not:** a closed-loop mission, full CBBA, a test of Shield or Cover (those are planned, not implemented), "
        "or a confirmation. Style B was already seen, so everything here is exploratory.")
    add("")
    add("**Checks before the run:** " + "; ".join(ctx["checks"]) + ".")
    add("")

    # ---------------------------------------------------------------- 1
    add("## 1. Main result: real incidents not verified by 600 s (held-out B)")
    add("")
    add("U = unverified real incidents / real incidents. dU = U(system) - U(gold-record reference), in percentage points. "
        "Intervals are 95%% family-bootstrap intervals over **%d families** (paired with the reference). V->U = verified with the gold "
        "record but not with the system's record. U->V = the opposite." % nF)
    add("")
    rows = [["GOLD-RECORD (reference)", "%s of %d" % (n_(sample["totals"]["ref_unver"]), ninc), ci_pct(refU), "0", "-", "-", "-"]]
    for a in arms["primary"]:
        s = V[a][sp]
        t = s["totals"]
        rows.append([a, "%s of %d" % (n_(t["test_unver"]), ninc), ci_pct(s["U_test"]), ci_pp(s["dU"]), n_(t["v2u"]), n_(t["u2v"]),
                     n_(t["both_unver"])])
    add(TABLE(["System", "Unverified", "U", "dU vs reference (pp)", "V->U", "U->V", "Unverified in both (resource-limited)"], rows))
    add("")
    add("'Unverified in both' are incidents the allocator could not verify even with the correct record (too few UAVs, camera limits, time). "
        "They are not caused by a record. " + (
        "Here the gold-record reference verified **all %d real incidents** on B, so there are no resource-limited misses: every miss below comes from a record."
        % ninc if sample["totals"]["ref_unver"] == 0 else
        "Here the reference left %d of %d incidents unverified; those are resource-limited and are not blamed on any system." % (sample["totals"]["ref_unver"], ninc)))
    add("")

    # ---------------------------------------------------------------- 2
    add("## 2. Does the precision change what happens? (system against system, held-out B)")
    add("")
    rows = []
    for key, byspl in S["pairs"].items():
        s = byspl[sp]
        t = s["totals"]
        rows.append([key, ci_pp(s["dU"]), n_(t["v2u"]), n_(t["u2v"]), n_(t["l0"]), n_(t["l1"]), n_(t["l2"]), n_(t["l3"]), n_(t["l4"]),
                     "%s / %s" % (n_(t["absorbed"]), n_(t["consequential"]))])
    add(TABLE(["First -> second", "dU (pp)", "V->U", "U->V", "L0 record", "L1 table", "L2 assignment", "L3 route", "L4 verification",
               "Absorbed / consequential"], rows))
    add("")
    add("dU here = U(second) - U(first). Levels are counts of reports (out of %d) where that level differs between the two systems. "
        "Absorbed = the task table differs but no verification changes; consequential = the table differs and a verification changes "
        "(a verification time moves by more than %.1f s, or a miss appears or disappears)." % (nrep, cfg["eps_s"]))
    add("")

    # ---------------------------------------------------------------- 3
    add("## 3. Secondary outcomes (held-out B, each separately)")
    add("")
    add("Delay = system minus reference, in seconds, over incidents verified in **both** runs (the count is shown; unverified incidents are in "
        "section 1, not hidden). Brackets = 95% family-bootstrap interval of that system's own value (not of a difference). RMIVT = mean verification time with a miss counted as 600 s (the `mission.py` convention). "
        "Trips = empty + wrong-camera visits per report. Distance = metres flown per report.")
    add("")
    ex = S["extras"]
    rows = []
    for a in [hl.GOLD_NAME] + arms["primary"] + arms["secondary"]:
        if a == hl.GOLD_NAME:
            s = sample
            rows.append([a, "-", ci_num(s["rmivt_ref"], 1), ci_num(s["trips_ref"], 2), ci_num(s["dist_ref"], 0),
                         "%.1f / %.1f" % (ex[a][sp]["verified_median_s"], ex[a][sp]["verified_p90_s"]), "%.2f" % ex[a][sp]["compute_ms_median"]])
            continue
        s = V[a][sp]
        e = ex[a][sp]
        rows.append([a, "%s (n=%s)" % (ci_num(s["delay_mean"], 1, " s"), n_(s["totals"]["delay_n"])), ci_num(s["rmivt_test"], 1),
                     ci_num(s["trips_test"], 2), ci_num(s["dist_test"], 0),
                     "%.1f / %.1f" % (e["verified_median_s"], e["verified_p90_s"]), "%.2f" % e["compute_ms_median"]])
    add(TABLE(["System", "Paired delay (s)", "RMIVT (s)", "Trips / report", "Distance (m) / report", "Verification time of verified: median / p90 (s)",
               "Compute ms (median)"], rows))
    add("")
    add("Compute time depends on this computer and is only descriptive. Incidents whose verification ended after 600 s (counted as unverified): "
        + ", ".join("%s %s" % (a, n_(V[a][sp]["totals"]["test_late"])) for a in arms["primary"]) + "; reference %s." % n_(sample["totals"]["ref_late"]))
    add("")

    # ---------------------------------------------------------------- 4
    add("## 4. Absorbed and consequential record changes (held-out B, against the gold-record reference)")
    add("")
    rows = []
    for a in arms["primary"] + arms["secondary"]:
        s = V[a][sp]
        t = s["totals"]
        rows.append([a, n_(t["l0"]), n_(t["l1"]), n_(t["absorbed"]), n_(t["consequential"]), pct(s["absorbed_share"]["point"], 0) if t["l1"] else "-",
                     "%s of %s" % (n_(t["harmful"]), n_(t["reports"]))])
    add(TABLE(["System", "Record differs from gold", "Task table differs", "Absorbed", "Consequential", "Absorbed share of table changes",
               "Harmful by the 30 s rule (exploratory)"], rows))
    add("")
    add("The 30 s rule is from `funnel.py` (`HARM_SECONDS = 30.0`, chosen by me after seeing the pilot cases). It is **exploratory**. "
        "'Harmful' = a new miss, or an incident verified at least 30 s later than in the reference.")
    add("")

    # ---------------------------------------------------------------- 5
    add("## 5. Secondary systems: fixed head, offset removed, shared head (held-out B)")
    add("")
    rows = []
    for a in arms["secondary"]:
        s = V[a][sp]
        t = s["totals"]
        rows.append([a, ci_pct(s["U_test"]), ci_pp(s["dU"]), n_(t["v2u"]), n_(t["u2v"]), n_(t["l1"]), n_(t["consequential"])])
    add(TABLE(["System", "U", "dU vs reference (pp)", "V->U", "U->V", "Task table differs", "Consequential"], rows))
    add("")

    # ---------------------------------------------------------------- 6
    nb = max((d["heads"] for d in (S.get("bootstrap") or {}).values()), default=20)
    add("## 6. The %d bootstrap-sample heads (held-out B)" % nb)
    add("")
    B = S.get("bootstrap")
    if not B:
        add("**Not run:** `bootstrap_predictions_end.csv` was not found. It is written by the extended `04_controls.py` (controls run 2 or later). "
            "This section is skipped, as the plan says.")
    else:
        add("Each head was trained on a bootstrap sample of the dev families and tested on the **same** B reports. They are not 20 independent "
            "datasets, so only the spread is shown (mean, lowest, highest over heads). 'Offset' = the constant offset removed from the Q vectors first.")
        add("")
        rows = []
        for v, d in B.items():
            rows.append([v, d["heads"], "%s (%s to %s)" % (pct(d["U"]["mean"]), pct(d["U"]["min"]), pct(d["U"]["max"])),
                         "%s (%s to %s)" % (pp(d["dU"]["mean"]), pp(d["dU"]["min"]), pp(d["dU"]["max"])),
                         "%.1f (%.0f to %.0f)" % (d["v2u"]["mean"], d["v2u"]["min"], d["v2u"]["max"]),
                         "%.1f (%.0f to %.0f)" % (d["u2v"]["mean"], d["u2v"]["min"], d["u2v"]["max"])])
        add(TABLE(["Vectors", "Heads", "U mean (lowest to highest)", "dU pp", "V->U", "U->V"], rows))
    add("")

    # ---------------------------------------------------------------- 7
    add("## 7. Context systems (held-out B)")
    add("")
    rows = []
    for a in arms["context"]:
        s = V[a][sp]
        t = s["totals"]
        rows.append([a, ci_pct(s["U_test"]), ci_pp(s["dU"]), n_(t["v2u"]), n_(t["u2v"]), n_(t["l1"]), n_(t["consequential"])])
    add(TABLE(["System", "U", "dU vs reference (pp)", "V->U", "U->V", "Task table differs", "Consequential"], rows))
    add("")
    add("The generative rows are the pilot's text writer (the EdgeSAR design). They are shown for comparison only.")
    add("")

    # ---------------------------------------------------------------- 8
    add("## 8. Development style A (descriptive)")
    add("")
    add("Who was fitted on style A matters. Heads and shared heads: out-of-fold by family (fair). Generative models: nothing is trained on A (fair). "
        "TF-IDF + LR: cross-validated by the pilot code. **Rule engine: written while style A was visible, so its result on A is not a fair test.** "
        "Style A is the easier style. Do not compare A with B as if they were the same test.")
    add("")
    rows = []
    sd = "dev"
    for a in arms["primary"] + arms["secondary"] + arms["context"]:
        s = V[a][sd]
        rows.append([a, ci_pct(s["U_test"]), ci_pp(s["dU"]), n_(s["totals"]["v2u"]), n_(s["totals"]["u2v"])])
    add("Reference U on A: %s (%d families)." % (ci_pct(V[arms["primary"][0]][sd]["U_ref"]), V[arms["primary"][0]][sd]["n_families"]))
    add("")
    add(TABLE(["System", "U", "dU vs reference (pp)", "V->U", "U->V"], rows))
    add("")

    # ---------------------------------------------------------------- 9
    add("## 9. Smallest fresh-family evaluation (approximate, from the spread seen here)")
    add("")
    rows = []
    for a in arms["primary"]:
        s = dict(V[a][sp]["dU"], n_fam=nF)
        rows.append([a + " vs reference", pp(s["point"]), "+/- %.1f" % (100 * (s["high"] - s["low"]) / 2), f_needed(s) or "-"])
    for key in ("Heads FP16 -> Heads Q4", "Heads FP16 -> Heads Q8"):
        if key in S["pairs"]:
            s = dict(S["pairs"][key][sp]["dU"], n_fam=nF)
            rows.append([key, pp(s["point"]), "+/- %.1f" % (100 * (s["high"] - s["low"]) / 2), f_needed(s) or "-"])
    add(TABLE(["Contrast", "dU now (pp)", "Half-width now (pp)", "Families needed for +/- 2 pp"], rows))
    add("")
    add("Approximate: F_needed = F_now x (half-width now / 2 pp)^2, assuming similar spread per family. A number below %d means the interval is already narrower than +/- 2 points; '-' means the interval has no width (nothing to scale). The confirmation" % nF + " uses fresh families from a "
        "new generator seed, fresh hidden-state extraction, and arms and settings frozen first. If Shield is used, it is recalibrated on separate data.")
    add("")

    # ---------------------------------------------------------------- 10
    add("## 10. Post-run look (NOT in the frozen plan; added after the first run; descriptive only)")
    add("")
    add("Which kind of record change caused the incidents that were verified with the gold record but not with the system's record (V->U), held-out B. "
        "The numbers in each row add up to the V->U column of section 1.")
    add("")
    MR = S.get("miss_reasons") or {}
    name = {"CREATE_VERIFICATION": "CREATE", "UPDATE_INCIDENT": "UPDATE", "CLOSE_INCIDENT": "CLOSE", "NO_ACTION": "NO_ACTION"}

    def label(k):
        g, s = [name.get(x.strip(), x.strip()) for x in k.split("->")]
        extra = {("CREATE", "NO_ACTION"): " (missed alarm)", ("UPDATE", "CLOSE"): " (wrong close)", ("NO_ACTION", "CLOSE"): " (wrong close)"}.get((g, s), "")
        return "gold %s, system %s%s" % (g, s, extra)
    rows = []
    for a in arms["primary"] + arms["secondary"] + arms["context"]:
        d = MR.get(a, {})
        top = sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
        rows.append([a, sum(d.values()), "; ".join("%d x %s" % (v, label(k)) for k, v in top) or "-"])
    add(TABLE(["System", "V->U", "Largest groups"], rows))
    add("")
    add("'Missed alarm' = a new real incident ignored. 'Wrong close' = a real incident removed from the table. These match the rough 'danger error' proxies of the controls report, "
        "but here they are counted by what happens in the simulator.")
    add("")

    # ---------------------------------------------------------------- 11
    add("## 11. Limits")
    add("")
    for t in (
        "Single-record fork-and-replay with a simplified CBBA (bundle size 1, perfect messages, no random parts). Not a closed-loop mission, "
        "and the result may not carry over to full CBBA, many reports over time, or message loss.",
        "Truth is the gold table. All tasks are known at t = 0. UAVs fly straight lines. Only 3 UAVs and 12 landmarks.",
        "Held-out B has %d families. Intervals are wide, and B was already seen, so nothing here is confirmatory." % nF,
        "Records come from one set of trained heads per precision. Head-to-head differences include head-training variability "
        "(see section 6 and `CONTROLS_PLAN.md`); a difference between Heads FP16 and Heads Q4 is not a pure quantization effect.",
        "The offset is fitted on dev A vectors, label-free. Its 'share explained' is about the vector, not about errors repaired.",
        "Candidate sets, the Shield gate and Cover are NOT implemented. Nothing here tests them.",
        "The priorities used (unverified incidents first, then delay, then trips) are an evaluation choice pending supervisor review.",
    ):
        add("* " + t)
    text = "\n".join(W) + "\n"
    path.write_text(text, encoding="utf-8")
    return text


def write_table(path, S, cfg):
    sp = cfg["primary_split"]
    rows = []
    for a, d in S["vs_gold"].items():
        s = d[sp]
        t = s["totals"]
        rows.append({"arm": a, "group": d["group"], "split": sp, "incidents": int(t["n_truth"]), "unverified": int(t["test_unver"]),
                     "U": round(s["U_test"]["point"], 4), "dU_vs_reference": round(s["dU"]["point"], 4), "dU_low": round(s["dU"]["low"], 4),
                     "dU_high": round(s["dU"]["high"], 4), "verified_to_unverified": int(t["v2u"]), "unverified_to_verified": int(t["u2v"]),
                     "paired_delay_mean_s": round(s["delay_mean"]["point"], 2), "rmivt_s": round(s["rmivt_test"]["point"], 2),
                     "trips_per_report": round(s["trips_test"]["point"], 3), "distance_m_per_report": round(s["dist_test"]["point"], 1),
                     "families": s["n_families"]})
    hl.write_csv(path, rows)


# ------------------------------------------------------------------ the picture
INK, MUTED, SURFACE, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"
BLUE, GRAY = "#2a78d6", "#8a8985"


def write_plot(path, S, cfg):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:                      # matplotlib is optional
        return False
    sp = cfg["primary_split"]
    V = S["vs_gold"]
    order = [(a, "primary") for a in cfg["arms"]["primary"] if a in V] + [(a, "secondary") for a in cfg["arms"]["secondary"] if a in V]
    n = len(order)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 0.42 * n + 2.0), sharey=True, facecolor=SURFACE)
    y = np.arange(n)[::-1]
    panels = [("dU", 100.0, "Real incidents left unverified at 600 s,\nsystem minus gold-record reference (percentage points)", "%+.1f"),
              ("v2u_per100", 1.0, "Incidents verified with the gold record\nbut not with the system's record, per 100 reports", "%.1f")]
    for ax, (key, k, title, fmt) in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        for yi, (a, g) in zip(y, order):
            s = V[a][sp][key]
            col = BLUE if g == "primary" else GRAY
            ax.plot([k * s["low"], k * s["high"]], [yi, yi], color=col, lw=2, solid_capstyle="round", zorder=2)
            ax.plot([k * s["point"]], [yi], marker="o", ms=8, color=col, mec=SURFACE, mew=2, zorder=3)
            ax.annotate(fmt % (k * s["point"]), (k * s["high"], yi), xytext=(7, 0), textcoords="offset points", va="center", fontsize=8.5, color=INK)
        ax.axvline(0, color=MUTED, lw=1, zorder=1)
        ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(axis="both", length=0, labelsize=9, colors=MUTED)
        ax.set_title(title, loc="left", fontsize=9.5, color=INK)
        lo = min(0, min(k * V[a][sp][key]["low"] for a, _ in order))
        hi = max(0, max(k * V[a][sp][key]["high"] for a, _ in order))
        pad = (hi - lo) * 0.14 or 1.0
        ax.set_xlim(lo - pad * 0.3, hi + pad)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([a for a, _ in order], fontsize=9, color=INK)
    fig.suptitle("Harm test, held-out style B (exploratory): blue = precision-specific heads, gray = fixed, offset-removed and shared heads. "
                 "Bars = 95%% family-bootstrap interval over %d families." % V[order[0][0]][sp]["n_families"],
                 x=0.01, ha="left", fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return True
