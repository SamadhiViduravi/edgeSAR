"""Recompute the wording-shift mission tables from the saved per-episode records (numpy only; no model, simulator or study code), then compare every
number with results.json written by wording_shift_mission.py.
   python verify_wording_shift.py <out_wording_shift folder>
Ordinary = (late + unverified) / incidents; weighted = the same with priority weights 3/2/1 (externally resolved incidents excluded)."""
import gzip, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_from_records as v
from verify_text_baselines import wvec

ARMS = ["gold", "tfidf", "rule", "f16p", "q4p", "recp", "alnp", "rawp", "f16", "q4", "rec", "aln", "raw"]
PAIRS = [("tfidf", "f16p"), ("tfidf", "q4p"), ("tfidf", "recp"), ("tfidf", "alnp"), ("tfidf", "gold"), ("rule", "f16p"), ("rule", "q4p"), ("rule", "recp"),
         ("rule", "alnp"), ("rule", "gold"), ("tfidf", "rule"), ("f16p", "q4p"), ("alnp", "q4p"), ("alnp", "recp"), ("recp", "q4p"), ("f16p", "gold"),
         ("tfidf", "f16"), ("tfidf", "q4"), ("tfidf", "rec"), ("tfidf", "aln"), ("rule", "f16"), ("rule", "q4"), ("rule", "rec"), ("rule", "aln"),
         ("aln", "q4"), ("aln", "rec"), ("rec", "q4"), ("f16", "q4")]


def main(folder):
    folder = Path(folder); ref = json.loads((folder / "results.json").read_text(encoding="utf-8")); bad = n_ok = 0

    def chk(label, got, want, tol=1e-9):
        nonlocal bad, n_ok
        if abs(got - want) <= tol: n_ok += 1
        else: bad += 1; print("  MISMATCH %s: recomputed %.12g, saved %.12g" % (label, got, want))
    for lev in "LMH":
        recs = []
        for s in (1, 2, 3): recs += json.load(gzip.open(folder / ("records_%s_s%d.json.gz" % (lev, s))))
        by = v.by_arm(recs); print("\n== Level %s ==" % lev)
        for arm in ARMS:
            sh, lo, hi, E, N = v.share_ci(by, arm); ids = sorted(by[arm]); a, b = wvec(by, arm, ids)
            idx = np.random.RandomState(11).randint(0, len(ids), size=(2000, len(ids))); u = a[idx].sum(1) / b[idx].sum(1)
            w, wlo, whi = a.sum() / b.sum(), float(np.percentile(u, 2.5)), float(np.percentile(u, 97.5))
            print("  %-6s every incident once %6.2f%% (%.2f to %.2f)   priority-weighted %6.2f%% (%.2f to %.2f)   episodes %d" % (arm, 100 * sh, 100 * lo, 100 * hi, 100 * w, 100 * wlo, 100 * whi, E))
            s = ref["levels"][lev]["arms"][arm]
            for nm, g, t in (("share", sh, s["share"]), ("lo", lo, s["ci"][0]), ("hi", hi, s["ci"][1]), ("w", w, s["w_share"]), ("wlo", wlo, s["w_ci"][0]), ("whi", whi, s["w_ci"][1])):
                chk("%s %s %s" % (lev, arm, nm), g, t)
        for x, y in PAIRS:
            d, lo, hi, wn, l, t = v.paired(by, x, y); ids = sorted(set(by[x]) & set(by[y])); ax, bx = wvec(by, x, ids); ay, _ = wvec(by, y, ids)
            idx = np.random.RandomState(7).randint(0, len(ids), size=(10000, len(ids))); dw = (ax[idx].sum(1) - ay[idx].sum(1)) / bx[idx].sum(1)
            print("  %s minus %-4s: %+.2f pp (%+.2f to %+.2f) | weighted %+.2f (%+.2f to %+.2f) | first better/worse/tied %d/%d/%d" % (
                x, y, 100 * d, 100 * lo, 100 * hi, 100 * (ax.sum() - ay.sum()) / bx.sum(), 100 * np.percentile(dw, 2.5), 100 * np.percentile(dw, 97.5), wn, l, t))
            p = ref["levels"][lev]["paired"]["%s-%s" % (x, y)]
            for nm, g, tt in (("diff", d, p["ordinary"]["diff_U"]), ("lo", lo, p["ordinary"]["ci"][0]), ("hi", hi, p["ordinary"]["ci"][1]),
                              ("wdiff", (ax.sum() - ay.sum()) / bx.sum(), p["weighted"]["diff"]), ("wlo", float(np.percentile(dw, 2.5)), p["weighted"]["ci"][0]), ("whi", float(np.percentile(dw, 97.5)), p["weighted"]["ci"][1])):
                chk("%s %s-%s %s" % (lev, x, y, nm), g, tt)
    print("\nCompared with results.json: %d numbers agree, %d differ -> %s" % (n_ok, bad, "PASS" if bad == 0 else "FAIL"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1])
