"""
The development set with saved vectors: for each outer fold k, the CAL reports and the EVAL reports with the probabilities of every arm's readout.

    ds = DevSet()                       # reads results/cache/readout_probs.npz (build it with tools/build_readout_cache.py)
    ds.probs(k, "q4", i)  -> (pa, ps, pp) for report i in fold k (CAL or EVAL role)
    ds.cands(k, "q4", i)  -> merged candidate list for that report
    ds.enum[i]            -> Enumerator of report i (what each combination assembles to)
"""
import numpy as np

from . import paths
from .calibrate import conformal_q, label_score
from .candidates import Enumerator, conformal_set, pilot
from .data import N_FOLDS, DevData
from .readout import load_cache

ARMS = ("q4", "f16", "q8", "rec", "raw")


class DevSet:
    def __init__(self, cache=None):
        self.D = DevData()
        cache = cache or (paths.RESULTS / "cache" / "readout_probs.npz")
        self.folds, self.fit_log = load_cache(cache)
        self.cases = self.D.cases
        self.enum = {int(i): Enumerator(self.cases[i]) for i in self.D.A}
        pc = pilot()[0]
        # labels live here (analysis side), never in the runtime objects: calibration and scoring use them, policies do not see them
        self.label_norm = {int(i): pc.gold_norm(self.cases[i]) for i in self.D.A}
        self.label_key = {i: pc.strict_key(n) for i, n in self.label_norm.items()}
        self._pos = {}
        for k, f in self.folds.items():
            rows = np.concatenate([f["cal"], f["eval"]])
            self._pos[k] = {int(i): r for r, i in enumerate(rows)}
        self._cand_cache = {}

    def probs(self, k, arm, i):
        r = self._pos[k][int(i)]
        P = self.folds[k]["P"][arm]
        return P["action"][r], P["sensor"][r], P["prio"][r]

    def cands(self, k, arm, i):
        key = (k, arm, int(i))
        if key not in self._cand_cache:
            self._cand_cache[key] = self.enum[int(i)].candidates(*self.probs(k, arm, i))
        return self._cand_cache[key]

    def hier(self, k, arm, i):
        return self.enum[int(i)].hier_norm(*self.probs(k, arm, i))

    def make_episodes(self, idx, level, seed, R, gap=None):
        """Development: random partition of the reports into episodes of R (the overlay design)."""
        from .episodes import make_episodes
        return make_episodes(self, idx, level, seed, R, gap)

    def label_scores(self, k, arm, idx):
        return [label_score(self.cands(k, arm, i), self.label_key[int(i)]) for i in idx]

    def q_hat(self, k, arm, alpha):
        """Conformal threshold for outer fold k from its CAL reports only."""
        return conformal_q(self.label_scores(k, arm, self.folds[k]["cal"]), alpha)

    def conformal(self, k, arm, i, q):
        return conformal_set(self.cands(k, arm, i), q)


def build_service(ds, k, arm):
    """The runtime view of arm `arm`'s readout for the CAL and EVAL reports of outer fold k (no labels)."""
    from .service import Service, pilot_confidence
    pc = pilot()[0]
    cands, hier, conf = {}, {}, {}
    f = ds.folds[k]
    for i in list(f["cal"]) + list(f["eval"]):
        i = int(i)
        rid = ds.cases[i]["id"]
        cs = ds.cands(k, arm, i)
        cands[rid] = cs
        h = ds.hier(k, arm, i)
        hk = pc.strict_key(h)
        hier[rid] = next(c for c in cs if c["key"] == hk)
        pa, ps, pp = ds.probs(k, arm, i)
        conf[rid] = pilot_confidence(pa, ps, pp, h["action"])
    return Service(cands, hier, conf)
