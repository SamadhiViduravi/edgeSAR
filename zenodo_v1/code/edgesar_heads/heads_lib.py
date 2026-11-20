"""
EdgeSAR heads test - training and measuring code.

No model and no server are needed here: it only reads feature files (one vector per report) and
the pilot cases. Every rule is plain Python so you can read it once.

The three "heads" are small classifiers (standardise -> logistic regression):
    action   : CREATE_VERIFICATION / UPDATE_INCIDENT / CLOSE_INCIDENT / NO_ACTION   (4 classes)
    sensor   : RGB / THERMAL / ANY                                                  (3 classes)
    priority : 1 / 2 / 3                                                            (3 classes)
The location and the incident id are NOT read from the model. They come from the same string matching
that the pilot's TF-IDF/LR baseline uses (the place list and the I<number> pattern).
The four answers are joined into one decision by the pilot's own `_assemble`, then checked by the
pilot's own validator, so a heads decision is scored exactly like a generated decision.
"""
import json
import warnings
from collections import Counter

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from heads_common import PILOT, pb, pc

ACTIONS = list(pc.ACTIONS)
SENSORS = list(pc.SENSORS)
PRIOS = ["1", "2", "3"]
HEAD_CLASSES = {"action": ACTIONS, "sensor": SENSORS, "prio": PRIOS}
REC_ACTIONS = ("CREATE_VERIFICATION", "UPDATE_INCIDENT")
MAX_ITER = 500


# ------------------------------------------------------------------ labels
def make_labels(cases):
    """Gold labels for the three heads. Sensor and priority exist only for CREATE and UPDATE cases."""
    y = {
        "action": np.array([c["gold"]["action"] for c in cases]),
        "sensor": np.array([c["gold"].get("sensor", "") for c in cases]),
        "prio": np.array([str(c["gold"].get("priority", "")) for c in cases]),
    }
    rec = np.array([c["gold"]["action"] in REC_ACTIONS for c in cases])
    return y, rec


# ------------------------------------------------------------------ one head
class FitLog:
    """Counts fits that stopped at the iteration limit (reported, so nothing is hidden)."""
    def __init__(self):
        self.fits = 0
        self.hit_limit = 0
        self.chosen_c = Counter()


def _pipe(C):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=MAX_ITER, tol=1e-3))


def _nll(model, X, y):
    P = model.predict_proba(X)
    pos = {c: j for j, c in enumerate(model.classes_)}
    p = np.array([P[r, pos[v]] if v in pos else 1e-12 for r, v in enumerate(y)])
    return float(-np.log(np.clip(p, 1e-12, 1.0)).sum())


def fit_head(X, y, groups, c_grid, inner_folds, log=None):
    """Choose C by grouped cross-validation INSIDE the training rows (log-loss), then refit on all training rows.
    The held-out rows never take part in this choice."""
    k = max(2, min(inner_folds, len(set(groups))))
    gkf = GroupKFold(n_splits=k)
    splits = list(gkf.split(X, y, groups))
    best_c, best = None, float("inf")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for C in c_grid:
            total = 0.0
            for tr, te in splits:
                total += _nll(_pipe(C).fit(X[tr], y[tr]), X[te], y[te])
            if total < best:
                best, best_c = total, C
        model = _pipe(best_c).fit(X, y)
    if log is not None:
        log.fits += 1
        log.chosen_c[best_c] += 1
        if int(np.max(model[-1].n_iter_)) >= MAX_ITER:
            log.hit_limit += 1
    return model


def proba_fixed(model, X, fixed_classes):
    """Class probabilities in a fixed column order (a class missing from training gets probability 0)."""
    P = model.predict_proba(X)
    out = np.zeros((len(X), len(fixed_classes)))
    for j, c in enumerate(model.classes_):
        out[:, fixed_classes.index(c)] = P[:, j]
    return out


