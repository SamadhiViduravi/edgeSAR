# Post hoc analyses of the check confirmation (not pre-specified; descriptive)

Source: `results/check_results.json` (single run of the frozen script). Script: `posthoc_check_analyses.py`.

## A. The six label-free options only

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
The pick was the best option in 7 of 12 conditions and within 0.25 pp of it in 10 of 12 (largest loss 0.94 pp).
Conditions where the pick lost more than 0.25 pp (the H3 failures): Q4_K_M C1 H, Q4_K_M C2 H; their top-two check gaps: 0.15, 0.03 pp.
The best option was among the two smallest check penalties in 11 of 12 conditions.

## B. Label draws averaged (15 options per condition)

| Condition (target, set, load) | Options | Spearman: check penalty | Spearman: record flips | Spearman: labeled accuracy drop |
|---|---:|---:|---:|---:|
| Q4_K_M C1 L | 15 | 0.882 | 0.561 | 0.850 |
| Q4_K_M C1 M | 15 | 0.904 | 0.607 | 0.907 |
| Q4_K_M C1 H | 15 | 0.896 | 0.657 | 0.968 |
| Q4_K_M C2 L | 15 | 0.978 | 0.632 | 0.739 |
| Q4_K_M C2 M | 15 | 0.952 | 0.769 | 0.856 |
| Q4_K_M C2 H | 15 | 0.868 | 0.754 | 0.872 |
| Q3_K_M C1 L | 15 | 0.999 | 0.838 | 0.913 |
| Q3_K_M C1 M | 15 | 0.987 | 0.886 | 0.946 |
| Q3_K_M C1 H | 15 | 0.974 | 0.893 | 0.954 |
| Q3_K_M C2 L | 15 | 0.968 | 0.779 | 0.839 |
| Q3_K_M C2 M | 15 | 0.964 | 0.832 | 0.896 |
| Q3_K_M C2 H | 15 | 0.900 | 0.800 | 0.854 |

Check penalty: 0.868 to 0.999; record flips: 0.561 to 0.893; labeled accuracy drop: 0.739 to 0.968.
The check correlated more strongly than the flips in 12 of 12 conditions; the labeled accuracy drop correlated more strongly than the check in 3 of 12 (Q4_K_M C1 M, Q4_K_M C1 H, Q4_K_M C2 H).
