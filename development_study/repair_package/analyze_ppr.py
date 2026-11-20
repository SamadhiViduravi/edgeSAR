"""
Analysis for the readout-repair feasibility experiment. Reads out/predictions.csv and out/fold_log.json, writes out/RESULTS.md and
out/results.json. Written before the run; the tests T1-T4 and their labels are those of PROTOCOL_REPAIR_FEASIBILITY.md section 5.

  python analyze_ppr.py --root <folder with edgesar_pilot, edgesar_heads, V1> --out out
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
from ppr_lib import REC, Data

BOOT = 2000
FIELDS = ("action", "incident", "landmark", "sensor", "priority")
MAIN = ["REF", "FROZEN", "C1", "C2", "C3", "C4", "C5", "SHARED", "MATCHED", "ANCH", "ANCH2"]


def load(out):
    P = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))          # P[(proto, labels)][arm][repeat][case_id] = key tuple
    with open(out / "predictions.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            P[(r["protocol"], r["labels"])][r["arm"]][int(r["repeat"])][r["case_id"]] = tuple(r[k] for k in FIELDS)
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    D = Data(a.root)
    P = load(out)
    flog = json.loads((out / "fold_log.json").read_text(encoding="utf-8"))
    idx = {c["id"]: i for i, c in enumerate(D.cases)}
    gold = {c["id"]: tuple("" if v is None else str(v) for v in D.gold_key[i]) for i, c in enumerate(D.cases)}
    tmpl = {c["id"]: D.template[i] for i, c in enumerate(D.cases)}
    gact = {c["id"]: c["gold"]["action"] for c in D.cases}
    res = {"protocol_sha256": flog["protocol_sha256"]}
    md = ["# Readout-repair feasibility experiment: results", "",
          "Exploratory, development data only (all 1,400 pilot reports have been used before). Protocol hash `%s`." % flog["protocol_sha256"],
          "Arms and tests: `PROTOCOL_REPAIR_FEASIBILITY.md`. Every number is computed from `predictions.csv` by `analyze_ppr.py`.", ""]

    def ok_matrix(S, arm, ids):
        """reports x repeats matrix of 1/0 (record correct)."""
        reps = sorted(S[arm])
        return np.array([[S[arm][r][i] == gold[i] for r in reps] for i in ids], float)

    def boot_diff(S, a1, a2, ids, seed=1):
        d = (ok_matrix(S, a1, ids) - ok_matrix(S, a2, ids)).mean(1)
        groups = defaultdict(list)
        for k, i in enumerate(ids):
            groups[tmpl[i]].append(k)
        G = [np.array(v) for v in groups.values()]
        gs = np.array([d[g].sum() for g in G])
        gn = np.array([len(g) for g in G])
        rng = np.random.default_rng(seed)
        pick = rng.integers(0, len(G), size=(BOOT, len(G)))
        b = gs[pick].sum(1) / gn[pick].sum(1)
        return float(d.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))

    def fmt(t):
        return "%+.1f (%+.1f to %+.1f)" % tuple(100 * x for x in t)

    def arm_metrics(S, arm, ids):
        reps = sorted(S[arm])
        n = len(ids) * len(reps)
        rec = sum(S[arm][r][i] == gold[i] for r in reps for i in ids)
        act = sum(S[arm][r][i][0] == gold[i][0] for r in reps for i in ids)
        rids = [i for i in ids if gact[i] in REC]
        sen = sum(S[arm][r][i][3] == gold[i][3] for r in reps for i in rids)
        pri = sum(S[arm][r][i][4] == gold[i][4] for r in reps for i in rids)
        loc = sum(S[arm][r][i][1:3] == gold[i][1:3] for r in reps for i in ids)
        by = {}
        for g in ("CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION"):
            gi = [i for i in ids if gact[i] == g]
            by[g] = 1 - sum(S[arm][r][i] == gold[i] for r in reps for i in gi) / (len(gi) * len(reps))
        return {"n": n, "record": rec / n, "action": act / n, "sensor_on_gold_rec": sen / (len(rids) * len(reps)),
                "priority_on_gold_rec": pri / (len(rids) * len(reps)), "link_location": loc / n, "error_by_gold_action": by,
                "record_num": rec, "action_num": act}

    def cohort(S, r_arm, q_arm, m_arm, ids):
        reps = sorted(S[m_arm])
        c = Counter()
        for rp in reps:
            for i in ids:
                r, q, m, y = S[r_arm][rp][i], S[q_arm][rp][i], S[m_arm][rp][i], gold[i]
                r_ok, q_ok, m_ok = r == y, q == y, m == y
                c["N"] += 1
                c["both_right" if r_ok and q_ok else "H" if r_ok else "beneficial" if q_ok else "both_wrong"] += 1
                c["C"] += q_ok
                if r_ok and not q_ok:
                    c["H_repaired"] += m_ok
                if q_ok:
                    c["C_broken"] += not m_ok
                if m != q:
                    c["changed"] += 1
                    c["changed_correct"] += m_ok
                c["m_ok"] += m_ok
        d = dict(c)
        for k in ("H", "beneficial", "both_right", "both_wrong", "C", "H_repaired", "C_broken", "changed", "changed_correct"):
            d.setdefault(k, 0)
        d["harmful_incidence"] = d["H"] / d["N"]
        d["repair_rate"] = d["H_repaired"] / d["H"] if d["H"] else None
        d["new_error_rate"] = d["C_broken"] / d["C"] if d["C"] else None
        d["correction_precision"] = d["changed_correct"] / d["changed"] if d["changed"] else None
        d["reps"] = len(reps)
        return d

    def table_arms(S, arms, ids, title):
        md.extend(["", "### " + title, "",
                   "| Arm | Whole record right | Action right | Sensor right (gold CREATE/UPDATE) | Priority right (gold CREATE/UPDATE) | Error by gold action: CREATE / UPDATE / CLOSE / NO_ACTION |",
                   "|---|---|---|---|---|---|"])
        outd = {}
        for arm in arms:
            if arm not in S:
                continue
            m = arm_metrics(S, arm, ids)
            outd[arm] = m
            e = m["error_by_gold_action"]
            md.append("| %s | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.0f / %.0f / %.0f / %.0f%% |" % (
                arm, 100 * m["record"], 100 * m["action"], 100 * m["sensor_on_gold_rec"], 100 * m["priority_on_gold_rec"],
                100 * e["CREATE_VERIFICATION"], 100 * e["UPDATE_INCIDENT"], 100 * e["CLOSE_INCIDENT"], 100 * e["NO_ACTION"]))
        return outd

    def table_cohort(S, q_arm, arms, ids, title):
        base = cohort(S, "REF", q_arm, q_arm, ids)
        md.extend(["", "### " + title, "",
                   "Per repeat: N = %d reports. Reference right and unmodified Q4 right: %.0f. **Harmful (reference right, Q4 wrong): %.0f = %.1f%%.** "
                   "Beneficial (reference wrong, Q4 right): %.0f = %.1f%%. Both wrong: %.0f." % (
                       len(ids), base["both_right"] / base["reps"], base["H"] / base["reps"], 100 * base["harmful_incidence"],
                       base["beneficial"] / base["reps"], 100 * base["beneficial"] / base["N"], base["both_wrong"] / base["reps"]), "",
                   "| Method | Repair rate (share of harmful cases now right) | New errors (share of Q4-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |",
                   "|---|---|---|---|---|"])
        outd = {"base": base}
        for arm in arms:
            if arm not in S or arm == q_arm:
                continue
            c = cohort(S, "REF", q_arm, arm, ids)
            outd[arm] = c
            md.append("| %s | %s | %s | %s | %+.1f |" % (
                arm, "undefined" if c["repair_rate"] is None else "%.1f%% (%d/%d)" % (100 * c["repair_rate"], c["H_repaired"], c["H"]),
                "undefined" if c["new_error_rate"] is None else "%.1f%% (%d/%d)" % (100 * c["new_error_rate"], c["C_broken"], c["C"]),
                "undefined" if c["correction_precision"] is None else "%.1f%% (%d/%d)" % (100 * c["correction_precision"], c["changed_correct"], c["changed"]),
                100 * (c["m_ok"] - c["C"]) / c["N"]))
        return outd

    # =============================================================== Protocol A, all labels
    S = P[("A", "all")]
    idsA = sorted(S["REF"][0])
    md.extend(["## 1. Protocol A: same wording style (1,000 style-A reports, 5 folds by template, 3 repeats)", "",
               "Rates are pooled over the 3 repeats (3,000 report decisions per arm)."])
    res["A"] = {"arms": table_arms(S, MAIN + ["TFIDF", "RULES", "GEN_FP16", "GEN_Q8", "GEN_Q4"], idsA, "1.1 Accuracy on Q4 vectors (REF is on FP16 vectors)")}
    res["A"]["cohort_frozen"] = table_cohort(S, "FROZEN", ["C1", "C2", "C3", "C4", "C5", "SHARED", "MATCHED", "ANCH", "ANCH2"], idsA,
                                             "1.2 Repair of the frozen cohort (unmodified Q4 = FP16 heads on raw Q4 vectors)")
    res["A"]["cohort_matched"] = table_cohort(S, "MATCHED", ["C1", "C2", "C3", "C4", "C5", "SHARED", "ANCH", "ANCH2"], idsA,
                                              "1.3 Repair of the matched cohort (unmodified Q4 = heads refitted on Q4 vectors)")
    diffs = {}
    md.extend(["", "### 1.4 Paired differences in whole-record accuracy (percentage points, 95% template-bootstrap interval)", "",
               "| Comparison | Difference |", "|---|---|"])
    for a1, a2 in (("C2", "C1"), ("C2", "MATCHED"), ("C1", "MATCHED"), ("ANCH", "MATCHED"), ("ANCH2", "MATCHED"), ("C3", "MATCHED"), ("C4", "MATCHED"),
                   ("C5", "MATCHED"), ("SHARED", "MATCHED"), ("MATCHED", "REF"), ("ANCH", "REF"), ("FROZEN", "REF"), ("C1", "REF"),
                   ("Q8_MATCHED", "REF"), ("Q8_FROZEN", "REF"), ("Q8_C1", "REF"), ("TFIDF", "MATCHED"), ("GEN_Q4", "GEN_FP16")):
        if a1 in S and a2 in S:
            diffs["%s-%s" % (a1, a2)] = t = boot_diff(S, a1, a2, idsA)
            md.append("| %s minus %s | %s |" % (a1, a2, fmt(t)))
    res["A"]["diffs"] = diffs
    # readout position
    pos_arms = ["REF", "POS_prefix_FP16", "POS_both_FP16", "Q8_MATCHED", "POS_prefix_Q8", "POS_both_Q8", "MATCHED", "POS_prefix_Q4", "POS_both_Q4",
                "POSprefix_FROZEN_Q4", "POSprefix_C1_Q4"]
    res["A"]["position"] = table_arms(S, pos_arms, idsA, "1.5 Readout position (matched heads; REF, Q8_MATCHED and MATCHED read at `end`)")
    pd_ = {}
    md.extend(["", "| Comparison | Difference in whole-record accuracy |", "|---|---|"])
    for a1, a2 in (("POS_prefix_Q4", "MATCHED"), ("POS_both_Q4", "MATCHED"), ("POS_prefix_FP16", "REF"), ("POS_both_FP16", "REF"),
                   ("POS_prefix_Q8", "Q8_MATCHED"), ("POS_both_Q8", "Q8_MATCHED"), ("POS_prefix_Q4", "POS_prefix_FP16"), ("POS_both_Q4", "POS_both_FP16"),
                   ("POS_both_Q4", "REF")):
        if a1 in S and a2 in S:
            pd_["%s-%s" % (a1, a2)] = t = boot_diff(S, a1, a2, idsA)
            md.append("| %s minus %s | %s |" % (a1, a2, fmt(t)))
    res["A"]["position_diffs"] = pd_

    # =============================================================== few labels
    md.extend(["", "## 2. Few labels (Protocol A folds; pair bank = whole training fold, no labels)", "",
               "| Labels | REF (FP16) | FROZEN | C1 | C2 | C3 | C4 | MATCHED | ANCH | TFIDF | ANCH minus MATCHED | C3 minus MATCHED | C2 minus MATCHED |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|"])
    res["few"] = {}
    budgets = sorted((k[1] for k in P if k[0] == "A" and k[1] != "all"), key=int)
    for lab in budgets + ["all"]:
        Sx = P[("A", lab)]
        ids = sorted(Sx["REF"][0])
        acc = {arm: arm_metrics(Sx, arm, ids)["record"] for arm in ("REF", "FROZEN", "C1", "C2", "C3", "C4", "MATCHED", "ANCH", "TFIDF") if arm in Sx}
        dd = {k: boot_diff(Sx, k.split("-")[0], "MATCHED", ids) for k in ("ANCH-MATCHED", "C3-MATCHED", "C2-MATCHED")}
        res["few"][lab] = {"acc": acc, "diffs": dd}
        md.append("| %s | %s | %s | %s | %s |" % (lab, " | ".join("%.1f%%" % (100 * acc[k]) if k in acc else "-" for k in ("REF", "FROZEN", "C1", "C2", "C3", "C4", "MATCHED", "ANCH", "TFIDF")),
                                                     fmt(dd["ANCH-MATCHED"]), fmt(dd["C3-MATCHED"]), fmt(dd["C2-MATCHED"])))

    # =============================================================== Protocol B
    S = P[("B", "all")]
    idsB = sorted(S["REF"][0])
    md.extend(["", "## 3. Protocol B: new wording (fit on all 1,000 style-A reports, test on the 400 style-B reports)", "",
               "Style B was seen many times before with other methods, so this is exploratory. One run, no repeats."])
    res["B"] = {"arms": table_arms(S, MAIN + ["Q8_FROZEN", "Q8_C1", "Q8_MATCHED", "POS_prefix_FP16", "POS_both_FP16", "POS_prefix_Q4", "POS_both_Q4",
                                              "TFIDF", "RULES", "GEN_FP16", "GEN_Q8", "GEN_Q4"], idsB, "3.1 Accuracy")}
    res["B"]["cohort_frozen"] = table_cohort(S, "FROZEN", ["C1", "C2", "C3", "C4", "C5", "SHARED", "MATCHED", "ANCH", "ANCH2"], idsB, "3.2 Repair of the frozen cohort")
    res["B"]["cohort_matched"] = table_cohort(S, "MATCHED", ["C1", "C2", "C3", "C4", "C5", "SHARED", "ANCH", "ANCH2"], idsB, "3.3 Repair of the matched cohort")
    dB = {}
    md.extend(["", "### 3.4 Paired differences in whole-record accuracy (percentage points, 95% template-bootstrap interval)", "", "| Comparison | Difference |", "|---|---|"])
    for a1, a2 in (("C2", "C1"), ("C2", "MATCHED"), ("ANCH", "MATCHED"), ("ANCH2", "MATCHED"), ("C3", "MATCHED"), ("C4", "MATCHED"), ("C5", "MATCHED"),
                   ("SHARED", "MATCHED"), ("MATCHED", "REF"), ("ANCH", "REF"), ("POS_prefix_Q4", "MATCHED"), ("POS_both_Q4", "MATCHED"),
                   ("POS_both_FP16", "REF"), ("POS_both_Q4", "POS_both_FP16"), ("TFIDF", "MATCHED")):
        if a1 in S and a2 in S:
            dB["%s-%s" % (a1, a2)] = t = boot_diff(S, a1, a2, idsB)
            md.append("| %s minus %s | %s |" % (a1, a2, fmt(t)))
    res["B"]["diffs"] = dB

    # downstream: legacy single-record replay (V1 greedy allocator, 600 s; sees only action errors)
    from packages.allocation import mission, world
    from packages.allocation.decisions import apply_decision
    pc = D.pc

    def norm_of(k):
        n = {"action": k[0]}
        if k[0] in ("UPDATE_INCIDENT", "CLOSE_INCIDENT"):
            n["incident"] = k[1]
        if k[0] in REC:
            n["landmark"], n["sensor"], n["priority"] = k[2], k[3], int(k[4])
        return n

    md.extend(["", "### 3.5 Downstream check on style B: real incidents left unverified in the legacy single-record replay", "",
               "V1 greedy allocator, 3 UAVs, 600 s horizon, one report per mission. This replay only sees action errors (audit 03).", "",
               "| Arm | Unverified of real incidents | Share |", "|---|---|---|"])
    res["B"]["replay"] = {}
    for arm in ["REF", "FROZEN", "C1", "C2", "C3", "C4", "C5", "SHARED", "MATCHED", "ANCH", "ANCH2", "POS_prefix_Q4", "POS_both_Q4", "POS_both_FP16", "TFIDF", "GEN_FP16", "GEN_Q4"]:
        if arm not in S:
            continue
        unv = tot = 0
        for cid in idsB:
            c = D.cases[idx[cid]]
            truth = {t["landmark"]: t["sensor"] for t in apply_decision(c, pc.gold_norm(c))}
            r = mission.run_mission(world.UAVS, apply_decision(c, norm_of(S[arm][0][cid])), truth)
            unv += sum(1 for l in truth if r["verify_time"].get(l) is None or r["verify_time"][l] > mission.HORIZON)
            tot += len(truth)
        res["B"]["replay"][arm] = {"unverified": unv, "incidents": tot}
        md.append("| %s | %d of %d | %.1f%% |" % (arm, unv, tot, 100 * unv / tot))

    # =============================================================== tests
    A = res["A"]["diffs"]
    t1 = A["C2-C1"][1] > 0 and A["C2-MATCHED"][0] >= -0.01
    t2 = A["ANCH-MATCHED"][1] > 0 and dB["ANCH-MATCHED"][0] >= 0
    t3 = res["few"][budgets[0]]["diffs"]["ANCH-MATCHED"][1] > 0
    pdd = res["A"]["position_diffs"]
    t4p, t4b = pdd["POS_prefix_Q4-MATCHED"][1] > 0, pdd["POS_both_Q4-MATCHED"][1] > 0
    res["tests"] = {"T1": bool(t1), "T2": bool(t2), "T3": bool(t3), "T4_prefix": bool(t4p), "T4_both": bool(t4b)}
    lab = lambda b: "SUPPORTED" if b else "NOT SHOWN"
    md.extend(["", "## 4. Tests fixed in the protocol", "",
               "| Test | Numbers | Label |", "|---|---|---|",
               "| T1 label-free transfer (C2) | C2 minus C1 %s; C2 minus MATCHED %s | **%s** |" % (fmt(A["C2-C1"]), fmt(A["C2-MATCHED"]), lab(t1)),
               "| T2 repair beyond retraining (ANCH) | Protocol A: ANCH minus MATCHED %s; Protocol B: %s | **%s** |" % (fmt(A["ANCH-MATCHED"]), fmt(dB["ANCH-MATCHED"]), lab(t2)),
               "| T3 few labels (ANCH, %s labels) | ANCH minus MATCHED %s | **%s** |" % (budgets[0], fmt(res["few"][budgets[0]]["diffs"]["ANCH-MATCHED"]), lab(t3)),
               "| T4 readout position, Q4 (general change, not a repair) | prefix minus end %s; both minus end %s; FP16 control: prefix %s, both %s | prefix **%s**, both **%s** |" % (
                   fmt(pdd["POS_prefix_Q4-MATCHED"]), fmt(pdd["POS_both_Q4-MATCHED"]), fmt(pdd["POS_prefix_FP16-REF"]), fmt(pdd["POS_both_FP16-REF"]), lab(t4p), lab(t4b))])

    # =============================================================== chosen settings
    full = [f for f in flog["folds"] if f["proto"] == "A" and f["n_lab"] == f["n_bank"]]
    md.extend(["", "## 5. Chosen settings (Protocol A, all labels, 15 folds)", ""])
    for key in ("C_REF", "C_MATCHED", "C_C3", "C_C4", "C_C5", "C_ANCH", "C_ANCH2", "C_SHARED"):
        cnt = {h: dict(Counter(str(f[key][h]) for f in full if key in f)) for h in ("action", "sensor", "prio")}
        md.append("* %s: %s" % (key, cnt))
    lam = Counter(str(f["C2_lambda"]) for f in full)
    ratio = [min(f["C2_cv_err"].values()) / f["C2_cv_err_recentre_only"] for f in full]
    md.append("* C2 lambda multiplier chosen: %s. Held-out pair reconstruction error of the chosen map / recentring only: mean %.3f (min %.3f, max %.3f)."
              % (dict(lam), np.mean(ratio), min(ratio), max(ratio)))
    res["settings"] = {"C2_lambda": dict(lam), "C2_err_ratio_mean": float(np.mean(ratio))}
    md.append("* Run time: %.0f s of fold time in total." % sum(f["seconds"] for f in flog["folds"]))
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
