"""
The readout: three small heads (action 4, sensor 3, priority 3) on the saved last-token vector, trained the way the pilot trained them
(standardise -> logistic regression, C chosen by grouped cross-validation INSIDE the training reports), with the audit's fix:
solver tolerance 1e-6 instead of 1e-3, and a larger iteration limit. Non-converged fits are counted and reported.

Nothing here reads the hidden truth: a head sees a vector and a training label. At run time only the probabilities are used.

Arms that need their own probabilities (per outer fold, for the CAL and EVAL reports):
    q4   Q4 vectors, Q4-fitted heads          (A1, A6-A11)
    f16  FP16 vectors, FP16-fitted heads      (A2)
    q8   Q8 vectors, Q8-fitted heads          (A3)
    rec  Q4 vectors minus the mean shift (Q4 - FP16, mean over FIT reports, no labels), FP16-fitted heads    (A4)
    raw  Q4 vectors as they are, FP16-fitted heads    (A5, DIAGNOSTIC ONLY)
"""
import json
import time
import warnings
from collections import Counter

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import paths
from .data import N_FOLDS

ACTIONS = ["CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION"]      # order of pilot common.ACTIONS
SENSORS = ["RGB", "THERMAL", "ANY"]
PRIOS = ["1", "2", "3"]
REC = ("CREATE_VERIFICATION", "UPDATE_INCIDENT")
C_GRID = (0.0003, 0.003, 0.03, 0.3, 3)
INNER_FOLDS = 3
TOL = 1e-6
MAX_ITER = 3000
CLASSES = {"action": ACTIONS, "sensor": SENSORS, "prio": PRIOS}


class FitLog:
    def __init__(self):
        self.fits = 0
        self.hit_limit = 0
        self.chosen_c = Counter()
        self.seconds = 0.0

    def as_dict(self):
        return {"fits": self.fits, "hit_iteration_limit": self.hit_limit, "chosen_C": {str(k): v for k, v in sorted(self.chosen_c.items())},
                "seconds": round(self.seconds, 1), "tol": TOL, "max_iter": MAX_ITER}


def _pipe(C):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=MAX_ITER, tol=TOL))


def _nll(model, X, y):
    P = model.predict_proba(X)
    pos = {c: j for j, c in enumerate(model.classes_)}
    p = np.array([P[r, pos[v]] if v in pos else 1e-12 for r, v in enumerate(y)])
    return float(-np.log(np.clip(p, 1e-12, 1.0)).sum())


def fit_head(X, y, groups, log=None):
    """C by grouped CV (log loss) inside the training reports, then one refit on all of them."""
    t0 = time.perf_counter()
    k = max(2, min(INNER_FOLDS, len(set(groups))))
    splits = list(GroupKFold(n_splits=k).split(X, y, groups))
    best_c, best = None, float("inf")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for C in C_GRID:
            total = sum(_nll(_pipe(C).fit(X[tr], y[tr]), X[te], y[te]) for tr, te in splits)
            if total < best:
                best, best_c = total, C
        model = _pipe(best_c).fit(X, y)
    if log is not None:
        log.fits += 1
        log.chosen_c[best_c] += 1
        log.seconds += time.perf_counter() - t0
        if int(np.max(model[-1].n_iter_)) >= MAX_ITER:
            log.hit_limit += 1
    return model


def proba_fixed(model, X, classes):
    P = model.predict_proba(X)
    out = np.zeros((len(X), len(classes)))
    for j, c in enumerate(model.classes_):
        out[:, classes.index(c)] = P[:, j]
    return out


class Heads:
    """The three heads of one precision, fitted on given reports."""

    def __init__(self, cases, X, fit_idx, groups, log=None):
        ya = np.array([cases[i]["gold"]["action"] for i in fit_idx])
        ys = np.array([cases[i]["gold"].get("sensor", "") for i in fit_idx])
        yp = np.array([str(cases[i]["gold"].get("priority", "")) for i in fit_idx])
        rec = np.isin(ya, REC)
        Xf = X[fit_idx]
        g = np.array([groups[i] for i in fit_idx])
        self.m = {"action": fit_head(Xf, ya, g, log),
                  "sensor": fit_head(Xf[rec], ys[rec], g[rec], log),
                  "prio": fit_head(Xf[rec], yp[rec], g[rec], log)}

    def proba(self, X):
        return {h: proba_fixed(self.m[h], X, CLASSES[h]) for h in ("action", "sensor", "prio")}


def cross_fit(D, log=None, verbose=False):
    """Probabilities for every outer fold.  Returns {k: {"fit": idx, "cal": idx, "eval": idx, "P": {arm: {head: array over cal+eval rows}}}}.
    Row order of the arrays: cal indices (sorted), then eval indices (sorted)."""
    out = {}
    for k in range(N_FOLDS):
        fit, cal, ev = D.split(k)
        rows = np.concatenate([cal, ev])
        t0 = time.perf_counter()
        heads = {m: Heads(D.cases, D.X[m], fit, D.group, log) for m in ("f16", "Q8_0", "Q4_K_M")}
        delta = (D.X["Q4_K_M"][fit] - D.X["f16"][fit]).mean(axis=0)          # label-free shift, FIT reports only
        P = {"q4": heads["Q4_K_M"].proba(D.X["Q4_K_M"][rows]),
             "f16": heads["f16"].proba(D.X["f16"][rows]),
             "q8": heads["Q8_0"].proba(D.X["Q8_0"][rows]),
             "rec": heads["f16"].proba(D.X["Q4_K_M"][rows] - delta),
             "raw": heads["f16"].proba(D.X["Q4_K_M"][rows])}
        out[k] = {"fit": fit, "cal": cal, "eval": ev, "P": P, "delta_norm": float(np.linalg.norm(delta))}
        if verbose:
            print("fold %d done in %.1f s" % (k, time.perf_counter() - t0), flush=True)
    return out


def save_cache(path, folds, log):
    arrays = {}
    meta = {"log": log.as_dict() if log else None, "folds": {}}
    for k, f in folds.items():
        meta["folds"][str(k)] = {"fit": f["fit"].tolist(), "cal": f["cal"].tolist(), "eval": f["eval"].tolist(), "delta_norm": f["delta_norm"]}
        for arm, d in f["P"].items():
            for h, a in d.items():
                arrays["f%d_%s_%s" % (k, arm, h)] = a
    np.savez_compressed(path, meta=np.array(json.dumps(meta)), **arrays)


def load_cache(path):
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    folds = {}
    for ks, f in meta["folds"].items():
        k = int(ks)
        P = {}
        for name in z.files:
            if name.startswith("f%d_" % k):
                _, arm, h = name.split("_", 2)
                P.setdefault(arm, {})[h] = z[name]
        folds[k] = {"fit": np.array(f["fit"]), "cal": np.array(f["cal"]), "eval": np.array(f["eval"]), "P": P, "delta_norm": f["delta_norm"]}
    return folds, meta["log"]
