"""
Exploratory analyses added AFTER the pre-registered fresh confirmation, in answer to the strict review of 19 Nov 2026.
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

    def save():
        out.mkdir(parents=True, exist_ok=True)
        (out / "review_results.json").write_text(json.dumps({k: v for k, v in res.items()}, indent=1, default=float), encoding="utf-8")

    res = {"note": "Exploratory analyses after the registered fresh run (review of 19 Nov 2026). Not pre-registered."}
    A_idx = [i for i, c in enumerate(ev) if c["split"] == "fresh_eval_A"]
    B_idx = [i for i, c in enumerate(ev) if c["split"] == "fresh_eval_B"]
    base_arms = ["f16p", "rawp", "recp", "alnp", "q4p"] + ["q4p_n100_d%d" % d for d in range(5)] + ["tfidf", "rule", "q4p_goldS", "alnp_goldS"]

    def n100(tab):
        return np.mean([tab["q4p_n100_d%d" % d] for d in range(5)], axis=0)

    std_comps = [("rawp", "f16p"), ("alnp", "rawp"), ("q4p", "rawp"), ("alnp", "q4p_n100"), ("alnp", "q4p"), ("alnp", "f16p"),
                 ("alnp", "recp"), ("tfidf", "alnp"), ("rule", "alnp"), ("tfidf", "f16p")]

    # ---------------- R0 sanity
    sim = Sim(make_allocator("cbba_bounded"), SimConfig())
    epsA = make_fixed_episodes(ds, A_idx, "M", 11)
    tab, nn = run(epsA, ["f16p", "rawp", "alnp", "q4p"], sim)
    reg = json.loads((Path(a.fresh_out) / "results.json").read_text())["levels"]["A_M_s11"]["arms"]
    res["R0_sanity"] = {arm: [float(tab[arm].sum()), reg[arm]["missed"], abs(tab[arm].sum() - reg[arm]["missed"]) < 1e-9] for arm in ["gold", "f16p", "rawp", "alnp", "q4p"]}
    print("R0", res["R0_sanity"], flush=True)
    save()
    if not all(v[2] for v in res["R0_sanity"].values()):
        raise SystemExit("R0 failed: refitted arms do not reproduce the registered counts. Stop.")

    # ---------------- R1 overlap
    dev_text = {c["text"] for c in D.cases}
    dev_prompt = {hc.prompt_for(c, "prefix") for c in D.cases}
    dev_tmpl = set(D.template.tolist())
    ov = {}
    for st, idx in (("A", A_idx), ("B", B_idx)):
        cs = [ev[i] for i in idx]
        tk = [template_key(c["text"], pc.LANDMARKS) for c in cs]
        ov[st] = {"reports": len(cs), "text_in_development": sum(c["text"] in dev_text for c in cs),
                  "full_prompt_in_development": sum(hc.prompt_for(c, "prefix") in dev_prompt for c in cs),
                  "template_in_development": sum(t in dev_tmpl for t in tk), "distinct_templates": len(set(tk)),
                  "distinct_templates_not_in_development": len(set(tk) - dev_tmpl)}
    res["R1_overlap"] = ov
    print("R1", ov, flush=True)
    save()

    # ---------------- R2 novel-text episodes (medium load), regrouped with a fixed seed
    res["R2_novel_text"] = {}
    for st, idx in (("A", A_idx), ("B", B_idx)):
        nov = [i for i in idx if ev[i]["text"] not in dev_text]
        nov = nov[: (len(nov) // EPISODE_REPORTS) * EPISODE_REPORTS]
        eps = make_episodes(ds, nov, "M", 4242, EPISODE_REPORTS)
        tab, nn = run(eps, base_arms, sim)
        tab["q4p_n100"] = n100(tab)
        res["R2_novel_text"][st] = summarize(tab, nn, std_comps)
        print("R2", st, len(eps), flush=True)
        save()

    # ---------------- R3 AUC vs accuracy per head (fresh set A)
    A_arr = np.array(A_idx)
    ep_of = np.array([ev[i]["episode"] for i in A_idx])
    uniq = sorted(set(ep_of))
    ep_rows = {e: np.where(ep_of == e)[0] for e in uniq}
    gold = {"action": np.array([ACTIONS.index(ev[i]["gold"]["action"]) for i in A_idx])}
    isrec = np.array([ev[i]["gold"]["action"] in REC and ev[i]["gold"].get("sensor") in SENSORS for i in A_idx])
    gold["sensor"] = np.array([SENSORS.index(ev[i]["gold"]["sensor"]) if isrec[k] else -1 for k, i in enumerate(A_idx)])
    gold["prio"] = np.array([PRIOS.index(str(ev[i]["gold"]["priority"])) if isrec[k] else -1 for k, i in enumerate(A_idx)])

    def head_metrics(L, h, rows):
        y = gold[h][rows]
        z = L[h][A_arr][rows]
        pz = np.exp(z - z.max(1, keepdims=True)); pz /= pz.sum(1, keepdims=True)
        acc = float(np.mean(z.argmax(1) == y))
        labs = list(range(z.shape[1]))
        auc = float(roc_auc_score(y, pz, multi_class="ovr", average="macro", labels=labs)) if len(set(y)) == len(labs) else float("nan")
        return acc, auc

    r3 = {}
    rng = np.random.RandomState(3)
    for pos in ("end", "prefix"):
        fpos = fit[pos]
        Fe_, Qe_ = EV[("f16", pos)], EV[("Q4_K_M", pos)]
        L16, Lq = logits(fpos["ref"], Fe_), logits(fpos["ref"], Qe_)
        Lal = logits(fpos["ref"], fpos["aln"](Qe_))
        for h in HEADS:
            allrows = np.arange(len(A_idx)) if h == "action" else np.where(isrec)[0]
            m16, mq, mal = head_metrics(L16, h, allrows), head_metrics(Lq, h, allrows), head_metrics(Lal, h, allrows)
            bs = []
            for b in range(1000):
                pick = rng.randint(0, len(uniq), len(uniq))
                rows = np.concatenate([ep_rows[uniq[k]] for k in pick])
                rows = rows[np.isin(rows, allrows)]
                a16, u16 = head_metrics(L16, h, rows)
                aq, uq = head_metrics(Lq, h, rows)
                bs.append((aq - a16, uq - u16))
            bs = np.array(bs)
            r3["%s_%s" % (pos, h)] = {"n": int(len(allrows)), "fp16_acc": m16[0], "fp16_auc": m16[1], "q4raw_acc": mq[0], "q4raw_auc": mq[1],
                                     "map_acc": mal[0], "map_auc": mal[1],
                                     "acc_diff": mq[0] - m16[0], "acc_diff_ci": [float(np.nanpercentile(bs[:, 0], 2.5)), float(np.nanpercentile(bs[:, 0], 97.5))],
                                     "auc_diff": mq[1] - m16[1], "auc_diff_ci": [float(np.nanpercentile(bs[:, 1], 2.5)), float(np.nanpercentile(bs[:, 1], 97.5))]}
    res["R3_auc_vs_accuracy"] = r3
    print("R3 done", flush=True)
    save()

    # ---------------- R4 label draws (registered records, set A, M, seed 11)
    recs_reg = json.load(gzip.open(Path(a.fresh_out) / "records_A_M_s11.json.gz", "rt", encoding="utf-8"))
    T = {}
    for r in recs_reg:
        T.setdefault(r["arm"], {})[r["episode"]] = (r["counts"]["late"] + r["counts"]["unverified"], r["counts"]["n"])
    eps_ids = sorted(T["gold"])
    nn = np.array([T["gold"][e][1] for e in eps_ids], float)
    arr = {arm: np.array([T[arm][e][0] for e in eps_ids], float) for arm in T}
    r4 = {}
    for n in (100, 300):
        per = {}
        for d in range(5):
            per["d%d" % d] = paired_arrays(arr["alnp"], arr["q4p_n%d_d%d" % (n, d)], nn)
        M = np.array([arr["q4p_n%d_d%d" % (n, d)] for d in range(5)])
        rng = np.random.RandomState(11)
        bs = []
        for b in range(N_BOOT):
            dd = rng.randint(0, 5, 5)
            ee = rng.randint(0, len(nn), len(nn))
            bs.append((arr["alnp"][ee].sum() - M[dd][:, ee].mean(0).sum()) / nn[ee].sum())
        r4["n%d" % n] = {"per_draw": per, "two_level_bootstrap_ci": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                         "mean_diff": float((arr["alnp"].sum() - M.mean(0).sum()) / nn.sum())}
    res["R4_label_draws"] = r4
    print("R4 done", flush=True)
    save()

    # ---------------- R5 two thermal UAVs
    orig_specs = simmod.uav_specs

    def specs2():
        s = dict(orig_specs())
        u = s["UAV-03"]
        s["UAV-03"] = u._replace(sensors=("RGB", "THERMAL")) if hasattr(u, "_replace") else dataclasses.replace(u, sensors=("RGB", "THERMAL"))
        return s
    simmod.uav_specs = specs2
    sim2 = Sim(make_allocator("cbba_bounded"), SimConfig())
    simmod.uav_specs = orig_specs
    assert sorted(sim2.specs["UAV-03"].sensors) == ["RGB", "THERMAL"]
    tab, nn = run(epsA, ["f16p", "rawp", "alnp", "q4p", "q4p_goldS", "alnp_goldS"], sim2)
    res["R5_two_thermal"] = summarize(tab, nn, [("rawp", "f16p"), ("alnp", "rawp"), ("alnp", "q4p"), ("alnp", "f16p"), ("q4p_goldS", "q4p"), ("alnp_goldS", "alnp")])
    print("R5 done", flush=True)
    save()

    # ---------------- R6 inference delay inside the mission (single-server queue)
    import inspect
    import textwrap
    src = textwrap.dedent(inspect.getsource(Sim._on_report))
    old = "delay = runs * cfg.alloc_cost_s\n"
    assert src.count(old) == 1
    src = src.replace(old, "delay = runs * cfg.alloc_cost_s + self._model_delay(t)\n")
    nsd = dict(vars(simmod))
    exec(src, nsd)

    class DelaySim(Sim):
        model_s = 0.0
        _on_report = nsd["_on_report"]

        def _model_delay(self, t):
            start = max(t, self._gw_free)
            self._gw_free = start + self.model_s
            return self._gw_free - t

        def run(self, *args, **kw):
            self._gw_free = -1e18
            return Sim.run(self, *args, **kw)

    r6 = {}
    for lev in ("M", "H"):
        eps = make_fixed_episodes(ds, A_idx, lev, 11)
        for dly in (0.0, 2.0, 5.0):
            cfg = SimConfig()
            cfg.decision_timeout_s = 1e9
            simd = DelaySim(make_allocator("cbba_bounded"), cfg)
            simd.model_s = dly
            arms_d = ["f16p", "rawp", "alnp", "q4p"]
            tab, nn = run(eps, arms_d, simd)
            r6["%s_delay%.0f" % (lev, dly)] = {"tab": {k: float(v.sum()) for k, v in tab.items()}, "nn": float(nn.sum()), "_arrays": tab, "_nn": nn}
            print("R6", lev, dly, flush=True)
        # text arms and gold without delay
        tab0, nn0 = run(eps, ["tfidf"], sim)
        r6["%s_text_nodelay" % lev] = {"tab": {k: float(v.sum()) for k, v in tab0.items()}, "nn": float(nn0.sum()), "_arrays": tab0, "_nn": nn0}
    r6s = {}
    for lev in ("M", "H"):
        base = r6["%s_delay0" % lev]
        for dly in ("2", "5"):
            cur = r6["%s_delay%s" % (lev, dly)]
            r6s["%s_delay%s" % (lev, dly)] = {
                "shares": {k: v / cur["nn"] for k, v in cur["tab"].items() if k != "gold"},
                "delay_effect": {arm: paired_arrays(cur["_arrays"][arm], base["_arrays"][arm], cur["_nn"]) for arm in ("f16p", "rawp", "alnp", "q4p")},
                "with_delay": {"rawp-f16p": paired_arrays(cur["_arrays"]["rawp"], cur["_arrays"]["f16p"], cur["_nn"]),
                               "alnp-rawp": paired_arrays(cur["_arrays"]["alnp"], cur["_arrays"]["rawp"], cur["_nn"]),
                               "alnp-q4p": paired_arrays(cur["_arrays"]["alnp"], cur["_arrays"]["q4p"], cur["_nn"]),
                               "tfidf_nodelay-alnp_delay": paired_arrays(r6["%s_text_nodelay" % lev]["_arrays"]["tfidf"], cur["_arrays"]["alnp"], cur["_nn"])}}
        r6s["%s_gold" % lev] = r6["%s_delay0" % lev]["tab"]["gold"] / r6["%s_delay0" % lev]["nn"]
        r6s["%s_tfidf_nodelay" % lev] = r6["%s_text_nodelay" % lev]["tab"]["tfidf"] / r6["%s_text_nodelay" % lev]["nn"]
    res["R6_inference_delay"] = r6s
    res["seconds"] = round(time.time() - t_all, 1)
    (out / "review_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("DONE", res["seconds"], flush=True)


if __name__ == "__main__":
    main()
