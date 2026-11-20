# Development results: raw

Saved vectors, 1,000 style-A reports, 5 outer folds, 3 seed(s) [1, 2, 3]; overlay episodes of 20 reports sharing one fleet; verification budget b = 0.1 of reports (hard cap per episode), delay d_v = 60.0 s; alpha = 0.1, K = 8, allocator cbba_bounded, readout raw. EVAL reports only. Style B untouched.

U_deadline = (late + unverified) / incidents. Lower is better. CI = episode bootstrap, seeds pooled (optimistic: seeds re-use the same reports).

## Level M

### Outcomes and costs

| Arm | System | U_deadline (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 4.9% (4.1% to 5.8%) | 269 | 2 | 0.000 | 0.000 | 0 (0) | 1076 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 16.5% (15.6% to 17.4%) | 218 | 690 | 0.000 | 0.164 | 0 (0) | 1079 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 15.8% (14.8% to 16.8%) | 211 | 660 | 0.075 | 0.145 | 0 (0) | 1078 | 4.5 | 0.00 | 0.01 / 0.04 |
| A6b | Top-record-score gate | 16.2% (15.2% to 17.2%) | 216 | 676 | 0.074 | 0.134 | 0 (0) | 1073 | 4.5 | 0.00 | 0.01 / 0.03 |
| A7 | Random gate | 15.8% (14.9% to 16.7%) | 225 | 644 | 0.072 | 0.163 | 0 (0) | 1082 | 4.3 | 0.00 | 0.01 / 0.03 |
| A8 | Shield + full cover fallback (plan) | 10.3% (9.2% to 11.4%) | 528 | 41 | 0.069 | 0.237 | 955 (296) | 1165 | 4.1 | 3.58 | 0.46 / 4.97 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 8.2% (7.1% to 9.2%) | 408 | 41 | 0.069 | 0.331 | 1051 (392) | 1224 | 4.1 | 3.58 | 0.44 / 5.19 |
| A9 | Shield, singleton sets only | 10.2% (9.0% to 11.3%) | 522 | 38 | 0.074 | 0.230 | 944 (292) | 1167 | 4.5 | 1.40 | 0.29 / 1.40 |
| A10 | Shield, no fallback | 16.3% (15.4% to 17.3%) | 213 | 685 | 0.069 | 0.134 | 0 (0) | 1062 | 4.1 | 2.95 | 0.26 / 3.17 |
| A12 | Oracle gate (diagnostic upper bound) | 14.2% (13.3% to 15.1%) | 213 | 566 | 0.100 | 0.145 | 0 (0) | 1094 | 6.0 | 0.00 | 0.00 / 0.01 |

Episodes per arm: 150, incidents per arm: 5505, reports per arm: 3000. Request rates should be near b = 0.1; the cap is 2 request(s) per 20-report episode.

### Paired comparisons (same episodes)

Difference in U_deadline (first minus second); negative = first is better. Per-seed differences in the last column.

| Comparison | diff (95% CI) | missed incidents: first / second | unverified: first / second | sign-flip p | episodes won / lost / tied | per seed |
|---|---|---|---|---|---|---|
| A8 vs A6: PRIMARY: Shield+cover vs confidence gate (same budget) | -5.49 pp (-6.53 to -4.43) | 569 / 871 | 41 / 660 | 0.000 | 115 / 25 / 10 | -5.6, -6.8, -4.0 |
| A8 vs A6b: Shield+cover vs record-score gate | -5.87 pp (-6.90 to -4.82) | 569 / 892 | 41 / 676 | 0.000 | 122 / 23 / 5 | -6.0, -7.0, -4.6 |
| A8 vs A7: Shield+cover vs random gate | -5.45 pp (-6.50 to -4.40) | 569 / 869 | 41 / 644 | 0.000 | 114 / 24 / 12 | -5.3, -6.4, -4.6 |
| A8 vs A1: Shield+cover vs always commit | -6.16 pp (-7.23 to -5.07) | 569 / 908 | 41 / 690 | 0.000 | 121 / 23 / 6 | -5.9, -7.3, -5.2 |
| A8c vs A6: REVISED (post-hoc): Shield+location cover vs confidence gate | -7.67 pp (-8.59 to -6.74) | 449 / 871 | 41 / 660 | 0.000 | 129 / 9 / 12 | -7.5, -8.1, -7.5 |
| A8c vs A1: Shield+location cover vs always commit | -8.34 pp (-9.29 to -7.37) | 449 / 908 | 41 / 690 | 0.000 | 131 / 8 / 11 | -7.8, -8.6, -8.7 |
| A8c vs A8: location cover vs full cover | -2.18 pp (-2.90 to -1.47) | 449 / 569 | 41 / 41 | 0.000 | 79 / 17 / 54 | -1.9, -1.3, -3.4 |
| A8c vs A10: location cover vs no fallback | -8.16 pp (-9.08 to -7.21) | 449 / 898 | 41 / 685 | 0.000 | 132 / 11 / 7 | -7.4, -8.7, -8.4 |
| A8 vs A10: fallback effect: with cover vs without | -5.98 pp (-7.01 to -4.92) | 569 / 898 | 41 / 685 | 0.000 | 117 / 22 / 11 | -5.5, -7.4, -5.0 |
| A8 vs A9: conformal sets vs singleton sets only | +0.16 pp (-0.38 to +0.72) | 569 / 560 | 41 / 38 | 0.602 | 22 / 29 / 99 | -0.4, -0.2, +1.1 |
| A10 vs A6: Shield without fallback vs confidence gate | +0.49 pp (+0.11 to +0.87) | 898 / 871 | 685 / 660 | 0.014 | 16 / 37 / 97 | -0.1, +0.6, +1.0 |
| A6 vs A1: confidence gate vs always commit | -0.67 pp (-1.02 to -0.31) | 871 / 908 | 660 / 690 | 0.000 | 40 / 7 / 103 | -0.3, -0.5, -1.2 |
| A12 vs A1: HEADROOM: perfect gate vs always commit | -2.34 pp (-2.93 to -1.77) | 779 / 908 | 566 / 690 | 0.000 | 94 / 21 / 35 | -2.2, -2.6, -2.2 |
| A1 vs A0: record-induced misses of the Q4 head (vs gold records) | +11.57 pp (+10.68 to +12.44) | 908 / 271 | 690 / 2 | 0.000 | 3 / 144 / 3 | +11.4, +11.7, +11.6 |

### What the Shield decided

| Outcome class | A8 reports | A8 share | A8c reports | A8c share |
|---|---|---|---|---|
| ACCEPT | 894 | 29.8% | 905 | 30.2% |
| ACCEPT_INFEASIBLE | 21 | 0.7% | 10 | 0.3% |
| ESCALATE | 207 | 6.9% | 207 | 6.9% |
| FALLBACK_COVERED | 1362 | 45.4% | 944 | 31.5% |
| FALLBACK_PARTIAL | 407 | 13.6% | 896 | 29.9% |
| FALLBACK_UNRESOLVED | 109 | 3.6% | 38 | 1.3% |

Certified (ACCEPT + ACCEPT_INFEASIBLE): 30.5% of reports; certified AND the committed plan differs from the gold plan: 30 reports = 1.00% of all reports (the marginal guarantee is <= alpha = 0.1, on exchangeable data). Set sizes of certified reports: {1: 915}.

### Which reports does each method flag? (reports whose best-guess record would have given a wrong plan)

| Arm | flagged (verify or cover) | of which wrong-plan | wrong-plan reports flagged (recall) | flagged that were wrong-plan (precision) | wrong-plan reports left unflagged, share of ALL reports |
|---|---|---|---|---|---|
| A1 | 0 (0.0%) | 0 | 0.0% | - | 42.0% |
| A6 | 226 (7.5%) | 122 | 9.7% | 54.0% | 37.8% |
| A6b | 223 (7.4%) | 148 | 11.8% | 66.4% | 37.0% |
| A7 | 217 (7.2%) | 89 | 7.1% | 41.0% | 39.0% |
| A8 | 2085 (69.5%) | 1241 | 97.6% | 59.5% | 1.0% |
| A8c | 2085 (69.5%) | 1237 | 97.6% | 59.3% | 1.0% |
| A9 | 2085 (69.5%) | 1234 | 97.6% | 59.2% | 1.0% |
| A10 | 207 (6.9%) | 153 | 12.2% | 73.9% | 36.9% |
| A12 | 300 (10.0%) | 273 | 21.5% | 91.0% | 33.1% |

### Equal-budget ranking: share of the wrong-plan reports caught when each method flags its top f of every episode

3000 reports, 1260 of them with a wrong plan. The OBS arm behaves exactly like A1 and logs every method's risk score.

| Ranking by | f = 5% | f = 10% | f = 20% | f = 30% | AUROC |
|---|---|---|---|---|---|
| A8 Shield (rho, 1-score) | 8.7% | 17.1% | 32.5% | 47.6% | 0.790 |
| A9 singleton-only | 8.9% | 16.6% | 30.0% | 44.5% | 0.778 |
| A11 top-2 what-if | 7.4% | 15.2% | 30.5% | 45.2% | 0.704 |
| A6 confidence | 6.4% | 12.1% | 23.9% | 35.0% | 0.595 |
| A6b record score | 8.9% | 16.6% | 30.0% | 44.5% | 0.776 |
| random | 4.4% | 8.9% | 19.0% | 29.2% | 0.500 |

## Level H

### Outcomes and costs

| Arm | System | U_deadline (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 13.4% (12.1% to 14.7%) | 700 | 39 | 0.000 | 0.000 | 0 (0) | 772 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 22.6% (21.3% to 23.8%) | 539 | 703 | 0.000 | 0.156 | 0 (0) | 769 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 22.0% (20.7% to 23.2%) | 536 | 673 | 0.075 | 0.133 | 0 (0) | 763 | 4.5 | 0.00 | 0.01 / 0.04 |
| A6b | Top-record-score gate | 22.1% (20.9% to 23.4%) | 530 | 689 | 0.074 | 0.120 | 0 (0) | 759 | 4.5 | 0.00 | 0.01 / 0.03 |
| A7 | Random gate | 22.4% (21.0% to 23.7%) | 574 | 658 | 0.072 | 0.155 | 0 (0) | 766 | 4.3 | 0.00 | 0.01 / 0.03 |
| A8 | Shield + full cover fallback (plan) | 21.0% (19.7% to 22.2%) | 1031 | 125 | 0.069 | 0.228 | 959 (300) | 837 | 4.1 | 3.58 | 0.97 / 13.23 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 17.9% (16.7% to 19.2%) | 890 | 96 | 0.069 | 0.309 | 1028 (370) | 845 | 4.1 | 3.58 | 1.02 / 13.99 |
| A9 | Shield, singleton sets only | 20.6% (19.3% to 21.8%) | 1002 | 132 | 0.074 | 0.222 | 946 (294) | 832 | 4.5 | 1.40 | 0.71 / 3.71 |
| A10 | Shield, no fallback | 22.4% (21.2% to 23.7%) | 540 | 694 | 0.069 | 0.119 | 0 (0) | 760 | 4.1 | 2.95 | 0.64 / 8.81 |
| A12 | Oracle gate (diagnostic upper bound) | 21.2% (19.9% to 22.4%) | 590 | 576 | 0.100 | 0.137 | 0 (0) | 766 | 6.0 | 0.00 | 0.01 / 0.01 |

Episodes per arm: 150, incidents per arm: 5505, reports per arm: 3000. Request rates should be near b = 0.1; the cap is 2 request(s) per 20-report episode.

### Paired comparisons (same episodes)

Difference in U_deadline (first minus second); negative = first is better. Per-seed differences in the last column.

| Comparison | diff (95% CI) | missed incidents: first / second | unverified: first / second | sign-flip p | episodes won / lost / tied | per seed |
|---|---|---|---|---|---|---|
| A8 vs A6: PRIMARY: Shield+cover vs confidence gate (same budget) | -0.96 pp (-2.19 to +0.27) | 1156 / 1209 | 125 / 673 | 0.139 | 72 / 56 / 22 | -0.3, -1.4, -1.2 |
| A8 vs A6b: Shield+cover vs record-score gate | -1.14 pp (-2.37 to +0.09) | 1156 / 1219 | 125 / 689 | 0.079 | 71 / 55 / 24 | -0.7, -1.4, -1.4 |
| A8 vs A7: Shield+cover vs random gate | -1.38 pp (-2.65 to -0.09) | 1156 / 1232 | 125 / 658 | 0.038 | 77 / 54 / 19 | -0.8, -1.8, -1.5 |
| A8 vs A1: Shield+cover vs always commit | -1.56 pp (-2.81 to -0.29) | 1156 / 1242 | 125 / 703 | 0.018 | 75 / 49 / 26 | -1.0, -1.9, -1.8 |
| A8c vs A6: REVISED (post-hoc): Shield+location cover vs confidence gate | -4.05 pp (-5.16 to -2.94) | 986 / 1209 | 96 / 673 | 0.000 | 102 / 26 / 22 | -3.9, -4.6, -3.7 |
| A8c vs A1: Shield+location cover vs always commit | -4.65 pp (-5.74 to -3.56) | 986 / 1242 | 96 / 703 | 0.000 | 109 / 24 / 17 | -4.6, -5.1, -4.3 |
| A8c vs A8: location cover vs full cover | -3.09 pp (-4.08 to -2.14) | 986 / 1156 | 96 / 125 | 0.000 | 87 / 29 / 34 | -3.5, -3.3, -2.5 |
| A8c vs A10: location cover vs no fallback | -4.50 pp (-5.58 to -3.44) | 986 / 1234 | 96 / 694 | 0.000 | 103 / 25 / 22 | -4.4, -5.1, -4.0 |
| A8 vs A10: fallback effect: with cover vs without | -1.42 pp (-2.67 to -0.16) | 1156 / 1234 | 125 / 694 | 0.034 | 74 / 54 / 22 | -0.8, -1.9, -1.6 |
| A8 vs A9: conformal sets vs singleton sets only | +0.40 pp (-0.05 to +0.87) | 1156 / 1134 | 125 / 132 | 0.113 | 19 / 31 / 100 | -0.1, +1.0, +0.3 |
| A10 vs A6: Shield without fallback vs confidence gate | +0.45 pp (-0.04 to +0.92) | 1234 / 1209 | 694 / 673 | 0.077 | 14 / 34 / 102 | +0.5, +0.5, +0.4 |
| A6 vs A1: confidence gate vs always commit | -0.60 pp (-0.98 to -0.24) | 1209 / 1242 | 673 / 703 | 0.002 | 37 / 13 / 100 | -0.7, -0.5, -0.6 |
| A12 vs A1: HEADROOM: perfect gate vs always commit | -1.38 pp (-2.07 to -0.68) | 1166 / 1242 | 576 / 703 | 0.000 | 76 / 30 / 44 | -1.1, -1.8, -1.3 |
| A1 vs A0: record-induced misses of the Q4 head (vs gold records) | +9.14 pp (+8.09 to +10.21) | 1242 / 739 | 703 / 39 | 0.000 | 10 / 134 / 6 | +8.5, +9.4, +9.5 |

### What the Shield decided

| Outcome class | A8 reports | A8 share | A8c reports | A8c share |
|---|---|---|---|---|
| ACCEPT | 830 | 27.7% | 856 | 28.5% |
| ACCEPT_INFEASIBLE | 85 | 2.8% | 59 | 2.0% |
| ESCALATE | 207 | 6.9% | 207 | 6.9% |
| FALLBACK_COVERED | 1228 | 40.9% | 886 | 29.5% |
| FALLBACK_PARTIAL | 345 | 11.5% | 851 | 28.4% |
| FALLBACK_UNRESOLVED | 305 | 10.2% | 141 | 4.7% |

Certified (ACCEPT + ACCEPT_INFEASIBLE): 30.5% of reports; certified AND the committed plan differs from the gold plan: 30 reports = 1.00% of all reports (the marginal guarantee is <= alpha = 0.1, on exchangeable data). Set sizes of certified reports: {1: 915}.

### Which reports does each method flag? (reports whose best-guess record would have given a wrong plan)

| Arm | flagged (verify or cover) | of which wrong-plan | wrong-plan reports flagged (recall) | flagged that were wrong-plan (precision) | wrong-plan reports left unflagged, share of ALL reports |
|---|---|---|---|---|---|
| A1 | 0 (0.0%) | 0 | 0.0% | - | 43.1% |
| A6 | 226 (7.5%) | 124 | 9.6% | 54.9% | 39.0% |
| A6b | 223 (7.4%) | 154 | 11.9% | 69.1% | 38.1% |
| A7 | 217 (7.2%) | 89 | 6.9% | 41.0% | 40.1% |
| A8 | 2085 (69.5%) | 1269 | 97.7% | 60.9% | 1.0% |
| A8c | 2085 (69.5%) | 1270 | 97.7% | 60.9% | 1.0% |
| A9 | 2085 (69.5%) | 1268 | 97.7% | 60.8% | 1.0% |
| A10 | 207 (6.9%) | 157 | 12.1% | 75.8% | 38.1% |
| A12 | 300 (10.0%) | 273 | 21.1% | 91.0% | 34.1% |

### Equal-budget ranking: share of the wrong-plan reports caught when each method flags its top f of every episode

3000 reports, 1293 of them with a wrong plan. The OBS arm behaves exactly like A1 and logs every method's risk score.

| Ranking by | f = 5% | f = 10% | f = 20% | f = 30% | AUROC |
|---|---|---|---|---|---|
| A8 Shield (rho, 1-score) | 9.0% | 17.4% | 32.9% | 48.1% | 0.800 |
| A9 singleton-only | 9.1% | 16.9% | 30.5% | 45.6% | 0.789 |
| A11 top-2 what-if | 8.2% | 16.0% | 31.6% | 46.1% | 0.742 |
| A6 confidence | 6.4% | 12.2% | 24.2% | 35.7% | 0.604 |
| A6b record score | 9.1% | 16.9% | 30.5% | 45.6% | 0.787 |
| random | 4.6% | 9.2% | 19.2% | 29.2% | 0.500 |
