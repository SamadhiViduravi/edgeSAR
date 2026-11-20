"""
Unplanned descriptive diagnostic (14 Nov 2026), added after reading Duan (arXiv 2606.15980), who reports that linear activation monitors
are "nearly flat" under quantization when measured by AUC. Question: under GGUF Q4_K_M, does the frozen FP16 head keep its RANKING quality
(AUC) while its DECISIONS (argmax) break? No test is attached; nothing is tuned; style B is only scored.

Protocol B setting of experiment 1: heads fitted on all 1,000 style-A reports (same seed as experiment 1, so the same heads), scored on the
400 style-B reports. Also the 5 folds of repeat 0 of Protocol A (same folds as experiment 1), pooled.

  python diag_auc.py --root <folder with edgesar_pilot, edgesar_heads, V1> --out out_diag
"""
import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
from sklearn.metrics import roc_auc_score

sys.dont_write_bytecode = True
import run_ppr as R1
from ppr_lib import HEADS, AffineMap, Data, Recentre, group_folds, softmax


def ovr_auc(y, S, classes):
    """Macro one-vs-rest AUC of the columns of S (one score per class). Classes absent from y are skipped."""
    out = []
    for k, c in enumerate(classes):
        pos = (y == c)
        if pos.sum() == 0 or pos.sum() == len(y):
            continue
        out.append(roc_auc_score(pos, S[:, k]))
    return float(np.mean(out))


def score(D, heads, X_by_arm, te, pos):
    res = {}
    for arm, X in X_by_arm.items():
        r = {}
        for h, cls in HEADS.items():
            rows = te if h == "action" else te[D.is_rec[te]]
            L = heads[h].logits(X[rows])
            y = D.y[h][rows]
            r[h] = {"n": int(len(rows)), "accuracy": float((np.array(cls)[L.argmax(1)] == y).mean()),
                    "auc_logit": ovr_auc(y, L, cls), "auc_prob": ovr_auc(y, softmax(L), cls)}
        res[arm] = r
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    D = Data(a.root)
    R1.D = D
    A = np.where(D.split == "dev")[0]
    B = np.where(D.split == "held")[0]
    res = {}
    for pos in ("end", "prefix"):
        F, Q4, Q8 = D.X[("f16", pos)], D.X[("Q4_K_M", pos)], D.X[("Q8_0", pos)]

        def arms(tr, te):
            return {"FP16 vectors (reference)": F, "raw Q4 vectors (frozen head)": Q4, "Q4 recentred (C1)": Recentre(F[tr], Q4[tr])(Q4),
                    "Q4 affine map (C2)": AffineMap(F[tr], Q4[tr], D.template[tr], seed)(Q4), "raw Q8 vectors (frozen head)": Q8}

        # Protocol B: fit on all style A, score style B (same seed as experiment 1)
        seed = R1.SEED + 999
        rows = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
        heads = R1.fit_heads(F, rows, seed)
        res["B_" + pos] = score(D, heads, arms(A, B), B, pos)
        # Protocol A, repeat 0: pooled over the 5 folds (scores are pooled after fitting each fold; AUC is computed per fold and averaged)
        f = group_folds(D.template[A], R1.FOLDS, R1.SEED + 0)
        per = []
        for k in range(R1.FOLDS):
            tr, te = A[f != k], A[f == k]
            seed = R1.SEED + k
            rows = {"action": tr, "sensor": tr[D.is_rec[tr]], "prio": tr[D.is_rec[tr]]}
            heads = R1.fit_heads(F, rows, seed)
            per.append(score(D, heads, arms(tr, te), te, pos))
        avg = {}
        for arm in per[0]:
            avg[arm] = {h: {m: float(np.mean([p[arm][h][m] for p in per])) for m in ("accuracy", "auc_logit", "auc_prob")} for h in HEADS}
        res["A_" + pos] = avg
    (out / "auc_diag.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = ["# Diagnostic: ranking (AUC) against decisions (argmax) for the frozen FP16 head", "",
          "Unplanned, descriptive, development data. Heads are fitted on FP16 vectors only. `AUC` is the macro one-vs-rest AUC of each class score "
          "(the class logit; the softmax probability gives the second number). `Accuracy` is the argmax decision of the same head.", ""]
    for key, title in (("A_end", "Style A (5 folds of repeat 0, mean over folds), `end` position"), ("B_end", "Style B (fit on all style A), `end` position"),
                       ("A_prefix", "Style A, `prefix` position"), ("B_prefix", "Style B, `prefix` position")):
        md.extend(["", "## " + title, "", "| Vectors given to the FP16 head | Action: accuracy | Action: AUC (logit / probability) | Sensor: accuracy | Sensor: AUC | Priority: accuracy | Priority: AUC |",
                   "|---|---|---|---|---|---|---|"])
        for arm, r in res[key].items():
            md.append("| %s | %.1f%% | %.3f / %.3f | %.1f%% | %.3f / %.3f | %.1f%% | %.3f / %.3f |" % (
                arm, 100 * r["action"]["accuracy"], r["action"]["auc_logit"], r["action"]["auc_prob"],
                100 * r["sensor"]["accuracy"], r["sensor"]["auc_logit"], r["sensor"]["auc_prob"],
                100 * r["prio"]["accuracy"], r["prio"]["auc_logit"], r["prio"]["auc_prob"]))
    (out / "AUC_DIAG.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
