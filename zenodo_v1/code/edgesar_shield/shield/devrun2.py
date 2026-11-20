"""
Iteration-1 runner (docs/ITERATION1_PROTOCOL.md).  Same episodes, same thresholds rules, same simulator as devrun.run_fold; the old arms are
built by the same code path, the new arms (B1-B4, G1) are added.  Does not touch devrun.py (the Windows-safe version of that file stays as it is).

The process pool works on Linux (fork) and Windows (spawn): every worker receives the dataset through an initializer.
"""
import multiprocessing
import time

import numpy as np

from .alloc import make_allocator
from .devrun import compact, eval_set_facts
from .devset import ARMS, build_service
from .episodes import EPISODE_REPORTS
from .oracle import ListGate, wrong_table_ids
from .policy import CommitPolicy, RiskGate, ShieldPolicy, rate_threshold
from .policy2 import GateFB, ObserverV2, ShieldV2
from .sim import Sim, SimConfig

ARM_ORDER2 = ["A0", "A1", "A2", "A3", "A4", "A5", "A6", "A8", "A8c", "A10", "A12", "B1", "B2", "B3", "B4", "G1"]
ARM_TEXT2 = {
    "B1": "Shield + strict candidate check (full cover)", "B2": "B1 + mass guard (full cover)",
    "B3": "Shield-2 = B2 + cost-aware fallback", "B4": "B1 + cost-aware fallback (no mass guard)",
    "G1": "Confidence gate with the same fallback and the same cap (equal footing)",
}


def run_fold_v2(ds, k, level, alpha=0.10, K=8, b=0.10, seed=1, R=EPISODE_REPORTS, allocator="cbba_bounded", cfg=None, arms=None, gap=None,
                max_episodes=None, readout="q4", shard=None, only_episodes=None, keep=None, wrap=None):
    cfg = cfg or SimConfig()
    cfg = SimConfig(**{**cfg.__dict__, "budget_fraction": b})
    arms = arms or (ARM_ORDER2 + ["OBS"])
    sim = Sim(make_allocator(allocator), cfg)
    f = ds.folds[k]
    svc = {a: build_service(ds, k, a) for a in ARMS}
    base = svc[readout]
    q = ds.q_hat(k, readout, alpha)
    obs = ObserverV2(base, q, K, alpha)
    for e in ds.make_episodes(f["cal"], level, seed * 1000 + 100 + k, R, gap):
        sim.run(e, obs, "observer")
    th = {}
    for name in ("conf", "topscore", "a8", "s1", "s2"):
        th[name] = rate_threshold([r[name] for r in obs.rows], b)
    p_flag = float(np.mean([r["s2_flag"] for r in obs.rows]))
    th["gfb"] = rate_threshold([r["conf"] for r in obs.rows], p_flag)             # G1: flags as many reports as B3 flags on CAL
    info = {"fold": k, "level": level, "seed": seed, "readout": readout, "q_hat": q, "n_cal_reports": len(obs.rows),
            "eval_set": eval_set_facts(ds, k, readout, q, K, f["eval"]),
            "cal_flag_rate_s1": float(np.mean([r["s1_flag"] for r in obs.rows])), "cal_flag_rate_s2": p_flag,
            "cal_flag_rate_a8": float(np.mean([not r["a8_cert"] for r in obs.rows])),
            "cal_s2_reasons": {s: int(c) for s, c in zip(*np.unique([r["s2_reason"] or "CERTIFIED" for r in obs.rows], return_counts=True))},
            "thresholds": {n: (None if t[0] is None else list(t[0]), float(t[1])) for n, t in th.items()}}
    pol = {
        "A1": CommitPolicy(base), "A2": CommitPolicy(svc["f16"]), "A3": CommitPolicy(svc["q8"]), "A4": CommitPolicy(svc["rec"]),
        "A5": CommitPolicy(svc["raw"]),
        "A6": RiskGate(base, "conf", *th["conf"], seed=seed),
        "A8": ShieldPolicy(base, q, K, "shield", True, *th["a8"], seed=seed),
        "A8c": ShieldPolicy(base, q, K, "shield", True, *th["a8"], seed=seed, cover_kw={"camera": "rhat", "priority": "rhat"}),
        "A10": ShieldPolicy(base, q, K, "shield", False, *th["a8"], seed=seed),
        "B1": ShieldV2(base, q, K, *th["s1"], seed=seed, alpha=alpha, mass_guard=False, cost_aware=False),
        "B2": ShieldV2(base, q, K, *th["s2"], seed=seed, alpha=alpha, mass_guard=True, cost_aware=False),
        "B3": ShieldV2(base, q, K, *th["s2"], seed=seed, alpha=alpha, mass_guard=True, cost_aware=True),
        "B4": ShieldV2(base, q, K, *th["s1"], seed=seed, alpha=alpha, mass_guard=False, cost_aware=True),
        "G1": GateFB(base, q, K, *th["conf"], *th["gfb"], seed=seed),
    }
    if "A12" in arms:
        pol["A12"] = ListGate(base, wrong_table_ids(ds, base, f["eval"]))
    out = []
    episodes = ds.make_episodes(f["eval"], level, seed * 1000 + k, R, gap)
    if max_episodes:
        episodes = episodes[:max_episodes]
    if shard:
        episodes = episodes[shard[0]::shard[1]]
    if only_episodes is not None:
        episodes = [e for e in episodes if e.id in only_episodes]
    for e in episodes:
        for a in arms:
            if a == "OBS":
                o = ObserverV2(base, q, K, alpha)
                res = sim.run(e, o, "OBS")
                out.append(compact(res, k, level, seed, o.rows))
                continue
            p = pol.get(a)
            if wrap is not None and p is not None:
                p = wrap(a, p)
            res = sim.run(e, p, a, oracle=(a == "A0"))
            if keep is not None:
                keep[(e.id, a)] = res
            out.append(compact(res, k, level, seed))
    return out, info


# ---------------------------------------------------------------------------------------------------------------------
# parallel running that works with fork (Linux) and spawn (Windows)
# ---------------------------------------------------------------------------------------------------------------------
_G = {}


def _init(ds):
    _G["ds"] = ds


def _job(args):
    k, kw = args
    t0 = time.time()
    kw = dict(kw)
    if kw.get("shard") is None:
        kw.pop("shard", None)
    recs, info = run_fold_v2(_G["ds"], k, **kw)
    info["seconds"] = round(time.time() - t0, 1)
    return recs, info


def run_level_v2(ds, level, folds=None, processes=2, shards=1, method=None, **kw):
    folds = list(folds if folds is not None else sorted(ds.folds))
    jobs = [(k, dict(kw, level=level, shard=((j, shards) if shards > 1 else None))) for k in folds for j in range(shards)]
    _init(ds)
    if processes > 1 and len(jobs) > 1:
        m = method or ("fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn")
        with multiprocessing.get_context(m).Pool(processes, initializer=_init, initargs=(ds,)) as pool:
            outs = pool.map(_job, jobs, chunksize=1)
    else:
        outs = [_job(j) for j in jobs]
    records, infos = [], []
    for n, (recs, info) in enumerate(outs):
        records.extend(recs)
        if shards == 1 or n % shards == 0:
            infos.append(dict(info, shards=shards))
        else:
            infos[-1]["seconds"] = round(infos[-1]["seconds"] + info["seconds"], 1)
    if shards > 1:
        order = {a: i for i, a in enumerate(ARM_ORDER2 + ["OBS"])}
        records.sort(key=lambda r: (r["episode"], order.get(r["arm"], 99)))
    return records, infos
