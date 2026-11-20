"""
EdgeSAR heads test - run every number and write the plain-English report.

`analyze_all` does the maths (no model, no server). `write_report` turns the numbers into results_heads/heads_report.md.
Rules for reading the result were written down BEFORE the run in HEADS_TEST_PLAN.md; the three outcome rules in
section 1 of the report are the same rules, coded in `outcomes()` below.
"""
import json
from collections import Counter

import numpy as np

import heads_lib as hl
from heads_common import CFG, CFG_SHA, now_text, pc

SPLITS = ("held", "dev", "all")
ARMS = ["FP16", "Q8", "Q4"]
MODEL_KEY = {"FP16": "f16", "Q8": "Q8_0", "Q4": "Q4_K_M"}

# outcome rules (same as HEADS_TEST_PLAN.md)
O1_ALPHA = 0.05          # McNemar p-value, as in the pilot's gate G2
O3_MIN_AUROC = 0.70
O3_MIN_LIFT_AT_20 = 2.0


# ------------------------------------------------------------------ small helpers
def paired(ok_a, ok_b):
    ok_a, ok_b = np.asarray(ok_a, bool), np.asarray(ok_b, bool)
    b, c = int(np.sum(ok_a & ~ok_b)), int(np.sum(~ok_a & ok_b))
    return {"only_first": b, "only_second": c, "p": pc.mcnemar_exact(b, c)}


def strip_acc(a):
    return {"n": a["n"], "action": list(a["action"]), "record": list(a["record"])}


def strip_flip(f, cases=None, Ref=None, idx=None):
    out = {"n": f["n"], "table_changing": f["table_changing"], "table_ci": list(f["table_ci"]),
           "any_field": f["any_field"], "any_ci": list(f["any_ci"]), "right_to_wrong": f["right_to_wrong"],
           "wrong_to_right": f["wrong_to_right"], "wrong_other": f["wrong_other"],
           "top_transitions": [[k, v] for k, v in f["transitions"].most_common(5)]}
    if cases is not None:
        out["ref_already_wrong"] = hl.head_correct_split(cases, Ref, f["tab_mask"], idx)
    return out


def recall_by_action(cases, D, idx):
    out = {}
    for a in hl.ACTIONS:
        rows = [i for i in idx if cases[i]["gold"]["action"] == a]
        out[a] = (sum(1 for i in rows if D[i]["norm"]["action"] == a) / len(rows)) if rows else None
    return out


def gate_block(conf, mask, fractions):
    return {"flips": int(np.sum(mask)), "n": int(len(mask)), "auroc": hl.auroc_flip(conf, mask),
            "coverage": hl.flag_coverage(conf, mask, fractions)}


