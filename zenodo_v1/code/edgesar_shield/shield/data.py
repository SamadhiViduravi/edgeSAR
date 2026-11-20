"""
The saved development data (read-only): the 1,400 pilot reports, their last-token vectors at three precisions, and the duplicate clusters.

Development with saved vectors uses only the 1,000 style-A reports. Style B (400) is NOT used to choose anything; it is touched once, after the
protocol is frozen, as an exploratory style-shift check.

Cross-fitting folds (plan deviation, see docs/DEVIATIONS.md):  the 1,000 style-A reports are split into 5 folds of 200 by *family* (the pilot's unit;
100 families of 10 reports). For outer fold k:
    EVAL = fold k      CAL = fold (k + 1) mod 5      FIT = the other three folds (about 600 reports)
Exact duplicates (audit04 clusters) join families into one giant component (950 of 1,000 reports), so they cannot be used as the grouping unit.
Instead, any FIT report that has an exact duplicate in CAL or EVAL is removed from FIT for that outer fold (the number removed is logged).
Heads are fitted on FIT only, the conformal threshold and the gate thresholds come from CAL only, and every number we report comes from EVAL only.
Every report is an EVAL report exactly once.
"""
import csv
import hashlib
import json
from collections import defaultdict

import numpy as np

from . import paths

PREC = ("f16", "Q8_0", "Q4_K_M")
PREC_NAME = {"f16": "FP16", "Q8_0": "Q8", "Q4_K_M": "Q4"}
FOLD_SEED = 20261113
N_FOLDS = 5


def load_cases():
    p = paths.PILOT / "data" / "cases.jsonl"
    if paths.sha256_file(p) != paths.PINS["edgesar_pilot/data/cases.jsonl"]:
        raise SystemExit("cases.jsonl is not the audited version. Stop.")
    with open(p, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_vectors(kind="end"):
    out = {}
    for m in PREC:
        p = paths.HEADS / "features" / ("%s_%s.npy" % (m, kind))
        key = "edgesar_heads/features/%s_%s.npy" % (m, kind)
        if key in paths.PINS and paths.sha256_file(p) != paths.PINS[key]:
            raise SystemExit("%s is not the audited version. Stop." % key)
        out[m] = np.load(p).astype(np.float64)
    ids = json.load(open(paths.HEADS / "features" / "case_ids.json", encoding="utf-8"))
    return out, ids


def load_clusters():
    p = paths.AUDIT / "out" / "audit04_duplicate_clusters.csv"
    with open(p, encoding="utf-8") as f:
        return {r["case_id"]: (r["family"], r["duplicate_cluster"]) for r in csv.DictReader(f)}


class DevData:
    """Cases, vectors, groups and folds for style A."""

    def __init__(self):
        paths.require_pins()
        self.cases = load_cases()
        self.X, ids = load_vectors("end")
        if ids != [c["id"] for c in self.cases]:
            raise SystemExit("case_ids.json does not match cases.jsonl order. Stop.")
        for m in PREC:
            if self.X[m].shape[0] != len(self.cases):
                raise SystemExit("vector count mismatch for %s" % m)
        clusters = load_clusters()
        self.A = np.array([i for i, c in enumerate(self.cases) if c["style"] == "A"])
        self.B = np.array([i for i, c in enumerate(self.cases) if c["style"] == "B"])
        self.clusters = clusters
        self.group = [clusters[c["id"]][0] for c in self.cases]            # family
        self.dup = [clusters[c["id"]][1] for c in self.cases]              # exact-duplicate cluster
        self.fold_of = self._folds()
        self.purged = {}

    def _folds(self):
        """Assign whole groups to folds of about equal size. Deterministic (seeded shuffle, then greedy to the emptiest fold)."""
        rng = np.random.RandomState(FOLD_SEED)
        by_group = defaultdict(list)
        for i in self.A:
            by_group[self.group[i]].append(int(i))
        keys = sorted(by_group)
        rng.shuffle(keys)
        keys.sort(key=lambda g: -len(by_group[g]))             # big groups first (stable after the shuffle)
        load = [0] * N_FOLDS
        fold = {}
        for g in keys:
            k = int(np.argmin(load))
            for i in by_group[g]:
                fold[i] = k
            load[k] += len(by_group[g])
        return fold

    def split(self, k):
        """(FIT, CAL, EVAL) index arrays for outer fold k."""
        ev = np.array(sorted(i for i, f in self.fold_of.items() if f == k))
        cal = np.array(sorted(i for i, f in self.fold_of.items() if f == (k + 1) % N_FOLDS))
        fit = np.array(sorted(i for i, f in self.fold_of.items() if f not in (k, (k + 1) % N_FOLDS)))
        held_dups = set(self.dup[i] for i in cal) | set(self.dup[i] for i in ev)
        keep = np.array([i for i in fit if self.dup[i] not in held_dups])
        self.purged[k] = int(len(fit) - len(keep))
        fit = keep
        fams = lambda ix: set(self.group[i] for i in ix)          # noqa: E731
        if fams(fit) & (fams(cal) | fams(ev)) or fams(cal) & fams(ev):
            raise RuntimeError("a family appears in two roles. Leak. Stop.")
        if set(self.dup[i] for i in fit) & held_dups:
            raise RuntimeError("an exact duplicate appears in FIT and CAL/EVAL. Leak. Stop.")
        return fit, cal, ev

    def fingerprint(self):
        h = hashlib.sha256()
        for i in sorted(self.fold_of):
            h.update(("%d:%d;" % (i, self.fold_of[i])).encode())
        return h.hexdigest()
