"""Fig. 4: the label-free mission check against the true mission penalty (R10, exploratory).

    python review_r10_fig4.py review_results_r10.json [output folder]
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42, "ps.fonttype": 42})
INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"
# first three slots of the validated categorical palette (all-pairs safe); marker shape is the second encoding
FAM = {"fp16_derived": ("#2a78d6", "o", "FP16 classifier reused (unchanged, recentered, map, recalibrated)"),
       "retrained": ("#1baf7a", "s", "Retrained on Q4 (100, 300 or 1,000 labels)"),
       "text": ("#eb6834", "^", "Text only (TF-IDF, rules)")}
NAMES = {"A": {"rawp": "unchanged", "alnp": "map", "tfidf": "TF-IDF, rules"},
         "B": {"rawp": "unchanged", "alnp": "map", "tfidf": "TF-IDF", "rule": "rules"}}


def family(arm):
    if arm in ("tfidf", "rule"):
        return "text"
    return "retrained" if arm.startswith("q4p") else "fp16_derived"


if len(sys.argv) < 2:
    sys.exit(__doc__)
rows = json.load(open(sys.argv[1]))["rows"]
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "."
cols = [("referee_pp", "Label-free mission check (pp)"), ("disagree_any", "Records changed vs. old records (%)"),
        ("accuracy_drop", "Accuracy drop vs. gold labels (points)")]
conds = [("A", "M", "Set A (familiar wording), medium load"), ("B", "M", "Set B (new wording), medium load")]
fig, axs = plt.subplots(2, 3, figsize=(7.1, 4.6))
for r_, (st, lev, title) in enumerate(conds):
    sel = [x for x in rows if x["set"] == st and x["level"] == lev]
    t = [x["true_pp"] for x in sel]
    for c_, (key, lab) in enumerate(cols):
        ax = axs[r_][c_]
        for fam, (col, mk, _) in FAM.items():
            fs = [x for x in sel if family(x["arm"]) == fam]
            ax.scatter([x["true_pp"] for x in fs], [x[key] for x in fs], s=14, c=col, marker=mk, edgecolors="white", linewidths=0.4, zorder=3)
        if key == "referee_pp":
            lo = min(min(t), min(x[key] for x in sel)) - 0.3
            hi = max(max(t), max(x[key] for x in sel)) + 0.3
            ax.plot([lo, hi], [lo, hi], ls="--", lw=0.7, color=MUTED, zorder=1)
            ax.text(lo + 0.45 * (hi - lo), lo + 0.45 * (hi - lo) - 0.06 * (hi - lo), "equal values", fontsize=5.8, color=MUTED, ha="left", va="top")
        for x in sel:
            if x["arm"] in NAMES[st]:
                ax.annotate(NAMES[st][x["arm"]], (x["true_pp"], x[key]), xytext=(4, -1), textcoords="offset points", fontsize=5.8, color=INK, va="center")
        rho = spearmanr([x[key] for x in sel], t)[0]
        ax.text(0.97, 0.04, "Spearman %.2f" % rho, transform=ax.transAxes, fontsize=6.8, ha="right", va="bottom", color=INK, zorder=2,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=GRID, lw=0.5))
        ax.margins(x=0.12, y=0.1)
        ax.grid(color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=6.5)
        if r_ == 1:
            ax.set_xlabel("True penalty (pp)", fontsize=7)
        if r_ == 0:
            ax.set_title(lab, fontsize=7.2)
        if c_ == 0:
            ax.set_ylabel(title.replace(", ", ",\n"), fontsize=7)
handles = [plt.Line2D([], [], ls="", marker=mk, color=col, markersize=4.5, label=lab_) for col, mk, lab_ in FAM.values()]
fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(OUTDIR + "/fig4_check.pdf", bbox_inches="tight")
fig.savefig(OUTDIR + "/fig4_check.png", dpi=600, bbox_inches="tight")
plt.close(fig)
print("fig4 written")
