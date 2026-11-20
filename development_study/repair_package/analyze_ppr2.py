"""
Analysis for readout-repair experiment 2 (PROTOCOL_REPAIR_EXP2.md). Written before the run. Reads out2/predictions.csv, out2/fold_log.json
and, for the integrity checks and cross-position comparisons, the experiment 1 file out/predictions.csv. Writes out2/RESULTS2.md and
out2/results2.json.

  python analyze_ppr2.py --root <folder with edgesar_pilot, edgesar_heads, V1> --exp1 out --out out2
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
BANKS = [50, 100, 200, 400]


def load(path):
    P = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))          # P[(proto, labels)][arm][repeat][case_id] = key tuple
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            P[(r["protocol"], r["labels"])][r["arm"]][int(r["repeat"])][r["case_id"]] = tuple(r[k] for k in FIELDS)
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--exp1", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    D = Data(a.root)
    P2 = load(out / "predictions.csv")
    P1 = load(Path(a.exp1) / "predictions.csv")
    flog = json.loads((out / "fold_log.json").read_text(encoding="utf-8"))
    idx = {c["id"]: i for i, c in enumerate(D.cases)}
    gold = {c["id"]: tuple("" if v is None else str(v) for v in D.gold_key[i]) for i, c in enumerate(D.cases)}
    tmpl = {c["id"]: D.template[i] for i, c in enumerate(D.cases)}
    gact = {c["id"]: c["gold"]["action"] for c in D.cases}
    res = {"protocol_sha256": flog["protocol_sha256"]}
    md = ["# Readout-repair experiment 2: results", "",
          "Exploratory, development data only, designed after experiment 1 was seen. Protocol hash `%s`." % flog["protocol_sha256"],
          "Arms and tests: `PROTOCOL_REPAIR_EXP2.md`. Every number is computed from `out2/predictions.csv` (and `out/predictions.csv` for "
          "experiment 1 arms) by `analyze_ppr2.py`.", ""]

    def merged(key):
        """Arms of both experiments for one (protocol, labels) cell. REF is in both (identical if the integrity check passes); experiment 2 wins."""
        S = dict(P1.get(key, {}))
        S.update(P2.get(key, {}))
        return S

    def ok_matrix(S, arm, ids):
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
        by = {}
        for g in ("CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION"):
            gi = [i for i in ids if gact[i] == g]
            by[g] = 1 - sum(S[arm][r][i] == gold[i] for r in reps for i in gi) / (len(gi) * len(reps))
        return {"n": n, "record": rec / n, "action": act / n, "sensor_on_gold_rec": sen / (len(rids) * len(reps)),
                "priority_on_gold_rec": pri / (len(rids) * len(reps)), "error_by_gold_action": by, "record_num": rec, "action_num": act}

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

    def table_cohort(S, r_arm, q_arm, arms, ids, title):
        base = cohort(S, r_arm, q_arm, q_arm, ids)
        md.extend(["", "### " + title, "",
                   "Per repeat: N = %d reports. Reference right and unmodified Q right: %.0f. **Harmful (reference right, Q wrong): %.0f = %.1f%%.** "
                   "Beneficial (reference wrong, Q right): %.0f = %.1f%%. Both wrong: %.0f." % (
                       len(ids), base["both_right"] / base["reps"], base["H"] / base["reps"], 100 * base["harmful_incidence"],
                       base["beneficial"] / base["reps"], 100 * base["beneficial"] / base["N"], base["both_wrong"] / base["reps"]), "",
                   "| Method | Repair rate (share of harmful cases now right) | New errors (share of Q-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |",
                   "|---|---|---|---|---|"])
        outd = {"base": base}
        for arm in arms:
            if arm not in S or arm == q_arm:
                continue
            c = cohort(S, r_arm, q_arm, arm, ids)
            outd[arm] = c
            md.append("| %s | %s | %s | %s | %+.1f |" % (
                arm, "undefined" if c["repair_rate"] is None else "%.1f%% (%d/%d)" % (100 * c["repair_rate"], c["H_repaired"], c["H"]),
                "undefined" if c["new_error_rate"] is None else "%.1f%% (%d/%d)" % (100 * c["new_error_rate"], c["C_broken"], c["C"]),
                "undefined" if c["correction_precision"] is None else "%.1f%% (%d/%d)" % (100 * c["correction_precision"], c["changed_correct"], c["changed"]),
                100 * (c["m_ok"] - c["C"]) / c["N"]))
        return outd

    def diff_table(S, pairs, ids, title):
        md.extend(["", "### " + title, "", "| Comparison | Difference in whole-record accuracy (points, 95% template-bootstrap interval) |", "|---|---|"])
        outd = {}
        for a1, a2 in pairs:
            if a1 in S and a2 in S:
                outd["%s-%s" % (a1, a2)] = t = boot_diff(S, a1, a2, ids)
                md.append("| %s minus %s | %s |" % (a1, a2, fmt(t)))
        return outd

    # =============================================================== integrity checks against experiment 1
    md.extend(["## 0. Integrity checks against experiment 1 (must be identical records)", ""])
    checks = {}
    same_as = {"REF": "REF", "REFp": "POS_prefix_FP16", "MATCHEDp": "POS_prefix_Q4", "FROZENp": "POSprefix_FROZEN_Q4", "C1p": "POSprefix_C1_Q4",
               "Q8_MATCHEDp": "POS_prefix_Q8"}
    all_ok = True
    for key in (("A", "all"), ("B", "all")):
        for a2, a1 in same_as.items():
            n = diff = 0
            for rp in P2[key][a2]:
                for cid, v in P2[key][a2][rp].items():
                    n += 1
                    diff += v != P1[key][a1][rp][cid]
            checks["%s %s=%s" % (key[0], a2, a1)] = {"n": n, "different": diff}
            all_ok &= diff == 0
            md.append("* Protocol %s: `%s` (experiment 2) against `%s` (experiment 1): %d of %d records differ." % (key[0], a2, a1, diff, n))
    md.append("* Few labels: the labelled reports are drawn with the same seeded call as in experiment 1; experiment 1 has no `prefix` arm at "
              "few labels, so there is nothing to compare record by record.")
    res["integrity"] = {"checks": checks, "all_identical": bool(all_ok)}
    md.append("")
    md.append("**Integrity: %s.**" % ("PASS" if all_ok else "FAIL - the run is void"))

    # =============================================================== Protocol A
    S = merged(("A", "all"))
    idsA = sorted(P2[("A", "all")]["REFp"][0])
    md.extend(["", "## 1. Protocol A: same wording style (1,000 style-A reports, 5 folds by template, 3 repeats)", "",
               "Rates are pooled over the 3 repeats (3,000 report decisions per arm)."])
    res["A"] = {"arms": table_arms(S, ["REFp", "FROZENp", "C1p", "C2p", "C3p", "MATCHEDp", "Q8_FROZENp", "Q8_C1p", "Q8_C2p", "Q8_MATCHEDp",
                                       "REF", "MATCHED", "C2", "Q8_FROZEN", "Q8_C1", "Q8_C2", "Q8_MATCHED"], idsA,
                                   "1.1 Accuracy (suffix p = `prefix` position; the last seven rows are the `end` position, from experiment 1 except Q8_C2)")}
    res["A"]["cohort_frozen_p"] = table_cohort(S, "REFp", "FROZENp", ["C1p", "C2p", "C3p", "MATCHEDp"], idsA,
                                               "1.2 Repair of the frozen cohort at `prefix` (unmodified Q4 = REFp heads on raw Q4 vectors)")
    res["A"]["cohort_matched_p"] = table_cohort(S, "REFp", "MATCHEDp", ["C1p", "C2p", "C3p"], idsA,
                                                "1.3 Repair of the matched cohort at `prefix` (unmodified Q4 = heads refitted on Q4 vectors)")
    res["A"]["cohort_q8_frozen_p"] = table_cohort(S, "REFp", "Q8_FROZENp", ["Q8_C1p", "Q8_C2p", "Q8_MATCHEDp"], idsA,
                                                  "1.4 Control at Q8, `prefix`: frozen cohort (unmodified Q8 = REFp heads on raw Q8 vectors)")
    res["A"]["cohort_q8_frozen_end"] = table_cohort(S, "REF", "Q8_FROZEN", ["Q8_C1", "Q8_C2", "Q8_MATCHED"], idsA,
                                                    "1.5 Control at Q8, `end`: frozen cohort")
    res["A"]["diffs"] = diff_table(S, [("C2p", "MATCHEDp"), ("C2p", "REFp"), ("C2p", "C1p"), ("C3p", "MATCHEDp"), ("C3p", "REFp"), ("C1p", "MATCHEDp"),
                                       ("MATCHEDp", "REFp"), ("FROZENp", "REFp"), ("C2p", "REF"), ("C2p", "MATCHED"), ("C2p", "C2"),
                                       ("Q8_C2p", "Q8_MATCHEDp"), ("Q8_C2p", "REFp"), ("Q8_MATCHEDp", "REFp"), ("Q8_FROZENp", "REFp"),
                                       ("Q8_C2", "Q8_MATCHED"), ("Q8_C2", "REF"), ("Q8_C2", "Q8_C1")], idsA, "1.6 Paired differences")
    # bank-size curve
    md.extend(["", "### 1.7 How many unlabelled pairs does the map need? (`prefix`, Q4; REFp heads use all labels)", "",
               "| Pairs in the bank | Recentring (C1p) | Affine map (C2p) | C2p minus MATCHEDp | C2p minus REFp |", "|---|---|---|---|---|"])
    res["A"]["bank"] = {}
    for nb in BANKS + ["all"]:
        a1, a2 = ("C1p", "C2p") if nb == "all" else ("C1p_bank%d" % nb, "C2p_bank%d" % nb)
        if a2 not in S:
            continue
        m1, m2 = arm_metrics(S, a1, idsA)["record"], arm_metrics(S, a2, idsA)["record"]
        d1, d2 = boot_diff(S, a2, "MATCHEDp", idsA), boot_diff(S, a2, "REFp", idsA)
        res["A"]["bank"][str(nb)] = {"C1p": m1, "C2p": m2, "C2p-MATCHEDp": d1, "C2p-REFp": d2}
        md.append("| %s | %.1f%% | %.1f%% | %s | %s |" % ("about 800 (whole training fold)" if nb == "all" else nb, 100 * m1, 100 * m2, fmt(d1), fmt(d2)))

    # =============================================================== few labels
    md.extend(["", "## 2. Few labels at `prefix` (Protocol A folds; pair bank = whole training fold, no labels)", "",
               "| Labels | REFp (FP16) | FROZENp | C1p | C2p | C3p | MATCHEDp | C2p minus MATCHEDp | C3p minus MATCHEDp | C2p minus REFp |",
               "|---|---|---|---|---|---|---|---|---|---|"])
    res["few"] = {}
    budgets = sorted((k[1] for k in P2 if k[0] == "A" and k[1] != "all"), key=int)
    for lab in budgets + ["all"]:
        Sx = P2[("A", lab)]
        ids = sorted(Sx["REFp"][0])
        acc = {arm: arm_metrics(Sx, arm, ids)["record"] for arm in ("REFp", "FROZENp", "C1p", "C2p", "C3p", "MATCHEDp")}
        dd = {"C2p-MATCHEDp": boot_diff(Sx, "C2p", "MATCHEDp", ids), "C3p-MATCHEDp": boot_diff(Sx, "C3p", "MATCHEDp", ids),
              "C2p-REFp": boot_diff(Sx, "C2p", "REFp", ids)}
        res["few"][lab] = {"acc": acc, "diffs": dd}
        md.append("| %s | %s | %s | %s | %s |" % (lab, " | ".join("%.1f%%" % (100 * acc[k]) for k in ("REFp", "FROZENp", "C1p", "C2p", "C3p", "MATCHEDp")),
                                                 fmt(dd["C2p-MATCHEDp"]), fmt(dd["C3p-MATCHEDp"]), fmt(dd["C2p-REFp"])))

    # =============================================================== Protocol B
    S = merged(("B", "all"))
    idsB = sorted(P2[("B", "all")]["REFp"][0])
    md.extend(["", "## 3. Protocol B: new wording (fit on all 1,000 style-A reports, test on the 400 style-B reports)", "",
               "Style B was seen many times before, so this is exploratory. One run, no repeats."])
    res["B"] = {"arms": table_arms(S, ["REFp", "FROZENp", "C1p", "C2p", "C3p", "MATCHEDp", "Q8_FROZENp", "Q8_C1p", "Q8_C2p", "Q8_MATCHEDp",
                                       "REF", "MATCHED", "C2", "Q8_C2", "Q8_MATCHED"], idsB, "3.1 Accuracy")}
    res["B"]["cohort_frozen_p"] = table_cohort(S, "REFp", "FROZENp", ["C1p", "C2p", "C3p", "MATCHEDp"], idsB, "3.2 Repair of the frozen cohort at `prefix`")
    res["B"]["cohort_matched_p"] = table_cohort(S, "REFp", "MATCHEDp", ["C1p", "C2p", "C3p"], idsB, "3.3 Repair of the matched cohort at `prefix`")
    res["B"]["diffs"] = diff_table(S, [("C2p", "MATCHEDp"), ("C2p", "REFp"), ("C2p", "C1p"), ("C3p", "MATCHEDp"), ("C3p", "REFp"), ("MATCHEDp", "REFp"),
                                       ("C2p", "REF"), ("C2p", "MATCHED"), ("Q8_C2p", "Q8_MATCHEDp"), ("Q8_C2p", "REFp"), ("Q8_C2", "Q8_MATCHED"),
                                       ("Q8_C2", "REF")], idsB, "3.4 Paired differences")
    md.extend(["", "### 3.5 Bank-size curve on style B (`prefix`, Q4)", "", "| Pairs in the bank | Recentring (C1p) | Affine map (C2p) |", "|---|---|---|"])
    res["B"]["bank"] = {}
    for nb in BANKS + ["all"]:
        a1, a2 = ("C1p", "C2p") if nb == "all" else ("C1p_bank%d" % nb, "C2p_bank%d" % nb)
        if a2 in S:
            m1, m2 = arm_metrics(S, a1, idsB)["record"], arm_metrics(S, a2, idsB)["record"]
            res["B"]["bank"][str(nb)] = {"C1p": m1, "C2p": m2}
            md.append("| %s | %.1f%% | %.1f%% |" % ("1,000 (all style A)" if nb == "all" else nb, 100 * m1, 100 * m2))

    # downstream: legacy single-record replay on style B
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

    md.extend(["", "### 3.6 Downstream check on style B: real incidents left unverified in the legacy single-record replay", "",
               "V1 greedy allocator, 3 UAVs, 600 s horizon, one report per mission. This replay only sees action errors (audit 03).", "",
               "| Arm | Unverified of real incidents | Share |", "|---|---|---|"])
    res["B"]["replay"] = {}
    for arm in ["REFp", "FROZENp", "C1p", "C2p", "C3p", "MATCHEDp", "Q8_C2p", "Q8_MATCHEDp", "REF", "MATCHED", "C2"]:
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
    t1 = A["C2p-MATCHEDp"][1] > 0
    t2 = A["C2p-REFp"][0] >= -0.01
    t3 = res["few"][budgets[0]]["diffs"]["C2p-MATCHEDp"][1] > 0
    res["tests"] = {"E2-T1": bool(t1), "E2-T2": bool(t2), "E2-T3": bool(t3)}
    lab = lambda b: "SUPPORTED" if b else "NOT SHOWN"
    dB = res["B"]["diffs"]
    md.extend(["", "## 4. Tests fixed in the protocol", "",
               "| Test | Numbers (Protocol A; Protocol B beside it, descriptive) | Label |", "|---|---|---|",
               "| E2-T1 transfer beyond retraining at `prefix` | C2p minus MATCHEDp %s; style B %s | **%s** |" % (fmt(A["C2p-MATCHEDp"]), fmt(dB["C2p-MATCHEDp"]), lab(t1)),
               "| E2-T2 repair to the reference level | C2p minus REFp %s; style B %s | **%s** |" % (fmt(A["C2p-REFp"]), fmt(dB["C2p-REFp"]), lab(t2)),
               "| E2-T3 few labels (%s labels) | C2p minus MATCHEDp %s | **%s** |" % (budgets[0], fmt(res["few"][budgets[0]]["diffs"]["C2p-MATCHEDp"]), lab(t3))])

    # =============================================================== chosen settings
    full = [f for f in flog["folds"] if f["proto"] == "A" and f["n_lab"] == f["n_bank"]]
    md.extend(["", "## 5. Chosen settings (Protocol A, all labels, 15 folds)", ""])
    for key in ("C_REFp", "C_MATCHEDp", "C_C3p"):
        md.append("* %s: %s" % (key, {h: dict(Counter(str(f[key][h]) for f in full)) for h in ("action", "sensor", "prio")}))
    for key, name in (("C2p", "Q4 `prefix`"), ("Q8_C2p", "Q8 `prefix`"), ("Q8_C2", "Q8 `end`")):
        lam = Counter(str(f[key + "_lambda"]) for f in full)
        ratio = [min(f[key + "_cv_err"].values()) / f[key + "_cv_err_recentre_only"] for f in full]
        md.append("* Affine map, %s: lambda multiplier chosen %s. Held-out pair reconstruction error of the chosen map / recentring only: mean %.3f (min %.3f, max %.3f)."
                  % (name, dict(lam), np.mean(ratio), min(ratio), max(ratio)))
        res.setdefault("settings", {})[key] = {"lambda": dict(lam), "err_ratio_mean": float(np.mean(ratio))}
    md.append("* Run time: %.0f s of fold time in total." % sum(f["seconds"] for f in flog["folds"]))
    (out / "RESULTS2.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "results2.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
