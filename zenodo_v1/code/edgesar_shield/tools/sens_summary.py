"""
One table for the sensitivity runs (development, level M, seeds 1-3):  python tools/sens_summary.py
Each row is one change from the default (b 10%, alpha 0.10, K 8, d_v 60 s, CBBA with bundle length 3, 0.02 s per allocator run).
"""
import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shield import devrun, paths                                  # noqa: E402

ROWS = [("main", "default (b 10%, alpha 0.10, K 8, d_v 60 s, CBBA, 0.02 s / run)"), ("b05", "budget b = 5%"), ("b20", "budget b = 20%"), ("b30", "budget b = 30%"),
        ("a05", "alpha = 0.05"), ("a20", "alpha = 0.20"), ("K4", "K = 4 (larger sets count as unusable)"),
        ("dv30", "verifier answers after 30 s"), ("dv120", "verifier answers after 120 s"),
        ("legacy", "legacy greedy allocator instead of bounded CBBA"),
        ("ac02", "an allocator run costs 0.2 s (limit 5 s)"), ("ac10", "an allocator run costs 1.0 s (limit 5 s)")]


def load(tag, level="M"):
    recs = []
    for s in (1, 2, 3):
        f = paths.RESULTS / "dev" / tag / ("records_%s_s%d.json.gz" % (level, s))
        if f.exists():
            recs += json.load(gzip.open(f, "rt"))
    return recs


def main():
    lines = ["# Sensitivity (development, level M, 3 seeds, 150 episodes)", "",
             "U = (late + unverified) / incidents. Differences are first minus second; negative = first is better. A8 = plan's full cover; A8c = location cover (post-hoc).", "",
             "| Setting | A0 gold | A1 commit | A6 conf. gate | A8 | A8c | A10 | A12 oracle | A8 - A6 (95% CI) | A8c - A6 (95% CI) | A8c - A1 | requests/report A6 / A8 | A8 timeouts | A8 allocator runs / report | A8 decision ms median / p99 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    out = {}
    for tag, text in ROWS:
        recs = load(tag)
        if not recs:
            continue
        T = devrun.arm_table(recs)
        p86 = devrun.paired(recs, "A8", "A6")
        pc6 = devrun.paired(recs, "A8c", "A6")
        pc1 = devrun.paired(recs, "A8c", "A1")
        to = sum(v for k, v in T["A8"]["outcome_classes"].items() if k.startswith("TIMEOUT"))
        f = lambda a: "%.1f%%" % (100 * T[a]["U_deadline"])                                       # noqa: E731
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %+.2f pp (%+.2f to %+.2f) | %+.2f pp (%+.2f to %+.2f) | %+.2f pp | %.3f / %.3f | %d | %.2f | %.2f / %.2f |" % (
            text, f("A0"), f("A1"), f("A6"), f("A8"), f("A8c"), f("A10"), f("A12"), 100 * p86["diff_U"], 100 * p86["ci"][0], 100 * p86["ci"][1],
            100 * pc6["diff_U"], 100 * pc6["ci"][0], 100 * pc6["ci"][1], 100 * pc1["diff_U"], T["A6"]["request_rate"], T["A8"]["request_rate"], to,
            T["A8"]["allocator_runs_per_report"], T["A8"]["wall_ms_median"], T["A8"]["wall_ms_p99"]))
        out[tag] = {"arms": {a: T[a]["U_deadline"] for a in ("A0", "A1", "A6", "A8", "A8c", "A10", "A12")}, "A8-A6": p86, "A8c-A6": pc6, "A8c-A1": pc1, "timeouts_A8": to}
    text = "\n".join(lines)
    (paths.RESULTS / "dev" / "SENSITIVITY.md").write_text(text + "\n", encoding="utf-8")
    (paths.RESULTS / "dev" / "SENSITIVITY.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
