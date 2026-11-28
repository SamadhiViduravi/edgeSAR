"""
K14 (exploratory, 28 Nov 2026): can the label-free adaptation be fitted on reports the old classifier never saw?

In Table 4 and in K9 the map's pairs come from the 1,000 development fitting reports (the reports the FP16 heads were trained on, used
without their labels), and pseudo-label retraining uses the FP16 classifier's records on those same reports. Here both are fitted only on
paired FP16 and Q4 vectors of reports that no head and no map has seen:

  A_*      new reports of the evaluation kind: fresh set A split into two halves by episode (150 + 150 episodes); the reports of each half
           are adapted with a map (or pseudo-label heads) fitted on the other half only (2-fold cross-fitting), so no episode is ever
           evaluated with a map that saw its reports. A_all uses all 3,000 reports of the other half, A_n100 / A_n300 draw 100 / 300.
  B_*      new reports in the second wording: fresh set B (1,000 reports, style B); B_n100 / B_n300 draw 100 / 300 of them.
  dev400_* the 400 development style-B reports (never used for fitting).

The FP16 heads are those of Table 4. Evaluation: fresh set A, medium load, arrival seed 11, the registered simulator. Labels are never used
by any adaptation arm. Before anything else the registered gold, FP16, unchanged, map and 100-label retraining counts are reproduced.

    python checklist_k14.py --root <ROOT> --cases cases_fresh.jsonl --vectors <fresh vector folder> --fresh-out <folder with results.json> --out <out>
"""
import argparse
import gzip
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np

sys.dont_write_bytecode = True
G = {}
N_DRAWS = 10


def paired_arrays(mx, my, nn, n_boot=10000, seed=7):
    mx, my, nn = (np.asarray(v, dtype=float) for v in (mx, my, nn))
    rng = np.random.RandomState(seed)
    E = len(nn)
    idx = rng.randint(0, E, size=(n_boot, E))
    diff = (mx[idx].sum(1) - my[idx].sum(1)) / nn[idx].sum(1)
    d = mx - my
    signs = rng.choice([-1.0, 1.0], size=(n_boot, E))
    p = (np.sum(np.abs((signs * d).sum(1)) >= abs(d.sum()) - 1e-12) + 1) / (n_boot + 1)
    return {"diff_pp": float(100 * d.sum() / nn.sum()), "ci_pp": [float(100 * np.percentile(diff, 2.5)), float(100 * np.percentile(diff, 97.5))],
            "p": float(p)}


def sim_job(arm):
    if "sim" not in G:
        G["sim"] = G["make_sim"]()
    devrun, CommitPolicy, Service, pc = G["devrun"], G["CommitPolicy"], G["Service"], G["pc"]
    svc = None
    if arm != "gold":
        cands, hier, conf = {}, {}, {}
        for i, nm in zip(G["rid"], G["recs"][arm]):
            c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cands[i], hier[i], conf[i] = [c], c, 1.0
        svc = Service(cands, hier, conf)
    miss, late, unv, nn = [], [], [], []
    for e in G["eps"]:
        r = G["sim"].run(e, None, "gold", oracle=True) if arm == "gold" else G["sim"].run(e, CommitPolicy(svc), arm)
        c = devrun.compact(r, 0, "x", 0)["counts"]
        miss.append(c["late"] + c["unverified"])
        late.append(c["late"])
        unv.append(c["unverified"])
        nn.append(c["n"])
    return arm, np.array(miss, float), np.array(late, float), np.array(unv, float), np.array(nn, float)


