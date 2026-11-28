"""
K3b (exploratory, 28 Nov 2026): sensitivity of the L2-SP warm start and of map + L2-SP fine-tuning to the penalty strength.
In checklist_analyses.py (K3) the inverse penalty strength C of the correction is chosen by inner cross-validation on the labelled reports.
Here C is fixed at 0.003, 0.03 or 0.3 for every head (weaker pulls toward the FP16 weights), on the five pre-specified label draws.
Same development fit, fresh set-A vectors, episodes (medium load, arrival seed 11) and simulator.

    python checklist_k3b.py --root <ROOT> --cases cases_fresh.jsonl --vectors <fresh vector folder> --fresh-out <folder with results.json> --out <out>
"""
import argparse
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
FIXED_C = (0.003, 0.03, 0.3)
G = {}


def paired_arrays(mx, my, nn, n_boot=10000, seed=7):
    mx, my, nn = (np.asarray(v, dtype=float) for v in (mx, my, nn))
    rng = np.random.RandomState(seed)
    E = len(nn)
    idx = rng.randint(0, E, size=(n_boot, E))
    diff = (mx[idx].sum(1) - my[idx].sum(1)) / nn[idx].sum(1)
    d = mx - my
    signs = rng.choice([-1.0, 1.0], size=(n_boot, E))
    p = (np.sum(np.abs((signs * d).sum(1)) >= abs(d.sum()) - 1e-12) + 1) / (n_boot + 1)
    return {"diff": float(d.sum() / nn.sum()), "ci": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))], "p": float(p)}


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
    miss, nn = [], []
    for e in G["eps"]:
        r = G["sim"].run(e, None, "gold", oracle=True) if arm == "gold" else G["sim"].run(e, CommitPolicy(svc), arm)
        c = devrun.compact(r, 0, "x", 0)["counts"]
        miss.append(c["late"] + c["unverified"])
        nn.append(c["n"])
    return arm, np.array(miss, float), np.array(nn, float)


