"""
EdgeSAR fresh confirmation (PROTOCOL_FRESH_CONFIRM.md). One script, two modes.

  check mode (run BEFORE any fresh data exists; no new model output):
      python fresh_confirm.py --root <ROOT> --mode check --supp <supplement folder> --out out_check
      Rebuilds the style-B check of 14 Nov with THIS code: records must equal the saved protocol-B predictions and the mission counts must
      equal the saved wording-shift results. If not, the fresh run is not allowed.

  fresh mode (run ONCE, after the protocol is hashed and the fresh vectors exist):
      python fresh_confirm.py --root <ROOT> --mode fresh --cases fresh/cases_fresh.jsonl --vectors fresh/vectors --out out_fresh

ROOT holds edgesar_pilot, edgesar_heads (with the saved development vectors), V1, edgesar_audit_2026-11-13, edgesar_shield, and
repair_package (ppr_lib.py, run_ppr.py from the supplement). Everything is fitted on the 1,000 development style-A reports only.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent

PRIMARY_LEVEL = "M"
LEVELS = ("L", "M", "H")
FRESH_SEEDS = (11, 12, 13)          # arrival seeds; seed 11 is the primary analysis (one use of every fresh report per level)
DRAWS = 5                           # independent label-subset draws for each scarce-label arm
BUDGETS = (100, 300)
N_BOOT = 10000
MARGINS = (0.0025, 0.005)           # non-inferiority margins (0.25 and 0.5 percentage points), secondary


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


# ------------------------------------------------------------------ statistics (same arithmetic as shield.devrun.paired)
def paired_arrays(mx, my, nn, n_boot=N_BOOT, seed=7):
    mx, my, nn = (np.asarray(v, dtype=float) for v in (mx, my, nn))
    rng = np.random.RandomState(seed)
    E = len(nn)
    idx = rng.randint(0, E, size=(n_boot, E))
    diff = (mx[idx].sum(1) - my[idx].sum(1)) / nn[idx].sum(1)
    d = mx - my
    obs = d.sum()
    signs = rng.choice([-1.0, 1.0], size=(n_boot, E))
    perm = np.abs((signs * d).sum(1))
    p = (np.sum(perm >= abs(obs) - 1e-12) + 1) / (n_boot + 1)
    return {"diff": float((mx.sum() - my.sum()) / nn.sum()), "ci": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))],
            "p": float(p), "episodes": int(E), "first_better": int((d < 0).sum()), "first_worse": int((d > 0).sum()), "ties": int((d == 0).sum()),
            "sd_episode_diff": float(np.std(d, ddof=1)) if E > 1 else float("nan")}


def share_ci(m, n, n_boot=2000, seed=11):
    m, n = np.asarray(m, float), np.asarray(n, float)
    rng = np.random.RandomState(seed)
    idx = rng.randint(0, len(n), size=(n_boot, len(n)))
    u = m[idx].sum(1) / n[idx].sum(1)
    return float(m.sum() / n.sum()), float(np.percentile(u, 2.5)), float(np.percentile(u, 97.5))


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj = [0.0] * len(ps)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


_RUN = None


def _call(task):
    return _RUN(task)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--mode", choices=["check", "fresh"], required=True)
    ap.add_argument("--supp", default=None, help="check mode: the supplement folder with repair_package/out2/predictions.csv and practical_advantage/out_wording_shift")
    ap.add_argument("--cases", default=None)
    ap.add_argument("--vectors", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-episodes", type=int, default=None, help="code test only")
    a = ap.parse_args()
    t_all = time.time()
    root = Path(a.root).resolve()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    os.environ["EDGESAR_ROOT"] = str(root)
    sys.path.insert(0, str(root / "repair_package"))
    sys.path.insert(0, str(root / "edgesar_shield"))
    proto = HERE / "PROTOCOL_FRESH_CONFIRM.md"
    psha = sha(proto) if proto.exists() else None
    code_sha = sha(Path(__file__))
    if a.mode == "fresh":
        frozen = HERE / "FROZEN.sha256"
        if not frozen.exists():
            raise SystemExit("No FROZEN.sha256: the protocol was not frozen. Stop.")
        want = dict(l.split()[::-1] for l in frozen.read_text().splitlines() if l.strip())
        if want.get("PROTOCOL_FRESH_CONFIRM.md") != psha or want.get("fresh_confirm.py") != code_sha:
            raise SystemExit("The protocol or this script changed after freezing. Stop.")
        if (out / "results.json").exists():
            raise SystemExit("The fresh run was already done (%s exists). One run only." % (out / "results.json"))

    import run_ppr as R1                                                   # noqa: E402
    from ppr_lib import ACTIONS, HEADS, PRIOS, REC, SENSORS, AffineMap, Data, Recentre   # noqa: E402
    from shield import devrun, paths                                       # noqa: E402
    bad = paths.check_pins()
    if bad:
        raise SystemExit("pinned files differ: %s" % bad)
    from shield.alloc import make_allocator                                # noqa: E402
    from shield.episodes import EPISODE_REPORTS, make_episodes, make_fixed_episodes   # noqa: E402
    from shield.policy import CommitPolicy                                 # noqa: E402
    from shield.service import Service                                     # noqa: E402
    from shield.sim import Sim, SimConfig                                  # noqa: E402

    D = Data(root)
    R1.D = D
    pc, pb = D.pc, D.pb
    A = np.where(D.split == "dev")[0]
    B = np.where(D.split == "held")[0]
    seed0 = R1.SEED + 999                                                  # the seed of the style-B task in run_ppr2.py (protocol B)
    rows_all = {"action": A, "sensor": A[D.is_rec[A]], "prio": A[D.is_rec[A]]}
    X = D.X
    print("fitting on the %d development style-A reports" % len(A), flush=True)
    t0 = time.time()
    fit = {}
    for pos in ("prefix", "end"):
        F, Q = X[("f16", pos)], X[("Q4_K_M", pos)]
        fit[pos] = {"ref": R1.fit_heads(F, rows_all, seed0), "mat": R1.fit_heads(Q, rows_all, seed0),
                    "rec": Recentre(F[A], Q[A]), "aln": AffineMap(F[A], Q[A], D.template[A], seed0)}
    draws = {}
    Qp = X[("Q4_K_M", "prefix")]
    for n in BUDGETS:
        for d in range(DRAWS):
            sd = seed0 + 1000 * (d + 1)
            rng = np.random.default_rng(sd + 7)
            while True:
                lab = np.sort(rng.choice(A, size=n, replace=False))
                if len(set(D.y["action"][lab])) == 4:
                    break
            rows = {"action": lab, "sensor": lab[D.is_rec[lab]], "prio": lab[D.is_rec[lab]]}
            draws[(n, d)] = {"heads": R1.fit_heads(Qp, rows, sd), "ids": [D.cases[int(i)]["id"] for i in lab]}
    tfidf = pb.LRBaseline().fit([D.cases[int(i)] for i in A])
    fit_seconds = time.time() - t0
    print("fitted in %.0f s" % fit_seconds, flush=True)

    # ------------------------------------------------------------------ evaluation reports
    if a.mode == "check":
        ev_cases = [D.cases[int(i)] for i in B]
        EV = {(m, p): X[(m, p)][B] for m in ("f16", "Q4_K_M") for p in ("prefix", "end")}
        ev_info = {"set": "development style B (400 reports; inspected many times)"}
    else:
        ev_cases = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
        vd = Path(a.vectors)
        ids = json.loads((vd / "case_ids.json").read_text(encoding="utf-8"))
        if ids != [c["id"] for c in ev_cases]:
            raise SystemExit("case_ids.json does not list the fresh reports in order. Stop.")
        EV = {}
        for m in ("f16", "Q4_K_M"):
            for p in ("prefix", "end"):
                V = np.load(vd / ("%s_%s.npy" % (m, p))).astype(np.float64)
                if V.shape != (len(ev_cases), X[(m, p)].shape[1]) or not np.all(np.isfinite(V)):
                    raise SystemExit("bad fresh vectors %s_%s: shape %s" % (m, p, V.shape))
                EV[(m, p)] = V
        dev_texts = {c["text"] for c in D.cases}
        ev_info = {"set": "fresh", "cases_sha256": sha(a.cases), "reports": len(ev_cases),
                   "text_also_in_development": sum(c["text"] in dev_texts for c in ev_cases),
                   "styles": {s: sum(c["style"] == s for c in ev_cases) for s in sorted({c["style"] for c in ev_cases})},
                   "vectors_sha256": {f: sha(vd / f) for f in sorted(os.listdir(vd)) if f.endswith(".npy")}}

    def assemble(P, cases):
        recs = []
        for r, c in enumerate(cases):
            act = ACTIONS[int(P["action"][r].argmax())]
            s = SENSORS[int(P["sensor"][r].argmax())]
            p = PRIOS[int(P["prio"][r].argmax())]
            recs.append(pc.validate(pb._assemble(c, act, s, int(p)), c)[0])
        return recs

    def logits(heads, Xe):
        return {h: heads[h].logits(Xe) for h in HEADS}

    def gold_sensor(P, cases):
        P = {h: np.array(v, copy=True) for h, v in P.items()}
        for r, c in enumerate(cases):
            g = c["gold"]
            if g["action"] in REC and g.get("sensor") in SENSORS:
                P["sensor"][r] = -1e9
                P["sensor"][r, SENSORS.index(g["sensor"])] = 0.0
        return P

    recs = {}
    Pp = {}
    for pos, sfx in (("prefix", "p"), ("end", "")):
        f = fit[pos]
        Fe, Qe = EV[("f16", pos)], EV[("Q4_K_M", pos)]
        Pp["f16" + sfx] = logits(f["ref"], Fe)
        Pp["raw" + sfx] = logits(f["ref"], Qe)
        Pp["rec" + sfx] = logits(f["ref"], f["rec"](Qe))
        Pp["aln" + sfx] = logits(f["ref"], f["aln"](Qe))
        Pp["q4" + sfx] = logits(f["mat"], Qe)
    for (n, d), v in draws.items():
        Pp["q4p_n%d_d%d" % (n, d)] = logits(v["heads"], EV[("Q4_K_M", "prefix")])
    Pp["q4p_goldS"] = gold_sensor(Pp["q4p"], ev_cases)
    Pp["alnp_goldS"] = gold_sensor(Pp["alnp"], ev_cases)
    for arm, P in Pp.items():
        recs[arm] = assemble(P, ev_cases)
    recs["tfidf"] = [pc.validate(d_, c)[0] for c, d_ in zip(ev_cases, tfidf.predict(ev_cases))]
    recs["rule"] = [pc.validate(pb.rule_decision(c), c)[0] for c in ev_cases]
    gold_key = [pc.strict_key(pc.gold_norm(c)) for c in ev_cases]
    dev_texts = {c["text"] for c in D.cases}
    set_of = ["B" if a.mode == "check" else c["split"].split("_")[-1] for c in ev_cases]
    acc = {}
    for st in sorted(set(set_of)):
        for sub, keep in (("all", lambda c: True), ("text_not_in_development", lambda c: c["text"] not in dev_texts)):
            ix = [j for j, c in enumerate(ev_cases) if set_of[j] == st and keep(c)]
            acc["%s_%s" % (st, sub)] = {"n": len(ix), **{arm: float(np.mean([pc.strict_key(rs[j]) == gold_key[j] for j in ix])) for arm, rs in recs.items()}}

    res = {"mode": a.mode, "protocol_sha256": psha, "script_sha256": code_sha, "eval": ev_info, "fit_seconds": round(fit_seconds, 1),
           "label_draws": {"%d_d%d" % k: v["ids"] for k, v in draws.items()}, "accuracy": acc,
           "map_lambda": {pos: fit[pos]["aln"].c for pos in fit}}

    # ------------------------------------------------------------------ check mode: records must equal the saved protocol-B predictions
    if a.mode == "check":
        supp = Path(a.supp)
        saved = {}
        for d_, names in (("out2", {"REFp": "f16p", "FROZENp": "rawp", "C1p": "recp", "C2p": "alnp", "MATCHEDp": "q4p"}),
                          ("out", {"REF": "f16", "FROZEN": "raw", "C1": "rec", "C2": "aln", "MATCHED": "q4", "TFIDF": "tfidf", "RULES": "rule"})):
            with open(supp / "repair_package" / d_ / "predictions.csv", encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    if r["protocol"] == "B" and r["labels"] == "all" and r["arm"] in names:
                        k = tuple(None if r[c] == "" else (int(r[c]) if c == "priority" else r[c]) for c in ("action", "incident", "landmark", "sensor", "priority"))
                        saved.setdefault(names[r["arm"]], {})[r["case_id"]] = k
        same = {}
        for arm, d_ in saved.items():
            same[arm] = sum(pc.strict_key(r) == d_[c["id"]] for r, c in zip(recs[arm], ev_cases))
        res["check_records_equal_saved"] = same
        print("records equal to the saved protocol-B predictions (of 400):", same, flush=True)

    # ------------------------------------------------------------------ missions
    rid = [c["id"] for c in ev_cases]
    svc = {}
    for arm, rs in recs.items():
        cands, hier, conf = {}, {}, {}
        for i, nm in zip(rid, rs):
            c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
            cands[i], hier[i], conf[i] = [c], c, 1.0
        svc[arm] = Service(cands, hier, conf)
    sim = Sim(make_allocator("cbba_bounded"), SimConfig())
    ds = SimpleNamespace(cases=ev_cases)
    allidx = list(range(len(ev_cases)))
    seeds = (1, 2, 3) if a.mode == "check" else FRESH_SEEDS
    sets = ["B"] if a.mode == "check" else sorted({c["split"].split("_")[-1] for c in ev_cases})
    per = {}            # (set, level, seed) -> {arm: {episode: (missed, n, unverified)}}
    viol = chk = 0
    tasks = [(st, lev, s) for st in sets for lev in LEVELS for s in seeds]

    def run_task(task):
            st, lev, s = task
            t1 = time.time()
            if a.mode == "check":
                eps = make_episodes(ds, allidx, lev, s * 1000, EPISODE_REPORTS)
            else:
                eps = make_fixed_episodes(ds, [i for i in allidx if ev_cases[i]["split"] == "fresh_eval_" + st], lev, s)
            if a.max_episodes:
                eps = eps[:a.max_episodes]
            tab = {}
            srecs = []
            for e in eps:
                g = devrun.compact(sim.run(e, None, "gold", oracle=True), 0, lev, s)
                srecs.append(g)
                for arm in recs:
                    srecs.append(devrun.compact(sim.run(e, CommitPolicy(svc[arm]), arm), 0, lev, s))
            for r in srecs:
                cnt = r["counts"]
                tab.setdefault(r["arm"], {})[r["episode"]] = (cnt["late"] + cnt["unverified"], cnt["n"], cnt["unverified"])
            with gzip.open(out / ("records_%s_%s_s%d.json.gz" % (st, lev, s)), "wt", encoding="utf-8") as fh:
                json.dump(srecs, fh, separators=(",", ":"))
            # replay consistency: a report whose record equals gold must give the gold table and plan
            c_, v_ = 0, 0
            for r in srecs:
                if r["arm"] == "gold":
                    continue
                for rep in r["reports"]:
                    if key_of[r["arm"]][rep["id"]] == gk[rep["id"]]:
                        c_ += 1
                        v_ += not (rep["tg"] and rep["pg"])
            print("set %s level %s seed %d: %d episodes in %.0f s" % (st, lev, s, len(eps), time.time() - t1), flush=True)
            return task, tab, c_, v_

    key_of = {arm: {i: pc.strict_key(nm) for i, nm in zip(rid, rs)} for arm, rs in recs.items()}
    gk = dict(zip(rid, gold_key))
    global _RUN
    _RUN = run_task
    import multiprocessing as mp
    with mp.get_context("fork").Pool(min(len(tasks), max(1, (os.cpu_count() or 2) - 0))) as pool:
        for task, tab, c_, v_ in pool.imap_unordered(_call, tasks):
            per[task] = tab
            chk += c_
            viol += v_
    res["replay_consistency"] = {"reports_checked": chk, "violations": viol}

    def arm_arrays(tab, arm, eps):
        if arm in ("q4p_n100", "q4p_n300"):
            n = int(arm.split("_n")[1])
            M = np.array([[tab["q4p_n%d_d%d" % (n, d)][e][0] for e in eps] for d in range(DRAWS)], float)
            return M.mean(0)
        return np.array([tab[arm][e][0] for e in eps], float)

    arms_report = ["gold", "f16p", "rawp", "recp", "alnp", "q4p", "q4p_n100", "q4p_n300", "tfidf", "rule", "q4p_goldS", "alnp_goldS",
                   "f16", "raw", "rec", "aln", "q4"]
    comparisons = {
        "H1": ("rawp", "f16p"), "H2a": ("alnp", "rawp"), "H2b": ("q4p", "rawp"), "H3": ("alnp", "q4p_n100"),
        "S1": ("alnp", "q4p"), "S2": ("alnp", "q4p_n300"), "S3": ("alnp", "recp"), "S4": ("recp", "q4p_n100"), "S5": ("q4p", "f16p"),
        "S6": ("alnp", "f16p"), "S7": ("tfidf", "f16p"), "S8": ("tfidf", "alnp"), "S9": ("rule", "alnp"), "S10": ("q4p_goldS", "q4p"),
        "S11": ("alnp_goldS", "alnp"), "S12": ("raw", "f16"), "S13": ("aln", "q4"), "S14": ("q4p_n100", "q4p"), "S15": ("f16p", "gold")}
    res["levels"] = {}
    for (st, lev, s), tab in per.items():
        eps = sorted(tab["gold"])
        nn = np.array([tab["gold"][e][1] for e in eps], float)
        L = {"episodes": len(eps), "incidents": int(nn.sum()), "arms": {}, "comparisons": {}}
        for arm in arms_report:
            m = arm_arrays(tab, arm, eps)
            sh, lo, hi = share_ci(m, nn)
            L["arms"][arm] = {"missed": float(m.sum()), "share": sh, "ci": [lo, hi]}
        for name, (x, y) in comparisons.items():
            L["comparisons"][name] = {"x": x, "y": y, **paired_arrays(arm_arrays(tab, x, eps), arm_arrays(tab, y, eps), nn)}
        res["levels"]["%s_%s_s%d" % (st, lev, s)] = L
    # pooled over the three arrival seeds (secondary)
    for st, lev in [(st, lev) for st in sets for lev in LEVELS]:
        eps_all = []
        for s in seeds:
            eps_all += [(s, e) for e in sorted(per[(st, lev, s)]["gold"])]
        nn = np.array([per[(st, lev, s)]["gold"][e][1] for s, e in eps_all], float)

        def pooled(arm):
            return np.concatenate([arm_arrays(per[(st, lev, s)], arm, sorted(per[(st, lev, s)]["gold"])) for s in seeds])
        L = {"episodes": len(eps_all), "incidents": int(nn.sum()), "arms": {}, "comparisons": {}}
        for arm in arms_report:
            sh, lo, hi = share_ci(pooled(arm), nn)
            L["arms"][arm] = {"share": sh, "ci": [lo, hi]}
        for name, (x, y) in comparisons.items():
            L["comparisons"][name] = {"x": x, "y": y, **paired_arrays(pooled(x), pooled(y), nn)}
        res["levels"]["%s_%s_pooled" % (st, lev)] = L
    # primary family (fresh: style A, level M, arrival seed 11; check: style B, level M pooled) with Holm
    key = "A_M_s%d" % seeds[0] if a.mode == "fresh" else "B_M_pooled"
    prim = res["levels"][key]["comparisons"]
    fam = ["H1", "H2a", "H2b", "H3"]
    adj = holm([prim[h]["p"] for h in fam])
    want_sign = {"H1": +1, "H2a": -1, "H2b": -1, "H3": -1}
    res["primary"] = {"analysis": key, "tests": {}}
    for h, p_adj in zip(fam, adj):
        c = prim[h]
        ok_dir = (c["ci"][0] > 0) if want_sign[h] > 0 else (c["ci"][1] < 0)
        res["primary"]["tests"][h] = {**c, "p_holm": p_adj, "confirmed": bool(ok_dir and p_adj < 0.05)}
    s1 = prim["S1"]
    res["primary"]["noninferiority_map_vs_retrain_all"] = {"margin_0.25pp": bool(s1["ci"][1] < 0.0025), "margin_0.5pp": bool(s1["ci"][1] < 0.005)}
    if a.mode == "check":                                                  # mission counts must equal the saved wording-shift results
        saved = json.loads((Path(a.supp) / "practical_advantage" / "out_wording_shift" / "results.json").read_text(encoding="utf-8"))["levels"]
        cmp = {}
        for lev in LEVELS:
            for arm in ("gold", "f16p", "q4p", "recp", "alnp", "rawp", "tfidf", "rule", "f16", "q4", "rec", "aln", "raw"):
                here = res["levels"]["B_%s_pooled" % lev]["arms"][arm]["share"]
                there = saved[lev]["arms"][arm]["share"]
                cmp["%s_%s" % (lev, arm)] = [round(100 * here, 3), round(100 * there, 3), abs(here - there) < 1e-12]
        res["check_mission_equal_saved"] = cmp
        res["check_all_equal"] = all(v[2] for v in cmp.values()) and all(v == 400 for v in res["check_records_equal_saved"].values())
    res["total_seconds"] = round(time.time() - t_all, 1)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    write_md(res, out, a.mode)
    print((out / "RESULTS.md").read_text(encoding="utf-8"))


NAMES = {"gold": "Gold records (reference)", "f16p": "FP16 reader", "rawp": "Q4, FP16 reader unchanged", "recp": "Q4, recentred",
         "alnp": "Q4, label-free map", "q4p": "Q4, retrained (1,000 labels)", "q4p_n100": "Q4, retrained (100 labels; mean of 5 draws)",
         "q4p_n300": "Q4, retrained (300 labels; mean of 5 draws)", "tfidf": "TF-IDF + LR (text)", "rule": "Keyword rules (text)",
         "q4p_goldS": "Q4 retrained, gold sensor", "alnp_goldS": "Q4 map, gold sensor", "f16": "FP16 reader (end)", "raw": "Q4 unchanged (end)",
         "rec": "Q4 recentred (end)", "aln": "Q4 map (end)", "q4": "Q4 retrained (end)"}


def write_md(res, out, mode):
    md = ["# EdgeSAR fresh confirmation: results (%s mode)" % mode, "",
          "Protocol SHA-256 `%s`; script SHA-256 `%s`." % (res["protocol_sha256"], res["script_sha256"]), "",
          "Evaluation set: `%s`" % json.dumps(res["eval"])[:600], ""]
    if "check_records_equal_saved" in res:
        md += ["Records equal to the saved protocol-B predictions (of 400): %s" % res["check_records_equal_saved"], "",
               "Mission shares equal to the saved wording-shift results (here, saved, equal): %s" % res["check_mission_equal_saved"], "",
               "**ALL CHECKS EQUAL: %s**" % res["check_all_equal"], ""]
    md += ["Replay consistency: %s" % res["replay_consistency"], "", "## Primary family (%s), Holm-adjusted" % res["primary"]["analysis"], "",
           "| Test | First minus second | Difference (pp) | 95% CI | p | p (Holm) | Confirmed |", "|---|---|---|---|---|---|---|"]
    for h, c in res["primary"]["tests"].items():
        md.append("| %s | %s minus %s | %+.2f | %+.2f to %+.2f | %.4f | %.4f | %s |" % (h, c["x"], c["y"], 100 * c["diff"], 100 * c["ci"][0], 100 * c["ci"][1],
                                                                       c["p"], c["p_holm"], "YES" if c["confirmed"] else "no"))
    md += ["", "Non-inferiority of the map against retraining with 1,000 labels (upper bound below the margin): %s" % res["primary"]["noninferiority_map_vs_retrain_all"], ""]
    for key, L in res["levels"].items():
        md += ["## %s (%d episodes, %d incidents)" % (key, L["episodes"], L["incidents"]), "", "| Arm | Missed share | 95% CI | Whole record right |", "|---|---|---|---|"]
        st_ = key.split("_")[0]
        for arm, v in L["arms"].items():
            accs = res["accuracy"].get("%s_all" % st_, {}).get(arm)
            md.append("| %s | %.2f%% | %.2f to %.2f | %s |" % (NAMES.get(arm, arm), 100 * v["share"], 100 * v["ci"][0], 100 * v["ci"][1],
                                                        "-" if accs is None else "%.1f%%" % (100 * accs)))
        md += ["", "| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |", "|---|---|---|---|---|"]
        for name, c in L["comparisons"].items():
            md.append("| %s: %s minus %s | %+.2f | %+.2f to %+.2f | %.4f | %d / %d / %d |" % (name, c["x"], c["y"], 100 * c["diff"], 100 * c["ci"][0], 100 * c["ci"][1],
                                                                                    c["p"], c["first_better"], c["first_worse"], c["ties"]))
        md.append("")
    md.append("Total run time %.0f s." % res["total_seconds"])
    (out / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
