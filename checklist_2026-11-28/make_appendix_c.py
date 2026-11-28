"""Build the LaTeX tables of Appendix C (draft v2.18) and a plain-text digest of every number used in the text, from the result files.
    python make_appendix_c.py <checklist_results.json> [<qwen_results.json>] <out_dir>
"""
import json
import sys
from pathlib import Path

M = "$-$"


def f(x, d=2, sign=False):
    s = ("%+." + str(d) + "f") % x if sign else ("%." + str(d) + "f") % x
    return s.replace("-", M)


def pp(x, d=2):
    return f(100 * x, d, sign=True)


def pct(x, d=2):
    return f(100 * x, d)


def ci(c, d=2):
    return "%s to %s" % (f(100 * c[0], d, sign=True), f(100 * c[1], d, sign=True))


def colspec(widths, first_left=True):
    out = []
    for k, w in enumerate(widths):
        al = "raggedright" if (k == 0 and first_left) else "raggedleft"
        out.append(r">{\%s\arraybackslash}p{\dimexpr %.4f\linewidth-2\tabcolsep\relax}" % (al, w))
    return "".join(out)


def table(label, caption, widths, header, rows, star=True):
    env = "table*" if star else "table"
    s = [r"\begin{%s}[!tp]" % env, r"\caption{%s}" % caption, r"\label{%s}" % label, r"\centering\footnotesize", r"\def\firstcol{0in}",
         r"\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.1}", r"\begin{tabular}{%s}" % colspec(widths), r"\hline",
         " & ".join(r"\textbf{%s}" % h for h in header) + r" \\", r"\hline"]
    for r in rows:
        if r == "HLINE":
            s.append(r"\hline")
        else:
            s.append(" & ".join(r) + r" \\")
    s += [r"\hline", r"\end{tabular}", r"\end{%s}" % env]
    return "\n".join(s)


