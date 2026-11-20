"""
Runner for the readout-repair feasibility experiment (PROTOCOL_REPAIR_FEASIBILITY.md).

  python run_ppr.py --root <folder with edgesar_pilot, edgesar_heads, V1> --out out [--procs 2] [--quick]

Writes out/predictions.csv (one row per protocol, repeat, fold, label budget, arm, report), out/fold_log.json (chosen C and lambda),
out/PROTOCOL.sha256. Nothing is written into the project folders. --quick runs one fold with few arms (code check only).
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
from ppr_lib import (ACTIONS, HEADS, REC, AffineMap, Data, Head, Recentre, assemble, fit_head, group_folds, softmax)

SEED = 20261113
REPEATS = 3
FOLDS = 5
LABEL_BUDGETS = [100, 300]
OOF = 5
AUG = 4
D = None


def fit_heads(X, rows, seed, T=None, O=None, scaler=None, groups=None, fixed_C=None, w=None):
    out = {}
    for h in HEADS:
        r = rows[h]
        out[h] = fit_head(X[h] if isinstance(X, dict) else X[r],
                          D.onehot(h, r) if T is None else T[h], D.template[r] if groups is None else groups[h], HEADS[h],
                          O=None if O is None else O[h], scaler=None if scaler is None else scaler[h],
                          fixed_C=None if fixed_C is None else fixed_C[h], w=None if w is None else w[h], seed=seed)
    return out


def logits(heads, X, offset=None):
    return {h: heads[h].logits(X, None if offset is None else offset[h]) for h in HEADS}


def run_fold(task):
    proto, rep, fold, n_lab, tr, te, seed, quick = task
    t0 = time.time()
    F, Q4, Q8 = D.X[("f16", "end")], D.X[("Q4_K_M", "end")], D.X[("Q8_0", "end")]
    full = n_lab is None
    if full:
        lab = tr
    else:
        rng = np.random.default_rng(seed + 7)
        while True:
            lab = np.sort(rng.choice(tr, size=n_lab, replace=False))
            if len(set(D.y["action"][lab])) == 4:
                break
    unl = np.setdiff1d(tr, lab)
    rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
    log = {"proto": proto, "repeat": rep, "fold": fold, "n_lab": len(lab), "n_bank": len(tr), "n_test": len(te)}
    pred = {}

    def put(arm, L):
        pred[arm] = assemble(D, te, L)

    # ---------------- reference heads and the frozen readout
    REF = fit_heads(F, rows, seed)
    log["C_REF"] = {h: REF[h].C for h in HEADS}
    put("REF", logits(REF, F[te]))
    put("FROZEN", logits(REF, Q4[te]))
    # ---------------- label-free maps
    rec = Recentre(F[tr], Q4[tr])
    put("C1", logits(REF, rec(Q4[te])))
    amap = AffineMap(F[tr], Q4[tr], D.template[tr], seed)
    log["C2_lambda"] = amap.c
    log["C2_cv_err"] = amap.cv_err
    log["C2_cv_err_recentre_only"] = amap.cv_err_recentre_only
    put("C2", logits(REF, amap(Q4[te])))
    # ---------------- matched heads
    MAT = fit_heads(Q4, rows, seed)
    log["C_MATCHED"] = {h: MAT[h].C for h in HEADS}
    put("MATCHED", logits(MAT, Q4[te]))
    if quick:
        return proto, rep, fold, n_lab, te, pred, log, time.time() - t0

    # ---------------- out-of-fold teacher logits on the labelled rows (teacher C fixed at REF's C)
    oofF, oofR, oofA = {}, {}, {}
    for h in HEADS:
        r = rows[h]
        K = len(HEADS[h])
        oofF[h], oofR[h], oofA[h] = np.zeros((len(r), K)), np.zeros((len(r), K)), np.zeros((len(r), K))
        f = group_folds(D.template[r], OOF, seed + 1)
        for k in range(OOF):
            a, b = r[f != k], r[f == k]
            if len(b) == 0:
                continue
            t = fit_head(F[a], D.onehot(h, a), D.template[a], HEADS[h], fixed_C=REF[h].C)
            oofF[h][f == k] = t.logits(F[b])
            oofR[h][f == k] = t.logits(rec(Q4[b]))
            oofA[h][f == k] = t.logits(amap(Q4[b]))
    # ---------------- C3: label-free distillation of the reference heads over the pair bank
    ref_act_bank = softmax(REF["action"].logits(F[tr]))
    bank_rec = tr[np.isin(np.array(ACTIONS)[ref_act_bank.argmax(1)], REC)]
    rows3 = {"action": tr, "sensor": bank_rec, "prio": bank_rec}
    T3 = {h: softmax(REF[h].logits(F[rows3[h]])) for h in HEADS}
    S3 = fit_heads(Q4, rows3, seed, T=T3)
    log["C_C3"] = {h: S3[h].C for h in HEADS}
    put("C3", logits(S3, Q4[te]))
    # ---------------- C4: privileged distillation (labels + reference probabilities)
    unl_rec = unl[np.isin(np.array(ACTIONS)[softmax(REF["action"].logits(F[unl])).argmax(1)], REC)] if len(unl) else unl
    rows4, T4 = {}, {}
    for h in HEADS:
        extra = unl if h == "action" else unl_rec
        rows4[h] = np.concatenate([rows[h], extra]).astype(int)
        mix = 0.5 * D.onehot(h, rows[h]) + 0.5 * softmax(oofF[h])
        T4[h] = np.vstack([mix, softmax(REF[h].logits(F[extra]))]) if len(extra) else mix
    S4 = fit_heads(Q4, rows4, seed, T=T4)
    log["C_C4"] = {h: S4[h].C for h in HEADS}
    put("C4", logits(S4, Q4[te]))
    # ---------------- ANCH / ANCH2: reference heads on mapped Q4 vectors + a learned correction
    for arm, mp_, oof in (("ANCH", rec, oofR), ("ANCH2", amap, oofA)):
        if arm == "ANCH2" and not full:
            continue
        Xm = mp_(Q4)
        Dl = fit_heads(Xm, rows, seed, O=oof, scaler={h: REF[h].scaler for h in HEADS})
        log["C_" + arm] = {h: Dl[h].C for h in HEADS}
        put(arm, logits(Dl, Xm[te], offset=logits(REF, Xm[te])))
    if full:
        # ---------------- C5: residual-bank augmentation
        rng = np.random.default_rng(seed + 11)
        X5, T5, G5 = {}, {}, {}
        for h in HEADS:
            r = rows[h]
            j = rng.choice(tr, size=(len(r), AUG))
            X5[h] = (F[r][:, None, :] + (Q4[j] - F[j])).reshape(len(r) * AUG, -1)
            T5[h] = np.repeat(D.onehot(h, r), AUG, axis=0)
            G5[h] = np.repeat(D.template[r], AUG)
        S5 = fit_heads(X5, rows, seed, T=T5, groups=G5)
        log["C_C5"] = {h: S5[h].C for h in HEADS}
        put("C5", logits(S5, Q4[te]))
        # ---------------- SHARED: one set of heads for FP16 and Q4 vectors
        Xs = {h: np.vstack([F[rows[h]], Q4[rows[h]]]) for h in HEADS}
        Ts = {h: np.vstack([D.onehot(h, rows[h])] * 2) for h in HEADS}
        Gs = {h: np.concatenate([D.template[rows[h]]] * 2) for h in HEADS}
        SH = fit_heads(Xs, rows, seed, T=Ts, groups=Gs)
        log["C_SHARED"] = {h: SH[h].C for h in HEADS}
        put("SHARED", logits(SH, Q4[te]))
        put("SHARED_on_FP16", logits(SH, F[te]))
        # ---------------- Q8 arms
        rec8 = Recentre(F[tr], Q8[tr])
        put("Q8_FROZEN", logits(REF, Q8[te]))
        put("Q8_C1", logits(REF, rec8(Q8[te])))
        M8 = fit_heads(Q8, rows, seed)
        put("Q8_MATCHED", logits(M8, Q8[te]))
        # ---------------- readout position (general change; all precisions)
        for m, name in (("f16", "FP16"), ("Q8_0", "Q8"), ("Q4_K_M", "Q4")):
            P = D.X[(m, "prefix")]
            Hp = fit_heads(P, rows, seed)
            put("POS_prefix_" + name, logits(Hp, P[te]))
            B = np.hstack([D.X[(m, "end")], P])
            Hb = fit_heads(B, rows, seed)
            put("POS_both_" + name, logits(Hb, B[te]))
        # frozen / recentred at the prefix position (does the offset finding hold there?)
        Pf, Pq = D.X[("f16", "prefix")], D.X[("Q4_K_M", "prefix")]
        Hpf = fit_heads(Pf, rows, seed)
        put("POSprefix_FROZEN_Q4", logits(Hpf, Pq[te]))
        put("POSprefix_C1_Q4", logits(Hpf, Recentre(Pf[tr], Pq[tr])(Pq[te])))
    # ---------------- non-LLM baselines (pilot code)
    tf = D.pb.LRBaseline().fit([D.cases[i] for i in lab])
    pred["TFIDF"] = [D.pc.validate(d, D.cases[i])[0] for i, d in zip(te, tf.predict([D.cases[i] for i in te]))]
    if full:
        pred["RULES"] = [D.pc.validate(D.pb.rule_decision(D.cases[i]), D.cases[i])[0] for i in te]
        pred["GEN_FP16"], pred["GEN_Q4"], pred["GEN_Q8"] = ([GEN[m][D.cases[i]["id"]] for i in te] for m in ("f16", "q4", "q8"))
    return proto, rep, fold, n_lab, te, pred, log, time.time() - t0


GEN = {}


def load_generative():
    for m, run in (("f16", "f16_P1"), ("q4", "q4_P1"), ("q8", "q8_P1")):
        GEN[m] = {}
        cb = {c["id"]: c for c in D.cases}
        with open(D.pilot / "runs" / (run + ".jsonl"), encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    r = json.loads(l)
                    obj, _ = D.pc.parse_decision(r["text"])
                    GEN[m][r["case_id"]] = D.pc.validate(obj, cb[r["case_id"]])[0]


def main():
    global D
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="code check only: small random subsample, all arms, separate output folder; numbers are meaningless")
    a = ap.parse_args()
    global REPEATS, FOLDS, LABEL_BUDGETS
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    psha = hashlib.sha256((here / "PROTOCOL_REPAIR_FEASIBILITY.md").read_bytes()).hexdigest()
    if not a.quick:
        (out / "PROTOCOL.sha256").write_text(psha + "  PROTOCOL_REPAIR_FEASIBILITY.md\n", encoding="utf-8")
    D = Data(a.root)
    load_generative()
    A = np.where(D.split == "dev")[0]
    B = np.where(D.split == "held")[0]
    if a.smoke:
        rs = np.random.default_rng(5)
        A, B = np.sort(rs.choice(A, 240, replace=False)), np.sort(rs.choice(B, 60, replace=False))
        REPEATS, FOLDS, LABEL_BUDGETS = 1, 2, [60]
    tasks = []
    for rep in range(REPEATS):
        f = group_folds(D.template[A], FOLDS, SEED + rep)
        for k in range(FOLDS):
            tr, te = A[f != k], A[f == k]
            assert not set(D.template[tr]) & set(D.template[te])
            tasks.append(("A", rep, k, None, tr, te, SEED + 100 * rep + k, a.quick))
            for nl in LABEL_BUDGETS:
                tasks.append(("A", rep, k, nl, tr, te, SEED + 100 * rep + k, False))
    tasks.append(("B", 0, 0, None, A, B, SEED + 999, a.quick))
    if a.quick:
        tasks = [tasks[0], tasks[-1]]
    tasks.sort(key=lambda t: -(len(t[4]) if t[3] is None else t[3]))          # long jobs first
    print("protocol sha256 %s; %d tasks; %d processes" % (psha[:16], len(tasks), a.procs), flush=True)
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
    name = "predictions_quick.csv" if a.quick else "predictions.csv"
    rows.sort(key=lambda r: (r[0], r[1], r[2], str(r[3]), r[4], r[5]))
    with open(out / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["protocol", "repeat", "fold", "labels", "arm", "case_id", "action", "incident", "landmark", "sensor", "priority", "record_ok", "action_ok"])
        w.writerows(rows)
    logs.sort(key=lambda l: (l["proto"], l["repeat"], l["fold"], l["n_lab"]))
    (out / ("fold_log_quick.json" if a.quick else "fold_log.json")).write_text(json.dumps({"protocol_sha256": psha, "seed": SEED, "folds": logs}, indent=1), encoding="utf-8")
    print("wrote %s (%d rows) in %.0f s" % (name, len(rows), time.time() - t0))


if __name__ == "__main__":
    main()
