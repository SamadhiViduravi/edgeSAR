"""
EdgeSAR heads - exploratory controls: write the plain-English report (results_controls/controls_report.md).
The reading rules used in section 4 are the ones written in CONTROLS_PLAN.md before the run.
"""
import json

import heads_controls as hc2
import heads_report as hr
from heads_common import now_text

P = hr._p
CI = hr.ci
TABLE = hr.table


def _pair_row(label, f):
    fam = f.get("table_family_ci")
    cell = CI(f["table_ci"]) + ("; resampling the 40 families: %s to %s" % (P(fam[1]), P(fam[2])) if fam else "")
    return [label, cell, "%d (%s)" % (f["action_changed"], P(f["action_changed"] / f["n"])),
            f["right_to_wrong"], f["wrong_to_right"], f["wrong_other"]]


def _spread_txt(s):
    return "%s (lowest %s, highest %s)" % (P(s["mean"]), P(s["min"]), P(s["max"]))


def write_controls_report(R, path, ccfg, meta_lines=None):
    W = []
    add = W.append
    n = R["n_held"]
    S, PR, BT, AU, VD = R["systems"], R["pairs"], R["bootstrap"], R["audit"], R["verdicts"]
    add("# EdgeSAR heads: exploratory controls")
    add("")
    add("Made: %s. Variant: `%s`. Reports: %d (development style A: %d, held-out style B: %d). "
        "Heads settings fingerprint: `%s`." % (R["created"], R["variant"], R["n_cases"], R["n_dev"], R["n_held"], R["heads_config_sha"][:8]))
    for m in meta_lines or []:
        add(m)
    add("")
    add("**Status: EXPLORATORY.** These controls were decided on 12 Nov 2026, AFTER the held-out B results of attempt 1 were seen. "
        "Nothing here was tuned on B, and the settings are the same as in step 3. The goal is to find out WHAT moved the answers, "
        "not to show a win. Every per-report answer is in `predictions_%s.csv`." % R["variant"])
    add("")

    # ---------------------------------------------------------------- 0
    c = R["attempt1_check"]
    add("## 0. Does this run give the same numbers as attempt 1?")
    add("")
    add("A MATCH is only a consistency check: the same code and the same data give the same numbers again. It does not show that the numbers are right.")
    add("")
    rp = R.get("reproduction")
    if rp:
        add("Reproduction of the saved run-1 records: **%s** (%d records compared, %d different, %d missing in run 1)."
            % (rp["status"], rp["rows_compared"], rp["rows_different"], rp["rows_missing_in_run1"]))
        add("")
    add("**%s.** %s" % (c["status"], " ".join(c["lines"][:1]) if c["status"] != "DIFFERENT" else ""))
    if c["status"] == "DIFFERENT":
        add("")
        add("Attempt 1 and this run disagree on the numbers below. Do NOT trust the rest of this report until we know why "
            "(different feature files? different settings?). Send me this file.")
        for l in c["lines"][:12]:
            add("* " + l)
    add("")

    # ---------------------------------------------------------------- 1
    add("## 1. What was the 27.5%? (the audit)")
    add("")
    add("The row is **Heads Q4 vs Heads FP16** (each head trained on its own vectors), held-out B, %d reports." % AU["n"])
    add("")
    add(TABLE(["Question", "Reports", "Share"], [
        ["The task table would be different (the number used in attempt 1)", AU["table_changing"], P(AU["table_changing"] / AU["n"])],
        ["Any field of the decision is different", AU["any_field"], P(AU["any_field"] / AU["n"])],
        ["The ACTION is different", AU["action_changed"], P(AU["action_changed"] / AU["n"])],
        ["Same action, but sensor, priority, location or link is different", AU["same_action_field_change"],
         P(AU["same_action_field_change"] / AU["n"])],
    ]))
    add("")
    add("Upper limit for action changes: two readers can disagree on the action in at most (errors of the FP16 heads) + (errors of the "
        "Q4 heads) = %d + %d = **%d** reports (%s). The measured action changes are **%d**, so the numbers are consistent."
        % (AU["fp16_action_errors"], AU["q4_action_errors"], AU["action_upper_bound"], P(AU["action_upper_bound"] / AU["n"]),
           AU["action_changed"])
        if AU["action_changed"] <= AU["action_upper_bound"] else
        "Upper limit for action changes: %d. The measured action changes are %d, which is MORE than the limit. "
        "Something is wrong with the numbers. Stop and send me this file." % (AU["action_upper_bound"], AU["action_changed"]))
    add("")
    if AU["top_transitions"]:
        add("Most common changes: " + "; ".join("%s (%d)" % (k, v) for k, v in AU["top_transitions"]) + ".")
        add("")

    # ---------------------------------------------------------------- 2
    add("## 2. The controls: how much do the answers move? (table-changing disagreement with the FP16 pipeline, held-out B)")
    add("")
    add("Read each row as: 'if the model is shrunk, in how many reports does the task table change?' The rows differ in WHAT is allowed to change.")
    add("")
    rows = []
    for a in ("Q8", "Q4"):
        rows.append(_pair_row("Separate heads: %s (vector AND head change)" % a, PR["Separate heads: %s vs FP16" % a]["held"]))
    for a in ("Q8", "Q4"):
        rows.append(_pair_row("Fixed FP16 head: %s (only the vector changes)" % a, PR["Fixed FP16 head: %s vs FP16 vectors" % a]["held"]))
    for a in ("Q8", "Q4"):
        rows.append(_pair_row("Fixed FP16 head, offset removed: %s" % a,
                              PR["Fixed FP16 head, offset removed: %s vs FP16 vectors" % a]["held"]))
    for a in ("Q8", "Q4"):
        rows.append(_pair_row("Shared head (one head, all precisions): %s" % a, PR["Shared head: %s vs FP16 vectors" % a]["held"]))
    for a in ("Q8", "Q4"):
        rows.append(_pair_row("Generative text (for comparison): %s" % a, PR["Generative: %s vs FP16" % a]["held"]))
    rows.append(["**Bootstrap-sample heads** vs the full-data FP16 head: %d heads trained on resampled dev families, FP16 vectors only "
                 "(only the training sample changes)" % BT["K"],
                 _spread_txt(BT["floor"]), "mean %s" % P(BT["floor_action"]["mean"]), "-", "-", "-"])
    if BT.get("floor_pairs"):
        rows.append(["Bootstrap head vs bootstrap head (consecutive pairs 1-2, 3-4, ...)", _spread_txt(BT["floor_pairs"]), "-", "-", "-", "-"])
    add(TABLE(["Comparison", "Table changes (95%% interval or spread over %d heads)" % BT["K"], "Action changed", "Right -> wrong",
               "Wrong -> right", "Both wrong, different"], rows))
    add("")
    add("'Right' means the whole record equals the gold answer. Dev A and all-1400 numbers are in controls_summary.json.")
    add("")
    add("### Spread over the %d bootstrap heads (held-out B)" % BT["K"])
    add("")
    add(TABLE(["Measure", "Mean", "Median", "Lowest", "Highest"], [
        [lab, P(BT[k]["mean"]), P(BT[k]["median"]), P(BT[k]["min"]), P(BT[k]["max"])] for lab, k in (
            ("Bootstrap head vs full-data FP16 head (table changes)", "floor"),
            ("Bootstrap head vs full-data FP16 head, action field only", "floor_action"),
            ("Same bootstrap head, Q8 vectors vs FP16 vectors", "fixed_q8"),
            ("Same bootstrap head, Q4 vectors vs FP16 vectors", "fixed_q4"),
            ("Same, Q8 vectors with offset removed", "off_q8"),
            ("Same, Q4 vectors with offset removed", "off_q4"),
            ("Bootstrap head accuracy on FP16 vectors: action", "own_fp16_action"),
            ("Bootstrap head accuracy on FP16 vectors: whole record", "own_fp16_record"))]))
    add("")
    add("A bootstrap sample holds about %s of the dev families (the rest are repeated), so a bootstrap head is a little weaker than "
        "the full-data head. These numbers measure **bootstrap training-sample variability of the head**. They are not a pure "
        "random-seed noise floor (head training has no random seed: it is deterministic)." % P(BT["unique_families_mean"] / BT["dev_families"], 0))
    add("")
    add("What the two percentages compare. The first row is the mean, over the %d bootstrap heads, of the share of B reports where a bootstrap "
        "head's task table differs from the full-data FP16 head's. The second row is the same share between two bootstrap heads (consecutive "
        "pairs), so it is head against head and is expected to be larger. **Neither number can be subtracted from the separate-heads "
        "disagreement** to get a quantization effect: the two comparisons use different heads, different training samples and different "
        "vectors, and the numbers are not additive." % BT["K"])
    add("")

    # ---------------------------------------------------------------- 3
    add("## 3. Are the answers right? (against the gold answers, held-out B)")
    add("")
    order = ["TF-IDF + LR", "Rule engine", "Generative FP16", "Generative Q4", "Heads FP16", "Heads Q8", "Heads Q4",
             hc2.S_FIX["Q8"], hc2.S_FIX["Q4"], hc2.S_OFF["Q4"], hc2.S_SHR["FP16"], hc2.S_SHR["Q8"], hc2.S_SHR["Q4"]]
    rows = []
    for name in order:
        b = S[name]["held"]
        f, cr = b["fields"], b["critical"]
        rows.append([name, P(b["action"][0]), P(b["record"][0]), P(f["sensor"][2]), P(f["priority"][2]), P(f["location"][2]),
                     P(f["link"][2]), cr["missed_alarm"], cr["wrong_close"], cr["priority_too_low"], cr["danger_total"],
                     cr["false_alarm"]])
    rows.append(["Bootstrap heads on FP16 vectors (mean of %d)" % BT["K"], P(BT["own_fp16_action"]["mean"]),
                 P(BT["own_fp16_record"]["mean"]), "-", "-", "-", "-", "-", "-", "-", "%.1f" % BT["own_fp16_danger"]["mean"], "-"])
    add(TABLE(["System", "Action", "Whole record", "Sensor", "Priority", "Location", "Link", "Missed alarm", "Wrong close",
               "Priority too low", "Danger total", "False alarm"], rows))
    add("")
    f0 = S["Heads FP16"]["held"]["fields"]
    add("Sensor, priority and location are counted on the %d reports whose gold answer is CREATE or UPDATE; link on the %d whose gold "
        "answer is UPDATE or CLOSE. The four error columns are COUNTS of reports (out of %d). They are my own rough proxies: "
        "'missed alarm' = gold says CREATE/UPDATE and the system does nothing; 'wrong close' = the system closes an incident gold does "
        "not close; 'priority too low' = right action but a lower priority number (3 is most urgent); 'danger total' = the first three added "
        "(no report is counted twice); 'false alarm' = the system starts or changes a record when gold does not (a wasted trip, "
        "less serious). The allocator harm test will replace them."
        % (f0["sensor"][1], f0["link"][1], n))
    add("")

    # ---------------------------------------------------------------- 4
    add("## 4. How to read it (rules written in CONTROLS_PLAN.md before this run)")
    add("")
    v1, v2, v3 = VD["V1_noise"], VD["V2_shared"], VD["V3_offset"]
    for a in ("Q4", "Q8"):
        s = v1[a]
        sep_rate = PR["Separate heads: %s vs FP16" % a]["held"]["table_changing"] / n
        if s["share"] is None:
            add("* **V1, bootstrap-sample variability, %s: %s.** The separate heads did not disagree, so there is nothing to explain." % (a, s["code"]))
            continue
        add("* **V1, bootstrap-sample variability, %s: %s.** The bootstrap-head disagreement is %s of the %s separate-heads disagreement (%s vs %s). %s" % (
            a, s["code"], P(s["share"], 0), a, P(BT["floor"]["mean"]), P(sep_rate),
            "Retraining a head on a slightly different sample of the SAME vectors already moves the answers by a similar amount. So the "
            "head is unstable on style B, and the separate-heads number alone cannot be read as a quantization effect. "
            "(This is a reading aid. It does not say how much of the number is quantization, and it is not a subtraction.)"
            if s["code"] == "TRAINING-SAMPLE VARIABILITY IS BIG" else
            "The bootstrap heads move much less than the separate heads do. That is consistent with the shrunk vectors mattering, "
            "but this reading aid does not measure how much."))
    add("* **V2, one shared head, Q4: %s.** Lower disagreement than separate heads: %s. Whole-record accuracy kept (within 2 points): %s. "
        "Danger errors not higher: %s." % (v2["code"], "yes" if v2["lower_disagreement"] else "no",
                                          "yes" if v2["accuracy_kept"] else "no", "yes" if v2["danger_not_higher"] else "no"))
    add("* **V3, offset removed from the Q4 vectors: %s.** In %s of the %d bootstrap heads the fixed-head disagreement dropped by at least "
        "5 points (mean drop %s)." % (v3["code"], P(v3["share_of_heads_with_clear_drop"], 0), BT["K"], P(v3["mean_reduction"])))
    add("")
    add("These codes are reading aids. They are not a registered test, and they decide nothing alone.")
    add("")

    # ---------------------------------------------------------------- 5
    add("## 5. Sanity checks")
    add("")
    o = R["offset"]
    add("* The average shift of the vectors (dev A, no labels) explains %s of the Q8 change and %s of the Q4 change. A LOW number means "
        "the change is not a simple constant shift, so an offset fix cannot do much." % (P(o["Q8"]["explained"]), P(o["Q4"]["explained"])))
    fl = R["fit_log"]
    add("* Fits: %d; stopped at the iteration limit: %d. Chosen regularisation C: %s." % (
        fl["fits"], fl["hit_iteration_limit"], ", ".join("%s x%d" % (k, v) for k, v in fl["chosen_c"].items())))
    add("* Family leak check: passed (the code stops if a family is in both training and test).")
    add("")

    # ---------------------------------------------------------------- 6
    add("## 6. What this cannot say")
    add("")
    add("* B was already seen in attempt 1, so everything here is exploratory. A claim needs fresh cases from a new generator seed and "
        "settings frozen before the run.")
    add("* Style B comes from the same generator as style A. It is a harder wording style, not independently written language.")
    add("* The bootstrap heads are trained on resampled data, so they are a slightly weak and slightly variable version of the real head. "
        "Their spread is training-sample variability, not a pure random-seed floor, and it is not subtracted from anything.")
    add("* A difference between FP16 and Q4 answers can go in either direction: compression can fix some answers and break others. "
        "Report what is observed, with its uncertainty, and do not call a small difference 'no effect' or a number of changes 'noise'.")
    add("* Fewer disagreements are not the goal by themselves: all heads can agree and still be wrong together. Look at section 3.")
    add("* 'Danger errors' are rough proxies. Which errors really cause late or missed victims is decided by the allocator harm test.")
    add("* Only Q8 and Q4_K_M were looked at. Nothing here says what happens at another bit width.")
    add("* Any repair changes the scores Shield uses, so Shield must be recalibrated on separate data after it.")
    text = "\n".join(W) + "\n"
    path.write_text(text, encoding="utf-8")
    return text


def write_controls_summary(R, path):
    path.write_text(json.dumps(R, indent=2, default=hr.jsonable), encoding="utf-8")
