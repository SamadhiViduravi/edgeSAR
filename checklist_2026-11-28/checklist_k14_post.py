"""
K14 post-processing (exploratory, 28 Nov 2026): two numbers quoted in the paper that checklist_k14.py did not write itself, computed from
its saved per-episode counts (no refitting, no simulation):
  - pseudo-label retraining minus the map, both fitted on the 400 development style-B reports (paired episode bootstrap, as in K14);
  - the range of single-draw missed shares for the 100- and 300-pair draws.

    python checklist_k14_post.py out_full/checklist_k14_episode_counts.json.gz out_full/checklist_k14_post_results.json
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from checklist_k14 import N_DRAWS, paired_arrays  # noqa: E402

E = json.load(gzip.open(sys.argv[1], "rt", encoding="utf-8"))
NN = np.array(E["incidents"], float)
M = {k: np.array(v, float) for k, v in E["missed"].items()}
res = {"note": "Computed from checklist_k14_episode_counts.json.gz; percentages of %d incidents." % int(NN.sum()),
       "comparisons": {"dev400_pl - dev400_map": paired_arrays(M["dev400_pl"], M["dev400_map"], NN),
                       "B_all_pl - B_all_map": paired_arrays(M["B_all_pl"], M["B_all_map"], NN)},
       "single_draw_share_pct": {}}
for pref in ("A_n100", "A_n300", "B_n100", "B_n300"):
    per = [100 * M["%s_d%d" % (pref, d)].sum() / NN.sum() for d in range(N_DRAWS)]
    res["single_draw_share_pct"][pref] = {"min": min(per), "max": max(per)}
Path(sys.argv[2]).write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
