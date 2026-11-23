"""
R9 only (control for R2 and R2b; see review_analyses.py). Exploratory analyses added AFTER the pre-registered fresh confirmation, in answer to the strict review of 19 Nov 2026.
They do not change or replace the registered results (out_fresh/). Same fitted classifiers, same fresh vectors.

    python review_analyses.py --root <ROOT> --cases fresh/cases_fresh.jsonl --vectors fresh/vectors --fresh-out out_fresh --out out_review

R0  sanity: the refitted arms reproduce the registered missed counts (set A, medium load, seed 11).
R1  overlap of fresh inputs with the development set (text, full prompt, template), by set.
R2  novel-text episodes: only fresh reports whose text never occurs in the development set, regrouped into episodes of 20.
R3  ranking (AUC) against decisions (accuracy) for every head, FP16 vectors vs raw Q4 vectors, on fresh set A, with episode-cluster intervals.
R4  label draws: each of the five 100- and 300-label draws separately, and a two-level bootstrap (draws and episodes).
R5  fleet with two thermal UAVs (UAV-03 also THERMAL): mismatch harm, recovery and the gold-sensor diagnosis again.
R6  measured CPU inference delay inside the mission: every model-based record is applied only after a single-server queue with 2.0 s
    (measured laptop mean) or 5.0 s (stress) per report; gold and text arms without delay.
"""
import argparse
import dataclasses
import gzip
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

sys.dont_write_bytecode = True
N_BOOT = 10000


