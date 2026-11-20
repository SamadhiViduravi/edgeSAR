"""Rebuild the pre-registered primary table of the EdgeSAR fresh confirmation from the per-episode outcomes, with one command:

    python rebuild_primary.py episode_outcomes.csv

Needs only Python 3 and numpy. Uses the same arithmetic as fresh_confirm.py (pooled missed share, paired by episode, 10,000 episode-bootstrap
resamples with seed 7, two-sided sign-flip test, Holm correction over H1, H2a, H2b, H3). Prints the table and checks it against results.json
if that file is in the same folder."""
import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np


def paired(mx, my, nn, n_boot=10000, seed=7):
    rng = np.random.RandomState(seed)
    E = len(nn)
    idx = rng.randint(0, E, size=(n_boot, E))
    diff = (mx[idx].sum(1) - my[idx].sum(1)) / nn[idx].sum(1)
    d = mx - my
    signs = rng.choice([-1.0, 1.0], size=(n_boot, E))
    p = (np.sum(np.abs((signs * d).sum(1)) >= abs(d.sum()) - 1e-12) + 1) / (n_boot + 1)
    return d.sum() / nn.sum(), np.percentile(diff, 2.5), np.percentile(diff, 97.5), p


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "episode_outcomes.csv"
    tab = defaultdict(dict)
    nn = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if (r["set"], r["level"], r["seed"]) != ("A", "M", "11"):
            continue
        tab[r["arm"]][r["episode"]] = float(r["missed"])
        nn[r["episode"]] = float(r["incidents"])
    eps = sorted(nn)
    n = np.array([nn[e] for e in eps])

    def arr(arm):
        if arm == "q4p_n100":
            return np.mean([[tab["q4p_n100_d%d" % d][e] for e in eps] for d in range(5)], axis=0)
        return np.array([tab[arm][e] for e in eps])
    tests = [("H1", "rawp", "f16p", +1), ("H2a", "alnp", "rawp", -1), ("H2b", "q4p", "rawp", -1), ("H3", "alnp", "q4p_n100", -1)]
    out = [paired(arr(x), arr(y), n) for _, x, y, _ in tests]
    ps = [o[3] for o in out]
    order = sorted(range(4), key=lambda i: ps[i])
    adj, run = [0.0] * 4, 0.0
    for r_, i in enumerate(order):
        run = max(run, min(1.0, (4 - r_) * ps[i]))
        adj[i] = run
    print("Set A, medium load, arrival seed 11: %d episodes, %d incidents" % (len(eps), n.sum()))
    ok_all = True
    reg = None
    rj = os.path.join(os.path.dirname(os.path.abspath(path)), "results.json")
    if os.path.exists(rj):
        reg = json.load(open(rj))["primary"]["tests"]
    for (h, x, y, sign), (d, lo, hi, p), pa in zip(tests, out, adj):
        conf = (lo > 0 if sign > 0 else hi < 0) and pa < 0.05
        line = "%-4s %-9s minus %-9s %+.2f pp (%+.2f to %+.2f)  p=%.4f  Holm p=%.4f  %s" % (h, x, y, 100 * d, 100 * lo, 100 * hi, p, pa, "confirmed" if conf else "not confirmed")
        if reg:
            same = abs(reg[h]["diff"] - d) < 1e-12 and abs(reg[h]["ci"][0] - lo) < 1e-12 and abs(reg[h]["ci"][1] - hi) < 1e-12 and abs(reg[h]["p_holm"] - pa) < 1e-12
            ok_all &= same
            line += "   [equals results.json: %s]" % same
        print(line)
    if reg:
        print("ALL EQUAL TO results.json:", ok_all)


if __name__ == "__main__":
    main()