# ------------------------------------------------------------------ all the numbers
def analyze_all(cases, dev, held, feats, G, B, cfg=None, say=print, controls=True):
    cfg = cfg or CFG
    N = len(cases)
    idx = {"held": list(held), "dev": list(dev), "all": list(range(N))}
    R = {"created": now_text(), "config_sha": CFG_SHA, "n_cases": N, "n_dev": len(dev), "n_held": len(held),
         "primary_variant": cfg["primary_variant"], "variants": {}, "reference": {}}

    ref_sys = {"Rule engine": B["rule"], "TF-IDF + LR": B["tfidf_lr"], "Generative FP16": G["FP16"],
               "Generative Q8": G["Q8"], "Generative Q4": G["Q4"]}
    R["reference"]["accuracy"] = {k: {sp: strip_acc(hl.accuracy(cases, D, idx[sp])) for sp in SPLITS} for k, D in ref_sys.items()}
    R["reference"]["recall_held"] = {k: recall_by_action(cases, D, idx["held"]) for k, D in ref_sys.items()}
    R["reference"]["gen_flips"] = {a: {sp: strip_flip(hl.flip_stats(cases, G["FP16"], G[a], idx[sp]), cases, G["FP16"], idx[sp])
                                       for sp in SPLITS} for a in ("Q8", "Q4")}
    R["reference"]["class_counts_held"] = dict(Counter(cases[i]["gold"]["action"] for i in idx["held"]))

    for v in cfg["variants"]:
        Xs = {a: feats.get((MODEL_KEY[a], v)) for a in ARMS}
        if any(x is None for x in Xs.values()):
            R["variants"][v] = {"missing": [a for a in ARMS if Xs[a] is None]}
            continue
        say("variant '%s': training heads ..." % v)
        log = hl.FitLog()
        prog = lambda a, b, tag="": say("   fold %d of %d %s" % (a, b, tag))
        P16 = hl.run_scheme(Xs["FP16"], {"FP16": Xs["FP16"], "Q8": Xs["Q8"], "Q4": Xs["Q4"]}, cases, dev, held, cfg, log=log,
                            progress=lambda a, b: prog(a, b, "(FP16 heads)"))
        P8 = hl.run_scheme(Xs["Q8"], {"Q8": Xs["Q8"]}, cases, dev, held, cfg, log=log,
                           progress=lambda a, b: prog(a, b, "(Q8 heads)"))["Q8"]
        P4 = hl.run_scheme(Xs["Q4"], {"Q4": Xs["Q4"]}, cases, dev, held, cfg, log=log,
                           progress=lambda a, b: prog(a, b, "(Q4 heads)"))["Q4"]
        own_P = {"FP16": P16["FP16"], "Q8": P8, "Q4": P4}
        tr_P = {"Q8": P16["Q8"], "Q4": P16["Q4"]}
        own = {a: hl.decisions_from_probs(cases, own_P[a]) for a in ARMS}
        tr = {a: hl.decisions_from_probs(cases, tr_P[a]) for a in ("Q8", "Q4")}

        V = {"fit_log": {"fits": log.fits, "hit_iteration_limit": log.hit_limit,
                         "chosen_c": {str(k): v_ for k, v_ in sorted(log.chosen_c.items())}}}
        systems = {"Heads FP16": own["FP16"], "Heads Q8": own["Q8"], "Heads Q4": own["Q4"],
                   "FP16-trained heads on Q8 vectors": tr["Q8"], "FP16-trained heads on Q4 vectors": tr["Q4"]}
        V["accuracy"] = {k: {sp: strip_acc(hl.accuracy(cases, D, idx[sp])) for sp in SPLITS} for k, D in systems.items()}
        V["recall_held"] = {k: recall_by_action(cases, D, idx["held"]) for k, D in systems.items()}

        # does the heads reading match the other readers? (held-out, same cases, paired)
        a_h = hl.accuracy(cases, own["FP16"], idx["held"])
        V["mcnemar_held"] = {}
        for name, D in (("TF-IDF + LR", B["tfidf_lr"]), ("Rule engine", B["rule"]), ("Generative FP16", G["FP16"])):
            o = hl.accuracy(cases, D, idx["held"])
            V["mcnemar_held"][name] = {"action": paired(a_h["a_ok"], o["a_ok"]), "record": paired(a_h["r_ok"], o["r_ok"])}

        # flips against the FP16 heads
        V["flips"] = {"own": {}, "transfer": {}}
        gate = {}
        for a in ("Q8", "Q4"):
            V["flips"]["own"][a], V["flips"]["transfer"][a], gate[a] = {}, {}, {}
            for sp in SPLITS:
                f = hl.flip_stats(cases, own["FP16"], own[a], idx[sp])
                V["flips"]["own"][a][sp] = strip_flip(f, cases, own["FP16"], idx[sp])
                ft = hl.flip_stats(cases, own["FP16"], tr[a], idx[sp])
                V["flips"]["transfer"][a][sp] = strip_flip(ft, cases, own["FP16"], idx[sp])
                conf_dep = [own[a][i]["conf"] for i in idx[sp]]
                conf_ref = [own["FP16"][i]["conf"] for i in idx[sp]]
                gate[a][sp] = {"deployed": gate_block(conf_dep, f["tab_mask"], cfg["flag_fractions"]),
                               "fp16_conf": gate_block(conf_ref, f["tab_mask"], cfg["flag_fractions"])}
        V["gate"] = gate

        V["cosine"] = {a: hl.cosine_stats(Xs["FP16"], Xs[a]) for a in ("Q8", "Q4")}
        V["dim"] = int(Xs["FP16"].shape[1])

        if controls and v == cfg["primary_variant"]:
            y, rec = hl.make_labels(cases)
            rng = np.random.RandomState(cfg["seed"])
            yp = {k: x.copy() for k, x in y.items()}
            yp["action"][np.array(dev)] = rng.permutation(y["action"][np.array(dev)])
            Pc = hl.run_scheme(Xs["FP16"], {"c": Xs["FP16"]}, cases, dev, held, cfg, labels=(yp, rec), heads=("action",))["c"]["action"]
            pred = np.array([hl.ACTIONS[int(k)] for k in Pc.argmax(axis=1)])
            dv = np.array(dev)
            maj = Counter(y["action"][dv]).most_common(1)[0]
            V["control_shuffled"] = {"dev_accuracy": float(np.mean(pred[dv] == y["action"][dv])),
                                     "majority_class": maj[0], "majority_share": maj[1] / len(dv)}
        R["variants"][v] = V
    R["outcomes"] = outcomes(R)
    return R