# ------------------------------------------------------------------ the scheme: out-of-fold on dev, one fit for held-out
def make_plan(cases, dev_idx, held_idx, outer_folds):
    """List of (train rows, test rows). Dev rows are tested out-of-fold (folds grouped by family, as in the
    pilot's TF-IDF/LR). Held-out rows are tested once, by heads trained on ALL dev rows."""
    groups = np.array([c["family"] for c in cases])
    dev = np.array(dev_idx)
    held = np.array(held_idx)
    gkf = GroupKFold(n_splits=outer_folds)
    plan = [(dev[tr], dev[te]) for tr, te in gkf.split(dev, groups=groups[dev])]
    plan.append((dev, held))
    for tr, te in plan:
        if set(groups[tr]) & set(groups[te]):
            raise RuntimeError("A family appears in both the training rows and the test rows. Leak. Stop.")
    return plan, groups


def run_scheme(X_train, X_apply, cases, dev_idx, held_idx, cfg, labels=None, heads=("action", "sensor", "prio"),
               log=None, progress=None):
    """
    X_train : (N, D) vectors the heads are trained on.
    X_apply : {name: (N, D)} vectors the trained heads are applied to (X_train itself may be one of them).
    Returns {name: {head: (N, n_classes) probabilities}}; dev rows are out-of-fold, held rows come from the all-dev fit.
    """
    y, rec = labels if labels is not None else make_labels(cases)
    N = len(cases)
    plan, groups = make_plan(cases, dev_idx, held_idx, cfg["outer_folds"])
    out = {name: {h: np.zeros((N, len(HEAD_CLASSES[h]))) for h in heads} for name in X_apply}
    for fi, (tr, te) in enumerate(plan):
        for h in heads:
            rows = tr if h == "action" else tr[rec[tr]]
            model = fit_head(X_train[rows], y[h][rows], groups[rows], cfg["c_grid"], cfg["inner_folds"], log)
            for name, XA in X_apply.items():
                out[name][h][te] = proba_fixed(model, XA[te], HEAD_CLASSES[h])
        if progress:
            progress(fi + 1, len(plan))
    return out


# ------------------------------------------------------------------ probabilities -> decisions (scored like generated ones)
def _record(case, norm, status, conf, head_action=None):
    return {"norm": norm, "status": status, "eff": pc.effect(norm, case), "key": pc.strict_key(norm),
            "conf": conf, "head_action": head_action}


def decisions_from_probs(cases, P):
    out = []
    for i, c in enumerate(cases):
        a = ACTIONS[int(P["action"][i].argmax())]
        s = SENSORS[int(P["sensor"][i].argmax())]
        p = int(PRIOS[int(P["prio"][i].argmax())])
        norm, status = pc.validate(pb._assemble(c, a, s, p), c)
        conf = float(P["action"][i].max())
        if a in REC_ACTIONS:      # a record decision is only as sure as its weakest head
            conf = min(conf, float(P["sensor"][i].max()), float(P["prio"][i].max()))
        out.append(_record(c, norm, status, conf, a))
    return out


def generative_decisions(cases, run_name, runs_dir=None):
    """The pilot's saved model answers, scored exactly as the pilot's analyze.py does."""
    path = (runs_dir or PILOT / "runs") / (run_name + ".jsonl")
    recs = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                recs[r["case_id"]] = r
    out = []
    for c in cases:
        rec = recs.get(c["id"])
        if rec is None or "text" not in rec:
            raise RuntimeError("run %s has no answer for %s" % (run_name, c["id"]))
        obj, _ = pc.parse_decision(rec["text"])
        norm, status = pc.validate(obj, c)
        out.append(_record(c, norm, status, None))
    return out


def baseline_decisions(cases):
    """Rule engine and TF-IDF/LR from the pilot's own code (same cross-validation as the pilot)."""
    table = pb.baseline_table(cases, with_lr=True)
    return {k: [_record(c, v[c["id"]], "ok", None) for c in cases] for k, v in table.items()}


