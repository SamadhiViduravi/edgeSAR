"""
Sample size for the confirmatory (fresh) test, from the iteration-1 development records.  Run only after the method is fixed.

    python tools/power_iter1.py            -> results/iter1/POWER_ITER1.md

For a paired comparison x - y of missed incidents per episode:   N = ((z_a + z_b) * sd / delta)^2
  sd     = standard deviation across episodes of (misses_x - misses_y); taken PER SEED (the episodes of one seed are independent; seeds reuse the same reports)
  delta  = the smallest difference worth detecting, written as percentage points of missed share (pp) and converted with the mean incidents per episode
Also given: the power of a design with N episodes for each delta.  Level M, readout q4.  Development sd is an estimate: the fresh sd will differ (+- 15% is common).
"""
import argparse
import gzip
import json
import sys
from math import erf, sqrt
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                                # noqa: E402

from shield import paths                                          # noqa: E402

PAIRS = [("B3", "G1"), ("B3", "A1"), ("B3", "A6")]
DELTAS_PP = [0.5, 0.75, 1.0, 1.5, 2.0]
NS = [400, 600, 1100, 1500]


def phi(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="q4")
    a = ap.parse_args()
    d = paths.RESULTS / "iter1" / a.tag
    rows, md = {}, ["# Sample size for the fresh test (from iteration-1 development data)", "",
                    "Level M, readout %s, episodes of 20 reports, paired differences of missed incidents per episode. sd is computed per arrival seed (episodes inside one seed are independent). "
                    "Two-sided 5%%. This is an estimate from development data; the fresh sd will differ." % a.tag, ""]
    for lv in ("M",):
        per = {}
        for f in sorted(d.glob("records_%s_s*.json.gz" % lv)):
            recs = json.load(gzip.open(f, "rt"))
            m = {}
            for r in recs:
                m.setdefault(r["arm"], {})[r["episode"]] = (r["counts"]["late"] + r["counts"]["unverified"], r["counts"]["n"])
            seed = int(f.stem.split("_s")[-1].split(".")[0])
            per[seed] = m
        for x, y in PAIRS:
            sds, means, nbar = [], [], []
            for s, m in per.items():
                ids = sorted(m[x])
                diff = np.array([m[x][e][0] - m[y][e][0] for e in ids], dtype=float)
                sds.append(float(np.std(diff, ddof=1)))
                means.append(float(diff.mean()))
                nbar.append(float(np.mean([m[x][e][1] for e in ids])))
            sd, nb = float(np.mean(sds)), float(np.mean(nbar))
            rows[(x, y)] = {"sd_misses_per_episode": sd, "mean_diff_misses_per_episode": float(np.mean(means)), "incidents_per_episode": nb,
                            "sd_by_seed": sds}
            md += ["## %s minus %s" % (x, y), "",
                   "sd of the per-episode difference: %.2f missed incidents (by seed: %s). Mean incidents per episode: %.1f. Observed mean difference: %+.2f misses/episode = %+.2f pp." % (
                       sd, ", ".join("%.2f" % v for v in sds), nb, np.mean(means), 100 * np.mean(means) / nb), "",
                   "| smallest effect to detect | misses/episode | episodes for 80% power | episodes for 90% power | " + " | ".join("power at %d episodes" % n for n in NS) + " |",
                   "|---|---|---|---|" + "---|" * len(NS)]
            for dpp in DELTAS_PP:
                dm = dpp / 100.0 * nb
                n80 = ((1.96 + 0.8416) * sd / dm) ** 2
                n90 = ((1.96 + 1.2816) * sd / dm) ** 2
                pw = [phi(dm * sqrt(n) / sd - 1.96) for n in NS]
                md.append("| %.2f pp | %.3f | %.0f | %.0f | %s |" % (dpp, dm, n80, n90, " | ".join("%.0f%%" % (100 * p) for p in pw)))
            md.append("")
    (paths.RESULTS / "iter1" / ("POWER_ITER1.md" if a.tag == "q4" else "POWER_ITER1_%s.md" % a.tag)).write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
