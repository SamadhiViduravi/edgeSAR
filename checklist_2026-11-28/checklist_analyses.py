"""
Exploratory analyses for the co-author checklist of 27 Nov 2026 (items 3, 7, 9, 10, 11, 12 and 13). Added 28 Nov 2026, AFTER the
pre-registered fresh confirmation and the check confirmation. Nothing here is pre-registered and nothing here changes a registered result.
Same development fit (the 1,000 development fitting reports), same fresh set-A vectors (prefix position), same simulator and allocator code.

    python checklist_analyses.py --root <ROOT> --cases cases_fresh.jsonl --vectors <fresh vector folder> \
        --fresh-out <folder with results.json and records/> --deploy <deployment_check folder> --out <out> [--workers 2] [--quick]

K0  sanity: the refitted arms reproduce the registered missed counts and the registered label draws (set A, medium load, seed 11).
K3  stronger adaptation baselines with 100 and 300 labels, on 20 label draws each (draws 0-4 are the registered draws): retraining
    (the registered arm), warm start from the FP16 heads with an L2 penalty toward the FP16 weights (L2-SP), bias-only and vector-scaling
    correction of the FP16 logits, the map followed by L2-SP fine-tuning, and the map followed by bias-only correction.
K7  incident accounting of set A: how 6,000 reports give 11,480 incidents.
K9  unlabelled budget: maps fitted on 25, 50, 100, 300 and 500 pairs (10 draws each from the development fitting reports) and on all 1,000;
    missed share, reconstruction error on fresh set A and fitting time.
K10 label-draw variability over 20 draws (two-level bootstrap: draws and episodes); non-inferiority at several margins and equivalence for
    the map vs all-label retraining; absolute and relative effects; precision expected for human-report sets of 300, 600 and 1,000 reports.
K11 CPU deployment run: decision margins (saved GPU vectors, the deployed folded classifier) of the 42 CPU-changed records vs the 358 others.
K12 gold-field substitution: all 8 combinations of action, sensor and priority for unchanged Q4, map and all-label retraining; Shapley
    attribution; whether decision margins predict changed records, changed plans and extra missed incidents.
K13 simulator variants: 5 UAVs with one or two thermal cameras; deadlines x0.75 and x1.5; burst arrivals; bundle length 1 and 5.
"""
import argparse
import csv
import dataclasses
import gzip
import hashlib
import json
import multiprocessing as mp
import os
import pickle
import sys
import time
from itertools import combinations
from math import factorial
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import numpy as np

sys.dont_write_bytecode = True
N_BOOT = 10000
N_DRAWS = 20
PAIR_SIZES = (25, 50, 100, 300, 500)
PAIR_DRAWS = 10
FIELDS = ("action", "sensor", "prio")
G = {}          # globals shared with forked workers


def paired_arrays(mx, my, nn, n_boot=N_BOOT, seed=7):
    """Same function as the registered analysis: pooled difference, episode bootstrap interval, two-sided sign-flip p."""
    mx, my, nn = (np.asarray(v, dtype=float) for v in (mx, my, nn))
    rng = np.random.RandomState(seed)
    E = len(nn)
    idx = rng.randint(0, E, size=(n_boot, E))
    diff = (mx[idx].sum(1) - my[idx].sum(1)) / nn[idx].sum(1)
    d = mx - my
    signs = rng.choice([-1.0, 1.0], size=(n_boot, E))
    p = (np.sum(np.abs((signs * d).sum(1)) >= abs(d.sum()) - 1e-12) + 1) / (n_boot + 1)
    return {"diff": float(d.sum() / nn.sum()), "ci": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))], "p": float(p),
            "episodes": int(E), "first_better": int((d < 0).sum()), "first_worse": int((d > 0).sum())}


def share(m, n):
    return float(np.sum(m) / np.sum(n))


def auc(score, y):
    """Probability that a positive has a higher score than a negative (ties count one half)."""
    from scipy.stats import rankdata
    score, y = np.asarray(score, float), np.asarray(y, bool)
    npos, nneg = int(y.sum()), int((~y).sum())
    if npos == 0 or nneg == 0:
        return float("nan")
    r = rankdata(score)
    return float((r[y].sum() - npos * (npos + 1) / 2) / (npos * nneg))


# =====================================================================================================================
# simulation workers (forked; read G)
# =====================================================================================================================
def _service(arm):
    cache = G.setdefault("svc", {})
    if arm not in cache:
        Service, pc = G["Service"], G["pc"]
        cands, hier, conf = {}, {}, {}
        for i, nm in zip(G["rid"], G["recs"][arm]):
            c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cands[i], hier[i], conf[i] = [c], c, 1.0
        cache[arm] = Service(cands, hier, conf)
    return cache[arm]


def _sim(variant):
    cache = G.setdefault("sims", {})
    if variant not in cache:
        cache[variant] = G["make_sim"](variant)
    return cache[variant]


def _episodes(variant):
    cache = G.setdefault("eps", {})
    key = "burst" if variant == "burst" else "fixed"
    if key not in cache:
        cache[key] = G["make_eps"](key)
    return cache[key]


def sim_job(job):
    variant, arm, detail = job
    sim = _sim(variant)
    eps = _episodes(variant)
    devrun, CommitPolicy = G["devrun"], G["CommitPolicy"]
    miss, nn, per_ns, per_rep = [], [], {}, {}
    t0 = time.time()
    for e in eps:
        if arm == "gold":
            r = sim.run(e, None, "gold", oracle=True)
        else:
            r = sim.run(e, CommitPolicy(_service(arm)), arm)
        c = devrun.compact(r, 0, "x", 0)["counts"]
        miss.append(c["late"] + c["unverified"])
        nn.append(c["n"])
        if detail:
            for inc in r["incidents"]:
                v = per_ns.setdefault(inc["ns"], [0, 0])
                v[0] += 1
                v[1] += inc["class"] in ("late", "unverified")
            for rep in r["log"]["reports"]:
                per_rep[rep["case_id"]] = [rep.get("table_equal_gold"), rep.get("plan_equal_gold")]
    return variant, arm, np.array(miss, float), np.array(nn, float), (per_ns if detail else None), (per_rep if detail else None), time.time() - t0


