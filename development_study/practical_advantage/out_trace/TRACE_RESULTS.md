# Practical-advantage check, Parts B and C: results

Exploratory, development data (style A, saved vectors, `prefix`), level M, 3 arrival seeds, 5 folds, always commit. Protocol hash `453c305909f040ac845828dc98341287d2377d988874942c696a06f46512b211`. Cloud run.

| Arm | What | Missed share | 95% CI (episodes) | Late | Unverified | Incidents |
|---|---|---|---|---|---|---|
| gold | gold records | 4.92% | 4.10 to 5.83 | 269 | 2 | 5505 |
| f16p | FP16 heads | 5.98% | 5.10 to 6.96 | 321 | 8 | 5505 |
| q4p | Q4 heads retrained, all FIT labels | 6.56% | 5.69 to 7.49 | 356 | 5 | 5505 |
| alnp | FP16 heads on mapped Q4 (no labels for the map) | 6.41% | 5.47 to 7.41 | 348 | 5 | 5505 |
| recp | FP16 heads on recentred Q4 | 6.85% | 5.96 to 7.76 | 357 | 20 | 5505 |
| rawp | FP16 heads on raw Q4 (diagnostic) | 9.43% | 8.51 to 10.36 | 313 | 206 | 5505 |
| q4p_n100 | Q4 heads retrained on 100 labels | 7.59% | 6.65 to 8.55 | 384 | 34 | 5505 |
| q4p_n300 | Q4 heads retrained on 300 labels | 6.83% | 5.91 to 7.80 | 365 | 11 | 5505 |
| q4p_ga | q4p with gold action | 6.43% | 5.53 to 7.35 | 352 | 2 | 5505 |
| q4p_gs | q4p with gold sensor | 5.09% | 4.27 to 5.98 | 275 | 5 | 5505 |
| q4p_gp | q4p with gold priority | 6.43% | 5.55 to 7.36 | 349 | 5 | 5505 |
| q4p_gas | q4p with gold action+sensor | 5.03% | 4.22 to 5.91 | 275 | 2 | 5505 |
| q4p_gap | q4p with gold action+priority | 6.30% | 5.42 to 7.26 | 345 | 2 | 5505 |
| q4p_gsp | q4p with gold sensor+priority | 5.03% | 4.18 to 5.93 | 272 | 5 | 5505 |
| q4p_gasp | q4p with gold action+sensor+priority | 4.92% | 4.10 to 5.83 | 269 | 2 | 5505 |
| alnp_ga | alnp with gold action | 6.38% | 5.44 to 7.38 | 349 | 2 | 5505 |
| alnp_gs | alnp with gold sensor | 5.21% | 4.38 to 6.11 | 282 | 5 | 5505 |
| alnp_gp | alnp with gold priority | 6.19% | 5.24 to 7.16 | 336 | 5 | 5505 |
| alnp_gas | alnp with gold action+sensor | 5.20% | 4.37 to 6.08 | 284 | 2 | 5505 |
| alnp_gap | alnp with gold action+priority | 6.16% | 5.20 to 7.11 | 337 | 2 | 5505 |
| alnp_gsp | alnp with gold sensor+priority | 5.00% | 4.16 to 5.89 | 270 | 5 | 5505 |
| alnp_gasp | alnp with gold action+sensor+priority | 4.92% | 4.10 to 5.83 | 269 | 2 | 5505 |

Integrity against the earlier prefix mission run (late, unverified, incidents): gold identical; f16p identical; q4p identical; alnp identical; recp identical; rawp identical

