"""
How many FRESH episodes are needed?  (plan section 8.4)   N_e = ((1.96 + 0.84) * sd_D / delta)^2   (two-sided 5%, power 80%)
sd_D  = standard deviation, across episodes, of the difference in missed incidents (late + unverified) between the two arms (paired)
delta = the difference we want to be able to detect, in missed incidents per episode.  The plan's default: 20% of the record-induced misses of the
        confidence gate, i.e. 0.20 * (misses of A6 - misses of A0) per episode.  Other delta values are listed too.
Uses ONE seed at a time (episodes of one seed are independent; seeds re-use the same reports) and reports each.

    python tools/power.py --tag main
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                                # noqa: E402

from shield import paths                                          # noqa: E402


def per_episode(recs, arm):
    return {r["episode"]: r["counts"]["late"] + r["counts"]["unverified"] for r in recs if r["arm"] == arm}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="main")
    ap.add_argument("--pairs", nargs="*", default=["A8:A6", "A8c:A6", "A8c:A1", "A8c:A10"])
    a = ap.parse_args()
    d = paths.RESULTS / "dev" / a.tag
    out = {}
    lines = ["| level | seed | comparison | mean diff / episode | sd of diff | delta (20% of A6 record-induced misses) | N_e for that delta | N_e for delta = observed mean diff | N_e for delta = 0.1 miss/episode |", "|---|---|---|---|---|---|---|---|---|"]
    for f in sorted(d.glob("records_*_s*.json.gz")):
        lv, sd = f.stem.split(".")[0].split("_")[1:3]
        recs = json.load(gzip.open(f, "rt"))
        m = {arm: per_episode(recs, arm) for arm in {r["arm"] for r in recs}}
        ids = sorted(m["A6"])
        rec_induced = np.mean([m["A6"][e] - m["A0"][e] for e in ids])
        delta = 0.20 * rec_induced
        for pr in a.pairs:
            x, y = pr.split(":")
            diff = np.array([m[x][e] - m[y][e] for e in ids], dtype=float)
            sdd = float(np.std(diff, ddof=1))
            ne = lambda dl: (2.8 * sdd / dl) ** 2 if dl > 0 else float("inf")      # noqa: E731
            out[(lv, sd, pr)] = {"mean": float(diff.mean()), "sd": sdd, "delta": float(delta), "N_e": ne(delta)}
            lines.append("| %s | %s | %s vs %s | %+.3f | %.3f | %.3f | %.0f | %.0f | %.0f |" % (lv, sd, x, y, diff.mean(), sdd, delta, ne(delta), ne(abs(diff.mean())), ne(0.1)))
    text = "\n".join(lines)
    (d / "POWER.md").write_text("# Power (development, per seed)\n\nEpisodes: 20 reports. %s\n\n" % __doc__.split("\n")[1] + text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
