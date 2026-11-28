"""
Second model family (co-author checklist of 27 Nov 2026, item 5). Exploratory, added 28 Nov 2026; not pre-registered.

Qwen2.5-1.5B-Instruct (Qwen team), FP16 and Q4_K_M GGUF files, the same llama.cpp build (b11901) and server settings, the same system prompt and
user message as the Llama study (only Qwen's chat format differs), reading position `prefix`. Every Qwen head, map and retrained head is fitted
only on the 1,000 development fitting reports, with the same functions, folds, C grid, seeds and label draws as the Llama study. The fresh
set-A reports, the fixed episodes, the simulator and the allocator are unchanged.

    python qwen_replication.py --root <ROOT> --cases cases_fresh.jsonl --qwen-vectors <edgesar_qwen_2026-11-28/vectors> \
        --fresh-out <folder with the registered results.json> --out <out> [--workers 2] [--position prefix]
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
N_BOOT = 10000
G = {}


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


def sim_job(job):
    level, arm = job
    if level not in G["sims"]:
        G["sims"][level] = G["make_sim"]()
    sim = G["sims"][level]
    eps = G["eps"][level]
    devrun, CommitPolicy = G["devrun"], G["CommitPolicy"]
    if arm != "gold" and arm not in G["svc"]:
        Service, pc = G["Service"], G["pc"]
        cands, hier, conf = {}, {}, {}
        for i, nm in zip(G["rid"], G["recs"][arm]):
            c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cands[i], hier[i], conf[i] = [c], c, 1.0
        G["svc"][arm] = Service(cands, hier, conf)
    miss, nn = [], []
    for e in eps:
        r = sim.run(e, None, "gold", oracle=True) if arm == "gold" else sim.run(e, CommitPolicy(G["svc"][arm]), arm)
        c = devrun.compact(r, 0, "x", 0)["counts"]
        miss.append(c["late"] + c["unverified"])
        nn.append(c["n"])
    return level, arm, np.array(miss, float), np.array(nn, float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--qwen-vectors", required=True)
    ap.add_argument("--fresh-out", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--position", default="prefix")
    ap.add_argument("--quick", action="store_true", help="smoke test with 12 episodes per load")
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
    from shield.alloc import make_allocator
    from shield.episodes import make_fixed_episodes
    from shield.policy import CommitPolicy
    from shield.service import Service
    from shield.sim import Sim, SimConfig

    def log(*x):
        print("[%6.0f s]" % (time.time() - t_all), *x, flush=True)

    pos = a.position
    D = Data(root)
    R1.D = D
    pc, pb = D.pc, D.pb
    qv = Path(a.qwen_vectors)
    assert json.loads((qv / "case_ids_dev.json").read_text()) == [c["id"] for c in D.cases], "Qwen development rows are not in case order"
    files = {(m, part): qv / ("qwen_%s_%s_%s.npy" % (m, pos, part)) for m in ("f16", "Q4_K_M") for part in ("dev", "fresh")}
    res = {"note": "Exploratory replication with a second model family (Qwen2.5-1.5B-Instruct), run 28 Nov 2026. Not pre-registered. "
                   "Fresh set A, arrival seed 11, loads L, M and H, reading position %s." % pos,
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "vector_sha256": {"%s_%s" % k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()}}
    for k, p in files.items():
        mp_ = p.with_suffix(".meta.json")
        if mp_.exists():
            res.setdefault("vector_meta", {})["%s_%s" % k] = json.loads(mp_.read_text(encoding="utf-8"))
    X = {k: np.load(p).astype(np.float64) for k, p in files.items()}
    for k, v in X.items():
        assert np.isfinite(v).all(), k
    A = np.where(D.split == "dev")[0]
    seed0 = R1.SEED + 999
    rows_all = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
    F, Q = X[("f16", "dev")], X[("Q4_K_M", "dev")]
    ref = R1.fit_heads(F, rows_all, seed0)
    mat = R1.fit_heads(Q, rows_all, seed0)
    rec = Recentre(F[A], Q[A])
    aln = AffineMap(F[A], Q[A], D.template[A], seed0)
    res["fit"] = {"dim": int(F.shape[1]), "C_ref": {h: ref[h].C for h in HEADS}, "C_q4": {h: mat[h].C for h in HEADS}, "map_lambda": aln.c,
                  "map_cv_err": aln.cv_err, "map_cv_err_recentre_only": aln.cv_err_recentre_only}
    draws = {}
    reg = json.loads((Path(a.fresh_out) / "results.json").read_text())
    for n in (100, 300):
        for d in range(5):
            sd = seed0 + 1000 * (d + 1)
            rng = np.random.default_rng(sd + 7)
            while True:
                lab = np.sort(rng.choice(A, size=n, replace=False))
                if len(set(D.y["action"][lab])) == 4:
                    break
            assert [D.cases[int(i)]["id"] for i in lab] == reg["label_draws"]["%d_d%d" % (n, d)], "label draw differs from the Llama study"
            rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
            draws[(n, d)] = R1.fit_heads(Q, rows, sd)
    log("Qwen heads, maps and draws fitted")

    ev_all = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
    assert json.loads((qv / "case_ids_fresh.json").read_text()) == [c["id"] for c in ev_all], "Qwen fresh rows are not in case order"
    A_idx = np.array([i for i, c in enumerate(ev_all) if c["split"] == "fresh_eval_A"])
    ev = [ev_all[i] for i in A_idx]
    Fe, Qe = X[("f16", "fresh")][A_idx], X[("Q4_K_M", "fresh")][A_idx]
    rid = [c["id"] for c in ev]
    gold_key = [pc.strict_key(pc.gold_norm(c)) for c in ev]

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

    P = {"f16p": logits(ref, Fe), "rawp": logits(ref, Qe), "recp": logits(ref, rec(Qe)), "alnp": logits(ref, aln(Qe)), "q4p": logits(mat, Qe)}
    for (n, d), h in draws.items():
        P["q4p_n%d_d%d" % (n, d)] = logits(h, Qe)
    P["q4p_goldS"] = gold_sensor(P["q4p"])
    P["alnp_goldS"] = gold_sensor(P["alnp"])
    recs = {k: assemble(v) for k, v in P.items()}
    res["record_accuracy_setA"] = {k: float(np.mean([pc.strict_key(x) == g for x, g in zip(v, gold_key)])) for k, v in recs.items()}
    res["action_accuracy_setA"] = {k: float(np.mean([x["action"] == pc.gold_norm(c)["action"] for x, c in zip(v, ev)])) for k, v in recs.items()}
    keyF = [pc.strict_key(x) for x in recs["f16p"]]
    res["records_changed_vs_f16p"] = {k: int(sum(pc.strict_key(x) != y for x, y in zip(v, keyF))) for k, v in recs.items()}
    cosr = np.sum(Qe * Fe, 1) / (np.linalg.norm(Qe, axis=1) * np.linalg.norm(Fe, axis=1))
    Xa = aln(Qe)
    cosa = np.sum(Xa * Fe, 1) / (np.linalg.norm(Xa, axis=1) * np.linalg.norm(Fe, axis=1))
    res["vector_similarity_setA"] = {"cos_raw_q4_vs_fp16_mean": float(cosr.mean()), "cos_raw_min": float(cosr.min()),
                                     "cos_mapped_vs_fp16_mean": float(cosa.mean())}
    log("records assembled")

    ds = SimpleNamespace(cases=ev)
    G.update({"recs": recs, "rid": rid, "pc": pc, "Service": Service, "CommitPolicy": CommitPolicy, "devrun": devrun, "svc": {}, "sims": {},
              "make_sim": lambda: Sim(make_allocator("cbba_bounded"), SimConfig()),
              "eps": {lv: make_fixed_episodes(ds, range(len(ev)), lv, 11)[:(12 if a.quick else None)] for lv in ("L", "M", "H")}})
    arms = ["gold", "f16p", "rawp", "recp", "alnp", "q4p", "q4p_goldS", "alnp_goldS"] + ["q4p_n%d_d%d" % (n, d) for n in (100, 300) for d in range(5)]
    jobs = [(lv, arm) for lv in ("L", "M", "H") for arm in arms]
    TAB, NN = {}, {}
    with mp.get_context("fork").Pool(a.workers) as pool:
        for lv, arm, miss, nn in pool.imap_unordered(sim_job, jobs):
            TAB[(lv, arm)], NN[(lv, arm)] = miss, nn
    log("missions done")
    llama = reg["levels"]
    comps = [("H1", "rawp", "f16p"), ("H2a", "alnp", "rawp"), ("H2b", "q4p", "rawp"), ("H3", "alnp", "q4p_n100"), ("S1", "alnp", "q4p"),
             ("S2", "alnp", "q4p_n300"), ("S3", "alnp", "recp"), ("S5", "q4p", "f16p"), ("S6", "alnp", "f16p"), ("S10", "q4p_goldS", "q4p"),
             ("S11", "alnp_goldS", "alnp"), ("S15", "f16p", "gold")]
    for lv in ("L", "M", "H"):
        t = {arm: TAB[(lv, arm)] for arm in arms}
        nn = NN[(lv, "gold")]
        for arm in arms:
            assert np.array_equal(NN[(lv, arm)], nn)
        for n in (100, 300):
            t["q4p_n%d" % n] = np.mean([t["q4p_n%d_d%d" % (n, d)] for d in range(5)], axis=0)
        L = llama["A_%s_s11" % lv]
        res["A_%s_s11" % lv] = {
            "episodes": len(nn), "incidents": int(nn.sum()), "incidents_llama": L["incidents"],
            "shares": {k: share(v, nn) for k, v in t.items() if "_d" not in k},
            "shares_llama": {k: L["arms"][k]["share"] for k in ["gold", "f16p", "rawp", "recp", "alnp", "q4p", "q4p_n100", "q4p_n300", "q4p_goldS", "alnp_goldS"]},
            "comparisons": {cid: {"comparison": "%s - %s" % (x, y), **paired_arrays(t[x], t[y], nn),
                                  "llama_diff": L["comparisons"][cid]["diff"], "llama_ci": L["comparisons"][cid]["ci"]} for cid, x, y in comps}}
    res["seconds"] = round(time.time() - t_all, 1)
    (out / "qwen_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    log("DONE")


if __name__ == "__main__":
    main()