def main():
    ap = argparse.ArgumentParser()
    for k in ("--root", "--cases", "--vectors", "--fresh-out", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    t_all = time.time()

    def log(*x):
        print("[%6.0f s]" % (time.time() - t_all), *x, flush=True)

    root = Path(a.root).resolve()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    os.environ["EDGESAR_ROOT"] = str(root)
    for sub in ("repair_package", "edgesar_shield", "edgesar_heads"):
        sys.path.insert(0, str(root / sub))
    import run_ppr as R1
    from ppr_lib import ACTIONS, HEADS, PRIOS, REC, SENSORS, AffineMap, Data, template_key
    from shield import devrun
    from shield.alloc import make_allocator
    from shield.episodes import make_fixed_episodes
    from shield.policy import CommitPolicy
    from shield.service import Service
    from shield.sim import Sim, SimConfig

    # ------------------------------------------------------------------ development fit (as in the registered analysis)
    D = Data(root)
    R1.D = D
    pc, pb = D.pc, D.pb
    A = np.where(D.split == "dev")[0]
    B400 = np.where(D.split != "dev")[0]
    assert len(A) == 1000 and len(B400) == 400, (len(A), len(B400))
    seed0 = R1.SEED + 999
    rows_all = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
    Fp, Qp = D.X[("f16", "prefix")], D.X[("Q4_K_M", "prefix")]
    ref = R1.fit_heads(Fp, rows_all, seed0)
    aln = AffineMap(Fp[A], Qp[A], D.template[A], seed0)
    log("development fit done; map lambda", aln.c)

    # ------------------------------------------------------------------ fresh reports
    ev_all = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
    assert json.loads((Path(a.vectors) / "case_ids.json").read_text(encoding="utf-8")) == [c["id"] for c in ev_all]
    A_idx = np.array([i for i, c in enumerate(ev_all) if c["split"] == "fresh_eval_A"])
    B_idx = np.array([i for i, c in enumerate(ev_all) if c["split"] == "fresh_eval_B"])
    assert len(A_idx) == 6000 and len(B_idx) == 1000
    Fall = np.load(Path(a.vectors) / "f16_prefix.npy").astype(np.float64)
    Qall = np.load(Path(a.vectors) / "Q4_K_M_prefix.npy").astype(np.float64)
    tmpl = np.array([template_key(c["text"], pc.LANDMARKS) for c in ev_all])
    ev = [ev_all[i] for i in A_idx]
    Fe, Qe, tA = Fall[A_idx], Qall[A_idx], tmpl[A_idx]
    FB, QB, tB = Fall[B_idx], Qall[B_idx], tmpl[B_idx]
    gold_key = [pc.strict_key(pc.gold_norm(c)) for c in ev]
    sdF = Fp[A].std(0)
    sdF = np.where(sdF > 0, sdF, 1.0)
    raw_err = float(np.mean(((Qe - Fe) / sdF) ** 2))

    def logits(heads, X):
        return {h: heads[h].logits(X) for h in HEADS}

    def assemble(P):
        return [pc.validate(pb._assemble(c, ACTIONS[int(P["action"][r].argmax())], SENSORS[int(P["sensor"][r].argmax())],
                                         int(PRIOS[int(P["prio"][r].argmax())])), c)[0] for r, c in enumerate(ev)]

    def pl_heads(Fsrc, Qsrc, groups):
        """Pseudo-label retraining: Q4 heads fitted on Qsrc with the FP16 classifier's own records on Fsrc as targets (as in the check
        confirmation, where Fsrc/Qsrc were the 1,000 fitting reports)."""
        Lf = {h: ref[h].logits(Fsrc) for h in HEADS}
        pa = np.array(ACTIONS)[Lf["action"].argmax(1)]
        r_all = np.arange(len(Fsrc))
        r_rec = r_all[np.isin(pa, REC)]
        rows = {"action": r_all, "sensor": r_rec, "prio": r_rec}
        T = {}
        for h in HEADS:
            t = np.zeros((len(rows[h]), len(HEADS[h])))
            t[np.arange(len(rows[h])), Lf[h][rows[h]].argmax(1)] = 1.0
            T[h] = t
        return R1.fit_heads({h: Qsrc[rows[h]] for h in HEADS}, rows, seed0, T=T, groups={h: groups[rows[h]] for h in HEADS})

    P, info = {}, {}

    def add_map(name, maps_by_target):
        """maps_by_target: list of (target index array into set A, fitted map). Builds the adapted logits for all 6,000 set-A reports."""
        Z = {h: np.zeros((len(ev), len(HEADS[h]))) for h in HEADS}
        err, lam = 0.0, []
        for tgt, m in maps_by_target:
            Xm = m(Qe[tgt])
            for h in HEADS:
                Z[h][tgt] = ref[h].logits(Xm)
            err += float(np.sum(((Xm - Fe[tgt]) / sdF) ** 2))
            lam.append(m.c)
        P[name] = Z
        info[name] = {"lambda": lam, "err_rel_raw": err / (len(ev) * Fe.shape[1]) / raw_err}

    def add_heads(name, heads_by_target):
        Z = {h: np.zeros((len(ev), len(HEADS[h]))) for h in HEADS}
        for tgt, hd in heads_by_target:
            for h in HEADS:
                Z[h][tgt] = hd[h].logits(Qe[tgt])
        P[name] = Z

    allA = np.arange(len(ev))
    # ---- registered reference arms
    P["f16p"], P["rawp"] = logits(ref, Fe), logits(ref, Qe)
    add_map("alnp", [(allA, aln)])
    add_heads("plp_dev", [(allA, pl_heads(Fp[A], Qp[A], D.template[A]))])
    reg_all = json.loads((Path(a.fresh_out) / "results.json").read_text())
    for d in range(5):
        sd = seed0 + 1000 * (d + 1)
        rng = np.random.default_rng(sd + 7)
        while True:
            lab = np.sort(rng.choice(A, size=100, replace=False))
            if len(set(D.y["action"][lab])) == 4:
                break
        assert [D.cases[int(i)]["id"] for i in lab] == reg_all["label_draws"]["100_d%d" % d]
        rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
        P["q4p_n100_d%d" % d] = logits(R1.fit_heads(Qp, rows, sd), Qe)
    log("reference arms fitted")

    # ---- new reports of the evaluation kind: 2-fold cross-fitting over set-A episodes
    epA = np.array([c["episode"] for c in ev])
    eps_sorted = sorted(set(epA.tolist()))
    perm = np.random.default_rng(seed0 + 95000).permutation(len(eps_sorted))
    fold_of = {eps_sorted[j]: int(k >= len(eps_sorted) // 2) for k, j in enumerate(perm)}
    foldA = np.array([fold_of[e] for e in epA])
    halves = [(np.where(foldA == k)[0], np.where(foldA != k)[0]) for k in (0, 1)]      # (target half, source half)
    t0 = time.time()
    add_map("A_all_map", [(tg, AffineMap(Fe[src], Qe[src], tA[src], seed0)) for tg, src in halves])
    info["A_all_map"]["fit_s"] = round(time.time() - t0, 1)
    add_heads("A_all_pl", [(tg, pl_heads(Fe[src], Qe[src], tA[src])) for tg, src in halves])
    for n in (100, 300):
        for d in range(N_DRAWS):
            mm = []
            for k, (tg, src) in enumerate(halves):
                rng = np.random.default_rng(seed0 + 96000 + 1000 * n + 10 * d + k)
                pick = np.sort(rng.choice(src, size=n, replace=False))
                mm.append((tg, AffineMap(Fe[pick], Qe[pick], tA[pick], seed0)))
            add_map("A_n%d_d%d" % (n, d), mm)
    log("set-A cross-fitted arms done")

    # ---- new reports in the second wording (fresh set B) and the development style-B reports
    add_map("B_all_map", [(allA, AffineMap(FB, QB, tB, seed0))])
    add_heads("B_all_pl", [(allA, pl_heads(FB, QB, tB))])
    for n in (100, 300):
        for d in range(N_DRAWS):
            rng = np.random.default_rng(seed0 + 97000 + 1000 * n + d)
            pick = np.sort(rng.choice(len(B_idx), size=n, replace=False))
            add_map("B_n%d_d%d" % (n, d), [(allA, AffineMap(FB[pick], QB[pick], tB[pick], seed0))])
    add_map("dev400_map", [(allA, AffineMap(Fp[B400], Qp[B400], D.template[B400], seed0))])
    add_heads("dev400_pl", [(allA, pl_heads(Fp[B400], Qp[B400], D.template[B400]))])
    log("set-B and style-B arms done; %d arms" % len(P))

    recs = {k: assemble(v) for k, v in P.items()}
    acc = {k: float(np.mean([pc.strict_key(x) == g for x, g in zip(v, gold_key)])) for k, v in recs.items()}
    ds = SimpleNamespace(cases=ev)
    eps = make_fixed_episodes(ds, range(len(ev)), "M", 11)
    G.update({"recs": recs, "rid": [c["id"] for c in ev], "pc": pc, "Service": Service, "CommitPolicy": CommitPolicy, "devrun": devrun,
              "make_sim": lambda: Sim(make_allocator("cbba_bounded"), SimConfig()), "eps": eps})
    arms = ["gold"] + list(recs)
    TAB, LATE, UNV, NN = {}, {}, {}, None
    log("running %d simulator jobs" % len(arms))
    with mp.get_context("fork").Pool(a.workers) as pool:
        for j, (arm, miss, late, unv, nn) in enumerate(pool.imap_unordered(sim_job, arms)):
            TAB[arm], LATE[arm], UNV[arm] = miss, late, unv
            assert NN is None or np.array_equal(NN, nn)
            NN = nn
            if (j + 1) % 10 == 0:
                log("  %d of %d jobs done" % (j + 1, len(arms)))

    # ------------------------------------------------------------------ sanity against the registered results
    reg = reg_all["levels"]["A_M_s11"]["arms"]
    san = {arm: [float(TAB[arm].sum()), reg[arm]["missed"]] for arm in ("gold", "f16p", "rawp", "alnp")}
    m100 = np.mean([TAB["q4p_n100_d%d" % d] for d in range(5)], axis=0)
    san["q4p_n100 (mean of draws 0-4)"] = [float(m100.sum()), reg["q4p_n100"]["missed"]]
    assert all(abs(v[0] - v[1]) < 1e-6 for v in san.values()), san
    assert int(NN.sum()) == reg_all["levels"]["A_M_s11"]["incidents"]
    log("sanity passed", san)

    sh = lambda m: float(100 * m.sum() / NN.sum())
    mean_of = lambda pref, k: np.mean([TAB["%s_d%d" % (pref, d)] for d in range(k)], axis=0)
    S = {"gold": TAB["gold"], "f16p": TAB["f16p"], "rawp": TAB["rawp"], "alnp": TAB["alnp"], "plp_dev": TAB["plp_dev"], "q4p_n100": m100}
    for k in ("A_all_map", "A_all_pl", "B_all_map", "B_all_pl", "dev400_map", "dev400_pl"):
        S[k] = TAB[k]
    for n in (100, 300):
        S["A_n%d" % n] = mean_of("A_n%d" % n, N_DRAWS)
        S["B_n%d" % n] = mean_of("B_n%d" % n, N_DRAWS)
    res = {"note": "K14 exploratory (28 Nov 2026): label-free adaptation fitted only on reports never used for fitting. Evaluation on fresh "
                   "set A, medium load, arrival seed 11 (the Table 4 condition). Shares in percent of 11,480 incidents; differences in "
                   "percentage points with paired episode-bootstrap 95% intervals (10,000 resamples, seed 7) and sign-flip p values; arms "
                   "with draws use the per-episode mean over the draws (intervals over episodes only).",
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "sanity_missed": san,
           "fold_episodes": [int((np.array(list(fold_of.values())) == k).sum()) for k in (0, 1)],
           "share_pct": {k: sh(v) for k, v in S.items()},
           "never_verified": {k: int(UNV[k].sum()) for k in ("gold", "f16p", "rawp", "alnp", "plp_dev", "A_all_map", "A_all_pl", "B_all_map", "dev400_map")},
           "late": {k: int(LATE[k].sum()) for k in ("gold", "f16p", "rawp", "alnp", "plp_dev", "A_all_map", "A_all_pl", "B_all_map", "dev400_map")},
           "accuracy_pct": {k: 100 * v for k, v in acc.items() if "_d" not in k},
           "info": info, "per_draw_share_pct": {}, "comparisons": {}}
    for pref in ("A_n100", "A_n300", "B_n100", "B_n300"):
        per = [sh(TAB["%s_d%d" % (pref, d)]) for d in range(N_DRAWS)]
        res["per_draw_share_pct"][pref] = {"min": min(per), "max": max(per), "all": per,
                                          "acc_mean_pct": 100 * float(np.mean([acc["%s_d%d" % (pref, d)] for d in range(N_DRAWS)])),
                                          "err_rel_raw_mean": float(np.mean([info["%s_d%d" % (pref, d)]["err_rel_raw"] for d in range(N_DRAWS)]))}
    for k in ("A_all_map", "A_n100", "A_n300", "B_all_map", "B_n100", "B_n300", "dev400_map", "A_all_pl", "B_all_pl", "dev400_pl", "plp_dev"):
        for base in ("rawp", "f16p", "alnp", "q4p_n100", "plp_dev"):
            if base != k:
                res["comparisons"]["%s - %s" % (k, base)] = paired_arrays(S[k], S[base], NN)
    res["comparisons"]["A_all_pl - A_all_map"] = paired_arrays(S["A_all_pl"], S["A_all_map"], NN)
    res["comparisons"]["B_all_pl - B_all_map"] = paired_arrays(S["B_all_pl"], S["B_all_map"], NN)
    res["seconds"] = round(time.time() - t_all, 1)
    (out / "checklist_k14_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    with gzip.open(out / "checklist_k14_episode_counts.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"episodes": [e.id for e in eps], "incidents": NN.tolist(), "missed": {k: v.tolist() for k, v in TAB.items()},
                   "fold_of_episode": fold_of}, f)
    log("ALL DONE")


if __name__ == "__main__":
    main()
