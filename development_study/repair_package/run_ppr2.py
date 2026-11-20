"""
Runner for readout-repair experiment 2 (PROTOCOL_REPAIR_EXP2.md): the label-free affine map at the `prefix` readout position,
Q8 controls, and the bank-size curve. Uses ppr_lib.py and the helper functions of run_ppr.py unchanged, with the same seeds, folds and
few-label draws as experiment 1, so every arm is paired with the experiment 1 arms.

  python run_ppr2.py --root <folder with edgesar_pilot, edgesar_heads, V1> --out out2 [--procs 2] [--smoke]

Writes out2/predictions.csv, out2/fold_log.json, out2/PROTOCOL2.sha256. Nothing is written into the project folders.
"""
import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np

sys.dont_write_bytecode = True
import run_ppr as R1                                         # fit_heads, logits, SEED, REPEATS, FOLDS, LABEL_BUDGETS (experiment 1)
from ppr_lib import ACTIONS, HEADS, REC, AffineMap, Data, Recentre, assemble, group_folds, softmax

BANK_SIZES = [50, 100, 200, 400]
D = None


def run_fold(task):
    proto, rep, fold, n_lab, tr, te, seed = task
    t0 = time.time()
    Fe, Q8e = D.X[("f16", "end")], D.X[("Q8_0", "end")]
    Fp, Q4p, Q8p = D.X[("f16", "prefix")], D.X[("Q4_K_M", "prefix")], D.X[("Q8_0", "prefix")]
    full = n_lab is None
    if full:
        lab = tr
    else:                                                    # the same draw as experiment 1
        rng = np.random.default_rng(seed + 7)
        while True:
            lab = np.sort(rng.choice(tr, size=n_lab, replace=False))
            if len(set(D.y["action"][lab])) == 4:
                break
    rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
    log = {"proto": proto, "repeat": rep, "fold": fold, "n_lab": len(lab), "n_bank": len(tr), "n_test": len(te)}
    pred = {}

    def put(arm, L):
        pred[arm] = assemble(D, te, L)

    # ---------------- prefix position: reference, frozen, label-free maps, matched
    REFp = R1.fit_heads(Fp, rows, seed)
    log["C_REFp"] = {h: REFp[h].C for h in HEADS}
    put("REFp", R1.logits(REFp, Fp[te]))
    put("FROZENp", R1.logits(REFp, Q4p[te]))
    recp = Recentre(Fp[tr], Q4p[tr])
    put("C1p", R1.logits(REFp, recp(Q4p[te])))
    amapp = AffineMap(Fp[tr], Q4p[tr], D.template[tr], seed)
    log["C2p_lambda"], log["C2p_cv_err"], log["C2p_cv_err_recentre_only"] = amapp.c, amapp.cv_err, amapp.cv_err_recentre_only
    put("C2p", R1.logits(REFp, amapp(Q4p[te])))
    MATp = R1.fit_heads(Q4p, rows, seed)
    log["C_MATCHEDp"] = {h: MATp[h].C for h in HEADS}
    put("MATCHEDp", R1.logits(MATp, Q4p[te]))
    # ---------------- C3p: label-free distillation of the prefix reference heads over the pair bank
    ref_act_bank = softmax(REFp["action"].logits(Fp[tr]))
    bank_rec = tr[np.isin(np.array(ACTIONS)[ref_act_bank.argmax(1)], REC)]
    rows3 = {"action": tr, "sensor": bank_rec, "prio": bank_rec}
    T3 = {h: softmax(REFp[h].logits(Fp[rows3[h]])) for h in HEADS}
    S3 = R1.fit_heads(Q4p, rows3, seed, T=T3)
    log["C_C3p"] = {h: S3[h].C for h in HEADS}
    put("C3p", R1.logits(S3, Q4p[te]))
    if full:
        # ---------------- Q8 at prefix (control at a higher precision)
        put("Q8_FROZENp", R1.logits(REFp, Q8p[te]))
        put("Q8_C1p", R1.logits(REFp, Recentre(Fp[tr], Q8p[tr])(Q8p[te])))
        amap8p = AffineMap(Fp[tr], Q8p[tr], D.template[tr], seed)
        log["Q8_C2p_lambda"], log["Q8_C2p_cv_err"], log["Q8_C2p_cv_err_recentre_only"] = amap8p.c, amap8p.cv_err, amap8p.cv_err_recentre_only
        put("Q8_C2p", R1.logits(REFp, amap8p(Q8p[te])))
        M8p = R1.fit_heads(Q8p, rows, seed)
        put("Q8_MATCHEDp", R1.logits(M8p, Q8p[te]))
        # ---------------- end position: REF (integrity check against experiment 1) and the affine map at Q8
        REFe = R1.fit_heads(Fe, rows, seed)
        put("REF", R1.logits(REFe, Fe[te]))
        amap8e = AffineMap(Fe[tr], Q8e[tr], D.template[tr], seed)
        log["Q8_C2_lambda"], log["Q8_C2_cv_err"], log["Q8_C2_cv_err_recentre_only"] = amap8e.c, amap8e.cv_err, amap8e.cv_err_recentre_only
        put("Q8_C2", R1.logits(REFe, amap8e(Q8e[te])))
        # ---------------- bank-size curve (prefix, Q4): how many unlabelled pairs does the map need?
        rngb = np.random.default_rng(seed + 23)
        log["bank"] = {}
        for nb in BANK_SIZES:
            sub = np.sort(rngb.choice(tr, size=nb, replace=False))
            put("C1p_bank%d" % nb, R1.logits(REFp, Recentre(Fp[sub], Q4p[sub])(Q4p[te])))
            m = AffineMap(Fp[sub], Q4p[sub], D.template[sub], seed)
            log["bank"][str(nb)] = {"lambda": m.c, "templates": int(len(set(D.template[sub])))}
            put("C2p_bank%d" % nb, R1.logits(REFp, m(Q4p[te])))
    return proto, rep, fold, n_lab, te, pred, log, time.time() - t0