# ------------------------------------------------------------------ the three outcome rules (primary variant, held-out B)
def outcomes(R):
    v = R["primary_variant"]
    V = R["variants"].get(v)
    if not V or "missing" in V:
        return None
    out = {}
    # O1: do the heads read as well as TF-IDF/LR? (action correctness, paired, held-out)
    m = V["mcnemar_held"]["TF-IDF + LR"]["action"]
    code = "SAME"
    if m["p"] < O1_ALPHA:
        code = "BETTER" if m["only_first"] > m["only_second"] else "WORSE"
    g = V["mcnemar_held"]["Generative FP16"]["action"]
    gcode = "SAME"
    if g["p"] < O1_ALPHA:
        gcode = "BETTER" if g["only_first"] > g["only_second"] else "WORSE"
    out["O1"] = {"vs_tfidf": code, "vs_generative_fp16": gcode, "tfidf": m, "generative": g}
    # O2: do the heads change less than text generation, when the model is shrunk? (held-out)
    o2 = {}
    for a in ("Q8", "Q4"):
        h = V["flips"]["own"][a]["held"]
        gen = R["reference"]["gen_flips"][a]["held"]["table_ci"][0]
        o2[a] = {"heads_pct": h["table_ci"][0], "heads_hi": h["table_ci"][2], "heads_lo": h["table_ci"][1],
                 "generative_pct": gen, "code": "LOWER" if h["table_ci"][2] < gen else "NOT SHOWN LOWER"}
    out["O2"] = o2
    # O3: does low confidence of the deployed (shrunk) head point at the flips? (held-out, Q4)
    q = V["gate"]["Q4"]["held"]["deployed"]
    row20 = next((r for r in q["coverage"] if abs(r["fraction"] - 0.2) < 1e-9), None)
    lift = row20["lift"] if row20 else None
    ok = (q["auroc"] is not None and q["auroc"] >= O3_MIN_AUROC and lift is not None and lift >= O3_MIN_LIFT_AT_20)
    out["O3"] = {"auroc": q["auroc"], "lift_at_20": lift, "flips": q["flips"], "n": q["n"],
                 "coverage_at_20": row20["coverage"] if row20 else None,
                 "code": "USEFUL" if ok else ("TOO FEW FLIPS TO JUDGE" if q["flips"] < 10 else "NOT SHOWN")}
    return out


# ------------------------------------------------------------------ writing the report
def _p(x, nd=1):
    return "n/a" if x is None else ("%." + str(nd) + "f%%") % (100 * x)


def ci(t):
    return "%s (%.1f to %.1f)" % (_p(t[0]), 100 * t[1], 100 * t[2])


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def pv(p):
    return "p < 0.001" if p < 0.001 else "p = %.3f" % p