def paired_arrays(mx, my, nn, n_boot=N_BOOT, seed=7):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--fresh-out", required=True)
    ap.add_argument("--out", required=True)
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
    from ppr_lib import ACTIONS, HEADS, PRIOS, REC, SENSORS, AffineMap, Data, Recentre, template_key
    from shield import devrun
    import shield.sim as simmod
    from shield.alloc import make_allocator
    from shield.episodes import EPISODE_REPORTS, make_episodes, make_fixed_episodes
    from shield.policy import CommitPolicy
    from shield.service import Service
    from shield.sim import Sim, SimConfig
    import heads_common as hc
    from sklearn.metrics import roc_auc_score

    D = Data(root)
    R1.D = D
    pc, pb = D.pc, D.pb
    A = np.where(D.split == "dev")[0]
    seed0 = R1.SEED + 999
    rows_all = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
    X = D.X
    fit = {}
    for pos in ("prefix", "end"):
        F, Q = X[("f16", pos)], X[("Q4_K_M", pos)]
        fit[pos] = {"ref": R1.fit_heads(F, rows_all, seed0), "mat": R1.fit_heads(Q, rows_all, seed0),
                    "rec": Recentre(F[A], Q[A]), "aln": AffineMap(F[A], Q[A], D.template[A], seed0)}
    draws = {}
    Qp = X[("Q4_K_M", "prefix")]
    for n in (100, 300):
        for d in range(5):
            sd = seed0 + 1000 * (d + 1)
            rng = np.random.default_rng(sd + 7)
            while True:
                lab = np.sort(rng.choice(A, size=n, replace=False))
                if len(set(D.y["action"][lab])) == 4:
                    break
            rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
            draws[(n, d)] = R1.fit_heads(Qp, rows, sd)
    tfidf = pb.LRBaseline().fit([D.cases[int(i)] for i in A])

    ev = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
    vd = Path(a.vectors)
    EV = {(m, p): np.load(vd / ("%s_%s.npy" % (m, p))).astype(np.float64) for m in ("f16", "Q4_K_M") for p in ("prefix", "end")}

    def logits(heads, Xe):
        return {h: heads[h].logits(Xe) for h in HEADS}

    def assemble(P):
        return [pc.validate(pb._assemble(c, ACTIONS[int(P["action"][r].argmax())], SENSORS[int(P["sensor"][r].argmax())],
                                         int(PRIOS[int(P["prio"][r].argmax())])), c)[0] for r, c in enumerate(ev)]

    def gold_sensor(P):
        P = {h: np.array(v, copy=True) for h, v in P.items()}
        for r, c in enumerate(ev):
            g = c["gold"]
            if g["action"] in REC and g.get("sensor") in SENSORS:
                P["sensor"][r] = -1e9
                P["sensor"][r, SENSORS.index(g["sensor"])] = 0.0
        return P

    f = fit["prefix"]
    Fe, Qe = EV[("f16", "prefix")], EV[("Q4_K_M", "prefix")]
    P = {"f16p": logits(f["ref"], Fe), "rawp": logits(f["ref"], Qe), "recp": logits(f["ref"], f["rec"](Qe)), "alnp": logits(f["ref"], f["aln"](Qe)),
         "q4p": logits(f["mat"], Qe)}
    for (n, d), h in draws.items():
        P["q4p_n%d_d%d" % (n, d)] = logits(h, Qe)
    P["q4p_goldS"] = gold_sensor(P["q4p"])
    P["alnp_goldS"] = gold_sensor(P["alnp"])
    recs = {k: assemble(v) for k, v in P.items()}
    recs["tfidf"] = [pc.validate(x, c)[0] for c, x in zip(ev, tfidf.predict(ev))]
    recs["rule"] = [pc.validate(pb.rule_decision(c), c)[0] for c in ev]
    rid = [c["id"] for c in ev]
    svc = {}
    for arm, rs in recs.items():
        cands, hier, conf = {}, {}, {}
        for i, nm in zip(rid, rs):
            c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cands[i], hier[i], conf[i] = [c], c, 1.0
        svc[arm] = Service(cands, hier, conf)
    ds = SimpleNamespace(cases=ev)

    def run(eps, arms, sim):
        tab = {arm: [] for arm in ["gold"] + arms}
        nn = []
        for e in eps:
            g = devrun.compact(sim.run(e, None, "gold", oracle=True), 0, "x", 0)["counts"]
            tab["gold"].append(g["late"] + g["unverified"])
            nn.append(g["n"])
            for arm in arms:
                c = devrun.compact(sim.run(e, CommitPolicy(svc[arm]), arm), 0, "x", 0)["counts"]
                tab[arm].append(c["late"] + c["unverified"])
        return {k: np.array(v, float) for k, v in tab.items()}, np.array(nn, float)

    def summarize(tab, nn, comps):
        return {"episodes": len(nn), "incidents": int(nn.sum()), "shares": {k: share(v, nn) for k, v in tab.items()},
                "comparisons": {"%s-%s" % (x, y): paired_arrays(tab[x], tab[y], nn) for x, y in comps}}

    res = {"note": "R9 exploratory decision-level recalibration comparator, added 23 Nov 2026 after the third strict review. Not pre-registered. Set A, medium load, registered episodes (seed 11). The FP16 heads are kept; only per-class offsets (bias) or per-class scales and offsets (vector scaling) are refitted on Q4 vectors of the same labelled draws used for the 100- and 300-label retraining arms."}
    from scipy.optimize import minimize
    A_idx = [i for i, c in enumerate(ev) if c["split"] == "fresh_eval_A"]
    sim = Sim(make_allocator("cbba_bounded"), SimConfig())
    epsA = make_fixed_episodes(ds, A_idx, "M", 11)
    labs = {}
    for n in (100, 300):
        for d in range(5):
            sd = seed0 + 1000 * (d + 1)
            rng = np.random.default_rng(sd + 7)
            while True:
                lab = np.sort(rng.choice(A, size=n, replace=False))
                if len(set(D.y["action"][lab])) == 4:
                    break
            labs[(n, d)] = lab

    def fit_cal(Z, Y, scale):
        K = Z.shape[1]
        lam = 1e-2

        def obj(p):
            a = p[:K] if scale else np.ones(K)
            b = p[K:] if scale else p
            S = Z * a + b
            S = S - S.max(1, keepdims=True)
            lp = S - np.log(np.exp(S).sum(1, keepdims=True))
            reg = lam * (np.sum(b ** 2) + (np.sum((a - 1) ** 2) if scale else 0.0))
            return -np.mean(lp[np.arange(len(Y)), Y]) + reg
        p0 = np.concatenate([np.ones(K), np.zeros(K)]) if scale else np.zeros(K)
        r = minimize(obj, p0, method="L-BFGS-B")
        a = r.x[:K] if scale else np.ones(K)
        b = r.x[K:] if scale else r.x
        return a, b

    Zq_eval = logits(f["ref"], Qe)            # FP16 heads on fresh Q4 vectors (= unchanged arm)
    Zq_dev = logits(f["ref"], Qp)             # FP16 heads on development Q4 vectors
    extra, params = {}, {}
    for (n, d), lab in labs.items():
        rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
        for kind, scale in (("bias", False), ("vecs", True)):
            outh = {}
            for h in HEADS:
                r = rows[h]
                Y = np.asarray(D.onehot(h, r)).argmax(1)
                sc_, of_ = fit_cal(np.asarray(Zq_dev[h])[r], Y, scale)
                outh[h] = np.asarray(Zq_eval[h]) * sc_ + of_
                params["%s%d_d%d_%s" % (kind, n, d, h)] = {"a": [float(x) for x in sc_], "b": [float(x) for x in of_]}
            extra["%s%d_d%d" % (kind, n, d)] = outh
    res["params"] = params
    for k, v in extra.items():
        rs = assemble(v)
        cands, hier, conf = {}, {}, {}
        for i, nm in zip(rid, rs):
            c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cands[i], hier[i], conf[i] = [c], c, 1.0
        svc[k] = Service(cands, hier, conf)
        recs[k] = rs
    fam = ["bias", "vecs"]
    arms = ["f16p", "rawp", "alnp", "q4p"] + ["q4p_n%d_d%d" % (n, d) for n in (100, 300) for d in range(5)] + \
           ["%s%d_d%d" % (fa, n, d) for fa in fam for n in (100, 300) for d in range(5)]
    t0 = time.time()
    tab, nn = run(epsA, arms, sim)
    print("ran %d arms in %.0f s" % (len(arms), time.time() - t0), flush=True)
    reg = json.loads((Path(a.fresh_out) / "results.json").read_text())["levels"]["A_M_s11"]["arms"]
    res["R0_sanity"] = {arm: [float(tab[arm].sum()), reg[arm]["missed"]] for arm in ["gold", "f16p", "rawp", "alnp", "q4p"]}
    assert all(abs(v[0] - v[1]) < 1e-9 for v in res["R0_sanity"].values()), res["R0_sanity"]
    # record-level accuracy of the action head per arm (fresh set A)
    yA = np.array([ACTIONS.index(c["gold"]["action"]) for c in ev])
    Aidx = np.array(A_idx)
    acc = {}
    for k, v in extra.items():
        acc[k] = float((np.asarray(v["action"]).argmax(1)[Aidx] == yA[Aidx]).mean())
    acc["rawp"] = float((np.asarray(Zq_eval["action"]).argmax(1)[Aidx] == yA[Aidx]).mean())
    res["action_accuracy_setA"] = acc
    for n in (100, 300):
        tab["q4p_n%d" % n] = np.mean([tab["q4p_n%d_d%d" % (n, d)] for d in range(5)], axis=0)
        for fa in fam:
            tab["%s%d" % (fa, n)] = np.mean([tab["%s%d_d%d" % (fa, n, d)] for d in range(5)], axis=0)
    comps = []
    for n in (100, 300):
        comps += [("bias%d" % n, "rawp"), ("bias%d" % n, "alnp"), ("bias%d" % n, "q4p_n%d" % n),
                  ("vecs%d" % n, "rawp"), ("vecs%d" % n, "alnp"), ("vecs%d" % n, "q4p_n%d" % n)]
    res["R9"] = {"episodes": len(nn), "incidents": int(nn.sum()), "shares": {k: share(v, nn) for k, v in tab.items()},
                 "comparisons": {"%s-%s" % (x, y): paired_arrays(tab[x], tab[y], nn) for x, y in comps}}
    res["seconds"] = round(time.time() - t_all, 1)
    (out / "review_results_r9.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("DONE", res["seconds"], flush=True)


if __name__ == "__main__":
    main()
