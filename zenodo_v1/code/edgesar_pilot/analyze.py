"""
Read the saved model answers, score them, and write results/pilot_report.md (plain English) + results/summary.json.

  python analyze.py

It never calls a model. You can run it as often as you like. Needs: numpy and scikit-learn.
Every number in the report comes from the files in runs/ and data/. Nothing is typed in by hand.
"""
import argparse
import csv
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

from common import (ROOT, effect, gold_norm, load_cases, load_config, load_subsets, mcnemar_exact, parse_decision,
                    pct, schema_ok, strict_key, transition, validate, wilson)

# ------------------------------------------------------------------ numbers taken from the design
DEV_DECISIONS = 14400          # decisions per stage (development and held-out)
HARMFUL_NEEDED_DEV = 120       # harmful flips needed in development
HARMFUL_NEEDED_HELD = 60       # harmful flips needed in held-out
PLANNED_CALLS = 132200         # confirmatory model calls planned
CALL_CAP = 135000              # hard cap on calls
HOUR_CAP = 75                  # hours available
HARM_SHARES = [0.05, 0.10, 0.25]
Z80_ONE_SIDED = 0.8416212      # "lower 80% bound" read as a one-sided 80% bound
N_BOOT = 2000

SHORT = {"CREATE_VERIFICATION": "CREATE", "UPDATE_INCIDENT": "UPDATE", "CLOSE_INCIDENT": "CLOSE", "NO_ACTION": "NO_ACTION"}
ACTION_LABELS = ["CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION"]
# (label, run name) for the models compared with FP16, in the order they are shown
ARMS = [("Q8_0", "q8_P1"), ("Q4_K_M", "q4_P1"), ("Q3_K_M", "q3_P1")]


# ------------------------------------------------------------------ loading
def read_jsonl(path):
    out = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        out[r["case_id"]] = r
                    except Exception:
                        pass
    return out


def process(rec, case):
    if rec is None or "text" not in rec:
        return None
    obj, _ = parse_decision(rec["text"])
    norm, status = validate(obj, case)
    return {"norm": norm, "status": status, "parsed": obj is not None, "schema": schema_ok(obj) if obj is not None else False,
            "eff": effect(norm, case), "key": strict_key(norm), "rec": rec, "truncated": rec.get("stop_type") == "limit"}


def process_norms(norms, cases_by_id):
    out = {}
    for cid, norm in norms.items():
        c = cases_by_id[cid]
        out[cid] = {"norm": norm, "status": "ok", "parsed": True, "schema": True, "eff": effect(norm, c),
                    "key": strict_key(norm), "rec": None, "truncated": False}
    return out


# ------------------------------------------------------------------ statistics helpers
def cluster_boot(values, fam, n_boot=N_BOOT, seed=11):
    """Mean of per-case values with a family (cluster) bootstrap: whole families are resampled."""
    values = np.asarray(values, dtype=float)
    fam = np.asarray(fam)
    uniq, inv = np.unique(fam, return_inverse=True)
    sums = np.bincount(inv, weights=values)
    cnts = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    k = len(uniq)
    idx = rng.integers(0, k, size=(n_boot, k))
    means = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    return {"mean": float(values.mean()), "p2.5": float(np.percentile(means, 2.5)), "p20": float(np.percentile(means, 20)),
            "p97.5": float(np.percentile(means, 97.5))}


def paired_compare(corr_a, corr_b, fam):
    """Paired comparison of two systems on the same cases. a - b."""
    a = np.asarray(corr_a, dtype=bool)
    b = np.asarray(corr_b, dtype=bool)
    only_a = int((a & ~b).sum())
    only_b = int((~a & b).sum())
    p = mcnemar_exact(only_a, only_b)
    bt = cluster_boot(a.astype(float) - b.astype(float), fam)
    return {"a_only": only_a, "b_only": only_b, "p": p, "diff": bt["mean"], "lo": bt["p2.5"], "hi": bt["p97.5"]}


def difference_verdict(c):
    """A difference is claimed only when BOTH the family bootstrap interval and McNemar agree."""
    if c["p"] < 0.05 and c["lo"] > 0:
        return "FP16 clearly better"
    if c["p"] < 0.05 and c["hi"] < 0:
        return "baseline clearly better"
    return "no clear difference"


