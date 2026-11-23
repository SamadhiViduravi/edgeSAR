"""
R7 only (control for R2 and R2b; see review_analyses.py). Exploratory analyses added AFTER the pre-registered fresh confirmation, in answer to the strict review of 19 Nov 2026.
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

    res = {"note": "R7 exploratory label-budget accounting, added 22 Nov 2026 after the second strict review. Not pre-registered. Set A, medium load, registered episodes (seed 11)."}
    A_idx = [i for i, c in enumerate(ev) if c["split"] == "fresh_eval_A"]
    sim = Sim(make_allocator("cbba_bounded"), SimConfig())
    epsA = make_fixed_episodes(ds, A_idx, "M", 11)
    Fp = X[("f16", "prefix")]
    # label draws: identical to the registered 100/300-label draws
    labs = {}
    for n in (100, 300):
        for d in range(5):
            sd = seed0 + 1000 * (d + 1)
            rng = np.random.default_rng(sd + 7)
            while True:
                lab = np.sort(rng.choice(A, size=n, replace=False))
                if len(set(D.y["action"][lab])) == 4:
                    break
            labs[(n, d)] = (lab, sd)
    extra = {}
    lam = {}
    for (n, d), (lab, sd) in labs.items():
        rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
        hF = R1.fit_heads(Fp, rows, sd)                                   # FP16 classifier trained on only n labels
        mp_n = AffineMap(Fp[lab], Qp[lab], D.template[lab], seed0)        # map fitted on only n unlabelled pairs
        lam["%d_d%d" % (n, d)] = mp_n.c
        extra["pairs%d_d%d" % (n, d)] = logits(f["ref"], mp_n(Qe))       # full FP16 classifier, map from n pairs
        extra["f16n%d_d%d" % (n, d)] = logits(hF, Fe)                     # small-label FP16 classifier on FP16
        extra["rawn%d_d%d" % (n, d)] = logits(hF, Qe)                     # ... unchanged on Q4
        extra["alnsame%d_d%d" % (n, d)] = logits(hF, mp_n(Qe))            # ... with a map fitted on the same n reports
        extra["alnn%d_d%d" % (n, d)] = logits(hF, f["aln"](Qe))           # ... with the map fitted on all 1,000 unlabelled pairs
    res["map_lambda_small"] = lam
    for k, v in extra.items():
        rs = assemble(v)
        cands, hier, conf = {}, {}, {}
        for i, nm in zip(rid, rs):
            c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cands[i], hier[i], conf[i] = [c], c, 1.0
        svc[k] = Service(cands, hier, conf)
        recs[k] = rs
    fam = ["pairs", "f16n", "rawn", "alnsame", "alnn"]
    arms = ["f16p", "rawp", "alnp", "q4p"] + ["q4p_n%d_d%d" % (n, d) for n in (100, 300) for d in range(5)] + \
           ["%s%d_d%d" % (fa, n, d) for fa in fam for n in (100, 300) for d in range(5)]
    t0 = time.time()
    tab, nn = run(epsA, arms, sim)
    print("ran %d arms in %.0f s" % (len(arms), time.time() - t0), flush=True)
    reg = json.loads((Path(a.fresh_out) / "results.json").read_text())["levels"]["A_M_s11"]["arms"]
    res["R0_sanity"] = {arm: [float(tab[arm].sum()), reg[arm]["missed"]] for arm in ["gold", "f16p", "rawp", "alnp", "q4p"]}
    assert all(abs(v[0] - v[1]) < 1e-9 for v in res["R0_sanity"].values()), res["R0_sanity"]
    for n in (100, 300):
        tab["q4p_n%d" % n] = np.mean([tab["q4p_n%d_d%d" % (n, d)] for d in range(5)], axis=0)
        for fa in fam:
            tab["%s%d" % (fa, n)] = np.mean([tab["%s%d_d%d" % (fa, n, d)] for d in range(5)], axis=0)
    comps = []
    for n in (100, 300):
        comps += [("pairs%d" % n, "f16p"), ("pairs%d" % n, "alnp"), ("pairs%d" % n, "q4p_n%d" % n),
                  ("rawn%d" % n, "f16n%d" % n), ("alnsame%d" % n, "f16n%d" % n), ("alnsame%d" % n, "q4p_n%d" % n),
                  ("alnn%d" % n, "q4p_n%d" % n), ("alnn%d" % n, "f16n%d" % n), ("f16n%d" % n, "q4p_n%d" % n)]
    res["R7"] = {"episodes": len(nn), "incidents": int(nn.sum()), "shares": {k: share(v, nn) for k, v in tab.items()},
                 "comparisons": {"%s-%s" % (x, y): paired_arrays(tab[x], tab[y], nn) for x, y in comps}}
    # per-draw ranges for the key comparisons
    pdr = {}
    for n in (100, 300):
        for x, y in (("pairs", "q4p_n"), ("alnsame", "q4p_n"), ("alnn", "q4p_n"), ("rawn", "f16n")):
            yy = (lambda d: tab["q4p_n%d_d%d" % (n, d)]) if y == "q4p_n" else (lambda d: tab["%s%d_d%d" % (y, n, d)])
            pdr["%s%d-%s%d" % (x, n, y, n)] = [float((tab["%s%d_d%d" % (x, n, d)].sum() - yy(d).sum()) / nn.sum()) for d in range(5)]
    res["R7_per_draw"] = pdr
    res["seconds"] = round(time.time() - t_all, 1)
    (out / "review_results_r7.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("DONE", res["seconds"], flush=True)


if __name__ == "__main__":
    main()
