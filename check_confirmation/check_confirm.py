"""
Confirmation of the LABEL-FREE MISSION CHECK on new reports (set C) for two migration targets, Q4_K_M and Q3_K_M.
Protocol: PROTOCOL_CHECK_CONFIRM.md. This file is frozen with it (FROZEN.sha256) before any model output on set C exists.

The check: replay the missions with the OLD classifier's records (FP16 classifier on FP16 vectors, prefix position) as the truth
instead of gold records; the check penalty of a candidate is its missed share minus the old classifier's missed share under that truth.
The true penalty is the same difference under gold records. Candidates per target (39): unchanged, recentring, affine map, pseudo-label
retraining, CORAL, orthogonal Procrustes (the six label-free options), retraining with 1,000 labels, retraining with 100 and 300 labels,
bias recalibration and vector scaling with 100 and 300 labels (five label draws each), TF-IDF and the rule engine.

    python check_confirm.py --root ROOT --cases cases_C.jsonl --vectors vectors_C --dev-vectors vectors_C --out out_checkC --workers 2

Test mode on the earlier fresh sets (exploratory; not part of the confirmation):
    python check_confirm.py --root ROOT --cases cases_fresh.jsonl --vectors fresh/vectors --targets Q4_K_M
                            --sets A=fresh_eval_A,B=fresh_eval_B --misspec-set A --registered out_fresh/results.json --out out_r11
"""
import argparse
import copy
import dataclasses
import hashlib
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
SEED = 11                         # arrival seed, as in the registered confirmation
SEED_BOOT = 20261126
RHO_MIN = 0.80                    # H1
REGRET_MAX_PP = 0.25              # H3
CONSERVATIVE_SHARE = 0.95         # H4
RHO_MIN_MISSPEC = 0.70            # H5
LABEL_FREE = ("rawp", "recp", "alnp", "plp", "coral", "proc")
MISSPEC = ("greedy", "twothermal", "slow", "tight")
_RUN = None


def _call(task):
    return _RUN(task)


def spearman(x, y):
    from scipy.stats import spearmanr
    r = spearmanr(x, y)
    return float(r.correlation if hasattr(r, "correlation") else r[0])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def _std(F, Q):
    muF, muQ, sd = F.mean(0), Q.mean(0), F.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    return muF, muQ, sd, (F - muF) / sd, (Q - muQ) / sd


def _mpow(C, p):
    w, V = np.linalg.eigh(C)
    w = np.clip(w, 1e-12, None)
    return (V * w ** p) @ V.T


class Coral:
    """CORAL (Sun, Feng and Saenko, AAAI 2016) in the FP16-standardised space: s' = s_q (C_q + I)^(-1/2) (C_f + I)^(1/2),
    x' = mu_f + sd * s'. C_q and C_f are the covariance matrices of the standardised Q and FP16 vectors of the paired fitting reports."""

    def __init__(self, F, Q):
        self.muF, self.muQ, self.sd, Sf, Sq = _std(F, Q)
        d = F.shape[1]
        self.M = _mpow(np.cov(Sq, rowvar=False) + np.eye(d), -0.5) @ _mpow(np.cov(Sf, rowvar=False) + np.eye(d), 0.5)

    def __call__(self, X):
        return self.muF + self.sd * (((X - self.muQ) / self.sd) @ self.M)