# =====================================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--fresh-out", required=True)
    ap.add_argument("--deploy", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--quick", action="store_true", help="smoke test: 12 episodes, 2 draws, few arms")
    a = ap.parse_args()
    t_all = time.time()
    root = Path(a.root).resolve()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    os.environ["EDGESAR_ROOT"] = str(root)
    sys.path.insert(0, str(root / "repair_package"))
    sys.path.insert(0, str(root / "edgesar_shield"))
    sys.path.insert(0, str(root / "edgesar_heads"))
    import run_ppr as R1
    from ppr_lib import ACTIONS, HEADS, PRIOS, REC, SENSORS, AffineMap, Data, Recentre
    from shield import devrun
    import shield.sim as simmod
    from shield.alloc import make_allocator
    from shield.episodes import LEVEL_GAP_S, make_fixed_episodes
    from shield.policy import CommitPolicy
    from shield.service import Service
    from shield.sim import Episode, ReportEvent, Sim, SimConfig
    from scipy.optimize import minimize

    res = {"note": "Exploratory analyses for the co-author checklist of 27 Nov 2026, run 28 Nov 2026. Not pre-registered. Set A, reading "
                   "position prefix, medium load, arrival seed 11 unless a section says otherwise. Every outcome is reported.",
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

    def save():
        (out / "checklist_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")

    def log(*x):
        print("[%6.0f s]" % (time.time() - t_all), *x, flush=True)

    # ------------------------------------------------------------------ development fit (as in the registered analysis)
    D = Data(root)
    R1.D = D
    pc, pb = D.pc, D.pb
    A = np.where(D.split == "dev")[0]
    seed0 = R1.SEED + 999
    rows_all = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
    Fp, Qp = D.X[("f16", "prefix")], D.X[("Q4_K_M", "prefix")]
    ref = R1.fit_heads(Fp, rows_all, seed0)
    mat = R1.fit_heads(Qp, rows_all, seed0)
    rec = Recentre(Fp[A], Qp[A])
    t0 = time.time()
    aln = AffineMap(Fp[A], Qp[A], D.template[A], seed0)
    t_map_1000 = time.time() - t0
    log("development fit done; map lambda", aln.c)

    ev_all = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
    ids = json.loads((Path(a.vectors) / "case_ids.json").read_text(encoding="utf-8"))
    assert ids == [c["id"] for c in ev_all], "vector rows are not in case order"
    A_idx = np.array([i for i, c in enumerate(ev_all) if c["split"] == "fresh_eval_A"])
    ev = [ev_all[i] for i in A_idx]
    vd = Path(a.vectors)
    Fe = np.load(vd / "f16_prefix.npy").astype(np.float64)[A_idx]
    Qe = np.load(vd / "Q4_K_M_prefix.npy").astype(np.float64)[A_idx]
    rid = [c["id"] for c in ev]
    gold = [pc.gold_norm(c) for c in ev]
    gold_key = [pc.strict_key(g) for g in gold]

    def logits(heads, X, offset=None):
        return {h: heads[h].logits(X, None if offset is None else offset[h]) for h in HEADS}

    def assemble(P):
        return [pc.validate(pb._assemble(c, ACTIONS[int(P["action"][r].argmax())], SENSORS[int(P["sensor"][r].argmax())],
                                         int(PRIOS[int(P["prio"][r].argmax())])), c)[0] for r, c in enumerate(ev)]

    def force(P, fields):
        """Gold-field substitution: the listed fields take the gold value (sensor and priority only where the gold action carries them)."""
        P = {h: np.array(v, copy=True) for h, v in P.items()}
        for r, c in enumerate(ev):
            g = c["gold"]
            if "action" in fields:
                P["action"][r] = -1e9
                P["action"][r, ACTIONS.index(g["action"])] = 0.0
            if "sensor" in fields and g["action"] in REC and g.get("sensor") in SENSORS:
                P["sensor"][r] = -1e9
                P["sensor"][r, SENSORS.index(g["sensor"])] = 0.0
            if "prio" in fields and g["action"] in REC and str(g.get("priority")) in PRIOS:
                P["prio"][r] = -1e9
                P["prio"][r, PRIOS.index(str(g["priority"]))] = 0.0
        return P

    # ------------------------------------------------------------------ label draws (registered rule; draws 0-4 = registered draws)
    n_draws = 2 if a.quick else N_DRAWS
    labs = {}
    for n in (100, 300):
        for d in range(n_draws):
            sd = seed0 + 1000 * (d + 1)
            rng = np.random.default_rng(sd + 7)
            while True:
                lab = np.sort(rng.choice(A, size=n, replace=False))
                if len(set(D.y["action"][lab])) == 4:
                    break
            labs[(n, d)] = lab
    reg = json.loads((Path(a.fresh_out) / "results.json").read_text())
    same = {k: [D.cases[int(i)]["id"] for i in labs[(int(k.split("_")[0]), int(k.split("_d")[1]))]] == v
            for k, v in reg["label_draws"].items() if (int(k.split("_")[0]), int(k.split("_d")[1])) in labs}
    res["K0_label_draws_equal_registered"] = same
    assert all(same.values()), same

    # ------------------------------------------------------------------ logits of every arm (set A)
    Xal_dev = aln(Qp)                                   # map applied to all development Q4 vectors
    Xal_e = aln(Qe)
    P = {"f16p": logits(ref, Fe), "rawp": logits(ref, Qe), "recp": logits(ref, rec(Qe)), "alnp": logits(ref, Xal_e), "q4p": logits(mat, Qe)}
    Zq_dev, Zal_dev = logits(ref, Qp), logits(ref, Xal_dev)

    def fit_cal(Z, Y, scale):
        K = Z.shape[1]
        lam = 1e-2

        def obj(p):
            a_ = p[:K] if scale else np.ones(K)
            b_ = p[K:] if scale else p
            S = Z * a_ + b_
            S = S - S.max(1, keepdims=True)
            lp = S - np.log(np.exp(S).sum(1, keepdims=True))
            reg_ = lam * (np.sum(b_ ** 2) + (np.sum((a_ - 1) ** 2) if scale else 0.0))
            return -np.mean(lp[np.arange(len(Y)), Y]) + reg_
        p0 = np.concatenate([np.ones(K), np.zeros(K)]) if scale else np.zeros(K)
        r = minimize(obj, p0, method="L-BFGS-B")
        return (r.x[:K] if scale else np.ones(K)), (r.x[K:] if scale else r.x)

    def draw_job(key):
        """All label-using arms of one draw: logits on set A and the chosen penalty strengths."""
        n, d = key
        lab = labs[key]
        sd = seed0 + 1000 * (d + 1)
        rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
        o = {}
        cs = {}
        h_re = R1.fit_heads(Qp, rows, sd)                                                      # retraining (registered arm)
        o["q4p_n%d_d%d" % key] = logits(h_re, Qe)
        cs["q4p"] = {h: h_re[h].C for h in HEADS}
        sc = {h: ref[h].scaler for h in HEADS}
        h_sp = R1.fit_heads(Qp, rows, sd, O={h: Zq_dev[h][rows[h]] for h in HEADS}, scaler=sc)  # L2-SP warm start on raw Q4
        o["wsp_n%d_d%d" % key] = logits(h_sp, Qe, offset=P["rawp"])
        cs["wsp"] = {h: h_sp[h].C for h in HEADS}
        h_mf = R1.fit_heads(Xal_dev, rows, sd, O={h: Zal_dev[h][rows[h]] for h in HEADS}, scaler=sc)   # map, then L2-SP fine-tuning
        o["mft_n%d_d%d" % key] = logits(h_mf, Xal_e, offset=P["alnp"])
        cs["mft"] = {h: h_mf[h].C for h in HEADS}
        for kind, Zd, Ze, scale in (("bias", Zq_dev, P["rawp"], False), ("vecs", Zq_dev, P["rawp"], True), ("mbias", Zal_dev, P["alnp"], False)):
            oh = {}
            for h in HEADS:
                r = rows[h]
                Y = np.asarray(D.onehot(h, r)).argmax(1)
                s_, b_ = fit_cal(np.asarray(Zd[h])[r], Y, scale)
                oh[h] = np.asarray(Ze[h]) * s_ + b_
            o["%s_n%d_d%d" % (kind, n, d)] = oh
        return key, o, cs

    def pair_job(key):
        n, d = key
        rng = np.random.default_rng(seed0 + 70000 + 100 * n + d)
        idx = np.sort(rng.choice(A, size=n, replace=False))
        t0 = time.time()
        mp_ = AffineMap(Fp[idx], Qp[idx], D.template[idx], seed0)
        t_fit = time.time() - t0
        t0 = time.time()
        rc = Recentre(Fp[idx], Qp[idx])
        t_rc = time.time() - t0
        Xm = mp_(Qe)
        return key, logits(ref, Xm), {"lambda": mp_.c, "fit_s": t_fit, "recentre_fit_s": t_rc, "err": recon(Xm), "err_recentre": recon(rc(Qe)),
                                      "cos": float(np.mean(np.sum(Xm * Fe, 1) / (np.linalg.norm(Xm, axis=1) * np.linalg.norm(Fe, axis=1))))}

    sdF = Fp[A].std(0)
    sdF = np.where(sdF > 0, sdF, 1.0)

    def recon(Xm):
        """Mean squared error per dimension against the FP16 vector of the same fresh report, in FP16 standard-deviation units."""
        return float(np.mean(((Xm - Fe) / sdF) ** 2))

    G["draw_job"], G["pair_job"] = draw_job, pair_job
    t0 = time.time()
    keys = sorted(labs)
    with mp.get_context("fork").Pool(a.workers) as pool:
        draw_out = pool.map(_call_draw, keys)
    C_chosen = {}
    for key, o, cs in draw_out:
        P.update(o)
        C_chosen["n%d_d%d" % key] = cs
    res["K3_C_chosen"] = C_chosen
    log("label-draw arms fitted in %.0f s" % (time.time() - t0))
    pair_keys = [(n, d) for n in PAIR_SIZES for d in range(2 if a.quick else PAIR_DRAWS)]
    t0 = time.time()
    with mp.get_context("fork").Pool(a.workers) as pool:
        pair_out = pool.map(_call_pair, pair_keys)
    k9 = {"full_1000": {"lambda": aln.c, "fit_s": t_map_1000, "err": recon(Xal_e), "err_recentre": recon(rec(Qe)), "err_raw": recon(Qe),
                        "cos": float(np.mean(np.sum(Xal_e * Fe, 1) / (np.linalg.norm(Xal_e, axis=1) * np.linalg.norm(Fe, axis=1)))),
                        "cos_raw": float(np.mean(np.sum(Qe * Fe, 1) / (np.linalg.norm(Qe, axis=1) * np.linalg.norm(Fe, axis=1))))}}
    for key, lg_, info in pair_out:
        P["map_p%d_d%d" % key] = lg_
        k9["p%d_d%d" % key] = info
    res["K9_maps"] = k9
    log("unlabelled-budget maps fitted in %.0f s" % (time.time() - t0))
    P["q4p_goldS"] = force(P["q4p"], ("sensor",))
    P["alnp_goldS"] = force(P["alnp"], ("sensor",))
    combos = [c for k in (1, 2) for c in combinations(FIELDS, k)]
    for base in ("rawp", "alnp", "q4p"):
        for cmb in combos:
            P["%s_G%s" % (base, "".join(f[0] for f in cmb))] = force(P[base], cmb)
    P["allgold"] = force(P["rawp"], FIELDS)

    recs = {k: assemble(v) for k, v in P.items()}
    res["K12_allgold_records_equal_gold"] = int(sum(pc.strict_key(x) == g for x, g in zip(recs["allgold"], gold_key)))
    acc = {k: float(np.mean([pc.strict_key(x) == g for x, g in zip(v, gold_key)])) for k, v in recs.items()}
    res["record_accuracy_setA"] = acc
    log("records assembled for %d arms" % len(recs))

    # ------------------------------------------------------------------ simulators
    base_specs = simmod.uav_specs()

    def five_uavs(two_thermal):
        s = dict(base_specs)
        u1 = s["UAV-01"]
        s["UAV-04"] = dataclasses.replace(u1, id="UAV-04", speed=18, sensors=("RGB",), start=(340, 140))
        s["UAV-05"] = dataclasses.replace(u1, id="UAV-05", speed=16, sensors=(("RGB", "THERMAL") if two_thermal else ("RGB",)), start=(400, 140))
        return s

    def make_sim(variant):
        alloc = make_allocator("cbba_bounded", bundle_len={"bundle1": 1, "bundle5": 5}.get(variant, 3))
        cfg = SimConfig()
        if variant == "dl075":
            cfg = SimConfig(deadlines={k: 0.75 * v for k, v in simmod.DEADLINE_S.items()})
        if variant == "dl150":
            cfg = SimConfig(deadlines={k: 1.5 * v for k, v in simmod.DEADLINE_S.items()})
        sim = Sim(alloc, cfg)
        if variant in ("uav5_1th", "uav5_2th"):
            sim.specs = five_uavs(variant == "uav5_2th")
        return sim

    ds = SimpleNamespace(cases=ev)
    n_eps = 12 if a.quick else None

    def make_eps(kind):
        if kind == "fixed":
            eps = make_fixed_episodes(ds, range(len(ev)), "M", 11)
        else:                                           # bursts of 5 reports: gaps of mean 2 s inside a burst, longer gaps between bursts,
            gap = LEVEL_GAP_S["M"]                      # so the expected episode length equals the medium level (19 gaps of 30 s)
            g_in, burst = 2.0, 5
            by = {}
            for i, c in enumerate(ev):
                by.setdefault(c["episode"], []).append(i)
            eps = []
            for ep in sorted(by):
                members = sorted(by[ep], key=lambda i: ev[i]["pos"])
                n_in = sum(1 for j in range(1, len(members)) if j % burst != 0)
                n_out = len(members) - 1 - n_in
                g_out = (gap * (len(members) - 1) - g_in * n_in) / max(n_out, 1)
                rng = np.random.RandomState(int(hashlib.sha256(("burst|11|%s" % ep).encode()).hexdigest()[:8], 16) % (2 ** 31))
                t, evs = 0.0, []
                for j, i in enumerate(members):
                    if j > 0:
                        t += float(rng.exponential(g_in if j % burst != 0 else g_out))
                    c = ev[i]
                    evs.append(ReportEvent(round(t, 3), c["id"], c["id"], [dict(r) for r in c["open"]], pc.gold_norm(c)))
                eps.append(Episode("burst-s11-%s" % ep, evs, "M"))
        return eps[:n_eps] if n_eps else eps

    G.update({"recs": recs, "rid": rid, "pc": pc, "Service": Service, "CommitPolicy": CommitPolicy, "devrun": devrun,
              "make_sim": make_sim, "make_eps": make_eps})

    nd = n_draws
    k3_arms = ["%s_n%d_d%d" % (k, n, d) for k in ("q4p", "wsp", "mft", "bias", "vecs", "mbias") for n in (100, 300) for d in range(nd)]
    k9_arms = ["map_p%d_d%d" % key for key in pair_keys]
    k12_arms = ["%s_G%s" % (b, "".join(f[0] for f in cmb)) for b in ("rawp", "alnp", "q4p") for cmb in combos] + ["allgold"]
    base_arms = ["gold", "f16p", "rawp", "recp", "alnp", "q4p", "q4p_goldS", "alnp_goldS"]
    detail_arms = {"gold", "f16p", "rawp", "alnp", "q4p"}
    variants = ["uav5_1th", "uav5_2th", "dl075", "dl150", "burst", "bundle1", "bundle5"]
    v_arms = ["gold", "f16p", "rawp", "alnp", "q4p", "q4p_goldS", "alnp_goldS"] + ["q4p_n100_d%d" % d for d in range(min(5, nd))]
    jobs = [("default", arm, arm in detail_arms) for arm in base_arms] + [("default", arm, False) for arm in k3_arms + k9_arms + k12_arms]
    jobs += [(v, arm, False) for v in variants for arm in v_arms]
    seen, uniq = set(), []
    for j in jobs:
        if (j[0], j[1]) not in seen:
            seen.add((j[0], j[1]))
            uniq.append(j)
    jobs = sorted(uniq, key=lambda j: (j[0] in ("uav5_1th", "uav5_2th")), reverse=True)    # slow variants first
    log("running %d simulator jobs with %d workers" % (len(jobs), a.workers))
    t0 = time.time()
    TAB, NN, NS, REP, SEC = {}, {}, {}, {}, {}
    with mp.get_context("fork").Pool(a.workers) as pool:
        for k, (variant, arm, miss, nn, per_ns, per_rep, sec) in enumerate(pool.imap_unordered(sim_job, jobs)):
            TAB[(variant, arm)] = miss
            NN[(variant, arm)] = nn
            SEC[(variant, arm)] = sec
            if per_ns is not None:
                NS[(variant, arm)], REP[(variant, arm)] = per_ns, per_rep
            if (k + 1) % 25 == 0:
                log("  %d of %d simulator jobs done" % (k + 1, len(jobs)))
    log("simulator jobs done in %.0f s" % (time.time() - t0))
    res["seconds_per_arm"] = {"%s|%s" % k: round(v, 1) for k, v in SEC.items()}
    with gzip.open(out / "checklist_episode_counts.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"%s|%s" % k: [list(map(int, TAB[k])), list(map(int, NN[k]))] for k in TAB}, f)

    def tab_of(variant):
        t = {arm: TAB[(v, arm)] for (v, arm) in TAB if v == variant}
        return t, NN[(variant, "gold")]

    tab, nn = tab_of("default")
    for v in ["default"] + variants:
        tv, nv = tab_of(v)
        for arm in tv:
            assert np.array_equal(NN[(v, arm)], nv), "incident counts differ between arms (%s, %s)" % (v, arm)

    # ------------------------------------------------------------------ K0 sanity against the registered records
    if not a.quick:
        regA = reg["levels"]["A_M_s11"]["arms"]
        san = {arm: [float(tab[arm].sum()), regA[arm]["missed"]] for arm in base_arms}
        for n in (100, 300):
            san["q4p_n%d (mean of draws 0-4)" % n] = [float(np.mean([tab["q4p_n%d_d%d" % (n, d)] for d in range(5)], axis=0).sum()), regA["q4p_n%d" % n]["missed"]]
        res["K0_sanity_missed"] = san
        assert all(abs(v[0] - v[1]) < 1e-6 for v in san.values()), san
        assert int(nn.sum()) == reg["levels"]["A_M_s11"]["incidents"]
        recs_reg = json.load(gzip.open(Path(a.fresh_out) / "records" / "records_A_M_s11.json.gz", "rt", encoding="utf-8"))
        T = {}
        for r in recs_reg:
            T.setdefault(r["arm"], {})[r["episode"]] = r["counts"]["late"] + r["counts"]["unverified"]
        eps_ids = [e.id for e in make_eps("fixed")]
        per_ep_ok = {}
        for arm in ["gold", "f16p", "rawp", "recp", "alnp", "q4p", "q4p_goldS", "alnp_goldS"] + ["q4p_n%d_d%d" % (n, d) for n in (100, 300) for d in range(5)]:
            if arm in T:
                per_ep_ok[arm] = bool(np.array_equal(np.array([T[arm][e] for e in eps_ids], float), tab[arm]))
        res["K0_sanity_per_episode_equal"] = per_ep_ok
        assert all(per_ep_ok.values()), per_ep_ok
        log("K0 sanity passed")
    save()

    def comp(x, y, t=None, n_=None):
        t = tab if t is None else t
        n_ = nn if n_ is None else n_
        return paired_arrays(t[x], t[y], n_)

    def mean_draws(prefix, n, t=None, draws=None):
        t = tab if t is None else t
        draws = range(nd) if draws is None else draws
        return np.mean([t["%s_n%d_d%d" % (prefix, n, d)] for d in draws], axis=0)

    def two_level(x_arr, prefix, n, t=None, seed=11):
        """Difference x - (mean over draws of prefix arm), bootstrapping draws and episodes together."""
        t = tab if t is None else t
        M = np.array([t["%s_n%d_d%d" % (prefix, n, d)] for d in range(nd)])
        rng = np.random.RandomState(seed)
        bs = np.empty(N_BOOT)
        for b in range(N_BOOT):
            dd = rng.randint(0, nd, nd)
            ee = rng.randint(0, len(nn), len(nn))
            bs[b] = (x_arr[ee].sum() - M[dd][:, ee].mean(0).sum()) / nn[ee].sum()
        return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]

    # ------------------------------------------------------------------ K3 + K10 (label draws)
    fam = ("q4p", "wsp", "mft", "bias", "vecs", "mbias")
    k3 = {"arms": {"q4p": "retraining on the labelled Q4 vectors (registered arm)",
                   "wsp": "warm start: FP16 heads kept as offsets, a correction fitted on the labelled Q4 vectors with the FP16 scaler; the L2 "
                          "penalty on the correction weights = penalty toward the FP16 weights (L2-SP); bias free; C chosen by inner grouped CV",
                   "mft": "map (all 1,000 unlabelled pairs) followed by the same L2-SP fine-tuning on the mapped labelled vectors",
                   "bias": "bias-only correction of the FP16 logits on raw Q4 vectors (as R9)",
                   "vecs": "vector scaling of the FP16 logits on raw Q4 vectors (as R9)",
                   "mbias": "map followed by bias-only correction of the FP16 logits"}, "draws": nd}
    for n in (100, 300):
        blk = {"shares_mean_of_draws": {}, "per_draw_shares": {}, "comparisons_mean_of_draws": {}, "two_level_ci": {}}
        for f_ in fam:
            m = mean_draws(f_, n)
            blk["shares_mean_of_draws"][f_] = share(m, nn)
            blk["per_draw_shares"][f_] = [share(tab["%s_n%d_d%d" % (f_, n, d)], nn) for d in range(nd)]
            for y in ("rawp", "alnp", "q4p", "f16p"):
                blk["comparisons_mean_of_draws"]["%s-%s" % (f_, y)] = paired_arrays(m, tab[y], nn)
            blk["two_level_ci"]["alnp-%s" % f_] = two_level(tab["alnp"], f_, n)
            blk["comparisons_mean_of_draws"]["alnp-%s" % f_] = paired_arrays(tab["alnp"], m, nn)
            blk["comparisons_mean_of_draws"]["%s-q4p_n%d" % (f_, n)] = paired_arrays(m, mean_draws("q4p", n), nn)
        blk["first5_vs_all20"] = {f_: {"first5": share(mean_draws(f_, n, draws=range(min(5, nd))), nn), "all": share(mean_draws(f_, n), nn)} for f_ in fam}
        blk["best_single_draw"] = {f_: min(blk["per_draw_shares"][f_]) for f_ in fam}
        blk["worst_single_draw"] = {f_: max(blk["per_draw_shares"][f_]) for f_ in fam}
        blk["draws_where_alnp_better"] = {f_: int(sum(share(tab["alnp"], nn) < s for s in blk["per_draw_shares"][f_])) for f_ in fam}
        k3["n%d" % n] = blk
    res["K3_K10_label_arms"] = k3
    save()
    log("K3 done")

    # ------------------------------------------------------------------ K10 margins, equivalence, relative effects, precision
    def boot_rel(x, y, seed=7):
        rng = np.random.RandomState(seed)
        E = len(nn)
        idx = rng.randint(0, E, size=(N_BOOT, E))
        d = (x[idx].sum(1) - y[idx].sum(1)) / nn[idx].sum(1)
        rel = x[idx].sum(1) / y[idx].sum(1) - 1.0
        return d, rel

    k10 = {}
    main_comps = [("rawp", "f16p"), ("alnp", "rawp"), ("q4p", "rawp"), ("alnp", "q4p_n100m"), ("alnp", "q4p_n300m"), ("alnp", "q4p"),
                  ("recp", "rawp"), ("alnp", "f16p"), ("q4p", "f16p"), ("f16p", "gold")]
    tabm = dict(tab)
    tabm["q4p_n100m"] = mean_draws("q4p", 100, draws=range(min(5, nd)))
    tabm["q4p_n300m"] = mean_draws("q4p", 300, draws=range(min(5, nd)))
    eff = {}
    for x, y in main_comps:
        d, rel = boot_rel(tabm[x], tabm[y])
        eff["%s-%s" % (x, y)] = {"first_share": share(tabm[x], nn), "second_share": share(tabm[y], nn),
                                 "abs_diff_pp": 100 * share(tabm[x] - tabm[y], nn), "abs_ci95_pp": [100 * float(np.percentile(d, 2.5)), 100 * float(np.percentile(d, 97.5))],
                                 "abs_ci90_pp": [100 * float(np.percentile(d, 5)), 100 * float(np.percentile(d, 95))],
                                 "relative_change": float(tabm[x].sum() / tabm[y].sum() - 1.0),
                                 "relative_ci95": [float(np.percentile(rel, 2.5)), float(np.percentile(rel, 97.5))]}
    k10["absolute_and_relative"] = eff
    s1 = eff["alnp-q4p"]
    margins = [0.1, 0.25, 0.5, 0.75, 1.0]
    k10["map_vs_all_label_retraining"] = {
        "diff_pp": s1["abs_diff_pp"], "ci95_pp": s1["abs_ci95_pp"], "ci90_pp": s1["abs_ci90_pp"],
        "noninferiority_upper95_below_margin": {str(m): bool(s1["abs_ci95_pp"][1] < m) for m in margins},
        "equivalence_tost_ci90_inside_margin": {str(m): bool(-m < s1["abs_ci90_pp"][0] and s1["abs_ci90_pp"][1] < m) for m in margins},
        "smallest_noninferiority_margin_pp": s1["abs_ci95_pp"][1],
        "smallest_equivalence_margin_pp_tost": max(abs(s1["abs_ci90_pp"][0]), abs(s1["abs_ci90_pp"][1])),
        "note": "Non-inferiority: the upper end of the 95% interval below the margin (the registered rule, margins 0.25 and 0.5 pp registered; "
                "the others are a sensitivity check). Equivalence (two one-sided tests at 5%): the 90% interval inside (-margin, +margin)."}
    # precision expected for a human-report set, from the registered per-episode variability (episodes of 20 reports)
    prec = {}
    rng = np.random.RandomState(5)
    for x, y in (("rawp", "f16p"), ("alnp", "rawp"), ("alnp", "q4p_n100m"), ("alnp", "q4p")):
        row = {}
        for reports in (300, 600, 1000):
            E = reports // 20
            idx = rng.randint(0, len(nn), size=(N_BOOT, E))
            d = (tabm[x][idx].sum(1) - tabm[y][idx].sum(1)) / nn[idx].sum(1)
            row[str(reports)] = {"episodes": E, "expected_ci95_halfwidth_pp": 100 * float((np.percentile(d, 97.5) - np.percentile(d, 2.5)) / 2)}
        prec["%s-%s" % (x, y)] = row
    k10["human_report_precision"] = {"rows": prec, "note": "Resampling E episodes of the registered set-A results; assumes human reports vary like the "
                                                          "synthetic ones per episode, which is not known. A planning aid only."}
    res["K10_statistics"] = k10
    save()

    # ------------------------------------------------------------------ K9 unlabelled budget
    k9s = {"full_1000": {"share": share(tab["alnp"], nn), **k9["full_1000"]}}
    for n in PAIR_SIZES:
        dr = [d for d in range(PAIR_DRAWS) if "map_p%d_d%d" % (n, d) in tab]
        sh = [share(tab["map_p%d_d%d" % (n, d)], nn) for d in dr]
        m = np.mean([tab["map_p%d_d%d" % (n, d)] for d in dr], axis=0)
        k9s["p%d" % n] = {"draws": len(dr), "share_mean_of_draws": share(m, nn), "share_min": min(sh), "share_max": max(sh), "per_draw": sh,
                          "map_vs_rawp": paired_arrays(m, tab["rawp"], nn), "map_vs_full_map": paired_arrays(m, tab["alnp"], nn),
                          "err_mean": float(np.mean([k9["p%d_d%d" % (n, d)]["err"] for d in dr])),
                          "err_recentre_mean": float(np.mean([k9["p%d_d%d" % (n, d)]["err_recentre"] for d in dr])),
                          "cos_mean": float(np.mean([k9["p%d_d%d" % (n, d)]["cos"] for d in dr])),
                          "fit_s_mean": float(np.mean([k9["p%d_d%d" % (n, d)]["fit_s"] for d in dr])),
                          "lambda_counts": {str(l): int(sum(k9["p%d_d%d" % (n, d)]["lambda"] == l for d in dr)) for l in sorted({k9["p%d_d%d" % (n, d)]["lambda"] for d in dr})},
                          "record_accuracy_mean": float(np.mean([acc["map_p%d_d%d" % (n, d)] for d in dr]))}
    res["K9_unlabelled_budget"] = k9s
    save()
    log("K9 done")

    # ------------------------------------------------------------------ K12 field substitution, Shapley, margins
    k12 = {}
    for base in ("rawp", "alnp", "q4p"):
        def M(S):
            S = tuple(f for f in FIELDS if f in S)
            if not S:
                return tab[base]
            if len(S) == 3:
                return tab["allgold"]
            return tab["%s_G%s" % (base, "".join(f[0] for f in S))]
        cells = {"".join(f[0] for f in S) or "none": share(M(S), nn) for k in range(4) for S in combinations(FIELDS, k)}
        phi = {}
        for f in FIELDS:
            rest = [g for g in FIELDS if g != f]
            v = np.zeros(len(nn))
            for k in range(3):
                for S in combinations(rest, k):
                    w = factorial(k) * factorial(3 - k - 1) / factorial(3)
                    v += w * (M(S) - M(S + (f,)))                       # misses removed by adding the gold value of f
            phi[f] = v
        rng = np.random.RandomState(7)
        idx = rng.randint(0, len(nn), size=(N_BOOT, len(nn)))
        sh = {f: {"pp": 100 * share(phi[f], nn), "ci95_pp": [100 * float(np.percentile(phi[f][idx].sum(1) / nn[idx].sum(1), q)) for q in (2.5, 97.5)],
                  "alone_pp": 100 * share(M(()) - M((f,)), nn)} for f in FIELDS}
        total = 100 * share(M(()) - M(FIELDS), nn)
        k12[base] = {"missed_share_by_fields_replaced": cells, "shapley": sh, "total_removed_pp": total,
                     "interaction_pp": total - sum(v["alone_pp"] for v in sh.values()),
                     "sensor_only_vs_none": paired_arrays(M(("sensor",)), M(()), nn)}
    k12["allgold_vs_gold"] = paired_arrays(tab["allgold"], tab["gold"], nn)
    k12["allgold_records_equal_gold_of_6000"] = res["K12_allgold_records_equal_gold"]
    # margins: report level
    def rec_margin(Pd):
        out_ = np.empty(len(ev))
        a_ = np.sort(Pd["action"], 1)
        ma = a_[:, -1] - a_[:, -2]
        act = np.array(ACTIONS)[Pd["action"].argmax(1)]
        s_ = np.sort(Pd["sensor"], 1)
        p_ = np.sort(Pd["prio"], 1)
        ms, mpr = s_[:, -1] - s_[:, -2], p_[:, -1] - p_[:, -2]
        isr = np.isin(act, REC)
        out_[:] = ma
        out_[isr] = np.minimum(ma[isr], np.minimum(ms[isr], mpr[isr]))
        return out_, ma
    epi = np.array([c["episode"] for c in ev])
    ue = np.unique(epi)
    pos_of = {e: np.where(epi == e)[0] for e in ue}

    def auc_ci(score, y, B=1000, seed=3):
        rng = np.random.RandomState(seed)
        vals = []
        for _ in range(B):
            ee = rng.randint(0, len(ue), len(ue))
            ii = np.concatenate([pos_of[ue[k]] for k in ee])
            vals.append(auc(score[ii], y[ii]))
        return [float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))]

    mF, mFa = rec_margin(P["f16p"])
    keyF = [pc.strict_key(x) for x in recs["f16p"]]
    disp = np.linalg.norm((Qe - Fe) / sdF, axis=1)
    mrg = {}
    for arm in ("rawp", "alnp", "q4p"):
        mA, _ = rec_margin(P[arm])
        keyA = [pc.strict_key(x) for x in recs[arm]]
        chg = np.array([x != y for x, y in zip(keyA, keyF)])
        wrong = np.array([x != g for x, g in zip(keyA, gold_key)])
        nsA, nsF = NS[("default", arm)], NS[("default", "f16p")]
        repA = REP[("default", arm)]
        extra = np.array([nsA.get(i, [0, 0])[1] - nsF.get(i, [0, 0])[1] for i in rid])
        plan_bad = np.array([repA.get(i, [None, None])[1] is False for i in rid])
        miss_A = np.array([nsA.get(i, [0, 0])[1] for i in rid])
        row = {"records_changed_vs_f16p": int(chg.sum()), "records_wrong_vs_gold": int(wrong.sum()),
               "plans_differ_from_gold_plan": int(plan_bad.sum()),
               "auc_fp16_margin_predicts_change": auc(-mF, chg), "auc_fp16_margin_predicts_change_ci": auc_ci(-mF, chg),
               "auc_own_margin_predicts_change": auc(-mA, chg), "auc_own_margin_predicts_change_ci": auc_ci(-mA, chg),
               "auc_own_margin_predicts_wrong": auc(-mA, wrong), "auc_own_margin_predicts_wrong_ci": auc_ci(-mA, wrong),
               "auc_own_margin_predicts_plan_differs": auc(-mA, plan_bad), "auc_own_margin_predicts_plan_differs_ci": auc_ci(-mA, plan_bad),
               "auc_own_margin_predicts_extra_miss": auc(-mA, extra > 0), "auc_own_margin_predicts_extra_miss_ci": auc_ci(-mA, extra > 0),
               "auc_own_margin_predicts_any_miss": auc(-mA, miss_A > 0),
               "median_own_margin_changed_vs_unchanged": [float(np.median(mA[chg])) if chg.any() else None, float(np.median(mA[~chg]))],
               "extra_missed_total_vs_f16p": int(extra.sum()),
               "extra_missed_in_reports_with_changed_record": int(extra[chg].sum()),
               "extra_missed_in_reports_with_same_record": int(extra[~chg].sum()),
               "reports_with_more_misses": int((extra > 0).sum()), "reports_with_fewer_misses": int((extra < 0).sum())}
        if arm == "rawp":
            row["auc_displacement_predicts_change"] = auc(disp, chg)
            row["auc_displacement_predicts_change_ci"] = auc_ci(disp, chg)
        mrg[arm] = row
    k12["margins"] = mrg
    res["K12_propagation"] = k12
    save()
    log("K12 done")

    # ------------------------------------------------------------------ K13 simulator variants
    k13 = {"variants": {"uav5_1th": "5 UAVs (UAV-04 RGB 18 m/s, UAV-05 RGB 16 m/s added), one thermal camera (UAV-02)",
                        "uav5_2th": "5 UAVs, UAV-05 also THERMAL (two thermal cameras)",
                        "dl075": "deadlines x0.75 (180/270/360 s)", "dl150": "deadlines x1.5 (360/540/720 s)",
                        "burst": "burst arrivals: 4 bursts of 5 reports, 2 s mean gap inside a burst, same expected episode length as medium load",
                        "bundle1": "bundle length 1 per auction pass", "bundle5": "bundle length 5 per auction pass"}}
    comps13 = [("rawp", "f16p"), ("alnp", "rawp"), ("q4p", "rawp"), ("alnp", "q4p_n100m"), ("alnp", "q4p"), ("q4p_goldS", "q4p"), ("alnp_goldS", "alnp"),
               ("f16p", "gold")]
    for v in ["default"] + variants:
        tv, nv = tab_of(v)
        tv = dict(tv)
        tv["q4p_n100m"] = np.mean([tv["q4p_n100_d%d" % d] for d in range(min(5, nd))], axis=0)
        k13[v] = {"episodes": len(nv), "incidents": int(nv.sum()),
                  "shares": {k: share(tv[k], nv) for k in ["gold", "f16p", "rawp", "alnp", "q4p", "q4p_n100m", "q4p_goldS", "alnp_goldS"]},
                  "comparisons": {"%s-%s" % (x, y): paired_arrays(tv[x], tv[y], nv) for x, y in comps13}}
    res["K13_simulator_variants"] = k13
    save()
    log("K13 done")

    # ------------------------------------------------------------------ K7 incident accounting (set A)
    n_open = int(sum(len(c["open"]) for c in ev))
    acts = {k: int(sum(1 for g in gold if g["action"] == k)) for k in ACTIONS}
    per_rep = np.array([NS[("default", "gold")].get(i, [0, 0])[0] for i in rid])
    k7 = {"reports": len(ev), "episodes": int(len(nn)), "incidents_counted": int(nn.sum()), "open_incidents_listed_in_reports": n_open,
          "gold_actions": acts, "formula": "incidents = open incidents listed in the reports + gold CREATE records - gold CLOSE records "
                                            "(a closure at the report's own arrival time marks that incident never real; it is not counted)",
          "formula_value": n_open + acts["CREATE_VERIFICATION"] - acts["CLOSE_INCIDENT"],
          "incidents_per_report": {str(k): int((per_rep == k).sum()) for k in sorted(set(per_rep.tolist()))},
          "resolved_externally": 0}
    k7["formula_matches"] = k7["formula_value"] == k7["incidents_counted"]
    res["K7_incident_accounting"] = k7
    save()

    # ------------------------------------------------------------------ K11 CPU deployment: margins of changed records
    dep = Path(a.deploy)
    z = np.load(dep / "folded" / "folded_q4.npz")
    W, b = z["map_W"].astype(np.float64), z["map_b"].astype(np.float64)
    runA = dep / "out" / "A_cpu_mmap_ctx4096_400reports"
    pr = list(csv.DictReader(open(runA / "per_report.csv", encoding="utf-8")))
    dis = {r["case_id"]: r for r in csv.DictReader(open(runA / "disagreements.csv", encoding="utf-8"))}
    id2row = {c["id"]: i for i, c in enumerate(D.cases)}
    cid = [r["case_id"] for r in pr]
    L = D.X[("Q4_K_M", "prefix")][[id2row[c] for c in cid]] @ W.T + b
    Pd = {"action": L[:, 0:4], "sensor": L[:, 4:7], "prio": L[:, 7:10]}
    mS, mSa = rec_margin_any(Pd, ACTIONS, REC)
    chg = np.array([c in dis for c in cid])
    live = np.array([min(float(dis[c]["live_action_margin"]), float(dis[c]["live_sensor_margin"]), float(dis[c]["live_priority_margin"])) for c in cid if c in dis])
    res["K11_cpu_margins"] = {"reports": len(cid), "changed": int(chg.sum()),
                              "saved_record_margin_median_changed": float(np.median(mS[chg])), "saved_record_margin_median_unchanged": float(np.median(mS[~chg])),
                              "auc_saved_margin_predicts_cpu_change": auc(-mS, chg),
                              "changed_with_saved_margin_below_0.5": int((mS[chg] < 0.5).sum()), "unchanged_with_saved_margin_below_0.5": int((mS[~chg] < 0.5).sum()),
                              "changed_with_saved_margin_below_1": int((mS[chg] < 1.0).sum()), "unchanged_with_saved_margin_below_1": int((mS[~chg] < 1.0).sum()),
                              "live_record_margin_median_changed": float(np.median(live)),
                              "note": "Saved = GPU vectors of the study, deployed folded map classifier (float64); live margins are from disagreements.csv "
                                      "(min of the three field margins). Margin = top-1 minus top-2 logit; record margin = min over action and, for records "
                                      "that carry them, sensor and priority."}
    res["seconds"] = round(time.time() - t_all, 1)
    save()
    log("ALL DONE")


def rec_margin_any(Pd, ACTIONS, REC):
    a_ = np.sort(Pd["action"], 1)
    ma = a_[:, -1] - a_[:, -2]
    act = np.array(ACTIONS)[Pd["action"].argmax(1)]
    s_, p_ = np.sort(Pd["sensor"], 1), np.sort(Pd["prio"], 1)
    ms, mpr = s_[:, -1] - s_[:, -2], p_[:, -1] - p_[:, -2]
    isr = np.isin(act, REC)
    out_ = ma.copy()
    out_[isr] = np.minimum(ma[isr], np.minimum(ms[isr], mpr[isr]))
    return out_, ma


def _call_draw(key):
    return G["draw_job"](key)


def _call_pair(key):
    return G["pair_job"](key)


if __name__ == "__main__":
    main()
