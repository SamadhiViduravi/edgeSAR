"""
The FRESH set: the same interface as DevSet (so the same runner and the same policies run on it), but

    FIT  = all 1,000 development style-A reports with their saved vectors   (the heads are fitted ONCE here)
    CAL  = fresh reports with role fresh_cal    (conformal threshold, gate thresholds)
    EVAL = fresh reports with role fresh_eval   (every reported number)

and one "fold" (k = 0).  The fresh vectors come from tools/extract_fresh_vectors.py (GPU) and are never used for fitting.

`FreshSet.from_dev_fold(D, k)` builds the same object from a DEVELOPMENT fold (FIT / CAL / EVAL of fold k) so the whole path can be tested without
fresh vectors: its probabilities must equal the cached development ones.
"""
import json
from pathlib import Path

import numpy as np

from . import paths
from .candidates import Enumerator, pilot
from .data import DevData
from .devset import DevSet
from .readout import FitLog, Heads

PREC = ("f16", "Q8_0", "Q4_K_M")
STYLE_B_SEED = 20261114                     # fixed partition of the 400 style-B reports into 20 episodes of 20 (exploratory shift check)


class FreshSet(DevSet):
    def __init__(self, fit_cases, fit_X, fit_groups, cases, X):
        self.D = None
        self.cases = cases
        cal = np.array([i for i, c in enumerate(cases) if c["split"] == "fresh_cal"])
        ev = np.array([i for i, c in enumerate(cases) if c["split"] == "fresh_eval"])
        if len(cal) == 0 or len(ev) == 0:
            raise ValueError("the fresh set needs reports with split fresh_cal and fresh_eval")
        for m in PREC:
            if X[m].shape[0] != len(cases):
                raise ValueError("vector count mismatch for %s" % m)
        log = FitLog()
        idx = np.arange(len(fit_cases))
        heads = {m: Heads(fit_cases, fit_X[m], idx, fit_groups, log) for m in PREC}
        delta = (fit_X["Q4_K_M"] - fit_X["f16"]).mean(axis=0)                 # label-free shift, FIT reports only
        rows = np.concatenate([cal, ev])
        P = {"q4": heads["Q4_K_M"].proba(X["Q4_K_M"][rows]), "f16": heads["f16"].proba(X["f16"][rows]), "q8": heads["Q8_0"].proba(X["Q8_0"][rows]),
             "rec": heads["f16"].proba(X["Q4_K_M"][rows] - delta), "raw": heads["f16"].proba(X["Q4_K_M"][rows])}
        self.folds = {0: {"fit": None, "cal": cal, "eval": ev, "P": P, "delta_norm": float(np.linalg.norm(delta))}}
        self.fit_log = log.as_dict()
        self.n_fit = len(fit_cases)
        self._pos = {0: {int(i): r for r, i in enumerate(rows)}}
        self.enum = {int(i): Enumerator(cases[int(i)]) for i in rows}
        pc = pilot()[0]
        self.label_norm = {int(i): pc.gold_norm(cases[int(i)]) for i in rows}
        self.label_key = {i: pc.strict_key(n) for i, n in self.label_norm.items()}
        self._cand_cache = {}

    # ---- episodes: membership was fixed when the reports were generated
    def make_episodes(self, idx, level, seed, R=None, gap=None):
        from .episodes import make_fixed_episodes
        return make_fixed_episodes(self, idx, level, seed, gap)

    # ---- constructors
    @classmethod
    def from_files(cls, cases_path, vectors_dir, eval_set="fresh"):
        """Real fresh data: cases_fresh.jsonl and <vectors_dir>/<model>_end.npy (+ case_ids.json) from the GPU step.
        eval_set = "fresh"   EVAL = the fresh evaluation episodes (confirmation)
                   "style_b" EXPLORATORY style-shift check: EVAL = the 400 style-B development reports (saved vectors) in 20 fixed episodes; the heads and the
                             conformal threshold are still the style-A ones (FIT = the 1,000 development style-A reports, CAL = the fresh calibration episodes)."""
        D = DevData()
        cases = [json.loads(l) for l in open(cases_path, encoding="utf-8") if l.strip()]
        vd = Path(vectors_dir)
        ids = json.loads((vd / "case_ids.json").read_text())
        if ids != [c["id"] for c in cases]:
            raise SystemExit("case_ids.json does not list the reports of the cases file, in the same order. Stop.")
        X = {m: np.load(vd / ("%s_end.npy" % m)).astype(np.float64) for m in PREC}
        for m in PREC:
            if not np.all(np.isfinite(X[m])):
                raise SystemExit("%s vectors contain NaN. Stop." % m)
            if X[m].shape[1] != D.X[m].shape[1]:
                raise SystemExit("%s vector length %d differs from the development vectors (%d). Stop." % (m, X[m].shape[1], D.X[m].shape[1]))
        A = D.A
        if eval_set == "style_b":
            cal = [i for i, c in enumerate(cases) if c["split"] == "fresh_cal"]
            perm = np.random.RandomState(STYLE_B_SEED).permutation(len(D.B))
            sb = [int(D.B[int(p)]) for p in perm]
            cases2 = [cases[i] for i in cal]
            for j, i in enumerate(sb):
                c = dict(D.cases[i])
                c["split"], c["episode"], c["pos"] = "fresh_eval", "SB%02d" % (j // 20), j % 20
                cases2.append(c)
            X = {m: np.concatenate([X[m][cal], D.X[m][sb]]) for m in PREC}
            cases = cases2
        elif eval_set != "fresh":
            raise ValueError(eval_set)
        return cls([D.cases[i] for i in A], {m: D.X[m][A] for m in PREC}, [D.group[i] for i in A], cases, X)

    @classmethod
    def from_dev_fold(cls, D, k):
        """SELF-TEST ONLY: a development fold dressed as a fresh set (same FIT, CAL, EVAL as the cached development run of fold k)."""
        fit, cal, ev = D.split(k)
        rows = list(cal) + list(ev)
        cases = []
        for j, i in enumerate(rows):
            c = dict(D.cases[int(i)])
            c["split"] = "fresh_cal" if j < len(cal) else "fresh_eval"
            c["episode"] = "X%03d" % (j // 20)
            c["pos"] = j % 20
            cases.append(c)
        return cls([D.cases[int(i)] for i in fit], {m: D.X[m][fit] for m in PREC}, [D.group[int(i)] for i in fit], cases,
                   {m: D.X[m][rows] for m in PREC})