def main():
    global D
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--smoke", action="store_true", help="code check only: small random subsample; numbers are meaningless")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    psha = hashlib.sha256((here / "PROTOCOL_REPAIR_EXP2.md").read_bytes()).hexdigest()
    (out / "PROTOCOL2.sha256").write_text(psha + "  PROTOCOL_REPAIR_EXP2.md\n", encoding="utf-8")
    D = Data(a.root)
    R1.D = D                                                  # the experiment 1 helpers read this global
    A = np.where(D.split == "dev")[0]
    B = np.where(D.split == "held")[0]
    repeats, folds, budgets = R1.REPEATS, R1.FOLDS, R1.LABEL_BUDGETS
    if a.smoke:
        rs = np.random.default_rng(5)
        A, B = np.sort(rs.choice(A, 240, replace=False)), np.sort(rs.choice(B, 60, replace=False))
        repeats, folds, budgets = 1, 2, [60]
        global BANK_SIZES
        BANK_SIZES = [50, 100]
    tasks = []
    for rep in range(repeats):
        f = group_folds(D.template[A], folds, R1.SEED + rep)
        for k in range(folds):
            tr, te = A[f != k], A[f == k]
            assert not set(D.template[tr]) & set(D.template[te])
            tasks.append(("A", rep, k, None, tr, te, R1.SEED + 100 * rep + k))
            for nl in budgets:
                tasks.append(("A", rep, k, nl, tr, te, R1.SEED + 100 * rep + k))
    tasks.append(("B", 0, 0, None, A, B, R1.SEED + 999))
    tasks.sort(key=lambda t: -(len(t[4]) if t[3] is None else t[3]))
    print("protocol2 sha256 %s; %d tasks; %d processes" % (psha[:16], len(tasks), a.procs), flush=True)
    t0 = time.time()
    rows, logs = [], []
    with mp.get_context("fork").Pool(a.procs) as pool:
        for proto, rep, fold, n_lab, te, pred, log, dt in pool.imap_unordered(run_fold, tasks):
            logs.append(dict(log, seconds=round(dt, 1)))
            for arm, recs in pred.items():
                for i, n in zip(te, recs):
                    k = D.pc.strict_key(n)
                    rows.append([proto, rep, fold, "all" if n_lab is None else n_lab, arm, D.cases[i]["id"], *["" if v is None else v for v in k],
                                 int(k == D.gold_key[i]), int(n["action"] == D.y["action"][i])])
            print("  done %s rep %d fold %d labels %s in %.0f s (total %.0f s)" % (proto, rep, fold, n_lab or "all", dt, time.time() - t0), flush=True)
    rows.sort(key=lambda r: (r[0], r[1], r[2], str(r[3]), r[4], r[5]))
    with open(out / "predictions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["protocol", "repeat", "fold", "labels", "arm", "case_id", "action", "incident", "landmark", "sensor", "priority", "record_ok", "action_ok"])
        w.writerows(rows)
    logs.sort(key=lambda l: (l["proto"], l["repeat"], l["fold"], l["n_lab"]))
    (out / "fold_log.json").write_text(json.dumps({"protocol_sha256": psha, "seed": R1.SEED, "folds": logs}, indent=1), encoding="utf-8")
    print("wrote predictions.csv (%d rows) in %.0f s" % (len(rows), time.time() - t0))


if __name__ == "__main__":
    main()