def macro_f1(pred, gold, labels):
    f1s = []
    for lab in labels:
        tp = sum(1 for p, g in zip(pred, gold) if p == lab and g == lab)
        fp = sum(1 for p, g in zip(pred, gold) if p == lab and g != lab)
        fn = sum(1 for p, g in zip(pred, gold) if p != lab and g == lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / len(f1s)


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def ci_text(p, lo, hi):
    return "%s (%s to %s)" % (pct(p), pct(lo), pct(hi))


def pf(p):
    """p-value as text."""
    return "< 0.0001" if p < 0.0001 else "= %.4f" % p


def required_rate(h, need=HARMFUL_NEEDED_DEV):
    """Flip rate needed to reach `need` harmful flips among 14,400 decisions if a share h of flips is harmful."""
    return need / (DEV_DECISIONS * h)


LEVEL_TEXT = {
    "COMFORTABLE": "Enough flips even if only 10% of them turn out harmful.",
    "ONLY IF HARM IS HIGH": "Enough flips only if about 25% of them turn out harmful. Check the harmful share early (60 forks).",
    "BORDERLINE": "The best guess reaches the need at 25% harmful, but the lower bound does not.",
    "SHORT": "Even at 25% harmful the design falls short. This is close to the design's own example (3% flips and 25% harmful gives 108 of 120). "
             "The design's remedy: more seeds inside the call cap, or add a Q3 arm.",
}


def yield_level(p, lo80):
    if lo80 >= required_rate(0.10):
        return "COMFORTABLE"
    if lo80 >= required_rate(0.25):
        return "ONLY IF HARM IS HIGH"
    if p >= required_rate(0.25):
        return "BORDERLINE"
    return "SHORT"


# ------------------------------------------------------------------ main analysis
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--runs-dir", default=str(ROOT / "runs"))
    ap.add_argument("--out-dir", default=str(ROOT / "results"))
    ap.add_argument("--no-lr", action="store_true", help="skip the TF-IDF/LR baseline (if scikit-learn is missing)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    cases = load_cases(ROOT / cfg["cases"]["file"])
    cb = {c["id"]: c for c in cases}
    subsets = load_subsets()
    runs_dir = Path(args.runs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True)

    # ---- model runs
    run_defs = {}
    for s in cfg["sessions"]:
        for r in s["runs"]:
            run_defs[r["run"]] = dict(r, model=s["model"], session=s["name"], optional=bool(s.get("optional")))
    R, raw = {}, {}
    for name in run_defs:
        recs = read_jsonl(runs_dir / (name + ".jsonl"))
        raw[name] = recs
        proc = {cid: process(rec, cb[cid]) for cid, rec in recs.items() if cid in cb}
        proc = {k: v for k, v in proc.items() if v is not None}
        if proc:
            R[name] = proc
    errors = {n: sum(1 for r in raw[n].values() if "text" not in r) for n in raw}

    # ---- baselines
    try:
        import baselines
        base_norms = baselines.baseline_table(cases, with_lr=not args.no_lr)
    except ImportError as e:
        print("A package is missing (%s). Install it with:  pip install numpy scikit-learn   (or run with --no-lr)" % e)
        sys.exit(1)
    B = {k: process_norms(v, cb) for k, v in base_norms.items()}

    dev_ids_all = [c["id"] for c in cases if c["split"] == "dev"]
    held_ids_all = [c["id"] for c in cases if c["split"] == "held"]
    all_ids = [c["id"] for c in cases]
    fam = {c["id"]: c["family"] for c in cases}

    def ids_of(P, base_ids):
        return [i for i in base_ids if i in P]

    f16 = R.get("f16_P1")
    rerun = R.get("f16_P1_rerun")
    arm_runs = {lab: R.get(run) for lab, run in ARMS if R.get(run)}

    summary = {"runs_found": {n: len(R[n]) for n in R}, "errors": {n: e for n, e in errors.items() if e}}
    L = []
    W = L.append

    # =================================================================== accuracy
    def acc_block(P, ids):
        n = len(ids)
        a_ok = [P[i]["norm"]["action"] == cb[i]["gold"]["action"] for i in ids]
        r_ok = [P[i]["norm"] == gold_norm(cb[i]) for i in ids]
        f1 = macro_f1([P[i]["norm"]["action"] for i in ids], [cb[i]["gold"]["action"] for i in ids], ACTION_LABELS)
        return {"n": n, "a_ok": a_ok, "r_ok": r_ok, "action": wilson(sum(a_ok), n), "record": wilson(sum(r_ok), n), "f1": f1}

    systems = []
    for lab, key in (("always NO_ACTION", "always_NO_ACTION"), ("always VERIFY", "always_VERIFY"), ("Rule engine", "rule"),
                     ("TF-IDF + logistic regression", "tfidf_lr")):
        if key in B:
            systems.append((lab, B[key]))
    if f16:
        systems.append(("Llama 3.2 1B FP16", f16))
    for lab, P in arm_runs.items():
        systems.append(("Llama 3.2 1B " + lab, P))

    acc_rows, acc_summary = [], {}
    for lab, P in systems:
        row = [lab]
        for split, base in (("dev", dev_ids_all), ("held", held_ids_all)):
            ids = ids_of(P, base)
            if not ids:
                row += ["not run", "", ""]
                continue
            a = acc_block(P, ids)
            row += [ci_text(*a["action"]), (ci_text(*a["record"]) if "always" not in lab else "n/a"), "%.2f" % a["f1"]]
            acc_summary.setdefault(lab, {})[split] = {"n": a["n"], "action_acc": a["action"][0], "record_acc": a["record"][0], "macro_f1": a["f1"]}
        acc_rows.append(row)

    # ---- G1: FP16 vs the two floors (development cases)
    g1 = None
    if f16:
        ids = ids_of(f16, dev_ids_all)
        a16 = acc_block(f16, ids)
        floors = {lab: acc_block(B[key], ids) for lab, key in (("always NO_ACTION", "always_NO_ACTION"), ("always VERIFY", "always_VERIFY"))}
        best_lab = max(floors, key=lambda k: np.mean(floors[k]["a_ok"]))
        other = [k for k in floors if k != best_lab][0]
        famv = [fam[i] for i in ids]
        c_best = paired_compare(a16["a_ok"], floors[best_lab]["a_ok"], famv)
        c_other = paired_compare(a16["a_ok"], floors[other]["a_ok"], famv)
        g1 = {"n": len(ids), "fp16_action_acc": a16["action"][0], "fp16_action_ci": a16["action"], "fp16_record_ci": a16["record"],
              "best_floor": best_lab, "best_floor_acc": float(np.mean(floors[best_lab]["a_ok"])), "cmp": c_best,
              "other_floor": other, "cmp_other": c_other, "pass": bool(c_best["p"] < 0.05 and c_best["diff"] > 0)}
    summary["G1"] = g1

    # ---- G2: FP16 vs Rule / TF-IDF+LR
    g2 = {}
    if f16:
        for lab, key in (("Rule engine", "rule"), ("TF-IDF + logistic regression", "tfidf_lr")):
            if key not in B:
                continue
            for split, base in (("held", held_ids_all), ("dev", dev_ids_all)):
                ids = ids_of(f16, base)
                if not ids:
                    continue
                a = acc_block(f16, ids)
                b = acc_block(B[key], ids)
                for metric, mname in (("a_ok", "action"), ("r_ok", "record")):
                    c_ = paired_compare(a[metric], b[metric], [fam[i] for i in ids])
                    c_["verdict"] = difference_verdict(c_)
                    c_["n"] = len(ids)
                    c_["fp16_acc"] = float(np.mean(a[metric]))
                    c_["base_acc"] = float(np.mean(b[metric]))
                    g2[(lab, split, mname)] = c_
    summary["G2"] = {"|".join(k): v for k, v in g2.items()}

    # =================================================================== flips
    def flip_stats(Ref, X, ids):
        n = len(ids)
        strict = [i for i in ids if Ref[i]["key"] != X[i]["key"]]
        oper = [i for i in ids if Ref[i]["eff"] != X[i]["eff"]]
        oper_set = set(oper)
        trans = Counter(transition(Ref[i]["eff"], X[i]["eff"]) for i in oper)
        FMT = ("fallback_unparsed", "fallback_schema")
        fmt = [i for i in oper if Ref[i]["status"] in FMT or X[i]["status"] in FMT]
        fmt_set = set(fmt)
        badinc = [i for i in oper if i not in fmt_set and "fallback_bad_incident" in (Ref[i]["status"], X[i]["status"])]
        sem = [i for i in oper if Ref[i]["status"] == "ok" and X[i]["status"] == "ok"]
        r2w = w2r = wdiff = 0
        for i in strict:
            g = gold_norm(cb[i])
            ra = Ref[i]["norm"] == g
            rx = X[i]["norm"] == g
            if ra and not rx:
                r2w += 1
            elif (not ra) and rx:
                w2r += 1
            else:
                wdiff += 1
        by_gold, by_split = {}, {"dev": [0, 0], "held": [0, 0]}
        for i in ids:
            g = cb[i]["gold"]["action"]
            by_gold.setdefault(g, [0, 0])
            by_gold[g][1] += 1
            by_split[cb[i]["split"]][1] += 1
            if i in oper_set:
                by_gold[g][0] += 1
                by_split[cb[i]["split"]][0] += 1
        boot = cluster_boot([1.0 if i in oper_set else 0.0 for i in ids], [fam[i] for i in ids])
        return {"n": n, "strict": strict, "oper": oper, "trans": trans, "format": fmt, "bad_incident": badinc, "semantic": sem,
                "right_to_wrong": r2w, "wrong_to_right": w2r, "wrong_both_differ": wdiff, "by_gold": by_gold, "by_split": by_split, "boot": boot}

    flips = {}
    if f16:
        for lab, P in arm_runs.items():
            flips[lab] = flip_stats(f16, P, [i for i in all_ids if i in f16 and i in P])
        if rerun:
            flips["rerun"] = flip_stats(f16, rerun, [i for i in all_ids if i in f16 and i in rerun])

    # ---- prompt noise (prompt subset, development cases only)
    prompt_ids = subsets["prompt"]
    noise_rows, noise_summary = [], {}

    def add_noise_row(label, Ref, X):
        if Ref is None or X is None:
            return
        ids = [i for i in prompt_ids if i in Ref and i in X]
        if not ids:
            return
        fs = flip_stats(Ref, X, ids)
        p, lo, hi = wilson(len(fs["oper"]), len(ids))
        pa, loa, hia = wilson(len(fs["strict"]), len(ids))
        noise_rows.append([label, len(ids), ci_text(pa, loa, hia), ci_text(p, lo, hi)])
        noise_summary[label] = {"n": len(ids), "changed": pa, "table_changing": p}

    add_noise_row("FP16 vs FP16 restarted (same prompt)", f16, rerun)
    for lab, P in arm_runs.items():
        add_noise_row("%s vs FP16 (same prompt P1)" % lab, f16, P)
    add_noise_row("FP16: prompt P1 vs prompt P2", f16, R.get("f16_P2"))
    add_noise_row("FP16: prompt P1 vs prompt P3", f16, R.get("f16_P3"))
    add_noise_row("Q4_K_M: prompt P1 vs prompt P2", arm_runs.get("Q4_K_M"), R.get("q4_P2"))
    add_noise_row("Q4_K_M: prompt P1 vs prompt P3", arm_runs.get("Q4_K_M"), R.get("q4_P3"))

    dir_rows, dir_summary = [], {}
    for pid, fname, qname in (("P1", "f16_P1", "q4_P1"), ("P2", "f16_P2", "q4_P2"), ("P3", "f16_P3", "q4_P3")):
        Pf, Pq = R.get(fname), R.get(qname)
        if Pf and Pq:
            ids = [i for i in prompt_ids if i in Pf and i in Pq]
            if ids:
                af = np.mean([Pf[i]["norm"]["action"] == cb[i]["gold"]["action"] for i in ids])
                aq = np.mean([Pq[i]["norm"]["action"] == cb[i]["gold"]["action"] for i in ids])
                rf = np.mean([Pf[i]["norm"] == gold_norm(cb[i]) for i in ids])
                rq = np.mean([Pq[i]["norm"] == gold_norm(cb[i]) for i in ids])
                dir_rows.append([pid, len(ids), pct(af), pct(aq), "%+.1f pts" % (100 * (aq - af)), pct(rf), pct(rq), "%+.1f pts" % (100 * (rq - rf))])
                dir_summary[pid] = {"n": len(ids), "action_f16": float(af), "action_q4": float(aq), "record_f16": float(rf), "record_q4": float(rq)}

    # =================================================================== validity
    val_rows, val_summary = [], {}
    for name in run_defs:
        P = R.get(name)
        if not P:
            continue
        n = len(P)
        parsed = sum(v["parsed"] for v in P.values())
        sch = sum(v["schema"] for v in P.values())
        stat = Counter(v["status"] for v in P.values())
        trunc = sum(v["truncated"] for v in P.values())
        fmt_fb = stat.get("fallback_unparsed", 0) + stat.get("fallback_schema", 0)
        val_rows.append([name, "yes" if run_defs[name].get("grammar", True) else "NO", n, pct(parsed / n), pct(sch / n),
                         stat.get("fallback_bad_incident", 0), fmt_fb, trunc])
        val_summary[name] = {"n": n, "json_ok": parsed / n, "schema_ok": sch / n, "bad_incident": stat.get("fallback_bad_incident", 0),
                             "format_fallback": fmt_fb, "truncated": trunc}

    # =================================================================== throughput
    thr_rows, thr_summary = [], {}
    total_ms = 0.0
    for name in R:
        total_ms += sum(v["rec"]["wall_ms"] for v in R[name].values() if v["rec"] and v["rec"].get("wall_ms"))
    for name, label in [("f16_P1", "FP16")] + [(run, lab) for lab, run in ARMS]:
        P = R.get(name)
        if not P:
            continue
        w = [v["rec"]["wall_ms"] for v in P.values() if v["rec"] and v["rec"].get("wall_ms")]
        if not w:
            continue
        pp = [v["rec"].get("prompt_per_s") for v in P.values() if v["rec"] and v["rec"].get("prompt_per_s")]
        gp = [v["rec"].get("predicted_per_s") for v in P.values() if v["rec"] and v["rec"].get("predicted_per_s")]
        pn = [v["rec"].get("tokens_evaluated") for v in P.values() if v["rec"] and v["rec"].get("tokens_evaluated")]
        gn = [v["rec"].get("tokens_predicted") for v in P.values() if v["rec"] and v["rec"].get("tokens_predicted")]
        mean_s = statistics.mean(w) / 1000.0
        thr_rows.append([label, len(w), "%.2f s" % (statistics.median(w) / 1000.0), "%.2f s" % mean_s,
                         "%.2f s" % (float(np.percentile(w, 90)) / 1000.0), "%.0f" % (3600.0 / mean_s),
                         ("%.0f" % statistics.median(pp)) if pp else "n/a", ("%.0f" % statistics.median(gp)) if gp else "n/a",
                         ("%.0f / %.0f" % (statistics.mean(pn), statistics.mean(gn))) if pn and gn else "n/a"])
        thr_summary[label] = {"n": len(w), "median_s": statistics.median(w) / 1000.0, "mean_s": mean_s,
                              "p90_s": float(np.percentile(w, 90)) / 1000.0, "calls_per_hour": 3600.0 / mean_s}
    g5 = None
    if thr_summary:
        worst = max(v["mean_s"] for v in thr_summary.values())
        avg = statistics.mean(v["mean_s"] for v in thr_summary.values())
        g5 = {"slowest_mean_s": worst, "avg_mean_s": avg, "hours_slowest": PLANNED_CALLS * worst / 3600.0,
              "hours_avg": PLANNED_CALLS * avg / 3600.0,
              "pass": bool(PLANNED_CALLS * worst / 3600.0 <= HOUR_CAP and PLANNED_CALLS <= CALL_CAP)}
    summary["G5"] = g5
    summary["throughput"] = thr_summary
    summary["total_model_hours"] = total_ms / 3.6e6

    # =================================================================== yield (Q4 is the main arm; Q3 only if you ran it)
    yield_info = {}
    for lab in ("Q4_K_M", "Q3_K_M"):
        fs = flips.get(lab)
        if not fs:
            continue
        n, k = fs["n"], len(fs["oper"])
        p, lo, hi = wilson(k, n)
        _, lo80_w, _ = wilson(k, n, Z80_ONE_SIDED)
        lo80 = min(lo80_w, fs["boot"]["p20"])
        rows = [{"harm_share": h, "needed_flip_rate": required_rate(h), "projected_harmful": p * DEV_DECISIONS * h,
                 "projected_harmful_low80": lo80 * DEV_DECISIONS * h} for h in HARM_SHARES]
        yield_info[lab] = {"n": n, "k": k, "rate": p, "ci95": [lo, hi], "low80_wilson": lo80_w, "low80_boot": fs["boot"]["p20"], "low80": lo80,
                           "rows": rows, "level": yield_level(p, lo80)}
    summary["yield"] = yield_info

    # =================================================================== gates and the overall call
    gates = []

    def gate(code, what, result, detail, design):
        gates.append({"gate": code, "what": what, "result": result, "detail": detail, "design_says": design})

    fs = flips.get("rerun")
    if fs:
        ch = len(fs["strict"])
        gate("G0", "FP16 gives the same answers after a restart", "PASS" if ch == 0 else "FAIL",
             "%d of %d answers changed. (Tests T1 to T8 need your CBBA code and are not checked here.)" % (ch, fs["n"]), "Fix it before piloting.")
    else:
        gate("G0", "FP16 gives the same answers after a restart", "NOT RUN", "the restart run is missing", "Fix it before piloting.")
    if g1:
        gate("G1", "FP16 beats the better floor", "PASS" if g1["pass"] else "FAIL",
             "FP16 %s against %s %s (%+.1f pts, McNemar p %s, %d development cases)" % (
                 pct(g1["fp16_action_acc"]), g1["best_floor"], pct(g1["best_floor_acc"]), 100 * g1["cmp"]["diff"], pf(g1["cmp"]["p"]), g1["n"]),
             "If it fails: move to the 3B model once. If 3B also fails, stop the SLM study and apply the analysis to Rule and classifier flips.")
    else:
        gate("G1", "FP16 beats the better floor", "NOT RUN", "the FP16 run is missing", "")
    held_rec = {lab: g2.get((lab, "held", "record")) for lab in ("Rule engine", "TF-IDF + logistic regression")}
    if all(held_rec.values()):
        ok = all(r["verdict"] == "FP16 clearly better" for r in held_rec.values())
        gate("G2", "FP16 clearly beats Rule and TF-IDF/LR on held-out wording", "PASS" if ok else "FAIL",
             "; ".join("%s: %s (%+.1f pts)" % (k, r["verdict"], 100 * r["diff"]) for k, r in held_rec.items()),
             "If Rule or the classifier match or beat FP16: drop the necessity claim, report it, and continue.")
    else:
        gate("G2", "FP16 clearly beats Rule and TF-IDF/LR on held-out wording", "NOT RUN", "needs the FP16 run", "")
    q4f = flips.get("Q4_K_M")
    if q4f:
        nf = len(q4f["oper"])
        if nf == 0:
            gate("G3", "Format flips are not the majority", "PASS", "no table-changing flips", "If format flips are the majority: fix the grammar or prompt on development families before freezing.")
        else:
            maj = len(q4f["format"]) > nf / 2
            gate("G3", "Format flips are not the majority", "FAIL" if maj else "PASS",
                 "Q4 vs FP16: %d meaning flips, %d format flips, %d bad-incident flips" % (len(q4f["semantic"]), len(q4f["format"]), len(q4f["bad_incident"])),
                 "If format flips are the majority: fix the grammar or prompt on development families before freezing.")
    else:
        gate("G3", "Format flips are not the majority", "NOT RUN", "needs the FP16 and Q4 runs", "")
    y4 = yield_info.get("Q4_K_M")
    if y4:
        gate("G4", "Enough flips to reach 120 harmful flips", y4["level"],
             "Q4 changed the task table in %s of %d cases; lower 80%% bound %s; the design needs %s (if 25%% harmful), %s (if 10%%), %s (if 5%%)" % (
                 pct(y4["rate"]), y4["n"], pct(y4["low80"]), pct(required_rate(0.25)), pct(required_rate(0.10)), pct(required_rate(0.05))),
             "If short: add Q3 as a separate arm in place of the Q8 subset and one robustness subset. If still short, the exploratory analyses become descriptive (C1 to C3 stay).")
    else:
        gate("G4", "Enough flips to reach 120 harmful flips", "NOT RUN", "needs the FP16 and Q4 runs", "")
    if g5:
        gate("G5", "%s calls fit in %d hours" % (format(PLANNED_CALLS, ","), HOUR_CAP), "PASS" if g5["pass"] else "FAIL",
             "%.2f s per call at the slowest precision gives %.0f hours" % (g5["slowest_mean_s"], g5["hours_slowest"]), "Cut in the order given in the design (section G).")
    else:
        gate("G5", "%s calls fit in %d hours" % (format(PLANNED_CALLS, ","), HOUR_CAP), "NOT RUN", "no timing data", "")
    gate("G6, G7", "Clustering of harm; absorption", "NOT TESTED", "these need the simulator", "")
    summary["gates"] = gates

    # ---- overall call
    G = {g["gate"]: g for g in gates}
    reasons = []
    if G["G0"]["result"] == "FAIL":
        call = "FIX FIRST"
        reasons.append("FP16 gave different answers when it was run twice. Until this is zero, differences between precisions cannot be trusted. "
                       "Check that nothing else uses the GPU, that `-np 1` is set, and that the prompt cache is off.")
    elif G["G1"]["result"] == "FAIL":
        call = "STOP (for the 1B model)"
        reasons.append("FP16 does not clearly beat the better floor. You may improve the prompt on development cases first (write down every change and the accuracy before and after). "
                       "If it still fails, the design says to try the 3B model once. If 3B also fails, the SLM study stops and the analysis is applied to Rule and classifier flips.")
    elif G["G3"]["result"] == "FAIL":
        call = "FIX FIRST"
        reasons.append("Most flips are format flips (the answer was not readable or broke the schema). Fix the grammar or the prompt on development cases, then run again.")
    elif y4:
        lvl = y4["level"]
        if lvl == "COMFORTABLE":
            call = "GO"
            reasons.append("Q4 changes enough decisions. Even a low harmful share (10%) should reach the 120 harmful flips needed. Build the CBBA harness.")
        elif lvl == "ONLY IF HARM IS HIGH":
            call = "CONDITIONAL"
            reasons.append("Enough flips only if about 25% of them are harmful. Build the harness, but measure the harmful share early (60 forks) and plan the Q3 arm and extra seeds.")
        elif lvl == "BORDERLINE":
            call = "CONDITIONAL"
            reasons.append("The best guess reaches the need at a 25% harmful share but the lower bound does not. Add the Q3 arm (see README) and measure it before you decide.")
        else:
            call = "CONDITIONAL"
            reasons.append("Q4 flips too few decisions to reach 120 harmful flips even at a 25% harmful share. The design's own remedy is a Q3 arm. "
                           "Run the optional Q3 session (see README) and re-check. If Q3 is also short, the exploratory analyses become descriptive and C1 to C3 stay.")
    else:
        call = "NOT ENOUGH RUNS YET"
        reasons.append("The FP16 and Q4 runs are needed for a call.")
    if G["G2"]["result"] == "FAIL":
        reasons.append("G2: on held-out wording FP16 did not clearly beat both Rule and TF-IDF/LR. The design says: drop the claim that a language model is necessary, report it, and continue.")
    if G["G5"]["result"] == "FAIL":
        reasons.append("G5: the planned calls do not fit in the time. Cut items in the order given in the design.")
    summary["overall_call"] = {"call": call, "reasons": reasons}

    # =================================================================== write the report
    W("# EdgeSAR pilot report")
    W("")
    W("Made by analyze.py on %s from the files in `runs/`. Cases: %d (development style A: %d, held-out style B: %d). Runs found: %s." % (
        time.strftime("%Y-%m-%d %H:%M"), len(cases), len(dev_ids_all), len(held_ids_all),
        ", ".join("%s (%d)" % (n, len(R[n])) for n in R) or "none"))
    if any(errors.values()):
        W("")
        W("**Warning: some calls failed:** %s" % {n: e for n, e in errors.items() if e})
    missing = [n for n, d in run_defs.items() if n not in R and not d["optional"]]
    if missing:
        W("")
        W("**Not run yet:** %s" % ", ".join(missing))
    W("")
    W("## Suggested call: %s" % call)
    W("")
    for r_ in reasons:
        W("- " + r_)
    W("")
    W("This is my reading of the design's gates (G0 to G5), as a guide for your talk with your supervisors. It is not a rule from them. "
      "The yield levels (COMFORTABLE, ONLY IF HARM IS HIGH, BORDERLINE, SHORT) are my own cut-offs, not from the design.")
    W("")
    W("### The gates one by one")
    W("")
    W(md_table(["gate", "what it checks", "result", "details", "what the design says to do"],
               [[g["gate"], g["what"], "**%s**" % g["result"], g["detail"], g["design_says"]] for g in gates]))
    W("")

    # ---- the eight questions
    W("## Your eight questions in one page")
    W("")
    ans = []
    if g1:
        ans.append(["1. Is FP16 competent?",
                    "On development cases FP16 chose the right action in %s. It got the whole record right in %s." % (
                        ci_text(*g1["fp16_action_ci"]), ci_text(*g1["fp16_record_ci"]))])
        ans.append(["2. Does it beat always-NO_ACTION and always-VERIFY?",
                    "Better floor: %s at %s. FP16 minus floor: %+.1f points, McNemar p %s. **%s.** Other floor (%s): p %s." % (
                        g1["best_floor"], pct(g1["best_floor_acc"]), 100 * g1["cmp"]["diff"], pf(g1["cmp"]["p"]),
                        "Yes, it beats it" if g1["pass"] else "No, not clearly", g1["other_floor"], pf(g1["cmp_other"]["p"]))])
    else:
        ans.append(["1-2. FP16 competence and floors", "The FP16 run is missing."])
    if all(held_rec.values()):
        r1, r2 = held_rec["Rule engine"], held_rec["TF-IDF + logistic regression"]
        ans.append(["3. Do Rule and TF-IDF/LR match or beat FP16?",
                    "On held-out wording (the fair test), whole-record accuracy: FP16 %s, Rule %s, TF-IDF/LR %s. FP16 against Rule: %s. FP16 against TF-IDF/LR: %s." % (
                        pct(r1["fp16_acc"]), pct(r1["base_acc"]), pct(r2["base_acc"]), r1["verdict"], r2["verdict"])])
    else:
        ans.append(["3. Do Rule and TF-IDF/LR match or beat FP16?", "Needs the FP16 run."])
    q_txt = []
    for lab in ("Q8_0", "Q4_K_M", "Q3_K_M"):
        fs_ = flips.get(lab)
        if fs_:
            p_, lo_, hi_ = wilson(len(fs_["oper"]), fs_["n"])
            q_txt.append("%s changes the task table in %s of %d cases" % (lab, ci_text(p_, lo_, hi_), fs_["n"]))
    if flips.get("rerun"):
        q_txt.append("FP16 against itself after a restart: %d changed" % len(flips["rerun"]["strict"]))
    ans.append(["4. How often do Q8 and Q4 change the FP16 decision?", "; ".join(q_txt) if q_txt else "Runs missing."])
    tr_txt = []
    for lab in ("Q4_K_M", "Q8_0"):
        fs_ = flips.get(lab)
        if fs_:
            top = fs_["trans"].most_common(4)
            tr_txt.append("%s: %s" % (lab, ("; ".join("%s (%d)" % (k, v) for k, v in top)) if top else "no table-changing flips"))
    ans.append(["5. Which transition types happen?", " | ".join(tr_txt) if tr_txt else "Runs missing."])
    v_txt = []
    for name in ("f16_P1", "q4_P1", "f16_P1_nogrammar", "q4_P1_nogrammar"):
        if name in val_summary:
            v = val_summary[name]
            v_txt.append("%s: valid JSON %s, schema ok %s" % (name, pct(v["json_ok"]), pct(v["schema_ok"])))
    ans.append(["6. Are the outputs valid under the fixed schema?", "; ".join(v_txt) if v_txt else "Runs missing."])
    if g5:
        t_txt = "; ".join("%s: %.2f s per call (%.0f per hour)" % (k, v["mean_s"], v["calls_per_hour"]) for k, v in thr_summary.items())
        t_txt += ". The design needs about %s calls: %.0f hours at the slowest speed (limit %d hours). **%s.**" % (
            format(PLANNED_CALLS, ","), g5["hours_slowest"], HOUR_CAP, "It fits" if g5["pass"] else "It does NOT fit")
    else:
        t_txt = "Runs missing."
    ans.append(["7. What is the real laptop speed?", t_txt])
    if y4:
        ans.append(["8. Is the flip yield high enough for the CBBA experiment?",
                    "**%s.** Q4 changed the task table in %s of cases. The design needs at least %s if 25%% of changes are harmful, %s if 10%%, %s if 5%%. %s" % (
                        y4["level"], pct(y4["rate"]), pct(required_rate(0.25)), pct(required_rate(0.10)), pct(required_rate(0.05)), LEVEL_TEXT[y4["level"]])])
    else:
        ans.append(["8. Is the flip yield high enough for the CBBA experiment?", "Needs the FP16 and Q4 runs."])
    W(md_table(["Question", "Answer"], ans))
    W("")

    # ---- section 1
    W("## 1. Accuracy against the construction labels")
    W("")
    W("Action accuracy = the right one of the four actions. Record accuracy = the whole decision is right (action, incident, landmark, sensor, priority). "
      "Intervals are 95% Wilson. 'dev' = development style A. 'held' = held-out style B, written with words the Rule engine and the classifier never saw.")
    W("")
    W(md_table(["System", "dev: action acc", "dev: record acc", "dev: macro-F1", "held: action acc", "held: record acc", "held: macro-F1"], acc_rows))
    W("")
    W("The 'always VERIFY' floor has no meaningful full record, so its record accuracy is not shown.")
    W("")
    if g1:
        W("**G1 (FP16 against the floors, %d development cases):** FP16 action accuracy %s. Better floor = %s at %s. FP16 minus floor = %+.1f points "
          "(95%% family-bootstrap interval %+.1f to %+.1f). McNemar exact p %s (FP16 only right in %d cases, floor only right in %d). **%s**" % (
              g1["n"], ci_text(*g1["fp16_action_ci"]), g1["best_floor"], pct(g1["best_floor_acc"]), 100 * g1["cmp"]["diff"],
              100 * g1["cmp"]["lo"], 100 * g1["cmp"]["hi"], pf(g1["cmp"]["p"]), g1["cmp"]["a_only"], g1["cmp"]["b_only"], "PASS" if g1["pass"] else "NOT MET"))
        W("")
    if f16:
        W("### FP16: what it answered for each true action (all cases)")
        W("")
        conf = {a: Counter() for a in ACTION_LABELS}
        for i in f16:
            conf[cb[i]["gold"]["action"]][f16[i]["norm"]["action"]] += 1
        rows = []
        for a in ACTION_LABELS:
            tot = sum(conf[a].values())
            rows.append([SHORT[a], tot] + ["%d" % conf[a][b] for b in ACTION_LABELS] + [pct(conf[a][a] / tot) if tot else "n/a"])
        W(md_table(["true action", "cases"] + ["said " + SHORT[b] for b in ACTION_LABELS] + ["recall"], rows))
        W("")
    if g2:
        W("### G2: FP16 against the Rule engine and TF-IDF/LR (same cases, paired)")
        W("")
        rows = []
        for (lab, split, metric), r in sorted(g2.items(), key=lambda kv: (kv[0][0], kv[0][1] != "held", kv[0][2])):
            rows.append([lab, "held-out" if split == "held" else "development", metric, r["n"], pct(r["fp16_acc"]), pct(r["base_acc"]),
                         "%+.1f pts" % (100 * r["diff"]), "%+.1f to %+.1f" % (100 * r["lo"], 100 * r["hi"]), pf(r["p"]).replace("= ", ""), r["verdict"]])
        W(md_table(["baseline", "cases", "metric", "n", "FP16", "baseline", "FP16 minus baseline", "95% interval (family bootstrap)", "McNemar p", "verdict"], rows))
        W("")
        W("A difference is claimed only when the family-bootstrap interval and McNemar both agree. Read the held-out rows first: on development wording the baselines were built from the same words, so they have an unfair advantage.")
        W("")

    # ---- section 2
    W("## 2. How often do the smaller models change the FP16 decision?")
    W("")
    W("'Changed' = the validated answer is not identical. 'Table-changing' = the answer would change what the allocator sees "
      "(NO_ACTION and an UPDATE that changes nothing count as the same). The design calls these operational flips.")
    W("")
    rows = []
    for lab, title in (("Q8_0", "Q8_0 vs FP16"), ("Q4_K_M", "Q4_K_M vs FP16"), ("Q3_K_M", "Q3_K_M vs FP16 (optional arm)"), ("rerun", "FP16 restarted vs FP16 (must be 0)")):
        fs_ = flips.get(lab)
        if fs_:
            ps, los, his = wilson(len(fs_["strict"]), fs_["n"])
            po, loo, hio = wilson(len(fs_["oper"]), fs_["n"])
            rows.append([title, fs_["n"], len(fs_["strict"]), ci_text(ps, los, his), len(fs_["oper"]), ci_text(po, loo, hio),
                         len(fs_["semantic"]), len(fs_["format"]), len(fs_["bad_incident"]),
                         fs_["right_to_wrong"], fs_["wrong_to_right"], fs_["wrong_both_differ"]])
    if rows:
        W(md_table(["comparison", "cases", "changed", "changed %", "table-changing", "table-changing %",
                    "meaning flips", "format flips", "bad-incident flips", "right -> wrong", "wrong -> right", "wrong -> other wrong"], rows))
    else:
        W("Runs missing.")
    W("")
    W("Meaning flips = both answers were valid and still differ. Format flips = one answer could not be read or broke the schema, so the validator replaced it with NO_ACTION. "
      "Bad-incident flips = one answer named an incident that is not open. The design (gate G3) asks for these to be reported separately, because only meaning flips say something about the quantized model's decision.")
    W("")
    W("'right -> wrong' = FP16 had the whole record right and the smaller model did not. This is only a rough pointer to harm. Harm itself needs the simulator.")
    W("")
    rows = []
    for lab in ("Q8_0", "Q4_K_M", "Q3_K_M"):
        fs_ = flips.get(lab)
        if fs_:
            cells = []
            for sp in ("dev", "held"):
                k_, n_ = fs_["by_split"][sp]
                cells.append(ci_text(*wilson(k_, n_)) + " (%d of %d)" % (k_, n_) if n_ else "n/a")
            rows.append([lab] + cells)
    if rows:
        W("### Does the flip rate depend on the wording style? (table-changing flips)")
        W("")
        W(md_table(["model vs FP16", "development style A", "held-out style B"], rows))
        W("")
        W("If the two columns are very different, the flip rate depends on how the reports are written. Mission logs will be a third style, so treat the rate as a rough range, not a fixed number.")
        W("")
    for lab in ("Q4_K_M", "Q8_0", "Q3_K_M"):
        fs_ = flips.get(lab)
        if not fs_:
            continue
        W("### Transition types: %s vs FP16" % lab)
        W("")
        if fs_["trans"]:
            tot = sum(fs_["trans"].values())
            W(md_table(["transition (FP16 -> %s)" % lab, "count", "share of table-changing flips"],
                       [[k, v, pct(v / tot)] for k, v in fs_["trans"].most_common()]))
        else:
            W("No table-changing flips.")
        W("")
        W("Table-changing flips by true action: " + "; ".join("%s %d of %d (%s)" % (SHORT[g], a, n, pct(a / n)) for g, (a, n) in sorted(fs_["by_gold"].items())))
        W("")

    W("### Is quantization bigger than prompt noise? (the %d-case prompt subset, development cases only)" % len(prompt_ids))
    W("")
    if noise_rows:
        W(md_table(["comparison", "cases", "changed", "table-changing"], noise_rows))
        W("")
        W("If a different wording of the prompt changes as many decisions as quantization does, a quantization result can really be a prompt result. "
          "The design asks you to freeze the prompt before any held-out run.")
    else:
        W("Runs missing.")
    W("")
    if dir_rows:
        W("### Does the sign of the Q4 effect depend on the prompt? (Q4 accuracy minus FP16 accuracy)")
        W("")
        W(md_table(["prompt", "cases", "FP16 action acc", "Q4 action acc", "Q4 minus FP16", "FP16 record acc", "Q4 record acc", "Q4 minus FP16"], dir_rows))
        W("")

    # ---- section 3
    W("## 3. Are the outputs valid under the fixed schema?")
    W("")
    W("With the grammar on, llama.cpp can only write the allowed JSON, so format errors should be 0. 'Bad incident' = the model named an incident that is not open; "
      "the validator replaces it with NO_ACTION (as in the design). 'Truncated' = it hit the 100-token limit.")
    W("")
    if val_rows:
        W(md_table(["run", "grammar", "cases", "valid JSON", "schema ok", "bad incident", "format fallback", "truncated"], val_rows))
    else:
        W("Runs missing.")
    W("")
    W("The two 'nogrammar' runs show what happens when the model is free to write anything. If they are much worse, the grammar is doing real work.")
    W("")

    # ---- section 4
    W("## 4. Laptop throughput")
    W("")
    if thr_rows:
        W(md_table(["model", "calls", "median per call", "mean per call", "90th percentile", "calls per hour", "prompt tok/s (median)", "generation tok/s (median)", "mean tokens in / out"], thr_rows))
        W("")
        W("Design check (G5): %s calls x %.2f s (slowest model) = **%.0f hours**; with the average of the models = %.0f hours. Limit: %d hours and %s calls. **%s**" % (
            format(PLANNED_CALLS, ","), g5["slowest_mean_s"], g5["hours_slowest"], g5["hours_avg"], HOUR_CAP, format(CALL_CAP, ","), "FITS" if g5["pass"] else "DOES NOT FIT"))
        W("")
        W("Total model time used by this pilot: %.1f hours. Mission prompts will be longer than these test prompts, and a hot laptop or battery mode is slower. Measure again in the simulator." % (total_ms / 3.6e6))
    else:
        W("Runs missing.")
    W("")
    sess = {}
    try:
        sess = json.load(open(out_dir / "env.json", encoding="utf-8")).get("sessions", {})
    except Exception:
        pass
    if sess:
        W("Model loading: " + "; ".join("%s %.0f s, %.2f GB%s" % (k, v.get("load_seconds", 0), v.get("model_gb", 0),
                                                              (", VRAM used %.0f MB" % v["gpu_after_load"]["vram_used_mb"]) if v.get("gpu_after_load") else "")
                                        for k, v in sess.items()))
        W("")

    # ---- section 5
    W("## 5. Is the flip yield high enough to build the CBBA / closed-loop experiment?")
    W("")
    W("The design needs at least %d harmful flips in development (and %d in held-out) from %d decisions per stage. "
      "Harmful flips = flip rate x %d x (share of flips that are harmful). The harmful share is unknown until the simulator exists, so three cases are shown. "
      "The 'lower 80%% bound' is the smaller of a one-sided Wilson bound and a family-bootstrap bound." % (
          HARMFUL_NEEDED_DEV, HARMFUL_NEEDED_HELD, DEV_DECISIONS, DEV_DECISIONS))
    W("")
    for lab in ("Q4_K_M", "Q3_K_M"):
        y_ = yield_info.get(lab)
        if not y_:
            continue
        W("**%s vs FP16:** table-changing rate %s of %d cases (95%% interval %s to %s; lower 80%% bound %s). Level: **%s.** %s" % (
            lab, pct(y_["rate"]), y_["n"], pct(y_["ci95"][0]), pct(y_["ci95"][1]), pct(y_["low80"]), y_["level"], LEVEL_TEXT[y_["level"]]))
        W("")
        W(md_table(["if this share of flips is harmful", "flip rate needed", "expected harmful flips (best guess)", "expected (lower 80% bound)", "enough?"],
                   [[pct(r["harm_share"], 0), pct(r["needed_flip_rate"]), "%.0f" % r["projected_harmful"], "%.0f" % r["projected_harmful_low80"],
                     "yes" if r["projected_harmful_low80"] >= HARMFUL_NEEDED_DEV else ("only at the best guess" if r["projected_harmful"] >= HARMFUL_NEEDED_DEV else "no")]
                    for r in y_["rows"]]))
        W("")
    W("Levels: COMFORTABLE = the lower bound reaches the need even at a 10% harmful share. ONLY IF HARM IS HIGH = it reaches the need only at 25%. "
      "BORDERLINE = only the best guess reaches the need at 25%. SHORT = even the best guess is below the need at 25%. "
      + "The held-out stage needs only %d harmful flips, so the development need (%d) is the harder one." % (HARMFUL_NEEDED_HELD, HARMFUL_NEEDED_DEV))
    W("")

    # ---- caveats
    W("## What this pilot cannot tell you (read before you quote any number)")
    W("")
    for t in [
        "The reports are templated. I wrote the templates and the Rule engine, so Rule and TF-IDF/LR can look better here than on real messages. Trust the held-out (style B) rows more than the development rows.",
        "Harm is not measured. Only flips are. The harmful share needs the simulator and the forks (design stage B).",
        "Q8_0 is not a safe 'no change' control. Quantizing to 8 bits can still change some decisions.",
        "One model family (Llama 3.2 1B), one quantization tool (llama-quantize, no importance matrix), one prompt family, one laptop.",
        "Greedy decoding with a fixed seed. The FP16 restart run is the test of whether the engine is repeatable on your machine.",
        "The class mix (25% create, 20% update, 15% close, 40% no action) is my guess. Mission logs will have a different mix, so the real flip rate will differ.",
        "Cases in one family share a template, so they tend to flip together. The family-bootstrap intervals allow for this; the Wilson intervals do not.",
        "This is the mini pilot on made-up reports. The pilot in your design (100 mission-sets, 60 forks) needs the simulator and comes later.",
        "Do not reuse these cases in the confirmatory study.",
    ]:
        W("- " + t)
    W("")
    W("## Files to send back")
    W("")
    W("`results/pilot_report.md`, `results/summary.json`, `results/env.json`, `results/model_hashes.json`. Do not send the model files.")
    W("")

    (out_dir / "pilot_report.md").write_text("\n".join(L), encoding="utf-8")

    # ---- csv of table-changing flips, for you to look at by eye
    if f16:
        for lab, P in arm_runs.items():
            fs_ = flips.get(lab)
            if not fs_:
                continue
            with open(out_dir / ("flips_%s_vs_FP16.csv" % lab), "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["case_id", "split", "gold", "FP16", lab, "transition", "FP16 right?", lab + " right?", "report text"])
                for i in fs_["oper"]:
                    g = gold_norm(cb[i])
                    w.writerow([i, cb[i]["split"], json.dumps(g, separators=(",", ":")), json.dumps(f16[i]["norm"], separators=(",", ":")),
                                json.dumps(P[i]["norm"], separators=(",", ":")), transition(f16[i]["eff"], P[i]["eff"]),
                                f16[i]["norm"] == g, P[i]["norm"] == g, cb[i]["text"]])

    # ---- summary.json
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.bool_):
            return bool(o)
        return o

    summary["accuracy"] = acc_summary
    summary["flips"] = {k: {"n": v["n"], "changed": len(v["strict"]), "table_changing": len(v["oper"]), "meaning": len(v["semantic"]),
                            "format": len(v["format"]), "bad_incident": len(v["bad_incident"]), "right_to_wrong": v["right_to_wrong"],
                            "wrong_to_right": v["wrong_to_right"], "wrong_both_differ": v["wrong_both_differ"],
                            "by_split": v["by_split"], "transitions": dict(v["trans"])} for k, v in flips.items()}
    summary["noise"] = noise_summary
    summary["prompt_direction"] = dir_summary
    summary["validity"] = val_summary
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(clean(summary), f, indent=2)
    print("Suggested call: %s" % call)
    print("Report written to", out_dir / "pilot_report.md")
    print("Numbers file     :", out_dir / "summary.json")


if __name__ == "__main__":
    main()
