"""OFFLINE PREPARATION (not part of the Q4 deployment). Needs the saved FP16 AND Q4 vectors of the 1,000 style-A reports.

Writes the FOLDED classifiers of the existing style-B setting (protocol B of the repair experiment: heads fitted on all 1,000 style-A
reports with all labels, label-free affine map fitted on the 1,000 unlabelled FP16/Q4 pairs, reading position `prefix`) as plain matrices:

    map_W (10 x 2048), map_b (10)          Q4 vector -> [action 4 | sensor 3 | priority 3] logits through the label-free map and the FP16 heads
                                           (map and FP16 head are ONE linear layer, so there is nothing else to run)
    retrained_W (10 x 2048), retrained_b   the Q4 heads trained directly on Q4 vectors (the comparator; same shape and same run-time cost)

Nothing new is fitted: the SAME functions with the SAME seed as run_ppr2.py (protocol B) are called, and the result is checked against the
SAVED predictions (repair_package/out2/predictions.csv, arms C2p and MATCHEDp, 400 style-B reports). If the check fails the files are still
written but the report says so, and deploy_bench.py refuses to use them unless told to.

    python export_folded_classifier.py --root "D:\\1 Samadhi UNI\\aFYP\\Claude" --repair-dir "D:\\1 Samadhi UNI\\aFYP\\Claude\\edgesar_repair_2026-11-14" --out folded

After this step the deployment benchmark needs NO FP16 file at all (no FP16 vector, no FP16 model).
"""
import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

KEYCOLS = ("action", "incident", "landmark", "sensor", "priority")
ARM_SAVED = {"map": "C2p", "retrained": "MATCHEDp"}
HEAD_ORDER = ("action", "sensor", "prio")


def find_repair_dir(rd, root):
    """The repair package (ppr_lib.py + out2/predictions.csv) is in different places in different copies of the workspace: look in the likely ones."""
    rd, root = Path(rd), Path(root)
    cands = [rd, rd / "repair_package", rd / "repair_pkg" / "edgesar_repair_2026-11-14",
             root / "edgesar_shield" / "repair_pkg" / "edgesar_repair_2026-11-14", root / "edgesar_shield" / "repair_package",
             root / "edgesar_repair_2026-11-14", root / "repair_pkg" / "edgesar_repair_2026-11-14", root / "repair_package"]
    for c in cands:
        if (c / "ppr_lib.py").exists() and (c / "out2" / "predictions.csv").exists():
            return c.resolve()
    sys.exit("Cannot find the repair package (ppr_lib.py and out2\\predictions.csv). Looked in:\n  " + "\n  ".join(str(c) for c in cands) +
             "\nGive the right folder with --repair-dir.")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def arrays_sha256(arrs):
    h = hashlib.sha256()
    for k in sorted(arrs):
        a = np.ascontiguousarray(arrs[k])
        h.update(k.encode() + b"|" + str(a.dtype).encode() + b"|" + str(a.shape).encode() + b"|" + a.tobytes())
    return h.hexdigest()


def load_saved(path, arm):
    """{case_id: key tuple} for protocol B, labels all, one arm."""
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["protocol"] == "B" and r["labels"] == "all" and r["arm"] == arm:
                out[r["case_id"]] = tuple(None if r[c] == "" else (int(r[c]) if c == "priority" else r[c]) for c in KEYCOLS)
    return out


def fold_head(h):
    """ppr_lib.Head -> (W', b') with logits = x @ W'.T + b' on the RAW vector x."""
    W = h.W / h.scaler.sd[None, :]
    b = h.b - (h.scaler.mu / h.scaler.sd) @ h.W.T
    return W, b


