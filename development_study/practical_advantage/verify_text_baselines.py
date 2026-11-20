"""Recompute the text-baseline comparison from saved per-episode records (numpy only; no model, simulator or study code).
   python verify_text_baselines.py <repair_package/out_mission> <out_text_baselines>
Reads records_{L,M,H}_s{1,2,3}.json.gz of the reference arms (gold, f16p, q4p, alnp, recp, rawp) and of the new arms (tfidf, rule).
Ordinary = (late + unverified) / incidents; weighted = the same with priority weights 3/2/1 (externally resolved incidents excluded)."""
import gzip, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_from_records as v

W = {3: 3.0, 2: 2.0, 1: 1.0}


def wvec(by, arm, ids):
    a, b = [], []
    for e in ids:
        x = y = 0.0
        for row in by[arm][e]["inc"]:
            if row[8] == "resolved_external": continue
            y += W[int(row[4])]
            if row[8] in ("late", "unverified"): x += W[int(row[4])]
        a.append(x); b.append(y)
    return np.array(a), np.array(b)


def main(ref, new):
    for lev in "LMH":
        recs = []
        for s in (1, 2, 3):
            recs += [r for r in json.load(gzip.open(Path(ref) / ("records_%s_s%d.json.gz" % (lev, s)))) if r["arm"] in ("gold", "f16p", "q4p", "alnp", "recp", "rawp")]
            recs += [r for r in json.load(gzip.open(Path(new) / ("records_%s_s%d.json.gz" % (lev, s)))) if r["arm"] in ("tfidf", "rule")]
        by = v.by_arm(recs)
        # the gold arm was run again in `new`; the later copy overwrote the earlier one in by_arm, and the counts are identical by the integrity check
        print("\n== Level %s ==" % lev)
        for arm in ("gold", "f16p", "q4p", "alnp", "recp", "rawp", "tfidf", "rule"):
            s, lo, hi, E, N = v.share_ci(by, arm); ids = sorted(by[arm]); a, b = wvec(by, arm, ids)
            idx = np.random.RandomState(11).randint(0, len(ids), size=(2000, len(ids))); u = a[idx].sum(1) / b[idx].sum(1)
            print("  %-6s every incident once %6.2f%% (%.2f to %.2f)   priority-weighted %6.2f%% (%.2f to %.2f)   episodes %d" % (
                arm, 100 * s, 100 * lo, 100 * hi, 100 * a.sum() / b.sum(), 100 * np.percentile(u, 2.5), 100 * np.percentile(u, 97.5), E))
        for x in ("tfidf", "rule"):
            for y in ("f16p", "q4p", "alnp", "gold"):
                d, lo, hi, w, l, t = v.paired(by, x, y); ids = sorted(set(by[x]) & set(by[y])); ax, bx = wvec(by, x, ids); ay, _ = wvec(by, y, ids)
                idx = np.random.RandomState(7).randint(0, len(ids), size=(10000, len(ids))); dw = (ax[idx].sum(1) - ay[idx].sum(1)) / bx[idx].sum(1)
                print("  %s minus %-4s: %+.2f pp (%+.2f to %+.2f) | weighted %+.2f (%+.2f to %+.2f) | first better/worse/tied %d/%d/%d" % (
                    x, y, 100 * d, 100 * lo, 100 * hi, 100 * (ax.sum() - ay.sum()) / bx.sum(), 100 * np.percentile(dw, 2.5), 100 * np.percentile(dw, 97.5), w, l, t))


if __name__ == "__main__":
    main(*sys.argv[1:3])
