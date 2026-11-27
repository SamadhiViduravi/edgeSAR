# Post hoc: the check over the six label-free options only (not pre-specified)

Source: `results/check_results.json` (single run of the frozen script). Script: `posthoc_six_options.py`.

| Condition (target, set, load) | Spearman, six options | Pick by check | Best by true penalty | Loss of pick (pp) | Gap between two smallest check penalties (pp) | Rank of best by check |
|---|---:|---|---|---:|---:|---:|
| Q4_K_M C1 L | 0.83 | map | Procrustes | 0.05 | 0.02 | 3 |
| Q4_K_M C1 M | 1.00 | pseudo-labels | pseudo-labels | 0.00 | 0.05 | 1 |
| Q4_K_M C1 H | 0.94 | map | pseudo-labels | 0.33 | 0.15 | 2 |
| Q4_K_M C2 L | 0.99 | pseudo-labels | pseudo-labels | 0.00 | 0.00 | 1 |
| Q4_K_M C2 M | 0.99 | map | pseudo-labels | 0.18 | 0.00 | 2 |
| Q4_K_M C2 H | 0.75 | map | pseudo-labels | 0.94 | 0.03 | 2 |
| Q3_K_M C1 L | 0.99 | map | map | 0.00 | 0.05 | 1 |
| Q3_K_M C1 M | 0.94 | pseudo-labels | map | 0.18 | 0.07 | 2 |
| Q3_K_M C1 H | 0.94 | map | map | 0.00 | 0.28 | 1 |
| Q3_K_M C2 L | 1.00 | map | map | 0.00 | 0.03 | 1 |
| Q3_K_M C2 M | 1.00 | map | map | 0.00 | 0.31 | 1 |
| Q3_K_M C2 H | 1.00 | map | map | 0.00 | 0.80 | 1 |

Spearman over the six options: 0.75 to 1.00 (median 0.99).
Conditions where the pick lost more than 0.25 pp (the H3 failures): Q4_K_M C1 H, Q4_K_M C2 H; their top-two check gaps: 0.15, 0.03 pp.
The best option was among the two smallest check penalties in 11 of 12 conditions.
