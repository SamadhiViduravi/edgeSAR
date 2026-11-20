"""Part A of PROTOCOL_PRACTICAL_ADVANTAGE.md: cost of retraining Q4 heads versus fitting the label-free map (development folds, prefix position).
Driver:  python bench_cost.py --driver --root <root2> --out out_cost
Each measured step runs in a fresh process (so peak memory is per step). 1 BLAS thread. Cloud CPU, not the laptop."""
import argparse, json, os, resource, subprocess, sys, time, tracemalloc
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1"); os.environ.setdefault("MKL_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "repair_pkg" / "edgesar_repair_2026-11-14"
SEED = 20261113


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def setup(root):
    os.environ["EDGESAR_ROOT"] = str(root)
    sys.path.insert(0, str(Path(root) / "edgesar_shield")); sys.path.insert(0, str(PKG))
    import numpy as np
    from shield import data as sdata, readout
    from shield.candidates import pilot
    from ppr_lib import AffineMap, template_key
    D = sdata.DevData()
    Xp, ids = sdata.load_vectors("prefix")
    pc = pilot()[0]
    tmpl = np.array([template_key(c["text"], pc.LANDMARKS) for c in D.cases])
    return np, D, Xp, tmpl, readout, AffineMap


def step_main(a):
    t_imp = time.perf_counter()
    np, D, Xp, tmpl, readout, AffineMap = setup(a.root)
    base = rss_mb(); load_s = time.perf_counter() - t_imp
    fit, cal, ev = D.split(a.fold)
    fit = np.asarray(fit)
    out = {"step": a.step, "fold": a.fold, "n_fit": int(len(fit)), "rss_after_load_mb": round(base, 1), "load_s": round(load_s, 2)}
    if a.step == "base":
        pass
    else:
        tracemalloc.start()
        c0, w0 = time.process_time(), time.perf_counter()
        log = readout.FitLog()
        if a.step == "retrain_q4":
            readout.Heads(D.cases, Xp["Q4_K_M"], fit, D.group, log)
        elif a.step == "fit_f16":
            readout.Heads(D.cases, Xp["f16"], fit, D.group, log)
        elif a.step == "fit_map":
            AffineMap(Xp["f16"][fit], Xp["Q4_K_M"][fit], tmpl[fit], seed=SEED + a.fold)
        else:
            raise SystemExit("unknown step")
        out["wall_s"] = round(time.perf_counter() - w0, 3); out["cpu_s"] = round(time.process_time() - c0, 3)
        cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        out["tracemalloc_peak_mb"] = round(peak / 2**20, 1); out["rss_peak_mb"] = round(rss_mb(), 1)
        if a.step != "fit_map":
            out["fit_log"] = log.as_dict()
    print(json.dumps(out))


def fold_heads(np, Hh):
    """Folded logits layer of sklearn heads: dict head -> (W' K x 2048, b')."""
    r = {}
    for h, m in Hh.m.items():
        sc, lr = m[0], m[-1]
        W = lr.coef_ / sc.scale_[None, :]
        b = lr.intercept_ - (sc.mean_ / sc.scale_) @ lr.coef_.T
        r[h] = (W, b, m)
    return r


