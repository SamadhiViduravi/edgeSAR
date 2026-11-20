"""Independent reproduction of the label-free linear map (docs/REPRO_ALIGNMENT_PROTOCOL.md). Writes results/repro_alignment/."""
import argparse, gzip, hashlib, json, os, sys, time
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
from sklearn.model_selection import GroupKFold
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE)); sys.dont_write_bytecode = True
from shield import data as sdata, devrun, readout                    # noqa: E402
from shield.alloc import make_allocator                                # noqa: E402
from shield.candidates import pilot                                    # noqa: E402
from shield.devset import DevSet, build_service                        # noqa: E402
from shield.episodes import EPISODE_REPORTS                            # noqa: E402
from shield.policy import CommitPolicy                                 # noqa: E402
from shield.sim import Sim, SimConfig                                  # noqa: E402

GRID = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]


class MyMap:
    """x_Q -> F space. s = (x - mu)/sd_F ; target residual sF - sQ ; ridge in dual form on FIT pairs."""
    def __init__(self, F, Q, groups, seed=0):
        self.muF, self.muQ = F.mean(0), Q.mean(0)
        sd = F.std(0); self.sd = np.where(sd > 0, sd, 1.0)
        sF, sQ = (F - self.muF) / self.sd, (Q - self.muQ) / self.sd
        n = len(F); R = sF - sQ
        err = np.zeros(len(GRID))
        for tr, va in GroupKFold(3).split(sQ, groups=groups):
            K = sQ[tr] @ sQ[tr].T; u = np.trace(K) / len(tr)
            Kva = sQ[va] @ sQ[tr].T
            for j, c in enumerate(GRID):
                A = np.linalg.solve(K + c * u * np.eye(len(tr)), R[tr])
                err[j] += ((sQ[va] + Kva @ A - sF[va]) ** 2).sum()
        self.c = GRID[int(err.argmin())]; self.cv = err
        K = sQ @ sQ.T
        A = np.linalg.solve(K + self.c * np.trace(K) / n * np.eye(n), R)
        self.D = sQ.T @ A                     # 2048 x 2048 linear part: x -> s + s D
    def __call__(self, X):
        s = (X - self.muQ) / self.sd
        return self.muF + self.sd * (s + s @ self.D)