def fold_map_into_heads(amap, ref):
    """Label-free affine map followed by the FP16 heads = one linear layer on the Q4 vector."""
    sdF, muF, muQ, bank, A = amap.sd, amap.muF, amap.muQ, amap.sQ_bank, amap.A
    Ws, bs = [], []
    for h in HEAD_ORDER:
        H = ref[h]
        V = (sdF / H.scaler.sd)[:, None] * H.W.T                       # d x K
        c0 = ((muF - H.scaler.mu) / H.scaler.sd) @ H.W.T + H.b        # K
        U = V + bank.T @ (A @ V)                                       # d x K
        Ws.append((U / sdF[:, None]).T)                                # K x d
        bs.append(c0 - (muQ / sdF) @ U)
    return np.vstack(Ws), np.concatenate(bs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="folder that holds edgesar_pilot, edgesar_heads and V1")
    ap.add_argument("--repair-dir", required=True, help="folder with ppr_lib.py, run_ppr.py and out2\\predictions.csv (edgesar_repair_2026-11-14)")
    ap.add_argument("--out", default="folded")
    ap.add_argument("--compare-with", default=None, help="folder with an earlier folded_q4.npz (the shipped one): reports the largest difference")
    a = ap.parse_args()
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rd = find_repair_dir(a.repair_dir, a.root)
    print('repair package folder:', rd)
    sys.path.insert(0, str(rd))
    import ppr_lib
    import run_ppr as R1
    from ppr_lib import ACTIONS, HEADS, AffineMap, Data, assemble

    D = Data(a.root)
    R1.D = D
    A = np.where(D.split == "dev")[0]
    B = np.where(D.split == "held")[0]
    assert len(A) == 1000 and len(B) == 400, (len(A), len(B))
    seed = R1.SEED + 999                                            # exactly the seed of the style-B task in run_ppr2.py
    Fp, Q4p = D.X[("f16", "prefix")], D.X[("Q4_K_M", "prefix")]
    tr, lab, te = A, A, B
    rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}

    REFp = R1.fit_heads(Fp, rows, seed)
    amap = AffineMap(Fp[tr], Q4p[tr], D.template[tr], seed)
    MATp = R1.fit_heads(Q4p, rows, seed)

    Wm, bm = fold_map_into_heads(amap, REFp)
    Wr = np.vstack([fold_head(MATp[h])[0] for h in HEAD_ORDER])
    br = np.concatenate([fold_head(MATp[h])[1] for h in HEAD_ORDER])
    arrs = {"map_W": Wm, "map_b": bm, "retrained_W": Wr, "retrained_b": br}
    np.savez(out / "folded_q4.npz", **arrs)

    # ---------------------------------------------------------------- checks against the unfolded pipeline and the SAVED predictions
    def split_logits(L):
        return {"action": L[:, 0:4], "sensor": L[:, 4:7], "prio": L[:, 7:10]}

    checks = {}
    pred_path = rd / "out2" / "predictions.csv"
    for name, W, b, unfolded in (("map", Wm, bm, lambda X: R1.logits(REFp, amap(X))), ("retrained", Wr, br, lambda X: R1.logits(MATp, X))):
        Xte = Q4p[te]
        U = unfolded(Xte)
        Uc = np.concatenate([U[h] for h in HEAD_ORDER], axis=1)
        L64 = Xte @ W.T + b
        L32 = (Xte.astype(np.float32) @ W.astype(np.float32).T + b.astype(np.float32)).astype(np.float64)
        saved = load_saved(pred_path, ARM_SAVED[name])
        recs64 = assemble(D, te, split_logits(L64))
        recs32 = assemble(D, te, split_logits(L32))
        ids = [D.cases[int(i)]["id"] for i in te]
        keys64 = [D.pc.strict_key(r) for r in recs64]
        keys32 = [D.pc.strict_key(r) for r in recs32]
        n_saved = sum(1 for i in ids if i in saved)
        eq64 = sum(1 for i, k in zip(ids, keys64) if saved.get(i) == k)
        eq32 = sum(1 for i, k in zip(ids, keys32) if saved.get(i) == k)
        arg_unf = [np.argmax(U[h], axis=1) for h in HEAD_ORDER]
        arg32 = [np.argmax(split_logits(L32)[h], axis=1) for h in HEAD_ORDER]
        head_same32 = int(sum((x == y).all() for x, y in zip(arg_unf, arg32)))
        checks[name] = {
            "saved_arm": ARM_SAVED[name], "saved_rows": n_saved, "n_test": int(len(te)),
            "max_abs_logit_diff_folded64_vs_unfolded": float(np.abs(L64 - Uc).max()),
            "max_abs_logit_diff_folded32_vs_unfolded": float(np.abs(L32 - Uc).max()),
            "records_equal_saved_float64": int(eq64), "records_equal_saved_float32": int(eq32),
            "heads_argmax_equal_unfolded_float32": "%d of 3 heads" % head_same32,
            "head_argmax_changes_float32": int(sum((x != y).sum() for x, y in zip(arg_unf, arg32))),
        }
    ok = all(c["records_equal_saved_float64"] == c["n_test"] == c["saved_rows"] for c in checks.values())

    man = {
        "what": "folded Q4 classifiers of the style-B setting (protocol B, reading position prefix); see export_folded_classifier.py",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "classes": {"action": ACTIONS, "sensor": ppr_lib.SENSORS, "priority": ppr_lib.PRIOS},
        "row_order": "action(4) | sensor(3) | priority(3)  = 10 rows; logits = x @ W.T + b on the RAW 2048-d unit-norm Q4 prefix vector",
        "shapes": {k: list(v.shape) for k, v in arrs.items()},
        "numbers_per_classifier": int(Wm.size + bm.size),
        "bytes_float32_per_classifier": int(4 * (Wm.size + bm.size)),
        "arrays_sha256": arrays_sha256(arrs),
        "npz_sha256": sha256_file(out / "folded_q4.npz"),
        "training": {"protocol": "B", "n_fit_reports": int(len(tr)), "n_labelled": int(len(lab)), "n_test_reports": int(len(te)), "seed": int(seed),
                     "reading_position": "prefix", "C_REFp": {h: REFp[h].C for h in HEADS}, "C_MATCHEDp": {h: MATp[h].C for h in HEADS},
                     "map_lambda": amap.c, "n_pairs_in_map": int(len(tr))},
        "checks_against_saved_predictions": checks,
        "all_checks_pass": bool(ok),
        "sources_sha256": {"predictions_out2": sha256_file(pred_path), "ppr_lib.py": sha256_file(rd / "ppr_lib.py"), "run_ppr.py": sha256_file(rd / "run_ppr.py"),
                           "cases.jsonl": sha256_file(Path(a.root) / "edgesar_pilot" / "data" / "cases.jsonl"),
                           "f16_prefix.npy": sha256_file(Path(a.root) / "edgesar_heads" / "features" / "f16_prefix.npy"),
                           "Q4_K_M_prefix.npy": sha256_file(Path(a.root) / "edgesar_heads" / "features" / "Q4_K_M_prefix.npy")},
        "software": {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()},
        "seconds": round(time.time() - t0, 1),
    }
    (out / "folded_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")

    md = ["# Export check: folded Q4 classifiers against the saved style-B predictions", "",
          "Offline preparation (this step sees FP16 vectors; the deployment benchmark does not). Nothing new was fitted: same functions, same seed as `run_ppr2.py` protocol B.", "",
          "| Classifier | Saved arm | Reports compared | Whole record equal to saved (float64) | Whole record equal to saved (float32) | Max logit difference vs unfolded (float64 / float32) |",
          "|---|---|---|---|---|---|"]
    for name, c in checks.items():
        md.append("| %s | %s | %d | %d of %d | %d of %d | %.2e / %.2e |" % (name, c["saved_arm"], c["saved_rows"], c["records_equal_saved_float64"], c["n_test"], c["records_equal_saved_float32"],
                                                                         c["n_test"], c["max_abs_logit_diff_folded64_vs_unfolded"], c["max_abs_logit_diff_folded32_vs_unfolded"]))
    md += ["", "Size of one folded classifier: %d numbers = %d bytes in float32." % (Wm.size + bm.size, 4 * (Wm.size + bm.size)),
           "Overall: **%s**" % ("all checks pass (the folded matrices reproduce the saved style-B records)" if ok else "CHECK FAILED - see the table; do not use these files for the benchmark"),
           "arrays SHA-256 `%s`" % man["arrays_sha256"], ""]
    (out / "EXPORT_CHECK.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    if a.compare_with:
        other = np.load(Path(a.compare_with) / "folded_q4.npz")
        diffs = {k: float(np.abs(other[k] - arrs[k]).max()) for k in arrs}
        same = all(v < 1e-6 for v in diffs.values())
        print("compared with %s: largest difference per array %s -> %s" % (a.compare_with, {k: "%.2e" % v for k, v in diffs.items()},
                                                                         "SAME as the shipped files (to 1e-6)" if same else "DIFFERENT from the shipped files"))
        ok = ok and same
    print("done in %.0f s; files in %s" % (time.time() - t0, out.resolve()))
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
