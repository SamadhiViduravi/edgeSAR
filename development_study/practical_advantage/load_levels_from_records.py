"""Post-hoc re-analysis of EXISTING mission records (no new run, no new model call, no tuning).
Shows the all-label arms at the three load levels L, M, H (reading position `prefix`), episode-paired.
   python load_levels_from_records.py --root <root2> --records <dir with records_{L,M,H}_s{1,2,3}.json.gz> --out out_levels
Status: exploratory, development data. Pooled intervals are optimistic (arrival seeds reuse the same reports)."""
import argparse, gzip, json, os, sys
from pathlib import Path
sys.dont_write_bytecode = True
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--records", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
os.environ["EDGESAR_ROOT"] = str(Path(a.root).resolve())
sys.path.insert(0, str(Path(a.root).resolve() / "edgesar_shield"))
from shield import devrun
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
ARMS = [("gold", "Gold records"), ("f16p", "F16 reader"), ("q4p", "Q4 retrained, all labels"), ("alnp", "Q4 label-free map"), ("recp", "Q4 recentred"), ("rawp", "Q4 unchanged transfer")]
PAIRS = [("alnp", "q4p"), ("alnp", "recp"), ("recp", "q4p"), ("q4p", "f16p"), ("alnp", "f16p"), ("rawp", "q4p")]
res = {}; md = ["# All-label arms at three load levels (existing records; post-hoc re-analysis; exploratory)", "",
                "Reading position `prefix`, 3 arrival seeds x 50 episodes = 150 episodes and 5,505 incidents per level. No new run. Pooled intervals are optimistic (the seeds reuse the same reports).", ""]
for lev in "LMH":
    recs = []
    for s in (1, 2, 3):
        recs += json.load(gzip.open(Path(a.records) / ("records_%s_s%d.json.gz" % (lev, s))))
    res[lev] = {"arms": {}, "paired": {}}
    md += ["## Level %s" % lev, "", "| Arm | Missed share | 95% CI |", "|---|---|---|"]
    for arm, name in ARMS:
        eps = [r for r in recs if r["arm"] == arm]
        m = sum(r["counts"]["late"] + r["counts"]["unverified"] for r in eps); n = sum(r["counts"]["n"] for r in eps)
        lo, hi = devrun.episode_bootstrap_ci(recs, arm)
        res[lev]["arms"][arm] = {"missed": m, "incidents": n, "share": m / n, "ci": [lo, hi], "episodes": len(eps)}
        md.append("| %s | %.2f%% | %.2f to %.2f |" % (name, 100 * m / n, 100 * lo, 100 * hi))
    md += ["", "| First minus second (pp) | Difference | 95% CI | Episodes first better / worse / tied |", "|---|---|---|---|"]
    for x, y in PAIRS:
        p = devrun.paired(recs, x, y); res[lev]["paired"]["%s-%s" % (x, y)] = p
        md.append("| %s minus %s | %+.2f | %+.2f to %+.2f | %d / %d / %d |" % (x, y, 100 * p["diff_U"], 100 * p["ci"][0], 100 * p["ci"][1], p["wins_x"], p["wins_y"], p["ties"]))
    md.append("")
(out / "LOAD_LEVELS_RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
(out / "load_levels.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("\n".join(md))
