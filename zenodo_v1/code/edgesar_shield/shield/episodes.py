"""
Overlay episodes from the saved reports (development with saved vectors).

An episode is R independent pilot reports that arrive over time and SHARE the fleet.  Each report keeps its own namespace (its own open table
and its own incidents); its clock starts when it arrives; the reports compete only for UAV time.  Gaps between arrivals are exponential with a
mean that defines the contention level (L, M, H).  The gaps are tuned on the development set so that the gold-record policy misses about
1% / 5% / 15% of incidents by their deadline (plan section 5: M = 3-8%, H = 10-20%).

This replaces the plan's state-conditioned fresh episodes only for development (no GPU vectors exist for those yet); see docs/DEVIATIONS.md.
"""
import numpy as np

from .candidates import pilot
from .sim import Episode, ReportEvent

# mean gap between reports (seconds) for each level; set by tools/tune_levels.py on the development set and frozen in the evaluation plan
LEVEL_GAP_S = {"L": 60.0, "M": 30.0, "H": 8.0}
EPISODE_REPORTS = 20


def make_episodes(ds, idx, level, seed, R=EPISODE_REPORTS, gap=None):
    """Random partition of the report indices `idx` into episodes of R reports with exponential gaps. Deterministic for a given seed."""
    pc = pilot()[0]
    rng = np.random.RandomState(seed)
    order = list(rng.permutation(np.array(sorted(int(i) for i in idx))))
    g = LEVEL_GAP_S[level] if gap is None else gap
    episodes = []
    for e in range(len(order) // R):
        chunk = order[e * R:(e + 1) * R]
        t, evs = 0.0, []
        for j, i in enumerate(chunk):
            if j > 0:
                t += float(rng.exponential(g))
            c = ds.cases[int(i)]
            evs.append(ReportEvent(round(t, 3), c["id"], c["id"], [dict(r) for r in c["open"]], pc.gold_norm(c)))
        episodes.append(Episode("%s-s%d-e%02d" % (level, seed, e), evs, level))
    return episodes


def make_fixed_episodes(ds, idx, level, seed, gap=None):
    """Episodes whose members were fixed when the reports were generated (case["episode"], ordered by case["pos"]).  Only the arrival gaps are drawn,
    per episode, from the seed and the episode id, so an episode's arrival times do not depend on how many other episodes there are."""
    import hashlib
    g = LEVEL_GAP_S[level] if gap is None else gap
    pc = pilot()[0]
    by = {}
    for i in idx:
        by.setdefault(ds.cases[int(i)]["episode"], []).append(int(i))
    episodes = []
    for ep in sorted(by):
        members = sorted(by[ep], key=lambda i: ds.cases[i]["pos"])
        rng = np.random.RandomState((int(hashlib.sha256(("%s|%s" % (seed, ep)).encode()).hexdigest()[:8], 16)) % (2 ** 31))
        t, evs = 0.0, []
        for j, i in enumerate(members):
            if j > 0:
                t += float(rng.exponential(g))
            c = ds.cases[i]
            evs.append(ReportEvent(round(t, 3), c["id"], c["id"], [dict(r) for r in c["open"]], pc.gold_norm(c)))
        episodes.append(Episode("%s-s%d-%s" % (level, seed, ep), evs, level))
    return episodes