# ------------------------------------------------------------------ measures
def accuracy(cases, D, idx):
    a_ok = np.array([D[i]["norm"]["action"] == cases[i]["gold"]["action"] for i in idx], dtype=bool)
    r_ok = np.array([D[i]["norm"] == pc.gold_norm(cases[i]) for i in idx], dtype=bool)
    n = len(idx)
    return {"n": n, "a_ok": a_ok, "r_ok": r_ok,
            "action": pc.wilson(int(a_ok.sum()), n), "record": pc.wilson(int(r_ok.sum()), n)}


def flip_stats(cases, Ref, X, idx):
    """Ref = the reference (FP16) decisions, X = the shrunk model's decisions, both for the same cases.
    'table-changing' = the task table would be different (the pilot's operational flip).
    'any field' = at least one field of the decision is different."""
    idx = list(idx)
    tab = np.array([Ref[i]["eff"] != X[i]["eff"] for i in idx], dtype=bool)
    key = np.array([Ref[i]["key"] != X[i]["key"] for i in idx], dtype=bool)
    r2w = w2r = wdiff = 0
    for i, k in zip(idx, key):
        if not k:
            continue
        g = pc.gold_norm(cases[i])
        ra, rx = Ref[i]["norm"] == g, X[i]["norm"] == g
        if ra and not rx:
            r2w += 1
        elif (not ra) and rx:
            w2r += 1
        else:
            wdiff += 1
    trans = Counter(pc.transition(Ref[i]["eff"], X[i]["eff"]) for i, t in zip(idx, tab) if t)
    n = len(idx)
    return {"n": n, "tab_mask": tab, "table_changing": int(tab.sum()), "any_field": int(key.sum()),
            "table_ci": pc.wilson(int(tab.sum()), n), "any_ci": pc.wilson(int(key.sum()), n),
            "right_to_wrong": r2w, "wrong_to_right": w2r, "wrong_other": wdiff, "transitions": trans}


def head_correct_split(cases, Ref, flips_mask, idx):
    """Of the table-changing disagreements, how many happen where the reference was already WRONG (whole record)?"""
    idx = list(idx)
    ref_wrong = 0
    for i, t in zip(idx, flips_mask):
        if t and Ref[i]["norm"] != pc.gold_norm(cases[i]):
            ref_wrong += 1
    return ref_wrong


def auroc_flip(conf, flip_mask):
    """How well does low confidence point at the cases that flip? 0.5 = no better than chance, 1.0 = perfect."""
    flip_mask = np.asarray(flip_mask, dtype=bool)
    if flip_mask.all() or not flip_mask.any():
        return None
    return float(roc_auc_score(flip_mask, -np.asarray(conf, dtype=float)))


def flag_coverage(conf, flip_mask, fractions):
    """Flag the least-confident share of cases. How many of the flips land inside the flagged set?
    'remaining' = flips left after the flagged cases are handed to the big model (share of ALL cases)."""
    conf = np.asarray(conf, dtype=float)
    flip_mask = np.asarray(flip_mask, dtype=bool)
    n = len(conf)
    total = int(flip_mask.sum())
    order = np.argsort(conf, kind="stable")
    rows = []
    for f in fractions:
        k = int(round(f * n))
        got = int(flip_mask[order[:k]].sum())
        rows.append({"fraction": f, "flagged": k, "flips_inside": got, "flips_total": total,
                     "coverage": (got / total) if total else None,
                     "lift": ((got / total) / f) if (total and f) else None,
                     "remaining_share": (total - got) / n})
    return rows


def cosine_stats(XA, XB):
    a = XA / np.linalg.norm(XA, axis=1, keepdims=True)
    b = XB / np.linalg.norm(XB, axis=1, keepdims=True)
    cs = np.sum(a * b, axis=1)
    return {"mean": float(cs.mean()), "min": float(cs.min()), "p05": float(np.percentile(cs, 5))}