| Comparison (first minus second, same episodes) | Difference in missed share (pp) | 95% CI | p (sign-flip) | Episodes first better / worse / tied | sd of per-episode difference (missed incidents) |
|---|---|---|---|---|---|
| alnp minus q4p_n100 | -1.18 | -1.83 to -0.53 | 0.000 | 72 / 25 / 53 | 1.49 |
| alnp minus q4p_n300 | -0.42 | -0.96 to +0.13 | 0.137 | 40 / 26 / 84 | 1.21 |
| alnp minus q4p | -0.15 | -0.57 to +0.29 | 0.566 | 25 / 24 / 101 | 1.00 |
| recp minus q4p_n100 | -0.74 | -1.42 to -0.07 | 0.038 | 54 / 33 / 63 | 1.56 |
| alnp minus recp | -0.44 | -0.90 to +0.04 | 0.077 | 45 / 25 / 80 | 1.07 |
| q4p minus f16p | +0.58 | +0.09 to +1.10 | 0.031 | 30 / 37 / 83 | 1.17 |
| alnp minus f16p | +0.44 | +0.00 to +0.88 | 0.063 | 21 / 34 / 95 | 1.00 |
| q4p_n100 minus q4p | +1.04 | +0.37 to +1.70 | 0.002 | 29 / 69 / 52 | 1.51 |
| q4p_n300 minus q4p | +0.27 | -0.13 to +0.67 | 0.222 | 17 / 30 / 103 | 0.91 |
| q4p_ga minus q4p | -0.13 | -0.27 to +0.00 | 0.122 | 5 / 1 / 144 | 0.31 |
| q4p_gs minus q4p | -1.47 | -2.03 to -0.95 | 0.000 | 52 / 11 / 87 | 1.25 |
| q4p_gp minus q4p | -0.13 | -0.42 to +0.15 | 0.459 | 17 / 16 / 117 | 0.65 |
| q4p_gas minus q4p | -1.53 | -2.08 to -0.99 | 0.000 | 53 / 11 / 86 | 1.26 |
| q4p_gap minus q4p | -0.25 | -0.60 to +0.07 | 0.166 | 22 / 17 / 111 | 0.75 |
| q4p_gsp minus q4p | -1.53 | -2.08 to -1.00 | 0.000 | 56 / 14 / 80 | 1.25 |
| q4p_gasp minus q4p | -1.63 | -2.19 to -1.10 | 0.000 | 58 / 14 / 78 | 1.28 |
| q4p_ga minus gold | +1.51 | +0.99 to +2.06 | 0.000 | 14 / 56 / 80 | 1.25 |
| q4p_gs minus gold | +0.16 | -0.11 to +0.44 | 0.306 | 14 / 18 / 118 | 0.64 |
| q4p_gp minus gold | +1.51 | +1.02 to +2.02 | 0.000 | 12 / 57 / 81 | 1.18 |
| q4p_gasp minus gold | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 | 0.00 |
| alnp_ga minus alnp | -0.04 | -0.09 to +0.00 | 0.501 | 2 / 0 / 148 | 0.12 |
| alnp_gs minus alnp | -1.20 | -1.69 to -0.74 | 0.000 | 52 / 11 / 87 | 1.09 |
| alnp_gp minus alnp | -0.22 | -0.54 to +0.09 | 0.232 | 20 / 14 / 116 | 0.74 |
| alnp_gas minus alnp | -1.22 | -1.71 to -0.77 | 0.000 | 52 / 10 / 88 | 1.08 |
| alnp_gap minus alnp | -0.25 | -0.60 to +0.07 | 0.187 | 22 / 15 / 113 | 0.78 |
| alnp_gsp minus alnp | -1.42 | -1.93 to -0.93 | 0.000 | 56 / 12 / 82 | 1.16 |
| alnp_gasp minus alnp | -1.49 | -2.01 to -0.99 | 0.000 | 57 / 11 / 82 | 1.18 |
| alnp_ga minus gold | +1.45 | +0.95 to +1.97 | 0.000 | 12 / 56 / 82 | 1.19 |
| alnp_gs minus gold | +0.29 | +0.02 to +0.58 | 0.060 | 9 / 17 / 124 | 0.65 |
| alnp_gp minus gold | +1.27 | +0.85 to +1.73 | 0.000 | 7 / 50 / 93 | 1.04 |
| alnp_gasp minus gold | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 | 0.00 |
| q4p minus gold | +1.63 | +1.10 to +2.19 | 0.000 | 14 / 58 / 78 | 1.28 |
| alnp minus gold | +1.49 | +0.99 to +2.01 | 0.000 | 11 / 57 / 82 | 1.18 |

## Which fields are wrong, and does the committed plan differ from the gold plan? (reports counted once per arrival seed)

**q4p** (3000 report decisions)

| Wrong fields (A action, S sensor, P priority; - none) | Reports | Plan differs from gold plan | Table differs from gold table |
|---|---|---|---|
| - | 2346 | 0 (0%) | 0 |
| S | 342 | 342 (100%) | 342 |
| P | 234 | 63 (27%) | 234 |
| SP | 63 | 63 (100%) | 63 |
| A | 15 | 15 (100%) | 15 |

**alnp** (3000 report decisions)

| Wrong fields (A action, S sensor, P priority; - none) | Reports | Plan differs from gold plan | Table differs from gold table |
|---|---|---|---|
| - | 2361 | 0 (0%) | 0 |
| S | 306 | 306 (100%) | 306 |
| P | 261 | 67 (26%) | 261 |
| SP | 54 | 54 (100%) | 54 |
| A | 18 | 18 (100%) | 18 |

Fit sizes (reports used to fit maps and heads, per fold): {"0": 523, "1": 515, "2": 519, "3": 522, "4": 508}.
Head fits: {"fits": 60, "hit_iteration_limit": 0, "chosen_C": {"0.0003": 2, "0.003": 32, "0.03": 6, "0.3": 3, "3": 17}, "seconds": 230.3, "tol": 1e-06, "max_iter": 3000}
Total run time: 301 s.
