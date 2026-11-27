"""Post hoc analyses of the check confirmation (manuscript v2.16, Section V-L). NOT pre-specified; descriptive.

Input: results/check_results.json (the archived output of the single run of the frozen analysis script).
Usage: python posthoc_check_analyses.py results/check_results.json > results/posthoc_check_analyses.md
Needs Python 3, numpy and scipy.

Part A - the six label-free options only. For each of the 12 conditions (target, set, load) it ranks the six
label-free options (unchanged, recentering, map, pseudo-label retraining, CORAL, Procrustes) and reports the
Spearman correlation between the check penalty and the true penalty, the option picked by the check (smallest
check penalty), the best option (smallest true penalty), the loss of the pick in true penalty (pp), the gap
between the two smallest check penalties (pp) and the rank of the best option by check penalty.
(Same numbers as posthoc_six_options.py of v2.15, which it replaces.)

Part B - label draws averaged. Thirty of the 39 candidates are five label draws (d0..d4) of six
method-and-budget combinations (retraining, bias recalibration and vector scaling, each with 100 or 300 labels).
Averaging the five draws of each combination (check penalty, true penalty, record flips and labeled accuracy
drop) leaves 15 options per condition: the six combinations plus rawp, recp, alnp, plp, coral, proc, ret1000,
tfidf and rule. For each condition it reports the Spearman correlation of the check penalty, of the share of
changed records (flips) and of the labeled accuracy drop with the true penalty over these 15 options.
"""
import json, sys
from collections import defaultdict
import numpy as np
from scipy.stats import spearmanr

NAMES = {'rawp': 'unchanged', 'recp': 'recentering', 'alnp': 'map', 'plp': 'pseudo-labels', 'coral': 'CORAL', 'proc': 'Procrustes'}
d = json.load(open(sys.argv[1]))
lf = d['label_free_options']
rows = d['rows']
conds = list(d['conditions'])


def rows_of(cond):
    t, s, l = cond.split()
    return [r for r in rows if r['target'] == t and r['set'] == s and r['level'] == l]


print('# Post hoc analyses of the check confirmation (not pre-specified; descriptive)\n')
print('Source: `results/check_results.json` (single run of the frozen script). Script: `posthoc_check_analyses.py`.\n')

# ---------------- Part A ----------------
print('## A. The six label-free options only\n')
print('| Condition (target, set, load) | Spearman, six options | Pick by check | Best by true penalty | Loss of pick (pp) | Gap between two smallest check penalties (pp) | Rank of best by check |')
print('|---|---:|---|---|---:|---:|---:|')
outA, rhosA = [], []
for cond in conds:
    rr = [r for r in rows_of(cond) if r['arm'] in lf]
    assert len(rr) == 6, (cond, len(rr))
    rho = spearmanr([r['check_pp'] for r in rr], [r['true_pp'] for r in rr]).correlation
    rhosA.append(rho)
    by_check = sorted(rr, key=lambda r: r['check_pp'])
    pick, best = by_check[0], min(rr, key=lambda r: r['true_pp'])
    gap = by_check[1]['check_pp'] - by_check[0]['check_pp']
    rank_best = [r['arm'] for r in by_check].index(best['arm']) + 1
    loss = pick['true_pp'] - best['true_pp']
    outA.append((cond, rho, NAMES[pick['arm']], NAMES[best['arm']], loss, gap, rank_best))
    print(f'| {cond} | {rho:.2f} | {NAMES[pick["arm"]]} | {NAMES[best["arm"]]} | {loss:.2f} | {gap:.2f} | {rank_best} |')
print(f'\nSpearman over the six options: {min(rhosA):.2f} to {max(rhosA):.2f} (median {np.median(rhosA):.2f}).')
print(f'The pick was the best option in {sum(o[4] == 0 for o in outA)} of {len(outA)} conditions and within 0.25 pp of it in '
      f'{sum(o[4] <= 0.25 for o in outA)} of {len(outA)} (largest loss {max(o[4] for o in outA):.2f} pp).')
misses = [o for o in outA if o[4] > 0.25]
print(f'Conditions where the pick lost more than 0.25 pp (the H3 failures): {", ".join(o[0] for o in misses)}; '
      f'their top-two check gaps: {", ".join(f"{o[5]:.2f}" for o in misses)} pp.')
print(f'The best option was among the two smallest check penalties in {sum(o[6] <= 2 for o in outA)} of {len(outA)} conditions.\n')

# ---------------- Part B ----------------
print('## B. Label draws averaged (15 options per condition)\n')
print('| Condition (target, set, load) | Options | Spearman: check penalty | Spearman: record flips | Spearman: labeled accuracy drop |')
print('|---|---:|---:|---:|---:|')
outB = []
for cond in conds:
    groups = defaultdict(list)
    for r in rows_of(cond):
        key = r['arm'].split('_d')[0] if '_d' in r['arm'] else r['arm']
        groups[key].append(r)
    assert all(len(v) == 5 for k, v in groups.items() if k[-3:] in ('100', '300')), cond
    opts = {k: {f: float(np.mean([x[f] for x in v])) for f in ('true_pp', 'check_pp', 'flips', 'accuracy_drop')}
            for k, v in groups.items()}
    true = [o['true_pp'] for o in opts.values()]
    sc = spearmanr([o['check_pp'] for o in opts.values()], true).correlation
    sf = spearmanr([o['flips'] for o in opts.values()], true).correlation
    sa = spearmanr([o['accuracy_drop'] for o in opts.values()], true).correlation
    outB.append((cond, len(opts), sc, sf, sa))
    print(f'| {cond} | {len(opts)} | {sc:.3f} | {sf:.3f} | {sa:.3f} |')
sc = [o[2] for o in outB]; sf = [o[3] for o in outB]; sa = [o[4] for o in outB]
print(f'\nCheck penalty: {min(sc):.3f} to {max(sc):.3f}; record flips: {min(sf):.3f} to {max(sf):.3f}; '
      f'labeled accuracy drop: {min(sa):.3f} to {max(sa):.3f}.')
print(f'The check correlated more strongly than the flips in {sum(o[2] > o[3] for o in outB)} of {len(outB)} conditions; '
      f'the labeled accuracy drop correlated more strongly than the check in {sum(o[4] > o[2] for o in outB)} of {len(outB)} '
      f'({", ".join(o[0] for o in outB if o[4] > o[2])}).')
