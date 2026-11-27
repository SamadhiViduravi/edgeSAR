"""Post hoc analysis of the check confirmation (manuscript v2.15, Section V-L). NOT pre-specified.

For each of the 12 conditions (target, set, load) it ranks only the six label-free options
(unchanged, recentering, map, pseudo-label retraining, CORAL, Procrustes) and reports:
  - the Spearman correlation between the check penalty and the true penalty over these six options,
  - the option with the smallest check penalty (the pick), the option with the smallest true penalty (the best)
    and the loss of the pick in true penalty (pp),
  - the gap between the two smallest check penalties (pp) and the rank of the best option by check penalty.
Input: results/check_results.json (the archived output of the single, frozen analysis run).
Usage: python posthoc_six_options.py results/check_results.json > results/posthoc_six_options.md
Needs Python 3 and scipy (numpy for the median).
"""
import json, sys
import numpy as np
from scipy.stats import spearmanr

NAMES = {'rawp': 'unchanged', 'recp': 'recentering', 'alnp': 'map', 'plp': 'pseudo-labels', 'coral': 'CORAL', 'proc': 'Procrustes'}
d = json.load(open(sys.argv[1]))
lf = d['label_free_options']
rows = d['rows']
out = []
rhos = []
for cond in d['conditions']:
    t, s, l = cond.split()
    rr = [r for r in rows if r['target'] == t and r['set'] == s and r['level'] == l and r['arm'] in lf]
    assert len(rr) == 6, (cond, len(rr))
    rho = spearmanr([r['check_pp'] for r in rr], [r['true_pp'] for r in rr]).correlation
    rhos.append(rho)
    by_check = sorted(rr, key=lambda r: r['check_pp'])
    pick, best = by_check[0], min(rr, key=lambda r: r['true_pp'])
    gap = by_check[1]['check_pp'] - by_check[0]['check_pp']
    rank_best = [r['arm'] for r in by_check].index(best['arm']) + 1
    out.append((cond, rho, NAMES[pick['arm']], NAMES[best['arm']], pick['true_pp'] - best['true_pp'], gap, rank_best))

print('# Post hoc: the check over the six label-free options only (not pre-specified)\n')
print('Source: `results/check_results.json` (single run of the frozen script). Script: `posthoc_six_options.py`.\n')
print('| Condition (target, set, load) | Spearman, six options | Pick by check | Best by true penalty | Loss of pick (pp) | Gap between two smallest check penalties (pp) | Rank of best by check |')
print('|---|---:|---|---|---:|---:|---:|')
for c, rho, p, b, loss, gap, rk in out:
    print(f'| {c} | {rho:.2f} | {p} | {b} | {loss:.2f} | {gap:.2f} | {rk} |')
print(f'\nSpearman over the six options: {min(rhos):.2f} to {max(rhos):.2f} (median {np.median(rhos):.2f}).')
misses = [o for o in out if o[4] > 0.25]
print(f'Conditions where the pick lost more than 0.25 pp (the H3 failures): {", ".join(o[0] for o in misses)}; '
      f'their top-two check gaps: {", ".join(f"{o[5]:.2f}" for o in misses)} pp.')
print(f'The best option was among the two smallest check penalties in {sum(o[6] <= 2 for o in out)} of {len(out)} conditions.')
