"""
R10: a label-free, mission-level acceptance check for a classifier migration (exploratory; added 25 Nov 2026, after the confirmation).

Question: before deploying the Q4 model, can a team predict how much a candidate adapted classifier will raise the missed share, without
any labels? The check replays the missions with the OLD classifier's records (FP16 classifier on FP16 vectors, prefix position) used as
the truth ("referee") instead of the gold records, and reports the candidate's missed share minus the old classifier's own missed share.
This pseudo-penalty is compared with the true penalty (gold truth: candidate minus FP16 classifier) for 36 candidate classifiers
(unchanged, recentred, map, retraining with 100/300/1,000 labels, bias recalibration and vector scaling with 100/300 labels, five draws
each where labels are drawn, TF-IDF and rules), on fresh sets A and B at three loads (registered episodes, seed 11).
Also reported: two label-free record-level proxies (disagreement with the old records, any field; per field) and one label-based proxy
(whole-record accuracy drop against gold).

The registered results (out_fresh/) are not changed. Same fitted classifiers, same fresh vectors, same simulator.

    python review_r10.py --root <ROOT> --cases fresh/cases_fresh.jsonl --vectors fresh/vectors --fresh-out out_fresh --out out_review
"""
import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

sys.dont_write_bytecode = True
LEVELS = ("L", "M", "H")
SEED = 11
HARM_PP = 0.5            # a migration counts as harmful if it raises the missed share by more than 0.5 pp (twice the H3/S1 margin)
_RUN = None


def _call(task):
    return _RUN(task)


def spearman(x, y):
    from scipy.stats import spearmanr
    r = spearmanr(x, y)
    return float(r.correlation if hasattr(r, "correlation") else r[0])


