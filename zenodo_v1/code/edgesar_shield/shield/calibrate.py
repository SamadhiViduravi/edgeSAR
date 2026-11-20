"""
Calibration helpers (offline).  These are the only functions that read the labelled (gold) record of calibration reports.
They run before an episode starts, on calibration reports only, and produce one number per level (the conformal threshold q).
Nothing in the runtime path (service.py, candidates.py, policy.py, cover.py) imports this module.
"""
import math

import numpy as np


def label_score(cands, label_key):
    """Score of the labelled (calibration-time) record among the candidates; None when the heads + parser cannot express it (missing candidate)."""
    for c in cands:
        if c["key"] == label_key:
            return c["score"]
    return None


def conformal_q(label_scores, alpha):
    """Split-conformal threshold on the nonconformity s = 1 - score.  `label_scores` has None for a missing labelled record (counts as s = 1).
    q = the ceil((n+1)(1-alpha))-th smallest nonconformity;  if that rank exceeds n the threshold is infinite (the set is everything)."""
    s = np.array([1.0 if g is None else 1.0 - g for g in label_scores])
    n = len(s)
    k = int(math.ceil((n + 1) * (1.0 - alpha)))
    if k > n:
        return math.inf
    return float(np.sort(s)[k - 1])