def main():
    ap = argparse.ArgumentParser()
    for k in ("--root", "--cases", "--vectors", "--fresh-out", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    t_all = time.time()
    root = Path(a.root).resolve()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    os.environ["EDGESAR_ROOT"] = str(root)
    for sub in ("repair_package", "edgesar_shield", "edgesar_heads"):
        sys.path.insert(0, str(root / sub))
    import run_ppr as R1
    from ppr_lib import ACTIONS, HEADS, PRIOS, SENSORS, AffineMap, Data
    from shield import devrun
    from shield.alloc import make_allocator
    from shield.episodes import make_fixed_episodes
    from shield.policy import CommitPolicy
    from shield.service import Service
    from shield.sim import Sim, SimConfig

    D = Data(root)
    R1.D = D
    pc, pb = D.pc, D.pb
    A = np.where(D.split == "dev")[0]
    seed0 = R1.SEED + 999
    rows_all = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
    Fp, Qp = D.X[("f16", "prefix")], D.X[("Q4_K_M", "prefix")]
    ref = R1.fit_heads(Fp, rows_all, seed0)
    aln = AffineMap(Fp[A], Qp[A], D.template[A], seed0)
    ev_all = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
    assert json.loads((Path(a.vectors) / "case_ids.json").read_text()) == [c["id"] for c in ev_all]
    A_idx = np.array([i for i, c in enumerate(ev_all) if c["split"] == "fresh_eval_A"])
    ev = [ev_all[i] for i in A_idx]
    Qe = np.load(Path(a.vectors) / "Q4_K_M_prefix.npy").astype(np.float64)[A_idx]
    reg = json.loads((Path(a.fresh_out) / "results.json").read_text())
    gold_key = [pc.strict_key(pc.gold_norm(c)) for c in ev]

    def logits(heads, X, offset=None):
        return {h: heads[h].logits(X, None if offset is None else offset[h]) for h in HEADS}

    def assemble(P):
        return [pc.validate(pb._assemble(c, ACTIONS[int(P["action"][r].argmax())], SENSORS[int(P["sensor"][r].argmax())],
                                         int(PRIOS[int(P["prio"][r].argmax())])), c)[0] for r, c in enumerate(ev)]

    Xal_dev, Xal_e = aln(Qp), aln(Qe)
    Zq_dev, Zal_dev = logits(ref, Qp), logits(ref, Xal_dev)
    Zq_e, Zal_e = logits(ref, Qe), logits(ref, Xal_e)
    sc = {h: ref[h].scaler for h in HEADS}
    P = {"rawp": Zq_e, "alnp": Zal_e}
    for n in (100, 300):
        for d in range(5):
            sd = seed0 + 1000 * (d + 1)
            rng = np.random.default_rng(sd + 7)
            while True:
                lab = np.sort(rng.choice(A, size=n, replace=False))
                if len(set(D.y["action"][lab])) == 4:
                    break
            assert [D.cases[int(i)]["id"] for i in lab] == reg["label_draws"]["%d_d%d" % (n, d)]
            rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
            for C in FIXED_C:
                fc = {h: C for h in HEADS}
                h1 = R1.fit_heads(Qp, rows, sd, O={h: Zq_dev[h][rows[h]] for h in HEADS}, scaler=sc, fixed_C=fc)
                P["wspC%g_n%d_d%d" % (C, n, d)] = logits(h1, Qe, offset=Zq_e)
                h2 = R1.fit_heads(Xal_dev, rows, sd, O={h: Zal_dev[h][rows[h]] for h in HEADS}, scaler=sc, fixed_C=fc)
                P["mftC%g_n%d_d%d" % (C, n, d)] = logits(h2, Xal_e, offset=Zal_e)
    recs = {k: assemble(v) for k, v in P.items()}
    acc = {k: float(np.mean([pc.strict_key(x) == g for x, g in zip(v, gold_key)])) for k, v in recs.items()}
    ds = SimpleNamespace(cases=ev)
    G.update({"recs": recs, "rid": [c["id"] for c in ev], "pc": pc, "Service": Service, "CommitPolicy": CommitPolicy, "devrun": devrun,
              "make_sim": lambda: Sim(make_allocator("cbba_bounded"), SimConfig()), "eps": make_fixed_episodes(ds, range(len(ev)), "M", 11)})
    arms = ["gold", "rawp", "alnp"] + [k for k in recs if k not in ("rawp", "alnp")]
    TAB = {}
    with mp.get_context("fork").Pool(a.workers) as pool:
        for arm, miss, nn in pool.imap_unordered(sim_job, arms):
            TAB[arm] = miss
            NN = nn
    regA = reg["levels"]["A_M_s11"]["arms"]
    for arm in ("gold", "rawp", "alnp"):
        assert abs(TAB[arm].sum() - regA[arm]["missed"]) < 1e-9, arm
    res = {"note": "K3b exploratory sensitivity, 28 Nov 2026: fixed C for the L2-SP corrections (wsp: raw Q4; mft: mapped Q4); five pre-specified draws.",
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "rows": {}}
    for fam in ("wsp", "mft"):
        for C in FIXED_C:
            for n in (100, 300):
                m = np.mean([TAB["%sC%g_n%d_d%d" % (fam, C, n, d)] for d in range(5)], axis=0)
                res["rows"]["%s C=%g n=%d" % (fam, C, n)] = {"share": float(m.sum() / NN.sum()),
                                                             "acc": float(np.mean([acc["%sC%g_n%d_d%d" % (fam, C, n, d)] for d in range(5)])),
                                                             "map_minus_arm": paired_arrays(TAB["alnp"], m, NN)}
    res["seconds"] = round(time.time() - t_all, 1)
    (out / "checklist_k3b_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res["rows"].items():
        print(k, round(100 * v["share"], 2), round(100 * v["acc"], 1), round(100 * v["map_minus_arm"]["diff"], 2), [round(100 * x, 2) for x in v["map_minus_arm"]["ci"]])


if __name__ == "__main__":
    main()