def step_infer(a):
    np, D, Xp, tmpl, readout, AffineMap = setup(a.root)
    fit, cal, ev = D.split(0); fit = np.asarray(fit); log = readout.FitLog()
    Hq = readout.Heads(D.cases, Xp["Q4_K_M"], fit, D.group, log)
    Hf = readout.Heads(D.cases, Xp["f16"], fit, D.group, log)
    amap = AffineMap(Xp["f16"][fit], Xp["Q4_K_M"][fit], tmpl[fit], seed=SEED)
    x = Xp["Q4_K_M"][int(ev[0])].copy(); X = Xp["Q4_K_M"][np.asarray(ev)]
    # --- retrained heads, folded
    FQ = fold_heads(np, Hq)
    Wq = np.vstack([FQ[h][0] for h in ("action", "sensor", "prio")]); bq = np.concatenate([FQ[h][1] for h in ("action", "sensor", "prio")])
    # --- map, folded into the FP16 heads
    bank, A = amap.sQ_bank, amap.A
    Wm_parts, bm_parts = [], []
    FF = fold_heads(np, Hf)
    for h in ("action", "sensor", "prio"):
        m = FF[h][2]; sc, lr = m[0], m[-1]
        V = (amap.sd / sc.scale_)[:, None] * lr.coef_.T                       # 2048 x K
        const = ((amap.muF - sc.mean_) / sc.scale_) @ lr.coef_.T + lr.intercept_
        U = V + bank.T @ (A @ V)
        Wm_parts.append((U / amap.sd[:, None]).T)
        bm_parts.append(const - (amap.muQ / amap.sd) @ U)
    Wm = np.vstack(Wm_parts); bm = np.concatenate(bm_parts)
    # --- unfolded map logits (reference)
    def unfolded(xv):
        g = amap(xv[None, :])[0]
        return np.concatenate([(((g - FF[h][2][0].mean_) / FF[h][2][0].scale_) @ FF[h][2][-1].coef_.T + FF[h][2][-1].intercept_) for h in ("action", "sensor", "prio")])
    diffs = []
    for xv in X[:200]:
        diffs.append(float(np.abs(unfolded(xv) - (Wm @ xv + bm)).max()))
    dq = []
    for h, sl in (("action", slice(0, 4)), ("sensor", slice(4, 7)), ("prio", slice(7, 10))):
        m = FQ[h][2]
        dq.append(float(np.abs(((X - m[0].mean_) / m[0].scale_) @ m[-1].coef_.T + m[-1].intercept_ - (X @ Wq[sl].T + bq[sl])).max()))
    f32 = lambda z: z.astype(np.float32)
    art = {"retrained_folded_numbers": int(Wq.size + bq.size), "retrained_folded_bytes_f32": int(f32(Wq).nbytes + f32(bq).nbytes),
           "map_folded_numbers": int(Wm.size + bm.size), "map_folded_bytes_f32": int(f32(Wm).nbytes + f32(bm).nbytes),
           "map_unfolded_numbers": int(bank.size + A.size + 3 * 2048), "map_unfolded_bytes_f32": int(4 * (bank.size + A.size + 3 * 2048)),
           "pair_bank_fit_time_only_bytes_f32_two_matrices": int(4 * 2 * bank.size), "n_pairs": int(len(bank))}

    def timeit(fn, n):
        ts = []
        for _ in range(n):
            t0 = time.perf_counter_ns(); fn(); ts.append(time.perf_counter_ns() - t0)
        ts = np.array(ts) / 1000.0
        return {"median_us": round(float(np.median(ts)), 2), "p95_us": round(float(np.percentile(ts, 95)), 2), "calls": n}
    x32 = x.astype(np.float32); Wq32, bq32, Wm32, bm32 = f32(Wq), f32(bq), f32(Wm), f32(bm)
    tim = {"retrained_folded_float64": timeit(lambda: (Wq @ x + bq), 20000),
           "retrained_folded_float32": timeit(lambda: (Wq32 @ x32 + bq32), 20000),
           "map_folded_float64": timeit(lambda: (Wm @ x + bm), 20000),
           "map_folded_float32": timeit(lambda: (Wm32 @ x32 + bm32), 20000),
           "map_unfolded_float64": timeit(lambda: unfolded(x), 3000),
           "sklearn_predict_proba_3_heads": timeit(lambda: [Hq.m[h].predict_proba(x[None, :]) for h in ("action", "sensor", "prio")], 2000)}
    print(json.dumps({"fold_check": {"map_max_abs_logit_diff": max(diffs), "retrained_max_abs_logit_diff": max(dq), "reports_checked": 200},
                      "artifact": art, "inference": tim}))


def driver(a):
    reps, folds = a.repeats, range(5)
    rows = []
    for step in ("base", "retrain_q4", "fit_f16", "fit_map"):
        for k in folds:
            for r in range(reps):
                p = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--step", step, "--fold", str(k), "--root", a.root], capture_output=True, text=True,
                                   env={**os.environ, "PYTHONPATH": ""}, cwd=str(HERE))
                if p.returncode:
                    raise SystemExit(p.stderr[-2000:])
                d = json.loads(p.stdout.strip().splitlines()[-1]); d["repeat"] = r; rows.append(d)
                print(step, k, r, d.get("wall_s"), d.get("rss_peak_mb", d["rss_after_load_mb"]), flush=True)
    p = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--step", "infer", "--root", a.root], capture_output=True, text=True, cwd=str(HERE))
    if p.returncode:
        raise SystemExit(p.stderr[-2000:])
    inf = json.loads(p.stdout.strip().splitlines()[-1])
    Path(a.out).mkdir(exist_ok=True)
    json.dump({"rows": rows, "infer": inf, "cpu": "cloud container, 2 vCPU, 1 BLAS thread"}, open(Path(a.out) / "cost.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--driver", action="store_true"); ap.add_argument("--step"); ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--root", required=True); ap.add_argument("--out", default="out_cost"); ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    if a.driver: driver(a)
    elif a.step == "infer": step_infer(a)
    else: step_main(a)
