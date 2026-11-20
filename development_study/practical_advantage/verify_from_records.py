"""Recompute the headline mission numbers from the saved per-episode records. numpy only; needs no model, vectors or simulator.
   python verify_from_records.py out_trace/records_M.json.gz          (label-budget, recentring, map, gold-replacement arms; level M)
   python verify_from_records.py out_mission/records_{L,M,H}_s{1,2,3}.json.gz   (all-label arms at three load levels; the repair package)
Each record: {episode, arm, fold, level, seed, counts:{n, late, unverified, ...}}.  Missed share = (late + unverified) / incidents.
The bootstrap functions are the same as `episode_bootstrap_ci` and `paired` in the study code (same seeds), written out here so the file stands alone."""
import gzip, json, sys
import numpy as np


def by_arm(records):
    d = {}
    for r in records:
        d.setdefault(r["arm"], {})[r["episode"]] = r
    return d


def missed(r):
    return r["counts"]["late"] + r["counts"]["unverified"]


def share_ci(by, arm, n_boot=2000, seed=11):
    eps = list(by[arm].values())
    m = np.array([missed(e) for e in eps], float); n = np.array([e["counts"]["n"] for e in eps], float)
    idx = np.random.RandomState(seed).randint(0, len(eps), size=(n_boot, len(eps)))
    u = m[idx].sum(1) / n[idx].sum(1)
    return m.sum() / n.sum(), np.percentile(u, 2.5), np.percentile(u, 97.5), len(eps), int(n.sum())


def paired(by, x, y, n_boot=10000, seed=7):
    ids = sorted(set(by[x]) & set(by[y]))
    mx = np.array([missed(by[x][e]) for e in ids], float); my = np.array([missed(by[y][e]) for e in ids], float)
    nn = np.array([by[x][e]["counts"]["n"] for e in ids], float)
    assert np.array_equal(nn, np.array([by[y][e]["counts"]["n"] for e in ids], float)), "episodes are not paired"
    idx = np.random.RandomState(seed).randint(0, len(ids), size=(n_boot, len(ids)))
    diff = (mx[idx].sum(1) - my[idx].sum(1)) / nn[idx].sum(1)
    d = mx - my
    return (mx.sum() - my.sum()) / nn.sum(), np.percentile(diff, 2.5), np.percentile(diff, 97.5), int((d < 0).sum()), int((d > 0).sum()), int((d == 0).sum())


def main(paths):
    levels = {}
    for p in paths:
        for r in json.load(gzip.open(p)):
            levels.setdefault(r["level"], []).append(r)
    for lev in sorted(levels):
        by = by_arm(levels[lev])
        print("\n== Level %s ==  arms: %s" % (lev, ", ".join(sorted(by))))
        for arm in ["gold", "f16p", "q4p", "q4p_n300", "q4p_n100", "alnp", "recp", "rawp"]:
            if arm in by:
                s, lo, hi, E, N = share_ci(by, arm)
                print("  %-9s %6.2f%%  (%.2f to %.2f)  episodes %d  incidents %d" % (arm, 100 * s, 100 * lo, 100 * hi, E, N))
        for x, y in [("alnp", "q4p"), ("alnp", "q4p_n300"), ("alnp", "q4p_n100"), ("recp", "q4p_n100"), ("alnp", "recp"), ("q4p", "f16p")]:
            if x in by and y in by:
                d, lo, hi, w, l, t = paired(by, x, y)
                print("  %s minus %s: %+.2f pp (%+.2f to %+.2f)  first better/worse/tied %d/%d/%d" % (x, y, 100 * d, 100 * lo, 100 * hi, w, l, t))


if __name__ == "__main__":
    main(sys.argv[1:])
