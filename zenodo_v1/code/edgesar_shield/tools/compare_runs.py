"""
Reproducibility check: are two result folders identical in every number that is not a wall-clock time?

    python tools/compare_runs.py main main_rerun            (results/dev/<a> against results/dev/<b>)
    python tools/compare_runs.py --base fresh a b

The compact records contain per-report decision times (`ms`) and per-episode `wall_ms`: those measure the computer, not the science, and are ignored.
Everything else (outcomes, costs, decisions, risk scores, incident tables) must match exactly.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import paths                                          # noqa: E402


def clean(recs):
    out = []
    for r in recs:
        r = json.loads(json.dumps(r))
        for rep in r["reports"]:
            rep.pop("ms", None)
        r["cost"].pop("wall_ms", None)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--base", default="dev")
    n = ap.parse_args()
    da, db = paths.RESULTS / n.base / n.a, paths.RESULTS / n.base / n.b
    fa = sorted(p.name for p in da.glob("records_*.json.gz"))
    fb = sorted(p.name for p in db.glob("records_*.json.gz"))
    if fa != fb:
        sys.exit("DIFFERENT: the folders hold different record files: %s vs %s" % (fa, fb))
    bad = 0
    total = 0
    for name in fa:
        ra = clean(json.load(gzip.open(da / name, "rt")))
        rb = clean(json.load(gzip.open(db / name, "rt")))
        total += len(ra)
        if ra != rb:
            bad += 1
            k = next((i for i, (x, y) in enumerate(zip(ra, rb)) if x != y), None)
            print("DIFFERENT: %s (first differing record: %s)" % (name, None if k is None else (ra[k]["episode"], ra[k]["arm"])))
        else:
            print("identical: %s (%d records)" % (name, len(ra)))
    if bad:
        sys.exit(1)
    print("ALL IDENTICAL: %d files, %d records (wall-clock times ignored)." % (len(fa), total))


if __name__ == "__main__":
    main()