def write_report(R, path, meta_lines=None):
    L, W = [], None
    W = L.append
    prim = R["primary_variant"]
    W("# EdgeSAR heads test: report")
    W("")
    W("Made: %s. Settings fingerprint (heads_config.json): `%s`. Reports: %d (development style A: %d, held-out style B: %d)." % (
        R["created"], R["config_sha"][:8], R["n_cases"], R["n_dev"], R["n_held"]))
    for m in (meta_lines or []):
        W(m)
    W("")
    W("## How to read this report")
    W("")
    W("* **Heads** = three small classifiers (action, sensor, priority) that read the model's hidden state instead of letting "
      "the model write text. The place and the incident id come from string matching, the same as in the TF-IDF/LR baseline. "
      "Heads are *trained* on style A labels. So this is a model plus a small trained part, not the model as it is.")
    W("* **Table-changing disagreement** = how often two systems would give a different task table (the pilot's \"operational flip\").")
    W("* **Style B (held-out) is the fair test.** Style A repeats its wording, so every simple method looks very good there "
      "(TF-IDF/LR gets 100%% on A). Look at B first. B has only %d reports, so its intervals are wide." % R["n_held"])
    W("* The main variant is **'%s'** (the exact pilot prompt; the vector is the last token's hidden state). Variant 'prefix' "
      "(same prompt plus `{\"action\":\"`) is shown after it. Only the main variant is used for the three outcome rules." % prim)
    W("")

    O = R.get("outcomes")
    W("## 1. The three outcomes (rules written before the run)")
    W("")
    if not O:
        W("The main variant has no feature files yet. Run step 2.")
    else:
        o1, o2, o3 = O["O1"], O["O2"], O["O3"]
        W(table(["Outcome", "Rule", "Result"], [
            ["O1 Do the heads read as well as TF-IDF/LR?",
             "Held-out, action correct, paired test (McNemar), p < 0.05 decides",
             "**%s** (heads only right: %d, TF-IDF/LR only right: %d, %s). Against generative FP16: **%s** (%d vs %d, %s)" % (
                 o1["vs_tfidf"], o1["tfidf"]["only_first"], o1["tfidf"]["only_second"], pv(o1["tfidf"]["p"]),
                 o1["vs_generative_fp16"], o1["generative"]["only_first"], o1["generative"]["only_second"], pv(o1["generative"]["p"]))],
            ["O2 Do the heads change less than text generation when the model is shrunk?",
             "Held-out, table-changing disagreement with FP16: LOWER if the heads' 95% upper bound is below the generative point value",
             "Q4: heads %s (up to %.1f%%) vs generative %s: **%s**. Q8: heads %s (up to %.1f%%) vs generative %s: **%s**" % (
                 _p(o2["Q4"]["heads_pct"]), 100 * o2["Q4"]["heads_hi"], _p(o2["Q4"]["generative_pct"]), o2["Q4"]["code"],
                 _p(o2["Q8"]["heads_pct"]), 100 * o2["Q8"]["heads_hi"], _p(o2["Q8"]["generative_pct"]), o2["Q8"]["code"])],
            ["O3 Does low confidence point at the cases that flip?",
             "Held-out, Q4 head's own confidence: AUROC >= %.2f and the least-confident 20%% holds >= %.1fx its share of flips" % (O3_MIN_AUROC, O3_MIN_LIFT_AT_20),
             "**%s** (AUROC %s, share of flips caught by the least-confident 20%%: %s, flips: %d of %d)" % (
                 o3["code"], "n/a" if o3["auroc"] is None else "%.2f" % o3["auroc"], _p(o3["coverage_at_20"]), o3["flips"], o3["n"])],
        ]))
        W("")
        W("What the three codes mean together (this is only a guide; you decide with your supervisors):")
        W("")
        W("* O1 WORSE: the hidden state reads worse than words here. Stop the heads line. Keep the benchmark path and the Shield-only idea.")
        W("* O1 SAME or BETTER, O2 LOWER, O3 USEFUL: the \"prevent\" and \"sharpen\" lines look worth building next.")
        W("* O1 SAME or BETTER but O2 NOT SHOWN LOWER: the heads read well, but shrinking still moves them. The \"absorb\" and \"cover\" lines matter more.")
        W("* O2 LOWER but O3 NOT SHOWN: shrinking is calmer with heads, but we cannot yet say which cases are risky.")
        W("* If B has too few flips to judge (O3), say so in your own report. Do not stretch it.")
    W("")

    ref = R["reference"]
    for v in [prim] + [x for x in R["variants"] if x != prim]:
        V = R["variants"].get(v)
        W("## %s Variant '%s'%s" % ("2." if v == prim else "3.", v, " (main)" if v == prim else " (second look, not used for the outcome rules)"))
        W("")
        if V is None or "missing" in V:
            W("Not available yet (missing: %s)." % (", ".join(V["missing"]) if V else "all"))
            W("")
            continue
        W("### Can the heads read the reports? (action right / whole record right)")
        W("")
        rows = []
        for k in ("Rule engine", "TF-IDF + LR", "Generative FP16", "Generative Q8", "Generative Q4"):
            a = ref["accuracy"][k]
            rows.append([k, ci(a["held"]["action"]), ci(a["held"]["record"]), _p(a["dev"]["action"][0]), _p(a["dev"]["record"][0])])
        for k in ("Heads FP16", "Heads Q8", "Heads Q4"):
            a = V["accuracy"][k]
            rows.append(["**%s**" % k, ci(a["held"]["action"]), ci(a["held"]["record"]), _p(a["dev"]["action"][0]), _p(a["dev"]["record"][0])])
        W(table(["System", "Held-out B: action", "Held-out B: whole record", "Dev A: action", "Dev A: whole record"], rows))
        W("")
        W("Dev A for the heads and TF-IDF/LR is out-of-fold (the folds are grouped by family, so no family is in both training and test).")
        W("")
        W("Recall on held-out B, by true action (how often the true action was found):")
        W("")
        rrows = []
        for k, rec_ in (("Rule engine", ref["recall_held"]["Rule engine"]), ("TF-IDF + LR", ref["recall_held"]["TF-IDF + LR"]),
                        ("Generative FP16", ref["recall_held"]["Generative FP16"]), ("Heads FP16", V["recall_held"]["Heads FP16"]),
                        ("Heads Q4", V["recall_held"]["Heads Q4"])):
            rrows.append([k] + [_p(rec_[a]) for a in hl.ACTIONS])
        W(table(["System"] + [a.replace("_", " ").title() for a in hl.ACTIONS], rrows))
        W("")
        W("Paired tests on held-out B (Heads FP16 against each other system):")
        W("")
        mrows = []
        for name, m in V["mcnemar_held"].items():
            mrows.append([name, "%d vs %d, %s" % (m["action"]["only_first"], m["action"]["only_second"], pv(m["action"]["p"])),
                          "%d vs %d, %s" % (m["record"]["only_first"], m["record"]["only_second"], pv(m["record"]["p"]))])
        W(table(["Heads FP16 vs", "Action right: heads only / other only", "Whole record right: heads only / other only"], mrows))
        W("")

        W("### Does shrinking change the decisions? (table-changing disagreement with FP16)")
        W("")
        grows = []
        for a in ("Q8", "Q4"):
            gf = ref["gen_flips"][a]
            grows.append(["Generative %s vs generative FP16" % a] + [ci(gf[sp]["table_ci"]) for sp in SPLITS])
            ho = V["flips"]["own"][a]
            grows.append(["**Heads %s vs Heads FP16** (each trained on its own vectors)" % a] + [ci(ho[sp]["table_ci"]) for sp in SPLITS])
            ht = V["flips"]["transfer"][a]
            grows.append(["FP16-trained heads applied to %s vectors (no retraining)" % a] + [ci(ht[sp]["table_ci"]) for sp in SPLITS])
        W(table(["Comparison", "Held-out B (%d)" % R["n_held"], "Dev A (%d)" % R["n_dev"], "All %d" % R["n_cases"]], grows))
        W("")
        W("Any field of the decision different (not only the task table), held-out B: " + "; ".join(
            "%s: generative %s, heads %s" % (a, _p(ref["gen_flips"][a]["held"]["any_ci"][0]), _p(V["flips"]["own"][a]["held"]["any_ci"][0]))
            for a in ("Q8", "Q4")) + ".")
        W("")
        W("Important: two classifiers trained on the same labels agree whenever both are right. Low disagreement on A is mostly "
          "\"A is easy\". Compare on B, and look at the next table.")
        W("")

        W("### Which way do the changes go? (Q4 vs FP16; whole record right or wrong)")
        W("")
        drows = []
        for lab, f in (("Generative, held-out B", ref["gen_flips"]["Q4"]["held"]), ("Heads, held-out B", V["flips"]["own"]["Q4"]["held"]),
                       ("Generative, all %d" % R["n_cases"], ref["gen_flips"]["Q4"]["all"]), ("Heads, all %d" % R["n_cases"], V["flips"]["own"]["Q4"]["all"])):
            drows.append([lab, f["any_field"], f["right_to_wrong"], f["wrong_to_right"], f["wrong_other"],
                          f["table_changing"], f.get("ref_already_wrong", "n/a")])
        W(table(["", "Any field changed", "FP16 right -> Q4 wrong", "FP16 wrong -> Q4 right", "Both wrong, different",
                 "Table-changing", "Table-changing where FP16 was already wrong"], drows))
        W("")
        W("\"Right\" means the whole record equals the gold answer. The first four numbers add up (right->wrong + wrong->right + both wrong = any field changed), as in the pilot report.")
        W("")

        W("### Can we point at the cases that will flip?")
        W("")
        W("The deployed model is the shrunk one. Its own confidence = the smaller of the probabilities of the heads it uses. "
          "We flag the least-confident share of reports and ask: how many of the Q4-vs-FP16 (or Q8-vs-FP16) table-changing cases fall inside? "
          "\"Left over\" = flips that stay after the flagged reports are handed to FP16, as a share of all reports in that split.")
        W("")
        grows = []
        for a in ("Q4", "Q8"):
            for sp in ("held", "all"):
                g_ = V["gate"][a][sp]["deployed"]
                row = ["Heads %s, %s" % (a, "held-out B" if sp == "held" else "all"), "%d of %d" % (g_["flips"], g_["n"]),
                       "n/a" if g_["auroc"] is None else "%.2f" % g_["auroc"]]
                for cv in g_["coverage"]:
                    row.append("%s caught, %s left" % (_p(cv["coverage"], 0), _p(cv["remaining_share"])))
                grows.append(row)
        heads = ["Where", "Flips", "AUROC"] + ["Flag least-confident %d%%" % round(100 * f_) for f_ in CFG["flag_fractions"]]
        W(table(heads, grows))
        W("")
        g_ = V["gate"]["Q4"]["held"]["fp16_conf"]
        W("For comparison, using the FP16 head's confidence for the Q4 flips on held-out B: AUROC %s." % (
            "n/a" if g_["auroc"] is None else "%.2f" % g_["auroc"]))
        W("")

        W("### Sanity checks")
        W("")
        W("* Hidden-state size: %d numbers per report. Cosine between the FP16 vector and the shrunk vector for the same report: "
          "Q8 mean %.4f (lowest %.4f), Q4 mean %.4f (lowest %.4f). 1.0 = the vector did not move." % (
              V["dim"], V["cosine"]["Q8"]["mean"], V["cosine"]["Q8"]["min"], V["cosine"]["Q4"]["mean"], V["cosine"]["Q4"]["min"]))
        fl = V["fit_log"]
        grid = sorted(float(x) for x in CFG["c_grid"])
        edge = sum(c for k, c in fl["chosen_c"].items() if float(k) in (grid[0], grid[-1]))
        W("* Fits: %d; stopped at the iteration limit: %d. Chosen regularisation C: %s. %s" % (
            fl["fits"], fl["hit_iteration_limit"], ", ".join("%s x%d" % (k, c) for k, c in fl["chosen_c"].items()),
            ("The grid edge was chosen in %d of %d fits, so the grid may be too narrow. Say so in your own report; do not widen it after seeing B."
             % (edge, fl["fits"])) if edge > 0.5 * fl["fits"] else ""))
        if "control_shuffled" in V:
            c_ = V["control_shuffled"]
            W("* Shuffled-label control (action head, FP16, dev A, labels randomly mixed): accuracy %s. The most common class (%s) is %s. "
              "If the control is far above that, something leaks. Family leak check: passed (the code stops if a family is in both train and test)." % (
                  _p(c_["dev_accuracy"]), c_["majority_class"], _p(c_["majority_share"])))
        W("")

    W("## 4. What this test cannot say")
    W("")
    W("* It does not say anything about harm (delay to a person). Only the simulator can. Table-changing disagreement is a pointer, not harm.")
    W("* The reports are made-up and the labels come from the generator that wrote them. Heads learn that generator's habits. Style B is written by the same author program.")
    W("* Heads are trained. The claim \"a quantised model is stable\" is not the same as \"a quantised model plus trained heads is stable\".")
    W("* Only the last layer's last-token vector is used (that is all llama.cpp gives). Middle layers may carry more. If this test is weak, that is one thing to try next, not a proof that hidden states do not work.")
    W("* Held-out B has %d reports, so its intervals are wide. The pilot cases must not be reused in the confirmatory study." % R["n_held"])
    W("* Choices (variant, regularisation grid, outcome rules) were fixed before the run. Any change after you see B must be written in your log as a new attempt (attempts.log keeps count).")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return "\n".join(L)


def jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Counter):
        return dict(o)
    raise TypeError(type(o))


def write_summary(R, path):
    path.write_text(json.dumps(R, indent=2, default=jsonable), encoding="utf-8")