def logits_of(model, X):                      # sklearn pipeline: StandardScaler -> LogisticRegression (multinomial)
    sc, lr = model[0], model[-1]
    return ((X - sc.mean_) / sc.scale_) @ lr.coef_.T + lr.intercept_


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(HERE / "results" / "repro_alignment"))
    ap.add_argument("--no-missions", action="store_true"); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    psha = hashlib.sha256((HERE / "docs" / "REPRO_ALIGNMENT_PROTOCOL.md").read_bytes()).hexdigest()
    t_all = time.time()
    ds = DevSet(); D = ds.D; pc = pilot()[0]
    X = D.X                                   # {'f16','Q8_0','Q4_K_M'} end vectors (float64)
    log = readout.FitLog(); rng = np.random.default_rng(20261114)
    res = {"protocol_sha256": psha, "folds": {}, "fold_check": {}}
    ARMS = ["f16", "q4", "rec", "raw", "aln_mine", "aln_shuf", "raw8", "aln8"]
    for k in sorted(ds.folds):
        f = ds.folds[k]; fit = f["fit"]; rows = np.concatenate([f["cal"], f["eval"]])
        assert not (set(fit.tolist()) & set(f["eval"].tolist()))
        H16 = readout.Heads(D.cases, X["f16"], fit, D.group, log)
        grp = np.array([D.group[i] for i in fit])
        m4 = MyMap(X["f16"][fit], X["Q4_K_M"][fit], grp)
        perm = rng.permutation(len(fit))
        mshuf = MyMap(X["f16"][fit][perm], X["Q4_K_M"][fit], grp)          # pairing destroyed
        m8 = MyMap(X["f16"][fit], X["Q8_0"][fit], grp)
        f["P"]["aln_mine"] = H16.proba(m4(X["Q4_K_M"][rows]))
        f["P"]["aln_shuf"] = H16.proba(mshuf(X["Q4_K_M"][rows]))
        f["P"]["raw8"] = H16.proba(X["Q8_0"][rows]); f["P"]["aln8"] = H16.proba(m8(X["Q8_0"][rows]))
        # ---- folding check (action head, sensor head, prio head)
        chk = {}
        Xe = X["Q4_K_M"][f["eval"]]
        I = np.eye(Xe.shape[1]); z = np.zeros((1, Xe.shape[1]))
        for h in ("action", "sensor", "prio"):
            mod = H16.m[h]
            b0 = logits_of(mod, m4(z))[0]
            G = logits_of(mod, m4(I)) - b0                  # 2048 x C : the folded head
            fold_logits = Xe @ G + b0
            chk[h] = {"max_abs_logit_diff": float(np.abs(fold_logits - logits_of(mod, m4(Xe))).max()),
                      "argmax_changes": int((fold_logits.argmax(1) != logits_of(mod, m4(Xe)).argmax(1)).sum()),
                      "folded_shape": list(G.shape), "original_head_shape": list(mod[-1].coef_.T.shape)}
        res["fold_check"][str(k)] = chk
        res["folds"][str(k)] = {"n_fit": int(len(fit)), "lambda_c": m4.c, "lambda_c_shuffled": mshuf.c, "lambda_c_q8": m8.c,
                                "cv_err": {str(c): float(e) for c, e in zip(GRID, m4.cv)},
                                "cv_err_shuffled": {str(c): float(e) for c, e in zip(GRID, mshuf.cv)}}
        print("fold %d: lambda %s (shuffled %s, q8 %s); fold-check max logit diff %.1e" % (
            k, m4.c, mshuf.c, m8.c, max(v["max_abs_logit_diff"] for v in chk.values())), flush=True)
    # ---- decisions on EVAL
    acc = {}
    for arm in ARMS:
        ok = n = act = 0
        for k in sorted(ds.folds):
            for i in ds.folds[k]["eval"]:
                h = ds.hier(k, arm, int(i)); n += 1
                ok += pc.strict_key(h) == ds.label_key[int(i)]; act += h["action"] == ds.label_norm[int(i)]["action"]
        acc[arm] = {"n": n, "record": ok / n, "action": act / n}
    res["decisions_eval"] = acc
    print({k: round(v["record"], 4) for k, v in acc.items()}, flush=True)
    # ---- harm-cohort accounting (record level): H = f16 right & q4 wrong ; C = q4 right
    def right(arm, k, i): return pc.strict_key(ds.hier(k, arm, int(i))) == ds.label_key[int(i)]
    for tag, base in (("aln_mine", "raw"), ("aln_mine", "q4")):
        Hn = Hd = Cn = Cd = chg = chg_ok = 0
        for k in sorted(ds.folds):
            for i in ds.folds[k]["eval"]:
                r, b, m = right("f16", k, i), right(base, k, i), right(tag, k, i)
                if r and not b: Hd += 1; Hn += m
                if b: Cd += 1; Cn += (not m)
                if pc.strict_key(ds.hier(k, tag, int(i))) != pc.strict_key(ds.hier(k, base, int(i))): chg += 1; chg_ok += m
        res.setdefault("cohorts", {})["%s_vs_%s" % (tag, base)] = {
            "harmful_cohort_n": Hd, "repaired": Hn, "repair_rate": Hn / max(Hd, 1), "q_right_n": Cd, "newly_wrong": Cn, "new_error_rate": Cn / max(Cd, 1),
            "changed_records": chg, "changed_and_right": chg_ok, "correction_precision": chg_ok / max(chg, 1)}
    if a.no_missions:
        (out / "repro.json").write_text(json.dumps(res, indent=1, default=float)); return
    # ---- missions (always commit)
    cfg = SimConfig(); sim = Sim(make_allocator("cbba_bounded"), cfg)
    MA = ["f16", "q4", "rec", "raw", "aln_mine", "aln_shuf"]
    svc = {k: {arm: build_service(ds, k, arm) for arm in MA} for k in sorted(ds.folds)}
    PAIRS = [("aln_mine", "raw"), ("aln_mine", "rec"), ("aln_mine", "q4"), ("aln_mine", "f16"), ("aln_shuf", "aln_mine"), ("aln_shuf", "rec")]
    ref = json.loads((HERE / "results" / "dev" / "main" / "DEV_main.json").read_text())["levels"]
    res["levels"] = {}; ok_all = True
    for level in ("L", "M", "H"):
        recs = []
        for seed in (1, 2, 3):
            for k in sorted(ds.folds):
                for e in ds.make_episodes(ds.folds[k]["eval"], level, seed * 1000 + k, EPISODE_REPORTS):
                    recs.append(devrun.compact(sim.run(e, None, "gold", oracle=True), k, level, seed))
                    for arm in MA:
                        recs.append(devrun.compact(sim.run(e, CommitPolicy(svc[k][arm]), arm), k, level, seed))
        table = devrun.arm_table(recs); lv = {"arms": {}, "paired": {}, "integrity": {}}
        for arm in ["gold"] + MA:
            r = table[arm]; lo, hi = devrun.episode_bootstrap_ci(recs, arm)
            lv["arms"][arm] = {"missed": r["U_deadline"], "ci": [lo, hi], "late": r["late"], "unverified": r["unverified"], "incidents": r["incidents"]}
        for arm, pk in {"gold": "A0", "q4": "A1", "f16": "A2", "rec": "A4", "raw": "A5"}.items():
            w = ref[level]["arms"][pk]; same = (table[arm]["late"], table[arm]["unverified"], table[arm]["incidents"]) == (w["late"], w["unverified"], w["incidents"])
            lv["integrity"][arm] = bool(same); ok_all &= same
        for x, y in PAIRS: lv["paired"]["%s-%s" % (x, y)] = devrun.paired(recs, x, y)
        res["levels"][level] = lv
        print(level, {a_: round(100 * v["missed"], 2) for a_, v in lv["arms"].items()}, flush=True)
    res["integrity_package_counts"] = bool(ok_all); res["seconds"] = round(time.time() - t_all)
    (out / "repro.json").write_text(json.dumps(res, indent=1, default=float))
    print("done", res["seconds"], "s; package counts identical:", ok_all)


if __name__ == "__main__":
    main()