def main():
    R = json.load(open(sys.argv[1]))
    Q = json.load(open(sys.argv[2])) if len(sys.argv) > 3 else None
    QE = json.load(open(sys.argv[3])) if len(sys.argv) > 4 else None
    out = Path(sys.argv[-1])
    out.mkdir(parents=True, exist_ok=True)
    dig = []
    T = []
    acc = R["record_accuracy_setA"]
    k3 = R["K3_K10_label_arms"]
    nd = k3["draws"]
    k13d = R["K13_simulator_variants"]["default"]["shares"]
    eff = R["K10_statistics"]["absolute_and_relative"]

    # ---------------- C1 label-using arms
    names = [("q4p", "Retraining on Q4 (pre-specified arm)"), ("wsp", "Warm start from the FP16 heads, L2-SP"),
             ("bias", "Bias-only correction of the FP16 logits"), ("vecs", "Vector scaling of the FP16 logits"),
             ("mft", "Map, then L2-SP fine-tuning"), ("mbias", "Map, then bias-only correction")]
    rows = []
    for key, nm in names:
        row = [nm]
        for n in (100, 300):
            b = k3["n%d" % n]
            sh = b["shares_mean_of_draws"][key]
            lo, hi = b["best_single_draw"][key], b["worst_single_draw"][key]
            c2 = b["two_level_ci"]["alnp-%s" % key]
            dm = b["comparisons_mean_of_draws"]["alnp-%s" % key]["diff"]
            ac = sum(acc["%s_n%d_d%d" % (key, n, d)] for d in range(nd)) / nd
            row += ["%s (%s--%s)" % (pct(sh), pct(lo), pct(hi)), "%s (%s)" % (pp(dm), ci(c2)), f(100 * ac, 1)]
            dig.append("C1 n=%d %-5s share %.4f [%.4f-%.4f]  map-arm %+.4f two-level %s  acc %.4f  draws where map better %d/%d" %
                       (n, key, sh, lo, hi, dm, c2, ac, b["draws_where_alnp_better"][key], nd))
        rows.append(row)
    rows.append("HLINE")
    for key, nm in (("f16p", "Reference: FP16 classifier, FP16 vectors"), ("rawp", "Reference: Q4, unchanged (no new labels)"),
                    ("alnp", "Reference: Q4, map (no new labels)"), ("q4p", "Reference: Q4, retrained with 1,000 labels")):
        rows.append([nm, "%s" % pct(k13d[key]), "", f(100 * acc[key], 1), "", "", ""])
    T.append(table("tabC1",
                   "Label-using adaptations with 100 and 300 labels on %d label draws each (exploratory; set A, medium load, arrival seed 11). "
                   "Missed share: mean over the draws (range of single draws). Map minus arm: pooled difference of the map (fitted without labels) "
                   "and the mean over draws of the arm, with a 95\\%% interval from a two-level bootstrap over draws and episodes; negative "
                   "values favor the map. Accuracy: whole-record accuracy on set A, mean over draws. The first five draws are the pre-specified "
                   "draws of Table 4." % nd,
                   [0.25, 0.115, 0.15, 0.06, 0.115, 0.15, 0.06],
                   ["Adaptation (labels used)", "100 labels: missed, \\%", "100: map minus arm, pp (95\\% CI)", "100: acc., \\%",
                    "300 labels: missed, \\%", "300: map minus arm, pp (95\\% CI)", "300: acc., \\%"], rows))
    for n in (100, 300):
        b = k3["n%d" % n]
        dig.append("first5 vs all%d n=%d: %s" % (nd, n, json.dumps(b["first5_vs_all20"])))
        for k, v in b["comparisons_mean_of_draws"].items():
            if k.startswith(("wsp-", "mft-", "bias-", "vecs-", "mbias-", "q4p-")):
                dig.append("  n=%d %s diff %+.4f ci %s p %.4f" % (n, k, v["diff"], v["ci"], v["p"]))
    dig.append("C chosen (count by value) per family: " + json.dumps(_c_counts(R["K3_C_chosen"])))

    # ---------------- C2 unlabeled budget
    k9 = R["K9_unlabelled_budget"]
    raw_err = k9["full_1000"]["err_raw"]
    rows = []
    for n in (25, 50, 100, 300, 500):
        b = k9["p%d" % n]
        rows.append(["%d (10 draws)" % n, "%s (%s--%s)" % (pct(b["share_mean_of_draws"]), pct(b["share_min"]), pct(b["share_max"])),
                     "%s (%s)" % (pp(b["map_vs_rawp"]["diff"]), ci(b["map_vs_rawp"]["ci"])),
                     "%s (%s)" % (pp(b["map_vs_full_map"]["diff"]), ci(b["map_vs_full_map"]["ci"])),
                     f(b["err_mean"] / raw_err, 3), f(b["err_recentre_mean"] / raw_err, 3), f(1000 * b["fit_s_mean"], 0)])
        dig.append("C2 n=%d %s lambda %s acc %.4f cos %.5f" % (n, json.dumps({k: v for k, v in b.items() if k in ("share_mean_of_draws", "share_min", "share_max")}),
                                                            b["lambda_counts"], b["record_accuracy_mean"], b["cos_mean"]))
    full = k9["full_1000"]
    rows.append(["1,000 (all fitting reports)", pct(full["share"]), pp(k13d["alnp"] - k13d["rawp"]), "0", f(full["err"] / raw_err, 3),
                 f(full["err_recentre"] / raw_err, 3), f(1000 * full["fit_s"], 0)])
    dig.append("C2 full: %s" % json.dumps(full))
    T.append(table("tabC2",
                   "Unlabeled budget of the map (exploratory; set A, medium load, arrival seed 11). Maps fitted on paired FP16 and Q4 vectors of "
                   "n development fitting reports, never on fresh reports (ten draws per size); the FP16 heads are those of Table 4. Missed share: "
                   "mean over draws (range); differences use the mean over draws, with 95\\% episode-bootstrap intervals. Error: mean squared "
                   "difference between the mapped (or recentered, same pairs) Q4 vector and the FP16 vector of the same fresh set-A report, in "
                   "FP16 standard deviations, as a fraction of that of the raw Q4 vector. Fit time: cloud CPU, one core.",
                   [0.17, 0.15, 0.17, 0.17, 0.11, 0.12, 0.08],
                   ["Unlabeled pairs", "Missed, \\%", "Map minus unchanged, pp (95\\% CI)", "Map minus 1,000-pair map, pp (95\\% CI)",
                    "Error, map", "Error, recentering", "Fit time, ms"], rows))

    # ---------------- C3 field substitution
    k12 = R["K12_propagation"]
    order = ["none", "a", "s", "p", "as", "ap", "sp", "asp"]
    rows = []
    for base, nm in (("rawp", "Q4, unchanged"), ("alnp", "Q4, map"), ("q4p", "Q4, retrained (1,000 labels)")):
        b = k12[base]
        cells = b["missed_share_by_fields_replaced"]
        sh = b["shapley"]
        rows.append([nm] + [pct(cells[k]) for k in order] + ["%s (%s)" % (f(sh[x]["pp"], 2, True), "%s to %s" % (f(sh[x]["ci95_pp"][0], 2, True), f(sh[x]["ci95_pp"][1], 2, True)))
                                                             for x in ("action", "sensor", "prio")])
        dig.append("C3 %s total removed %.3f pp, interaction %.3f pp, alone %s" % (base, b["total_removed_pp"], b["interaction_pp"],
                                                                                 {x: round(sh[x]["alone_pp"], 3) for x in sh}))
    T.append(table("tabC3",
                   "Gold-field substitution in all eight combinations (exploratory; set A, medium load, arrival seed 11): missed share (\\%) when "
                   "the listed fields of every record are replaced by their gold values (A action, S sensor, P priority; sensor and priority only "
                   "where the gold action carries them), and the Shapley share of each field in the misses removed by replacing all three "
                   "(pp, 95\\% episode-bootstrap interval). Replacing all three fields gives the gold records exactly (5.71\\%).",
                   [0.15, 0.055, 0.055, 0.055, 0.055, 0.055, 0.055, 0.055, 0.055, 0.135, 0.135, 0.135],
                   ["Arm", "None", "A", "S", "P", "A+S", "A+P", "S+P", "All", "Shapley A, pp", "Shapley S, pp", "Shapley P, pp"], rows))
    mg = k12["margins"]
    for arm in ("rawp", "alnp", "q4p"):
        dig.append("margins %s: %s" % (arm, json.dumps(mg[arm])))

    # ---------------- C4 robustness: simulator variants and Qwen
    k13 = R["K13_simulator_variants"]
    labels = [("default", "Default (Table 4): 3 UAVs, one thermal"), ("uav5_1th", "5 UAVs, one thermal"), ("uav5_2th", "5 UAVs, two thermal"),
              ("dl075", "Deadlines $\\times$0.75"), ("dl150", "Deadlines $\\times$1.5"), ("burst", "Burst arrivals (bursts of 5)"),
              ("bundle1", "Bundle length 1"), ("bundle5", "Bundle length 5")]
    rows = []
    for v, nm in labels:
        b = k13[v]
        s, c = b["shares"], b["comparisons"]
        rows.append([nm] + [pct(s[k]) for k in ("gold", "f16p", "rawp", "alnp", "q4p", "q4p_n100m")] +
                    ["%s (%s)" % (pp(c[k]["diff"]), ci(c[k]["ci"])) for k in ("rawp-f16p", "alnp-rawp", "alnp-q4p_n100m")] +
                    [pp(c["q4p_goldS-q4p"]["diff"])])
        dig.append("C4 %s %s" % (v, json.dumps({k: [round(c[k]["diff"], 5), [round(x, 5) for x in c[k]["ci"]]] for k in c})))
    if Q is not None:
        rows.append("HLINE")
        qrows = [(Q, lv, "Qwen2.5-1.5B, prefix, %s load" % w) for lv, w in (("L", "low"), ("M", "medium"), ("H", "high"))]
        if QE is not None:
            qrows += [(QE, lv, "Qwen2.5-1.5B, end, %s load" % w) for lv, w in (("L", "low"), ("M", "medium"), ("H", "high"))]
        for QQ, lv, nm in qrows:
            b = QQ["A_%s_s11" % lv]
            s, c = b["shares"], b["comparisons"]
            rows.append([nm] + [pct(s[k]) for k in ("gold", "f16p", "rawp", "alnp", "q4p", "q4p_n100")] +
                        ["%s (%s)" % (pp(c[k]["diff"]), ci(c[k]["ci"])) for k in ("H1", "H2a", "H3")] + [pp(c["S10"]["diff"])])
            dig.append("%s %s" % (nm, json.dumps({k: [v["comparison"], round(v["diff"], 5), [round(x, 5) for x in v["ci"]], v["p"], round(v["llama_diff"], 5)]
                                                   for k, v in c.items()})))
            dig.append("%s shares %s" % (nm, json.dumps({k: round(v, 5) for k, v in s.items()})))
        dig.append("Qwen fit %s" % json.dumps(Q["fit"]))
        dig.append("Qwen record acc %s" % json.dumps({k: round(v, 4) for k, v in Q["record_accuracy_setA"].items() if "_d" not in k}))
        dig.append("Qwen changed vs f16p %s" % json.dumps({k: v for k, v in Q["records_changed_vs_f16p"].items() if "_d" not in k}))
        dig.append("Qwen similarity %s" % json.dumps(Q["vector_similarity_setA"]))
    cap_q = (", and a second model family (Qwen2.5-1.5B-Instruct, FP16 and Q4\\_K\\_M; heads, map and retraining refitted on the same "
             "development reports and label draws), read at the \\textit{prefix} position used throughout and at the \\textit{end} position "
             "(Section IV-A)") if Q is not None else ""
    T.append(table("tabC4",
                   "Robustness of the main comparisons (exploratory; set A, arrival seed 11, medium load unless stated): simulator variants that "
                   "replay the same records (Llama 3.2 1B)" + cap_q + ". Missed share (\\%); differences in pp with 95\\% "
                   "episode-bootstrap intervals; 100 labels: mean of the five pre-specified draws. Sensor: retrained (1,000 labels) with the gold "
                   "sensor minus retrained.",
                   [0.145, 0.05, 0.05, 0.055, 0.05, 0.05, 0.055, 0.15, 0.15, 0.15, 0.065],
                   ["Setting", "Gold", "FP16", "Q4 unch.", "Map", "Retr. all", "Retr. 100", "Unchanged minus FP16 (95\\% CI)",
                    "Map minus unchanged (95\\% CI)", "Map minus retr. 100 (95\\% CI)", "Sensor"], rows))

    # ---------------- digests of text-only results
    st = R["K10_statistics"]
    dig.append("K10 S1: " + json.dumps(st["map_vs_all_label_retraining"]))
    for k, v in eff.items():
        dig.append("K10 eff %s: abs %+.3f pp [%s] rel %+.4f [%s]" % (k, v["abs_diff_pp"], ", ".join("%+.3f" % x for x in v["abs_ci95_pp"]),
                                                                   v["relative_change"], ", ".join("%+.4f" % x for x in v["relative_ci95"])))
    dig.append("K10 precision " + json.dumps(st["human_report_precision"]["rows"]))
    dig.append("K7 " + json.dumps(R["K7_incident_accounting"]))
    dig.append("K11 " + json.dumps(R["K11_cpu_margins"]))
    dig.append("K0 " + json.dumps(R.get("K0_sanity_missed")) + json.dumps(R.get("K0_sanity_per_episode_equal")))
    (out / "appendix_c_tables.tex").write_text("\n\n".join(T) + "\n", encoding="utf-8")
    (out / "digest.txt").write_text("\n".join(dig) + "\n", encoding="utf-8")
    print("\n".join(dig))


def _c_counts(cc):
    out = {}
    for key, fams in cc.items():
        n = key.split("_")[0]
        for fam, hs in fams.items():
            for h, c in hs.items():
                d = out.setdefault("%s %s %s" % (n, fam, h), {})
                d[str(c)] = d.get(str(c), 0) + 1
    return out


if __name__ == "__main__":
    main()