class Procrustes:
    """Orthogonal Procrustes in the FP16-standardised space: R = U V' from the SVD of S_q' S_f (R minimises ||S_q R - S_f|| over
    orthogonal R), x' = mu_f + sd * (s_q R)."""

    def __init__(self, F, Q):
        self.muF, self.muQ, self.sd, Sf, Sq = _std(F, Q)
        U, _, Vt = np.linalg.svd(Sq.T @ Sf)
        self.R = U @ Vt

    def __call__(self, X):
        return self.muF + self.sd * (((X - self.muQ) / self.sd) @ self.R)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--vectors", required=True, help="folder with f16_prefix.npy, <target>_prefix.npy and case_ids.json of the evaluation reports")
    ap.add_argument("--dev-vectors", default=None, help="folder with dev_<target>_prefix.npy for targets that have no saved development vectors")
    ap.add_argument("--targets", default="Q4_K_M,Q3_K_M")
    ap.add_argument("--sets", default="C1=check_eval_C1,C2=check_eval_C2")
    ap.add_argument("--misspec-set", default="C1")
    ap.add_argument("--misspec-level", default="M")
    ap.add_argument("--registered", default=None, help="test mode only: results.json of the earlier confirmation, for a sanity check")
    ap.add_argument("--quick", type=int, default=0, help="smoke test only: first N episodes of every task")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    a = ap.parse_args()
    t_all = time.time()
    root = Path(a.root).resolve()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    os.environ["EDGESAR_ROOT"] = str(root)
    for p in ("repair_package", "edgesar_shield", "edgesar_heads"):
        sys.path.insert(0, str(root / p))
    import run_ppr as R1
    from ppr_lib import ACTIONS, HEADS, PRIOS, REC, SENSORS, AffineMap, Data, Recentre
    from shield import devrun
    from shield.alloc import make_allocator
    from shield.core import DEADLINE_S
    from shield.episodes import make_fixed_episodes
    from shield.policy import CommitPolicy
    from shield.service import Service
    from shield.sim import Sim, SimConfig
    from scipy.optimize import minimize

    targets = [t for t in a.targets.split(",") if t]
    sets_arg = dict(x.split("=") for x in a.sets.split(","))
    log = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "script_sha256": sha(__file__), "cases_sha256": sha(a.cases), "targets": targets,
           "sets": sets_arg, "quick": a.quick}

    # ------------------------------------------------------------------ development data, FP16 classifier and label draws (as in R10)
    D = Data(root)
    R1.D = D
    pc, pb = D.pc, D.pb
    A = np.where(D.split == "dev")[0]
    seed0 = R1.SEED + 999
    rows_all = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
    F = D.X[("f16", "prefix")]
    dev = {}
    for T in targets:
        if (T, "prefix") in D.X:
            dev[T] = D.X[(T, "prefix")]
        else:
            ids = json.loads((Path(a.dev_vectors) / "dev_case_ids.json").read_text(encoding="utf-8"))
            assert ids == [c["id"] for c in D.cases], "development vectors are not in development case order"
            dev[T] = np.load(Path(a.dev_vectors) / ("dev_%s_prefix.npy" % T)).astype(np.float64)
            assert dev[T].shape == F.shape, (T, dev[T].shape)
    ref = R1.fit_heads(F, rows_all, seed0)
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
    tfidf = pb.LRBaseline().fit([D.cases[int(i)] for i in A])

    # pseudo-labels: the FP16 classifier's own records on the FP16 vectors of the fitting reports
    Lf = {h: ref[h].logits(F) for h in HEADS}
    pa = np.array(ACTIONS)[Lf["action"].argmax(1)]
    rec_mask = np.isin(pa, REC)
    rows_pl = {"action": A, "sensor": A[rec_mask[A]], "prio": A[rec_mask[A]]}

    def onehot_pred(h, r):
        T_ = np.zeros((len(r), len(HEADS[h])))
        T_[np.arange(len(r)), Lf[h][r].argmax(1)] = 1.0
        return T_
    T_pl = {h: onehot_pred(h, rows_pl[h]) for h in HEADS}
    log["pseudo_label_rows"] = {h: int(len(rows_pl[h])) for h in HEADS}

    # ------------------------------------------------------------------ evaluation reports and vectors
    ev = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
    vd = Path(a.vectors)
    ids = json.loads((vd / "case_ids.json").read_text(encoding="utf-8"))
    assert ids == [c["id"] for c in ev], "evaluation vectors are not in case order"
    Fe = np.load(vd / "f16_prefix.npy").astype(np.float64)
    Qe = {T: np.load(vd / ("%s_prefix.npy" % T)).astype(np.float64) for T in targets}
    for T in targets:
        assert Qe[T].shape == Fe.shape == (len(ev), F.shape[1]), (T, Qe[T].shape, Fe.shape)
    sets = {name: [i for i, c in enumerate(ev) if c["split"] == split] for name, split in sets_arg.items()}
    assert all(len(v) > 0 for v in sets.values()), {k: len(v) for k, v in sets.items()}

    def logits(heads, Xe):
        return {h: heads[h].logits(Xe) for h in HEADS}

    def assemble(P):
        return [pc.validate(pb._assemble(c, ACTIONS[int(P["action"][r].argmax())], SENSORS[int(P["sensor"][r].argmax())],
                                         int(PRIOS[int(P["prio"][r].argmax())])), c)[0] for r, c in enumerate(ev)]

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

    P = {"f16p": logits(ref, Fe)}
    cand_names = []
    for T in targets:
        QT, QTe = dev[T], Qe[T]
        t0 = time.time()
        maps = {"rec": Recentre(F[A], QT[A]), "aln": AffineMap(F[A], QT[A], D.template[A], seed0), "coral": Coral(F[A], QT[A]),
                "proc": Procrustes(F[A], QT[A])}
        Pt = {"rawp": logits(ref, QTe), "recp": logits(ref, maps["rec"](QTe)), "alnp": logits(ref, maps["aln"](QTe)),
              "plp": logits(R1.fit_heads(QT, rows_pl, seed0, T=T_pl), QTe), "coral": logits(ref, maps["coral"](QTe)),
              "proc": logits(ref, maps["proc"](QTe)), "ret1000": logits(R1.fit_heads(QT, rows_all, seed0), QTe)}
        Zq_dev, Zq_eval = logits(ref, QT), Pt["rawp"]
        for (n, d), (lab, sd) in labs.items():
            rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
            Pt["ret%d_d%d" % (n, d)] = logits(R1.fit_heads(QT, rows, sd), QTe)
            for kind, scale in (("bias", False), ("vecs", True)):
                outh = {}
                for h in HEADS:
                    r = rows[h]
                    Y = np.asarray(D.onehot(h, r)).argmax(1)
                    sc_, of_ = fit_cal(np.asarray(Zq_dev[h])[r], Y, scale)
                    outh[h] = np.asarray(Zq_eval[h]) * sc_ + of_
                Pt["%s%d_d%d" % (kind, n, d)] = outh
        for k, v in Pt.items():
            P["%s|%s" % (T, k)] = v
        if not cand_names:
            cand_names = list(Pt.keys())
        log["fit_seconds_%s" % T] = round(time.time() - t0, 1)
        print("target %s: %d candidates fitted in %.0f s" % (T, len(Pt), time.time() - t0), flush=True)
    recs = {k: assemble(v) for k, v in P.items()}
    recs["tfidf"] = [pc.validate(x, c)[0] for c, x in zip(ev, tfidf.predict(ev))]
    recs["rule"] = [pc.validate(pb.rule_decision(c), c)[0] for c in ev]
    arms = list(recs.keys())                                   # f16p first
    rid = [c["id"] for c in ev]

    # ------------------------------------------------------------------ referee truth: the old records
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

    def make_sim(kind):
        cfg = SimConfig()
        alloc = make_allocator("legacy_greedy_s1" if kind == "greedy" else "cbba_bounded")
        if kind == "tight":
            cfg = SimConfig(deadlines={k: 0.75 * v for k, v in DEADLINE_S.items()})
        sim = Sim(alloc, cfg)
        if kind == "twothermal":
            sim.specs = {k: (dataclasses.replace(u, sensors=tuple(sorted(set(u.sensors) | {"THERMAL"}))) if k == "UAV-03" else u)
                         for k, u in sim.specs.items()}
        if kind == "slow":
            sim.specs = {k: dataclasses.replace(u, speed=0.75 * u.speed) for k, u in sim.specs.items()}
        return sim

    def run_task(task):
        st, lev, truth, kind = task
        t1 = time.time()
        ds = SimpleNamespace(cases=ev if truth == "gold" else ev_ref)
        sim = make_sim(kind)
        eps = make_fixed_episodes(ds, sets[st], lev, SEED)
        if a.quick:
            eps = eps[:a.quick]
        tab = {k: [] for k in ["oracle"] + arms}
        nn = []
        for e in eps:
            g = devrun.compact(sim.run(e, None, "gold", oracle=True), 0, lev, SEED)["counts"]
            tab["oracle"].append(g["late"] + g["unverified"])
            nn.append(g["n"])
            for arm in arms:
                cc = devrun.compact(sim.run(e, CommitPolicy(svc[arm]), arm), 0, lev, SEED)["counts"]
                tab[arm].append(cc["late"] + cc["unverified"])
        print("set %s level %s truth %s sim %s: %d episodes in %.0f s" % (st, lev, truth, kind, len(eps), time.time() - t1), flush=True)
        return task, {k: [float(x) for x in v] for k, v in tab.items()}, [float(x) for x in nn]

    global _RUN
    _RUN = run_task
    tasks = [(st, lev, tr, "default") for st in sets for lev in LEVELS for tr in ("gold", "referee")]
    tasks += [(a.misspec_set, a.misspec_level, tr, k) for k in MISSPEC for tr in ("gold", "referee")]
    tasks.sort(key=lambda t: {"H": 0, "M": 1, "L": 2}[t[1]])            # long tasks first
    import multiprocessing as mp
    raw = {}
    with mp.get_context("fork").Pool(min(len(tasks), a.workers)) as pool:
        for task, tab, nn in pool.imap_unordered(_call, tasks):
            raw["%s_%s_%s_%s" % task] = {"missed": tab, "n": nn}

    # test mode: the gold-truth default runs reproduce the registered counts of the earlier confirmation
    sanity = {}
    if a.registered and not a.quick:
        reg = json.loads(Path(a.registered).read_text())["levels"]
        T0 = targets[0]
        for st in sets:
            for lev in LEVELS:
                key = "%s_%s_s%d" % (st, lev, SEED)
                for arm, regarm in (("oracle", "gold"), ("f16p", "f16p"), ("%s|rawp" % T0, "rawp"), ("%s|recp" % T0, "recp"),
                                    ("%s|alnp" % T0, "alnp"), ("%s|ret1000" % T0, "q4p"), ("tfidf", "tfidf"), ("rule", "rule")):
                    sanity["%s %s" % (key, arm)] = [sum(raw["%s_%s_gold_default" % (st, lev)]["missed"][arm]), reg[key]["arms"][regarm]["missed"]]
        assert all(abs(x - y) < 1e-9 for x, y in sanity.values()), {k: v for k, v in sanity.items() if abs(v[0] - v[1]) > 1e-9}

    # ------------------------------------------------------------------ record-level measures (per set)
    gold_key = [pc.strict_key(pc.gold_norm(c)) for c in ev]
    ref_key = [pc.strict_key(nm) for nm in recs["f16p"]]
    rec_metrics = {}
    for st, ix in sets.items():
        for arm in arms:
            k_ = [pc.strict_key(recs[arm][j]) for j in ix]
            rec_metrics[(st, arm)] = {
                "flips": 100.0 * float(np.mean([k_[t] != ref_key[j] for t, j in enumerate(ix)])),
                "sensor_flips": 100.0 * float(np.mean([recs[arm][j].get("sensor") != recs["f16p"][j].get("sensor") for j in ix])),
                "accuracy": 100.0 * float(np.mean([k_[t] == gold_key[j] for t, j in enumerate(ix)]))}

    rawnp = {k: {"missed": {x: np.asarray(v, dtype=float) for x, v in t["missed"].items()}, "n": np.asarray(t["n"], dtype=float)}
             for k, t in raw.items()}

    def share(tab, arm, nn, idx=None):
        m, n_ = tab[arm], nn
        if idx is not None:
            m, n_ = m[idx], n_[idx]
        return 100.0 * float(m.sum() / n_.sum())

    def pens(key, idx=None):
        t = rawnp[key]
        base = share(t["missed"], "f16p", t["n"], idx)
        return {arm: share(t["missed"], arm, t["n"], idx) - base for arm in arms[1:]}, base

    def cand_arms(T):
        return ["%s|%s" % (T, c) for c in cand_names] + ["tfidf", "rule"]

    rows = []
    for T in targets:
        for st in sets:
            for lev in LEVELS:
                tp, base_t = pens("%s_%s_gold_default" % (st, lev))
                rp, base_r = pens("%s_%s_referee_default" % (st, lev))
                for arm in cand_arms(T):
                    rm = rec_metrics[(st, arm)]
                    rows.append({"target": T, "set": st, "level": lev, "arm": arm.split("|")[-1], "true_pp": tp[arm], "check_pp": rp[arm],
                                 "flips": rm["flips"], "sensor_flips": rm["sensor_flips"],
                                 "accuracy_drop": rec_metrics[(st, "f16p")]["accuracy"] - rm["accuracy"]})
    misspec_rows = []
    rp_default, _ = pens("%s_%s_referee_default" % (a.misspec_set, a.misspec_level))
    for T in targets:
        for k in MISSPEC:
            tp, _ = pens("%s_%s_gold_%s" % (a.misspec_set, a.misspec_level, k))
            rpk, _ = pens("%s_%s_referee_%s" % (a.misspec_set, a.misspec_level, k))
            for arm in cand_arms(T):
                misspec_rows.append({"target": T, "sim": k, "arm": arm.split("|")[-1], "true_pp": tp[arm], "check_default_pp": rp_default[arm],
                                     "check_same_sim_pp": rpk[arm]})

    # ------------------------------------------------------------------ hypotheses (PROTOCOL_CHECK_CONFIRM.md)
    def cond_rows(T, st, lev):
        return [x for x in rows if x["target"] == T and x["set"] == st and x["level"] == lev]
    conds = {}
    rng = np.random.default_rng(SEED_BOOT)
    for T in targets:
        for st in sets:
            for lev in LEVELS:
                sel = cond_rows(T, st, lev)
                t = [x["true_pp"] for x in sel]
                c = {"n_candidates": len(sel)}
                for k in ("check_pp", "flips", "sensor_flips", "accuracy_drop"):
                    c["spearman_" + k] = spearman([x[k] for x in sel], t)
                lf = [x for x in sel if x["arm"] in LABEL_FREE]
                pick = min(lf, key=lambda x: x["check_pp"])
                best = min(lf, key=lambda x: x["true_pp"])
                c["label_free_pick"], c["label_free_best"] = pick["arm"], best["arm"]
                c["label_free_regret_pp"] = pick["true_pp"] - best["true_pp"]
                over = np.array([x["check_pp"] - x["true_pp"] for x in sel])
                c["check_above_true"] = int((over > 0).sum())
                c["overestimate_pp"] = {"mean": float(over.mean()), "min": float(over.min()), "max": float(over.max())}
                ok = tot = 0
                for i in range(len(sel)):
                    for j in range(i + 1, len(sel)):
                        dt = sel[i]["true_pp"] - sel[j]["true_pp"]
                        if abs(dt) > 0.5:
                            tot += 1
                            ok += (dt * (sel[i]["check_pp"] - sel[j]["check_pp"]) > 0)
                c["pairs_ordered"] = [ok, tot]
                # episode bootstrap of the check's rank correlation
                kg, kr = "%s_%s_gold_default" % (st, lev), "%s_%s_referee_default" % (st, lev)
                ne = len(raw[kg]["n"])
                bs = []
                for _ in range(2000):
                    idx = rng.integers(0, ne, ne)
                    tpb, _ = pens(kg, idx)
                    rpb, _ = pens(kr, idx)
                    arms_c = cand_arms(T)
                    bs.append(spearman([rpb[x] for x in arms_c], [tpb[x] for x in arms_c]))
                c["check_spearman_bootstrap95"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
                # true penalties of the label-free options and the 1,000-label retrain, with 95% episode-bootstrap intervals (D1)
                tps = {}
                for arm in ["%s|%s" % (T, x) for x in LABEL_FREE + ("ret1000",)] + ["tfidf", "rule"]:
                    tb = []
                    for _ in range(1000):
                        idx = rng.integers(0, ne, ne)
                        tpb, _ = pens(kg, idx)
                        tb.append(tpb[arm])
                    tps[arm.split("|")[-1]] = [pens(kg)[0][arm], float(np.percentile(tb, 2.5)), float(np.percentile(tb, 97.5))]
                c["true_penalty_ci"] = tps
                c["fp16_missed_share"] = pens(kg)[1]
                conds["%s %s %s" % (T, st, lev)] = c
    H = {}
    H["H1"] = {"rule": "check Spearman >= %.2f in every condition" % RHO_MIN, "values": {k: c["spearman_check_pp"] for k, c in conds.items()}}
    H["H1"]["holds"] = all(v >= RHO_MIN for v in H["H1"]["values"].values())
    H["H2"] = {"rule": "check Spearman > flips Spearman in every condition",
               "values": {k: [c["spearman_check_pp"], c["spearman_flips"]] for k, c in conds.items()}}
    H["H2"]["holds"] = all(v[0] > v[1] for v in H["H2"]["values"].values())
    H["H3"] = {"rule": "label-free option chosen by the check within %.2f pp of the best label-free option in every condition" % REGRET_MAX_PP,
               "values": {k: [c["label_free_pick"], c["label_free_best"], c["label_free_regret_pp"]] for k, c in conds.items()}}
    H["H3"]["holds"] = all(v[2] <= REGRET_MAX_PP + 1e-12 for v in H["H3"]["values"].values())
    above = sum(c["check_above_true"] for c in conds.values())
    total = sum(c["n_candidates"] for c in conds.values())
    H["H4"] = {"rule": "check penalty above the true penalty in at least %d%% of candidate-condition pairs" % int(100 * CONSERVATIVE_SHARE),
               "values": [above, total, above / total]}
    H["H4"]["holds"] = above / total >= CONSERVATIVE_SHARE
    ms = {}
    for T in targets:
        for k in MISSPEC:
            sel = [x for x in misspec_rows if x["target"] == T and x["sim"] == k]
            ms["%s %s" % (T, k)] = {"check_default_vs_true_perturbed": spearman([x["check_default_pp"] for x in sel], [x["true_pp"] for x in sel]),
                                    "check_same_sim_vs_true": spearman([x["check_same_sim_pp"] for x in sel], [x["true_pp"] for x in sel])}
    H["H5"] = {"rule": "secondary: check from the default simulator vs true penalty in each perturbed simulator, Spearman >= %.2f" % RHO_MIN_MISSPEC,
               "values": ms}
    H["H5"]["holds"] = all(v["check_default_vs_true_perturbed"] >= RHO_MIN_MISSPEC for v in ms.values())
    H["confirmed_H1_to_H4"] = all(H[h]["holds"] for h in ("H1", "H2", "H3", "H4"))

    # unlabeled report budget (D2): the check on k random episodes of the first set against the true penalties on all episodes
    budget = {}
    st0 = list(sets)[0]
    for T in targets:
        for lev in LEVELS:
            kg, kr = "%s_%s_gold_default" % (st0, lev), "%s_%s_referee_default" % (st0, lev)
            tp_full, _ = pens(kg)
            ne = len(raw[kr]["n"])
            arms_c = cand_arms(T)
            lf_arms = ["%s|%s" % (T, x) for x in LABEL_FREE]
            best_lf = min(tp_full[x] for x in lf_arms)
            for k in (10, 25, 50):
                if k >= ne:
                    continue
                rs, reg_ = [], []
                for _ in range(1000):
                    idx = rng.choice(ne, k, replace=False)
                    rpb, _ = pens(kr, idx)
                    rs.append(spearman([rpb[x] for x in arms_c], [tp_full[x] for x in arms_c]))
                    reg_.append(tp_full[min(lf_arms, key=lambda x: rpb[x])] - best_lf)
                budget["%s %s k%d" % (T, lev, k)] = {"median": float(np.median(rs)), "p05": float(np.percentile(rs, 5)),
                                                     "label_free_regret_le_025": float(np.mean(np.array(reg_) <= REGRET_MAX_PP + 1e-12))}

    res = {"protocol": "PROTOCOL_CHECK_CONFIRM.md", "log": log, "seed": SEED, "candidates_per_target": cand_names + ["tfidf", "rule"],
           "label_free_options": list(LABEL_FREE), "misspecified_simulators": list(MISSPEC), "hypotheses": H, "conditions": conds,
           "unlabeled_budget": budget, "rows": rows, "misspec_rows": misspec_rows, "sanity_registered": sanity,
           "runtime_s": round(time.time() - t_all, 1)}
    (out / "check_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (out / "check_episodes.json").write_text(json.dumps({"seed": SEED, "tasks": raw}), encoding="utf-8")
    for h in ("H1", "H2", "H3", "H4", "H5"):
        print("%s %s: %s" % (h, "HOLDS" if H[h]["holds"] else "FAILS", H[h]["rule"]), flush=True)
    print("confirmed (H1-H4): %s; done in %.0f s" % (H["confirmed_H1_to_H4"], res["runtime_s"]), flush=True)


if __name__ == "__main__":
    main()
