# Development results: main

Saved vectors, 1,000 style-A reports, 5 outer folds, 3 seed(s) [1, 2, 3]; overlay episodes of 20 reports sharing one fleet; verification budget b = 0.1 of reports (hard cap per episode), delay d_v = 60.0 s; alpha = 0.1, K = 8, allocator cbba_bounded, readout q4. EVAL reports only. Style B untouched.

U_deadline = (late + unverified) / incidents. Lower is better. CI = episode bootstrap, seeds pooled (optimistic: seeds re-use the same reports).

## Level L

### Outcomes and costs

| Arm | System | U_deadline (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 1.3% (0.9% to 1.9%) | 73 | 1 | 0.000 | 0.000 | 0 (0) | 1193 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 2.4% (1.9% to 3.0%) | 121 | 12 | 0.000 | 0.075 | 0 (0) | 1250 | 0.0 | 0.00 | 0.01 / 0.01 |
| A2 | FP16 heads, always commit (off-board reference) | 1.8% (1.3% to 2.4%) | 96 | 4 | 0.000 | 0.054 | 0 (0) | 1240 | 0.0 | 0.00 | 0.01 / 0.01 |
| A3 | Q8 heads, always commit | 2.1% (1.6% to 2.7%) | 114 | 4 | 0.000 | 0.059 | 0 (0) | 1241 | 0.0 | 0.00 | 0.01 / 0.01 |
| A4 | Recentred Q4 (FP16 head, label-free shift removed) | 3.2% (2.7% to 3.8%) | 123 | 54 | 0.000 | 0.117 | 0 (0) | 1278 | 0.0 | 0.00 | 0.01 / 0.01 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 13.9% (13.1% to 14.7%) | 77 | 690 | 0.000 | 0.158 | 0 (0) | 1168 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 2.9% (2.4% to 3.4%) | 128 | 31 | 0.073 | 0.070 | 0 (0) | 1240 | 4.4 | 0.00 | 0.01 / 0.03 |
| A6b | Top-record-score gate | 2.9% (2.5% to 3.4%) | 114 | 46 | 0.077 | 0.074 | 0 (0) | 1241 | 4.6 | 0.00 | 0.01 / 0.03 |
| A7 | Random gate | 2.6% (2.0% to 3.2%) | 125 | 18 | 0.072 | 0.082 | 0 (0) | 1251 | 4.3 | 0.00 | 0.01 / 0.02 |
| A8 | Shield + full cover fallback (plan) | 3.2% (2.6% to 3.8%) | 153 | 21 | 0.072 | 0.041 | 411 (7) | 1227 | 4.3 | 1.94 | 0.18 / 1.25 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 2.5% (2.0% to 3.0%) | 119 | 20 | 0.072 | 0.076 | 480 (68) | 1244 | 4.3 | 1.94 | 0.18 / 1.29 |
| A9 | Shield, singleton sets only | 3.3% (2.7% to 3.8%) | 135 | 44 | 0.076 | 0.052 | 546 (8) | 1225 | 4.5 | 1.36 | 0.16 / 0.74 |
| A10 | Shield, no fallback | 2.5% (2.1% to 3.0%) | 118 | 22 | 0.072 | 0.065 | 0 (0) | 1236 | 4.3 | 1.69 | 0.17 / 0.99 |
| A11 | Top-2 what-if, no conformal | 4.1% (3.4% to 4.9%) | 207 | 20 | 0.074 | 0.385 | 983 (607) | 1410 | 4.4 | 2.55 | 0.35 / 1.39 |
| A12 | Oracle gate (diagnostic upper bound) | 2.6% (2.1% to 3.1%) | 105 | 37 | 0.099 | 0.066 | 0 (0) | 1233 | 6.0 | 0.00 | 0.00 / 0.01 |

Episodes per arm: 150, incidents per arm: 5505, reports per arm: 3000. Request rates should be near b = 0.1; the cap is 2 request(s) per 20-report episode.

### Paired comparisons (same episodes)

Difference in U_deadline (first minus second); negative = first is better. Per-seed differences in the last column.

| Comparison | diff (95% CI) | missed incidents: first / second | unverified: first / second | sign-flip p | episodes won / lost / tied | per seed |
|---|---|---|---|---|---|---|
| A8 vs A6: PRIMARY: Shield+cover vs confidence gate (same budget) | +0.27 pp (-0.25 to +0.80) | 174 / 159 | 21 / 31 | 0.355 | 36 / 37 / 77 | +0.0, +0.3, +0.5 |
| A8 vs A6b: Shield+cover vs record-score gate | +0.25 pp (-0.24 to +0.77) | 174 / 160 | 21 / 46 | 0.353 | 38 / 34 / 78 | +0.2, +0.0, +0.5 |
| A8 vs A7: Shield+cover vs random gate | +0.56 pp (+0.00 to +1.12) | 174 / 143 | 21 / 18 | 0.060 | 31 / 46 / 73 | +0.4, +0.7, +0.6 |
| A8 vs A1: Shield+cover vs always commit | +0.74 pp (+0.22 to +1.28) | 174 / 133 | 21 / 12 | 0.008 | 26 / 46 / 78 | +0.4, +0.6, +1.3 |
| A8c vs A6: REVISED (post-hoc): Shield+location cover vs confidence gate | -0.36 pp (-0.66 to -0.07) | 139 / 159 | 20 / 31 | 0.020 | 29 / 13 / 108 | -0.4, -0.3, -0.4 |
| A8c vs A1: Shield+location cover vs always commit | +0.11 pp (-0.20 to +0.41) | 139 / 133 | 20 / 12 | 0.559 | 16 / 24 / 110 | +0.0, +0.0, +0.3 |
| A8c vs A8: location cover vs full cover | -0.64 pp (-1.09 to -0.20) | 139 / 174 | 20 / 21 | 0.008 | 31 / 19 / 100 | -0.4, -0.6, -0.9 |
| A8c vs A10: location cover vs no fallback | -0.02 pp (-0.13 to +0.13) | 139 / 140 | 20 / 22 | 1.000 | 4 / 1 / 145 | +0.0, -0.1, +0.0 |
| A8 vs A10: fallback effect: with cover vs without | +0.62 pp (+0.16 to +1.08) | 174 / 140 | 21 / 22 | 0.012 | 22 / 31 / 97 | +0.4, +0.5, +0.9 |
| A8 vs A9: conformal sets vs singleton sets only | -0.09 pp (-0.45 to +0.27) | 174 / 179 | 21 / 44 | 0.696 | 29 / 23 / 98 | +0.0, -0.5, +0.3 |
| A8 vs A11: conformal sets vs top-2 what-if | -0.96 pp (-1.55 to -0.40) | 174 / 227 | 21 / 20 | 0.002 | 50 / 24 / 76 | -1.3, -0.9, -0.7 |
| A10 vs A6: Shield without fallback vs confidence gate | -0.35 pp (-0.64 to -0.07) | 140 / 159 | 22 / 31 | 0.025 | 27 / 12 / 111 | -0.4, -0.3, -0.4 |
| A6 vs A1: confidence gate vs always commit | +0.47 pp (+0.20 to +0.74) | 159 / 133 | 31 / 12 | 0.001 | 4 / 30 / 116 | +0.4, +0.3, +0.7 |
| A12 vs A1: HEADROOM: perfect gate vs always commit | +0.16 pp (-0.25 to +0.58) | 142 / 133 | 37 / 12 | 0.491 | 26 / 34 / 90 | -0.4, +0.1, +0.8 |
| A1 vs A0: record-induced misses of the Q4 head (vs gold records) | +1.07 pp (+0.66 to +1.51) | 133 / 74 | 12 / 1 | 0.000 | 5 / 44 / 101 | +1.3, +1.0, +0.9 |
| A1 vs A2: Q4 vs FP16 (quantisation effect) | +0.60 pp (+0.20 to +1.01) | 133 / 100 | 12 / 4 | 0.005 | 13 / 36 / 101 | +0.8, +0.9, +0.2 |
| A4 vs A1: recentred Q4 vs raw-trained Q4 | +0.80 pp (+0.33 to +1.29) | 177 / 133 | 54 / 12 | 0.001 | 21 / 54 / 75 | +0.5, +0.5, +1.4 |
| A5 vs A2: mismatched frozen head vs FP16 (diagnostic) | +12.12 pp (+11.39 to +12.86) | 767 / 100 | 690 / 4 | 0.000 | 0 / 150 / 0 | +12.1, +12.7, +11.6 |

### What the Shield decided

| Outcome class | A8 reports | A8 share | A8c reports | A8c share |
|---|---|---|---|---|
| ACCEPT | 2010 | 67.0% | 2019 | 67.3% |
| ACCEPT_INFEASIBLE | 12 | 0.4% | 9 | 0.3% |
| ESCALATE | 216 | 7.2% | 216 | 7.2% |
| FALLBACK_COVERED | 743 | 24.8% | 185 | 6.2% |
| FALLBACK_PARTIAL | 0 | 0.0% | 564 | 18.8% |
| FALLBACK_UNRESOLVED | 19 | 0.6% | 7 | 0.2% |

Certified (ACCEPT + ACCEPT_INFEASIBLE): 67.4% of reports; certified AND the committed plan differs from the gold plan: 63 reports = 2.10% of all reports (the marginal guarantee is <= alpha = 0.1, on exchangeable data). Set sizes of certified reports: {1: 1704, 2: 243, 3: 75}.

### Which reports does each method flag? (reports whose best-guess record would have given a wrong plan)

| Arm | flagged (verify or cover) | of which wrong-plan | wrong-plan reports flagged (recall) | flagged that were wrong-plan (precision) | wrong-plan reports left unflagged, share of ALL reports |
|---|---|---|---|---|---|
| A1 | 0 (0.0%) | 0 | 0.0% | - | 17.8% |
| A6 | 219 (7.3%) | 121 | 22.7% | 55.3% | 13.7% |
| A6b | 230 (7.7%) | 139 | 25.6% | 60.4% | 13.5% |
| A7 | 217 (7.2%) | 35 | 6.6% | 16.1% | 16.6% |
| A8 | 978 (32.6%) | 477 | 88.3% | 48.8% | 2.1% |
| A8c | 972 (32.4%) | 467 | 87.6% | 48.0% | 2.2% |
| A9 | 1296 (43.2%) | 510 | 94.3% | 39.4% | 1.0% |
| A10 | 215 (7.2%) | 144 | 27.2% | 67.0% | 12.9% |
| A11 | 2181 (72.7%) | 452 | 84.8% | 20.7% | 2.7% |
| A12 | 298 (9.9%) | 209 | 39.0% | 70.1% | 10.9% |

### Equal-budget ranking: share of the wrong-plan reports caught when each method flags its top f of every episode

3000 reports, 533 of them with a wrong plan. The OBS arm behaves exactly like A1 and logs every method's risk score.

| Ranking by | f = 5% | f = 10% | f = 20% | f = 30% | AUROC |
|---|---|---|---|---|---|
| A8 Shield (rho, 1-score) | 19.1% | 35.8% | 61.2% | 81.2% | 0.906 |
| A9 singleton-only | 16.3% | 31.7% | 55.5% | 73.4% | 0.875 |
| A11 top-2 what-if | 18.9% | 35.8% | 59.5% | 76.4% | 0.824 |
| A6 confidence | 16.9% | 30.6% | 55.7% | 75.4% | 0.874 |
| A6b record score | 15.8% | 31.7% | 54.8% | 72.8% | 0.874 |
| random | 6.0% | 9.8% | 18.2% | 29.8% | 0.500 |

## Level M

### Outcomes and costs

| Arm | System | U_deadline (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 4.9% (4.1% to 5.8%) | 269 | 2 | 0.000 | 0.000 | 0 (0) | 1076 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 7.4% (6.4% to 8.5%) | 392 | 16 | 0.000 | 0.076 | 0 (0) | 1114 | 0.0 | 0.00 | 0.01 / 0.02 |
| A2 | FP16 heads, always commit (off-board reference) | 6.3% (5.4% to 7.3%) | 342 | 5 | 0.000 | 0.057 | 0 (0) | 1106 | 0.0 | 0.00 | 0.01 / 0.02 |
| A3 | Q8 heads, always commit | 6.5% (5.5% to 7.5%) | 353 | 5 | 0.000 | 0.063 | 0 (0) | 1100 | 0.0 | 0.00 | 0.01 / 0.02 |
| A4 | Recentred Q4 (FP16 head, label-free shift removed) | 8.0% (7.1% to 9.0%) | 385 | 56 | 0.000 | 0.124 | 0 (0) | 1141 | 0.0 | 0.00 | 0.01 / 0.02 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 16.5% (15.6% to 17.4%) | 218 | 690 | 0.000 | 0.164 | 0 (0) | 1079 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 7.1% (6.1% to 8.1%) | 354 | 35 | 0.073 | 0.070 | 0 (0) | 1107 | 4.4 | 0.00 | 0.01 / 0.04 |
| A6b | Top-record-score gate | 7.6% (6.6% to 8.7%) | 372 | 47 | 0.077 | 0.074 | 0 (0) | 1115 | 4.6 | 0.00 | 0.01 / 0.03 |
| A7 | Random gate | 7.4% (6.4% to 8.4%) | 388 | 19 | 0.072 | 0.086 | 0 (0) | 1121 | 4.3 | 0.00 | 0.01 / 0.03 |
| A8 | Shield + full cover fallback (plan) | 8.2% (7.2% to 9.3%) | 428 | 25 | 0.076 | 0.043 | 436 (7) | 1094 | 4.6 | 1.96 | 0.31 / 2.44 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 7.0% (6.1% to 8.0%) | 361 | 27 | 0.077 | 0.079 | 493 (63) | 1119 | 4.6 | 1.95 | 0.31 / 2.37 |
| A9 | Shield, singleton sets only | 8.7% (7.7% to 9.8%) | 437 | 43 | 0.076 | 0.050 | 545 (8) | 1105 | 4.5 | 1.36 | 0.26 / 1.31 |
| A10 | Shield, no fallback | 7.0% (6.1% to 8.0%) | 356 | 30 | 0.077 | 0.069 | 0 (0) | 1116 | 4.6 | 1.69 | 0.28 / 1.82 |
| A11 | Top-2 what-if, no conformal | 9.6% (8.5% to 10.6%) | 499 | 27 | 0.076 | 0.385 | 1036 (607) | 1208 | 4.6 | 2.59 | 0.62 / 2.68 |
| A12 | Oracle gate (diagnostic upper bound) | 6.9% (6.0% to 8.0%) | 350 | 32 | 0.099 | 0.066 | 0 (0) | 1106 | 6.0 | 0.00 | 0.01 / 0.02 |

Episodes per arm: 150, incidents per arm: 5505, reports per arm: 3000. Request rates should be near b = 0.1; the cap is 2 request(s) per 20-report episode.

### Paired comparisons (same episodes)

Difference in U_deadline (first minus second); negative = first is better. Per-seed differences in the last column.

| Comparison | diff (95% CI) | missed incidents: first / second | unverified: first / second | sign-flip p | episodes won / lost / tied | per seed |
|---|---|---|---|---|---|---|
| A8 vs A6: PRIMARY: Shield+cover vs confidence gate (same budget) | +1.16 pp (+0.37 to +1.96) | 453 / 389 | 25 / 35 | 0.006 | 37 / 64 / 49 | +1.3, +0.8, +1.4 |
| A8 vs A6b: Shield+cover vs record-score gate | +0.62 pp (-0.17 to +1.43) | 453 / 419 | 25 / 47 | 0.152 | 42 / 49 / 59 | +0.4, +0.8, +0.7 |
| A8 vs A7: Shield+cover vs random gate | +0.84 pp (+0.00 to +1.67) | 453 / 407 | 25 / 19 | 0.061 | 46 / 58 / 46 | +1.1, +1.0, +0.4 |
| A8 vs A1: Shield+cover vs always commit | +0.82 pp (+0.04 to +1.58) | 453 / 408 | 25 / 16 | 0.046 | 41 / 55 / 54 | +0.5, +0.9, +1.1 |
| A8c vs A6: REVISED (post-hoc): Shield+location cover vs confidence gate | -0.02 pp (-0.49 to +0.45) | 388 / 389 | 27 / 35 | 1.000 | 29 / 30 / 91 | +0.3, -0.7, +0.3 |
| A8c vs A1: Shield+location cover vs always commit | -0.36 pp (-0.87 to +0.11) | 388 / 408 | 27 / 16 | 0.176 | 34 / 31 / 85 | -0.4, -0.6, -0.1 |
| A8c vs A8: location cover vs full cover | -1.18 pp (-1.90 to -0.47) | 388 / 453 | 27 / 25 | 0.001 | 56 / 30 / 64 | -0.9, -1.5, -1.1 |
| A8c vs A10: location cover vs no fallback | +0.04 pp (-0.13 to +0.20) | 388 / 386 | 27 / 30 | 0.843 | 5 / 6 / 139 | +0.2, -0.2, +0.1 |
| A8 vs A10: fallback effect: with cover vs without | +1.22 pp (+0.50 to +1.93) | 453 / 386 | 25 / 30 | 0.001 | 31 / 58 / 61 | +1.1, +1.3, +1.3 |
| A8 vs A9: conformal sets vs singleton sets only | -0.49 pp (-1.06 to +0.07) | 453 / 480 | 25 / 43 | 0.119 | 53 / 31 / 66 | -0.5, -0.5, -0.5 |
| A8 vs A11: conformal sets vs top-2 what-if | -1.33 pp (-2.12 to -0.55) | 453 / 526 | 25 / 27 | 0.001 | 70 / 36 / 44 | -1.9, -1.5, -0.6 |
| A10 vs A6: Shield without fallback vs confidence gate | -0.05 pp (-0.53 to +0.42) | 386 / 389 | 30 / 35 | 0.882 | 27 / 27 / 96 | +0.1, -0.4, +0.2 |
| A6 vs A1: confidence gate vs always commit | -0.35 pp (-0.84 to +0.13) | 389 / 408 | 35 / 16 | 0.185 | 34 / 28 / 88 | -0.8, +0.1, -0.3 |
| A12 vs A1: HEADROOM: perfect gate vs always commit | -0.47 pp (-1.07 to +0.13) | 382 / 408 | 32 / 16 | 0.141 | 44 / 33 / 73 | -1.0, -0.4, +0.0 |
| A1 vs A0: record-induced misses of the Q4 head (vs gold records) | +2.49 pp (+1.86 to +3.14) | 408 / 271 | 16 / 2 | 0.000 | 11 / 72 / 67 | +2.9, +2.4, +2.2 |
| A1 vs A2: Q4 vs FP16 (quantisation effect) | +1.11 pp (+0.47 to +1.77) | 408 / 347 | 16 / 5 | 0.001 | 27 / 54 / 69 | +1.4, +0.9, +1.0 |
| A4 vs A1: recentred Q4 vs raw-trained Q4 | +0.60 pp (-0.17 to +1.36) | 441 / 408 | 56 / 16 | 0.134 | 37 / 61 / 52 | +0.3, +0.9, +0.7 |
| A5 vs A2: mismatched frozen head vs FP16 (diagnostic) | +10.19 pp (+9.25 to +11.13) | 908 / 347 | 690 / 5 | 0.000 | 6 / 143 / 1 | +9.9, +10.2, +10.5 |

### What the Shield decided

| Outcome class | A8 reports | A8 share | A8c reports | A8c share |
|---|---|---|---|---|
| ACCEPT | 1944 | 64.8% | 1946 | 64.9% |
| ACCEPT_INFEASIBLE | 28 | 0.9% | 31 | 1.0% |
| ESCALATE | 228 | 7.6% | 230 | 7.7% |
| FALLBACK_COVERED | 746 | 24.9% | 204 | 6.8% |
| FALLBACK_PARTIAL | 0 | 0.0% | 569 | 19.0% |
| FALLBACK_UNRESOLVED | 54 | 1.8% | 20 | 0.7% |

Certified (ACCEPT + ACCEPT_INFEASIBLE): 65.7% of reports; certified AND the committed plan differs from the gold plan: 67 reports = 2.23% of all reports (the marginal guarantee is <= alpha = 0.1, on exchangeable data). Set sizes of certified reports: {1: 1704, 2: 217, 3: 51}.

### Which reports does each method flag? (reports whose best-guess record would have given a wrong plan)

| Arm | flagged (verify or cover) | of which wrong-plan | wrong-plan reports flagged (recall) | flagged that were wrong-plan (precision) | wrong-plan reports left unflagged, share of ALL reports |
|---|---|---|---|---|---|
| A1 | 0 (0.0%) | 0 | 0.0% | - | 18.6% |
| A6 | 219 (7.3%) | 124 | 21.9% | 56.6% | 14.7% |
| A6b | 230 (7.7%) | 142 | 25.0% | 61.7% | 14.2% |
| A7 | 217 (7.2%) | 37 | 6.6% | 17.1% | 17.5% |
| A8 | 1028 (34.3%) | 504 | 88.3% | 49.0% | 2.2% |
| A8c | 1023 (34.1%) | 506 | 88.6% | 49.5% | 2.2% |
| A9 | 1296 (43.2%) | 537 | 94.0% | 41.4% | 1.1% |
| A10 | 230 (7.7%) | 161 | 28.2% | 70.0% | 13.7% |
| A11 | 2289 (76.3%) | 505 | 87.7% | 22.1% | 2.4% |
| A12 | 298 (9.9%) | 217 | 38.2% | 72.8% | 11.7% |

### Equal-budget ranking: share of the wrong-plan reports caught when each method flags its top f of every episode

3000 reports, 558 of them with a wrong plan. The OBS arm behaves exactly like A1 and logs every method's risk score.

| Ranking by | f = 5% | f = 10% | f = 20% | f = 30% | AUROC |
|---|---|---|---|---|---|
| A8 Shield (rho, 1-score) | 18.8% | 35.1% | 61.1% | 79.9% | 0.904 |
| A9 singleton-only | 16.3% | 31.5% | 56.6% | 72.8% | 0.876 |
| A11 top-2 what-if | 18.3% | 34.6% | 59.1% | 76.5% | 0.830 |
| A6 confidence | 16.8% | 30.1% | 55.4% | 74.4% | 0.874 |
| A6b record score | 15.9% | 31.5% | 55.7% | 72.2% | 0.875 |
| random | 5.9% | 9.1% | 17.7% | 29.2% | 0.500 |

## Level H

### Outcomes and costs

| Arm | System | U_deadline (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 13.4% (12.1% to 14.7%) | 700 | 39 | 0.000 | 0.000 | 0 (0) | 772 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 16.4% (15.1% to 17.6%) | 832 | 70 | 0.000 | 0.073 | 0 (0) | 795 | 0.0 | 0.00 | 0.01 / 0.02 |
| A2 | FP16 heads, always commit (off-board reference) | 15.3% (14.0% to 16.6%) | 783 | 61 | 0.000 | 0.056 | 0 (0) | 792 | 0.0 | 0.00 | 0.01 / 0.01 |
| A3 | Q8 heads, always commit | 16.1% (14.6% to 17.5%) | 817 | 70 | 0.000 | 0.061 | 0 (0) | 791 | 0.0 | 0.00 | 0.01 / 0.01 |
| A4 | Recentred Q4 (FP16 head, label-free shift removed) | 16.5% (15.2% to 17.7%) | 799 | 108 | 0.000 | 0.119 | 0 (0) | 812 | 0.0 | 0.00 | 0.01 / 0.01 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 22.6% (21.3% to 23.8%) | 539 | 703 | 0.000 | 0.156 | 0 (0) | 769 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 16.1% (14.8% to 17.4%) | 816 | 70 | 0.073 | 0.056 | 0 (0) | 786 | 4.4 | 0.00 | 0.01 / 0.04 |
| A6b | Top-record-score gate | 16.1% (14.7% to 17.4%) | 806 | 80 | 0.077 | 0.058 | 0 (0) | 785 | 4.6 | 0.00 | 0.01 / 0.04 |
| A7 | Random gate | 16.2% (14.8% to 17.5%) | 813 | 78 | 0.072 | 0.073 | 0 (0) | 787 | 4.3 | 0.00 | 0.01 / 0.04 |
| A8 | Shield + full cover fallback (plan) | 17.9% (16.5% to 19.1%) | 898 | 86 | 0.076 | 0.036 | 474 (10) | 787 | 4.6 | 1.98 | 0.69 / 5.83 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 15.7% (14.4% to 17.0%) | 795 | 72 | 0.074 | 0.066 | 523 (57) | 795 | 4.4 | 1.98 | 0.70 / 6.13 |
| A9 | Shield, singleton sets only | 18.6% (17.1% to 19.9%) | 925 | 98 | 0.076 | 0.038 | 537 (6) | 790 | 4.5 | 1.36 | 0.58 / 2.92 |
| A10 | Shield, no fallback | 15.6% (14.3% to 16.9%) | 785 | 76 | 0.073 | 0.056 | 0 (0) | 793 | 4.4 | 1.69 | 0.66 / 4.41 |
| A11 | Top-2 what-if, no conformal | 19.9% (18.5% to 21.2%) | 959 | 134 | 0.075 | 0.354 | 1014 (549) | 841 | 4.5 | 2.62 | 1.51 / 6.69 |
| A12 | Oracle gate (diagnostic upper bound) | 15.7% (14.4% to 16.9%) | 790 | 74 | 0.099 | 0.055 | 0 (0) | 788 | 6.0 | 0.00 | 0.01 / 0.02 |

Episodes per arm: 150, incidents per arm: 5505, reports per arm: 3000. Request rates should be near b = 0.1; the cap is 2 request(s) per 20-report episode.

### Paired comparisons (same episodes)

Difference in U_deadline (first minus second); negative = first is better. Per-seed differences in the last column.

| Comparison | diff (95% CI) | missed incidents: first / second | unverified: first / second | sign-flip p | episodes won / lost / tied | per seed |
|---|---|---|---|---|---|---|
| A8 vs A6: PRIMARY: Shield+cover vs confidence gate (same budget) | +1.78 pp (+0.95 to +2.61) | 984 / 886 | 86 / 70 | 0.000 | 32 / 74 / 44 | +2.3, +1.7, +1.3 |
| A8 vs A6b: Shield+cover vs record-score gate | +1.78 pp (+0.85 to +2.70) | 984 / 886 | 86 / 80 | 0.000 | 37 / 75 / 38 | +2.9, +1.7, +0.7 |
| A8 vs A7: Shield+cover vs random gate | +1.69 pp (+0.71 to +2.66) | 984 / 891 | 86 / 78 | 0.000 | 36 / 71 / 43 | +2.1, +2.0, +1.0 |
| A8 vs A1: Shield+cover vs always commit | +1.49 pp (+0.58 to +2.40) | 984 / 902 | 86 / 70 | 0.001 | 35 / 72 / 43 | +1.6, +1.5, +1.4 |
| A8c vs A6: REVISED (post-hoc): Shield+location cover vs confidence gate | -0.35 pp (-0.86 to +0.15) | 867 / 886 | 72 / 70 | 0.205 | 39 / 25 / 86 | +0.3, -0.1, -1.2 |
| A8c vs A1: Shield+location cover vs always commit | -0.64 pp (-1.25 to -0.02) | 867 / 902 | 72 / 70 | 0.045 | 43 / 26 / 81 | -0.5, -0.3, -1.1 |
| A8c vs A8: location cover vs full cover | -2.13 pp (-2.95 to -1.36) | 867 / 984 | 72 / 86 | 0.000 | 74 / 24 / 52 | -2.1, -1.9, -2.5 |
| A8c vs A10: location cover vs no fallback | +0.11 pp (-0.11 to +0.33) | 867 / 861 | 72 / 76 | 0.429 | 4 / 9 / 137 | +0.3, +0.2, -0.1 |
| A8 vs A10: fallback effect: with cover vs without | +2.23 pp (+1.45 to +3.05) | 984 / 861 | 86 / 76 | 0.000 | 23 / 77 / 50 | +2.3, +2.0, +2.3 |
| A8 vs A9: conformal sets vs singleton sets only | -0.71 pp (-1.43 to -0.02) | 984 / 1023 | 86 / 98 | 0.057 | 52 / 29 / 69 | -0.2, -0.4, -1.5 |
| A8 vs A11: conformal sets vs top-2 what-if | -1.98 pp (-2.97 to -1.01) | 984 / 1093 | 86 / 134 | 0.000 | 77 / 37 / 36 | -2.0, -1.3, -2.7 |
| A10 vs A6: Shield without fallback vs confidence gate | -0.45 pp (-0.96 to +0.04) | 861 / 886 | 76 / 70 | 0.082 | 36 / 20 / 94 | +0.0, -0.3, -1.1 |
| A6 vs A1: confidence gate vs always commit | -0.29 pp (-0.83 to +0.25) | 886 / 902 | 70 / 70 | 0.322 | 37 / 29 / 84 | -0.8, -0.2, +0.1 |
| A12 vs A1: HEADROOM: perfect gate vs always commit | -0.69 pp (-1.45 to +0.11) | 864 / 902 | 74 / 70 | 0.095 | 59 / 34 / 57 | -1.1, -1.1, +0.1 |
| A1 vs A0: record-induced misses of the Q4 head (vs gold records) | +2.96 pp (+2.21 to +3.72) | 902 / 739 | 70 / 39 | 0.000 | 18 / 90 / 42 | +3.2, +3.3, +2.3 |
| A1 vs A2: Q4 vs FP16 (quantisation effect) | +1.05 pp (+0.31 to +1.80) | 902 / 844 | 70 / 61 | 0.009 | 38 / 63 / 49 | +1.5, +0.3, +1.3 |
| A4 vs A1: recentred Q4 vs raw-trained Q4 | +0.09 pp (-0.76 to +0.93) | 907 / 902 | 108 / 70 | 0.869 | 50 / 58 / 42 | +0.4, -0.1, -0.1 |
| A5 vs A2: mismatched frozen head vs FP16 (diagnostic) | +7.23 pp (+6.13 to +8.35) | 1242 / 844 | 703 / 61 | 0.000 | 13 / 125 / 12 | +6.8, +6.4, +8.5 |

### What the Shield decided

| Outcome class | A8 reports | A8 share | A8c reports | A8c share |
|---|---|---|---|---|
| ACCEPT | 1749 | 58.3% | 1790 | 59.7% |
| ACCEPT_INFEASIBLE | 141 | 4.7% | 107 | 3.6% |
| ESCALATE | 228 | 7.6% | 222 | 7.4% |
| FALLBACK_COVERED | 704 | 23.5% | 228 | 7.6% |
| FALLBACK_PARTIAL | 0 | 0.0% | 539 | 18.0% |
| FALLBACK_UNRESOLVED | 178 | 5.9% | 114 | 3.8% |

Certified (ACCEPT + ACCEPT_INFEASIBLE): 63.0% of reports; certified AND the committed plan differs from the gold plan: 62 reports = 2.07% of all reports (the marginal guarantee is <= alpha = 0.1, on exchangeable data). Set sizes of certified reports: {1: 1704, 2: 159, 3: 27}.

### Which reports does each method flag? (reports whose best-guess record would have given a wrong plan)

| Arm | flagged (verify or cover) | of which wrong-plan | wrong-plan reports flagged (recall) | flagged that were wrong-plan (precision) | wrong-plan reports left unflagged, share of ALL reports |
|---|---|---|---|---|---|
| A1 | 0 (0.0%) | 0 | 0.0% | - | 20.3% |
| A6 | 219 (7.3%) | 125 | 20.4% | 57.1% | 16.2% |
| A6b | 230 (7.7%) | 147 | 23.8% | 63.9% | 15.7% |
| A7 | 217 (7.2%) | 39 | 6.3% | 18.0% | 19.2% |
| A8 | 1110 (37.0%) | 566 | 90.1% | 51.0% | 2.1% |
| A8c | 1103 (36.8%) | 552 | 89.6% | 50.0% | 2.1% |
| A9 | 1296 (43.2%) | 594 | 94.0% | 45.8% | 1.3% |
| A10 | 220 (7.3%) | 156 | 25.4% | 70.9% | 15.3% |
| A11 | 2387 (79.6%) | 565 | 89.7% | 23.7% | 2.2% |
| A12 | 298 (9.9%) | 226 | 36.6% | 75.8% | 13.0% |

### Equal-budget ranking: share of the wrong-plan reports caught when each method flags its top f of every episode

3000 reports, 610 of them with a wrong plan. The OBS arm behaves exactly like A1 and logs every method's risk score.

| Ranking by | f = 5% | f = 10% | f = 20% | f = 30% | AUROC |
|---|---|---|---|---|---|
| A8 Shield (rho, 1-score) | 16.7% | 35.1% | 60.7% | 79.5% | 0.910 |
| A9 singleton-only | 15.9% | 30.8% | 55.1% | 73.0% | 0.884 |
| A11 top-2 what-if | 16.2% | 31.5% | 56.6% | 76.7% | 0.849 |
| A6 confidence | 15.2% | 28.9% | 53.9% | 74.4% | 0.880 |
| A6b record score | 15.6% | 30.8% | 54.6% | 72.5% | 0.883 |
| random | 5.6% | 9.3% | 18.2% | 29.0% | 0.500 |
