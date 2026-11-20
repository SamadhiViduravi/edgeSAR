"""Allocator-time sensitivity (docs/ITERATION1_ALLOC_SENSITIVITY.md): compare the 20 ms results with the 0.22 ms results. Applies the rule written before the run."""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_iter1 import load, table_for                          # noqa: E402
from shield import devrun, paths                                   # noqa: E402

PAIRS = [("B3", "G1"), ("B3", "A1"), ("B3", "A8"), ("A8", "A1")]
out = {"rule": "ASSUMPTION MATTERS if any of the four paired differences at M changes by >= 0.3 pp or changes CI status (contains 0 or not); else DOES NOT MATTER", "readouts": {}}
md = ["# Allocator-time sensitivity: 20 ms (original) vs 0.22 ms (measured)", "", "Protocol: `docs/ITERATION1_ALLOC_SENSITIVITY.md` (fixed before the run). Development data. Original results are unchanged.", ""]
matters = False
for ro, (t20, t02) in {"competent Q4 head": ("q4", "alloc022_q4"), "unadapted head (raw)": ("raw", "alloc022_raw")}.items():
    r20, r02 = load(t20)[0], load(t02)[0]
    A20, A02 = table_for(r20, "M"), table_for(r02, "M")
    md += ["## %s, level M" % ro, "", "| arm | missed 20 ms | missed 0.22 ms |", "|---|---|---|"]
    t20_, t02_ = devrun.arm_table(A20), devrun.arm_table(A02)
    for arm in ["A0", "A1", "A2", "A6", "A8", "A8c", "B1", "B2", "B3", "B4", "G1", "A12"]:
        if arm in t20_ and arm in t02_:
            md.append("| %s | %.2f%% | %.2f%% |" % (arm, 100 * t20_[arm]["U_deadline"], 100 * t02_[arm]["U_deadline"]))
    md += ["", "| paired (first minus second) | 20 ms: pp (95% CI) | 0.22 ms: pp (95% CI) | change (pp) | CI status changed |", "|---|---|---|---|---|"]
    out["readouts"][ro] = {}
    for x, y in PAIRS:
        p0, p1 = devrun.paired(A20, x, y), devrun.paired(A02, x, y)
        d0, d1 = 100 * p0["diff_U"], 100 * p1["diff_U"]
        z0, z1 = p0["ci"][0] <= 0 <= p0["ci"][1], p1["ci"][0] <= 0 <= p1["ci"][1]
        ch = abs(d1 - d0) >= 0.3 or (z0 != z1)
        matters |= ch
        out["readouts"][ro]["%s-%s" % (x, y)] = {"pp_20ms": d0, "ci_20ms": [100 * p0["ci"][0], 100 * p0["ci"][1]], "pp_022ms": d1, "ci_022ms": [100 * p1["ci"][0], 100 * p1["ci"][1]], "change_pp": d1 - d0, "ci_status_changed": z0 != z1, "flag": ch}
        md.append("| %s - %s | %+.2f (%+.2f to %+.2f) | %+.2f (%+.2f to %+.2f) | %+.2f | %s |" % (x, y, d0, 100 * p0["ci"][0], 100 * p0["ci"][1], d1, 100 * p1["ci"][0], 100 * p1["ci"][1], d1 - d0, "yes" if z0 != z1 else "no"))
    md.append("")
out["finding"] = "ASSUMPTION MATTERS" if matters else "ASSUMPTION DOES NOT MATTER"
md += ["## Finding (rule fixed in advance)", "", "**%s**" % out["finding"]]
(paths.RESULTS / "iter1" / "ALLOC_SENSITIVITY.md").write_text("\n".join(md) + "\n", encoding="utf-8")
(paths.RESULTS / "iter1" / "ALLOC_SENSITIVITY.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("\n".join(md))