def pearson(x, y):
    return float(np.corrcoef(np.asarray(x, float), np.asarray(y, float))[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--fresh-out", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
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
    from ppr_lib import ACTIONS, HEADS, PRIOS, SENSORS, AffineMap, Data, Recentre
    from shield import devrun
    from shield.alloc import make_allocator
    from shield.episodes import make_fixed_episodes
    from shield.policy import CommitPolicy
    from shield.service import Service
    from shield.sim import Sim, SimConfig
    from scipy.optimize import minimize

    # ------------------------------------------------------------------ fit exactly as in the confirmation and R9
    D = Data(root)
    R1.D = D
    pc, pb = D.pc, D.pb
    A = np.where(D.split == "dev")[0]
    seed0 = R1.SEED + 999
    rows_all = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
    X = D.X
    F, Q = X[("f16", "prefix")], X[("Q4_K_M", "prefix")]
    f = {"ref": R1.fit_heads(F, rows_all, seed0), "mat": R1.fit_heads(Q, rows_all, seed0),
         "rec": Recentre(F[A], Q[A]), "aln": AffineMap(F[A], Q[A], D.template[A], seed0)}
    labs, draws = {}, {}
    for n in (100, 300):
        for d in range(5):
            sd = seed0 + 1000 * (d + 1)
            rng = np.random.default_rng(sd + 7)
            while True:
                lab = np.sort(rng.choice(A, size=n, replace=False))
                if len(set(D.y["action"][lab])) == 4:
                    break
            labs[(n, d)] = lab
            rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
            draws[(n, d)] = R1.fit_heads(Q, rows, sd)
    tfidf = pb.LRBaseline().fit([D.cases[int(i)] for i in A])

    ev = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
    vd = Path(a.vectors)
    Fe = np.load(vd / "f16_prefix.npy").astype(np.float64)
    Qe = np.load(vd / "Q4_K_M_prefix.npy").astype(np.float64)

    def logits(heads, Xe):
        return {h: heads[h].logits(Xe) for h in HEADS}

    def assemble(P):
        return [pc.validate(pb._assemble(c, ACTIONS[int(P["action"][r].argmax())], SENSORS[int(P["sensor"][r].argmax())],
                                         int(PRIOS[int(P["prio"][r].argmax())])), c)[0] for r, c in enumerate(ev)]

    P = {"f16p": logits(f["ref"], Fe), "rawp": logits(f["ref"], Qe), "recp": logits(f["ref"], f["rec"](Qe)),
         "alnp": logits(f["ref"], f["aln"](Qe)), "q4p": logits(f["mat"], Qe)}
    for (n, d), h in draws.items():
        P["q4p_n%d_d%d" % (n, d)] = logits(h, Qe)

    # decision-level recalibration (identical to R9)
    def fit_cal(Z, Y, scale):
        K = Z.shape[1]
        lam = 1e-2

        def obj(p):
            a_ = p[:K] if scale else np.ones(K)
            b_ = p[K:] if scale else p
            S = Z * a_ + b_
            S = S - S.max(1, keepdims=True)
            lp = S - np.log(np.exp(S).sum(1, keepdims=True))
            reg = lam * (np.sum(b_ ** 2) + (np.sum((a_ - 1) ** 2) if scale else 0.0))
            return -np.mean(lp[np.arange(len(Y)), Y]) + reg
        p0 = np.concatenate([np.ones(K), np.zeros(K)]) if scale else np.zeros(K)
        r = minimize(obj, p0, method="L-BFGS-B")
        return (r.x[:K] if scale else np.ones(K)), (r.x[K:] if scale else r.x)

    Zq_eval = P["rawp"]
    Zq_dev = logits(f["ref"], Q)
    for (n, d), lab in labs.items():
        rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
        for kind, scale in (("bias", False), ("vecs", True)):
            outh = {}
            for h in HEADS:
                r = rows[h]
                Y = np.asarray(D.onehot(h, r)).argmax(1)
                sc_, of_ = fit_cal(np.asarray(Zq_dev[h])[r], Y, scale)
                outh[h] = np.asarray(Zq_eval[h]) * sc_ + of_
            P["%s%d_d%d" % (kind, n, d)] = outh

    recs = {k: assemble(v) for k, v in P.items()}
    recs["tfidf"] = [pc.validate(x, c)[0] for c, x in zip(ev, tfidf.predict(ev))]
    recs["rule"] = [pc.validate(pb.rule_decision(c), c)[0] for c in ev]
    rid = [c["id"] for c in ev]
    cands = [k for k in recs if k != "f16p"]
    print("fitted %d candidate classifiers in %.0f s" % (len(cands), time.time() - t_all), flush=True)

    # ------------------------------------------------------------------ the referee: old records as pseudo-truth
    ev_ref = copy.deepcopy(ev)
    for c, nm in zip(ev_ref, recs["f16p"]):
        c["gold"] = dict(nm)
    bad = sum(pc.strict_key(pc.gold_norm(c)) != pc.strict_key(nm) for c, nm in zip(ev_ref, recs["f16p"]))
    assert bad == 0, "pseudo-gold does not normalise to the old records (%d)" % bad

    svc = {}
    for arm, rs in recs.items():
        cd, hier, conf = {}, {}, {}
        for i, nm in zip(rid, rs):
            c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cd[i], hier[i], conf[i] = [c], c, 1.0
        svc[arm] = Service(cd, hier, conf)
    sets = {"A": [i for i, c in enumerate(ev) if c["split"] == "fresh_eval_A"], "B": [i for i, c in enumerate(ev) if c["split"] == "fresh_eval_B"]}
    arms = ["f16p"] + cands

    def run_task(task):
        st, lev, truth = task
        t1 = time.time()
        ds = SimpleNamespace(cases=ev if truth == "gold" else ev_ref)
        sim = Sim(make_allocator("cbba_bounded"), SimConfig())
        eps = make_fixed_episodes(ds, sets[st], lev, SEED)
        tab = {k: [] for k in ["oracle"] + arms}
        nn = []
        for e in eps:
            g = devrun.compact(sim.run(e, None, "gold", oracle=True), 0, lev, SEED)["counts"]
            tab["oracle"].append(g["late"] + g["unverified"])
            nn.append(g["n"])
            for arm in arms:
                cc = devrun.compact(sim.run(e, CommitPolicy(svc[arm]), arm), 0, lev, SEED)["counts"]
                tab[arm].append(cc["late"] + cc["unverified"])
        print("set %s level %s truth %s: %d episodes in %.0f s" % (st, lev, truth, len(eps), time.time() - t1), flush=True)
        return task, {k: [float(x) for x in v] for k, v in tab.items()}, [float(x) for x in nn]

    global _RUN
    _RUN = run_task
    tasks = [(st, lev, tr) for st in ("A", "B") for lev in LEVELS for tr in ("gold", "referee")]
    import multiprocessing as mp
    raw = {}
    with mp.get_context("fork").Pool(min(len(tasks), a.workers)) as pool:
        for task, tab, nn in pool.imap_unordered(_call, tasks):
            raw["%s_%s_%s" % task] = {"missed": tab, "n": nn}

    # sanity: the gold-truth runs reproduce the registered missed counts (set A and B, every level, seed 11)
    reg = json.loads((Path(a.fresh_out) / "results.json").read_text())["levels"]
    sanity = {}
    for st in ("A", "B"):
        for lev in LEVELS:
            key = "%s_%s_s%d" % (st, lev, SEED)
            for arm, regarm in (("oracle", "gold"), ("f16p", "f16p"), ("rawp", "rawp"), ("recp", "recp"), ("alnp", "alnp"), ("q4p", "q4p"), ("tfidf", "tfidf"), ("rule", "rule")):
                mine = sum(raw["%s_%s_gold" % (st, lev)]["missed"][arm])
                sanity["%s %s" % (key, arm)] = [mine, reg[key]["arms"][regarm]["missed"]]
    assert all(abs(x - y) < 1e-9 for x, y in sanity.values()), {k: v for k, v in sanity.items() if abs(v[0] - v[1]) > 1e-9}

    # ------------------------------------------------------------------ record-level proxies (per set)
    gold_key = [pc.strict_key(pc.gold_norm(c)) for c in ev]
    ref_key = [pc.strict_key(nm) for nm in recs["f16p"]]

    def fields(nm):
        return (nm.get("action"), nm.get("sensor"), nm.get("priority"), nm.get("landmark"), nm.get("incident"))

    rec_metrics = {}
    for st, ix in sets.items():
        for arm in arms:
            k_ = [pc.strict_key(recs[arm][j]) for j in ix]
            fa = [fields(recs[arm][j]) for j in ix]
            fr = [fields(recs["f16p"][j]) for j in ix]
            rec_metrics["%s %s" % (st, arm)] = {
                "disagree_any": float(np.mean([k_[t] != ref_key[j] for t, j in enumerate(ix)])),
                "disagree_action": float(np.mean([x[0] != y[0] for x, y in zip(fa, fr)])),
                "disagree_sensor": float(np.mean([x[1] != y[1] for x, y in zip(fa, fr)])),
                "disagree_priority": float(np.mean([x[2] != y[2] for x, y in zip(fa, fr)])),
                "disagree_place": float(np.mean([(x[3], x[4]) != (y[3], y[4]) for x, y in zip(fa, fr)])),
                "accuracy": float(np.mean([k_[t] == gold_key[j] for t, j in enumerate(ix)])),
            }

    # ------------------------------------------------------------------ predictive validity
    def share(tab, arm, nn):
        return 100.0 * float(np.sum(tab[arm]) / np.sum(nn))

    rows = []
    for st in ("A", "B"):
        for lev in LEVELS:
            g = raw["%s_%s_gold" % (st, lev)]
            r = raw["%s_%s_referee" % (st, lev)]
            base_true = share(g["missed"], "f16p", g["n"])
            base_ref = share(r["missed"], "f16p", r["n"])
            for arm in cands:
                rm = rec_metrics["%s %s" % (st, arm)]
                rows.append({"set": st, "level": lev, "arm": arm,
                             "true_pp": share(g["missed"], arm, g["n"]) - base_true,
                             "referee_pp": share(r["missed"], arm, r["n"]) - base_ref,
                             "disagree_any": 100 * rm["disagree_any"], "accuracy_drop": 100 * (rec_metrics["%s f16p" % st]["accuracy"] - rm["accuracy"]),
                             **{k: 100 * rm[k] for k in ("disagree_action", "disagree_sensor", "disagree_priority", "disagree_place")}})

    def validity(sel):
        t = np.array([x["true_pp"] for x in sel])
        out_ = {"n": len(sel)}
        for k in ("referee_pp", "disagree_any", "disagree_sensor", "accuracy_drop"):
            v = np.array([x[k] for x in sel])
            out_["spearman_" + k] = spearman(v, t)
            out_["pearson_" + k] = pearson(v, t)
        rp = np.array([x["referee_pp"] for x in sel])
        out_["referee_mae_pp"] = float(np.mean(np.abs(rp - t)))
        out_["referee_bias_pp"] = float(np.mean(rp - t))
        harm_t = t > HARM_PP
        for k, v in (("referee", rp), ("disagree_any_5pct", np.array([x["disagree_any"] for x in sel]) - 5.0 + HARM_PP)):
            pred = v > HARM_PP
            out_["gate_" + k] = {"harmful_true": int(harm_t.sum()), "flagged": int(pred.sum()), "correct": int((pred == harm_t).sum()),
                                 "missed_harmful": int((~pred & harm_t).sum()), "false_alarms": int((pred & ~harm_t).sum())}
        return out_

    res = {"note": __doc__.strip().splitlines()[1].strip(), "harm_threshold_pp": HARM_PP, "seed": SEED, "candidates": cands,
           "sanity_gold_truth_reproduces_registered": sanity, "rows": rows,
           "validity": {"all": validity(rows)},
           "runtime_s": None}
    for st in ("A", "B"):
        res["validity"]["set_" + st] = validity([x for x in rows if x["set"] == st])
        for lev in LEVELS:
            res["validity"]["%s_%s" % (st, lev)] = validity([x for x in rows if x["set"] == st and x["level"] == lev])
    hs = [x for x in rows if not x["arm"] in ("tfidf", "rule")]
    res["validity"]["hidden_state_only"] = validity(hs)
    res["runtime_s"] = round(time.time() - t_all, 1)
    (out / "review_results_r10.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    # per-episode missed counts (and incident counts) of every arm under both truths, for the episode-level analyses of R10
    (out / "review_results_r10_episodes.json").write_text(json.dumps({"seed": SEED, "levels": raw}), encoding="utf-8")
    v = res["validity"]
    print("all: spearman referee %.3f, disagree %.3f, accuracy drop %.3f; MAE %.2f pp; gate %s" % (
        v["all"]["spearman_referee_pp"], v["all"]["spearman_disagree_any"], v["all"]["spearman_accuracy_drop"], v["all"]["referee_mae_pp"],
        v["all"]["gate_referee"]), flush=True)
    print("done in %.0f s" % res["runtime_s"], flush=True)


if __name__ == "__main__":
    main()
