# All-label arms at three load levels (existing records; post-hoc re-analysis; exploratory)

Reading position `prefix`, 3 arrival seeds x 50 episodes = 150 episodes and 5,505 incidents per level. No new run. Pooled intervals are optimistic (the seeds reuse the same reports).

## Level L

| Arm | Missed share | 95% CI |
|---|---|---|
| Gold records | 1.34% | 0.91 to 1.86 |
| F16 reader | 2.07% | 1.57 to 2.63 |
| Q4 retrained, all labels | 2.23% | 1.69 to 2.81 |
| Q4 label-free map | 2.22% | 1.68 to 2.80 |
| Q4 recentred | 2.62% | 2.10 to 3.20 |
| Q4 unchanged transfer | 5.76% | 5.10 to 6.46 |

| First minus second (pp) | Difference | 95% CI | Episodes first better / worse / tied |
|---|---|---|---|
| alnp minus q4p | -0.02 | -0.24 to +0.20 | 11 / 8 / 131 |
| alnp minus recp | -0.40 | -0.69 to -0.11 | 31 / 9 / 110 |
| recp minus q4p | +0.38 | +0.07 to +0.70 | 12 / 26 / 112 |
| q4p minus f16p | +0.16 | -0.16 to +0.49 | 12 / 20 / 118 |
| alnp minus f16p | +0.15 | -0.09 to +0.40 | 12 / 16 / 122 |
| rawp minus q4p | +3.52 | +3.00 to +4.06 | 3 / 106 / 41 |

## Level M

| Arm | Missed share | 95% CI |
|---|---|---|
| Gold records | 4.92% | 4.10 to 5.83 |
| F16 reader | 5.98% | 5.10 to 6.96 |
| Q4 retrained, all labels | 6.56% | 5.69 to 7.49 |
| Q4 label-free map | 6.41% | 5.47 to 7.41 |
| Q4 recentred | 6.85% | 5.96 to 7.76 |
| Q4 unchanged transfer | 9.43% | 8.51 to 10.36 |

| First minus second (pp) | Difference | 95% CI | Episodes first better / worse / tied |
|---|---|---|---|
| alnp minus q4p | -0.15 | -0.57 to +0.29 | 25 / 24 / 101 |
| alnp minus recp | -0.44 | -0.90 to +0.04 | 45 / 25 / 80 |
| recp minus q4p | +0.29 | -0.18 to +0.76 | 29 / 44 / 77 |
| q4p minus f16p | +0.58 | +0.09 to +1.10 | 30 / 37 / 83 |
| alnp minus f16p | +0.44 | +0.00 to +0.88 | 21 / 34 / 95 |
| rawp minus q4p | +2.87 | +2.19 to +3.55 | 17 / 93 / 40 |

## Level H

| Arm | Missed share | 95% CI |
|---|---|---|
| Gold records | 13.42% | 12.11 to 14.67 |
| F16 reader | 14.57% | 13.25 to 15.91 |
| Q4 retrained, all labels | 15.39% | 14.04 to 16.71 |
| Q4 label-free map | 15.30% | 13.96 to 16.65 |
| Q4 recentred | 16.17% | 14.79 to 17.48 |
| Q4 unchanged transfer | 18.58% | 17.29 to 19.82 |

| First minus second (pp) | Difference | 95% CI | Episodes first better / worse / tied |
|---|---|---|---|
| alnp minus q4p | -0.09 | -0.72 to +0.51 | 33 / 30 / 87 |
| alnp minus recp | -0.87 | -1.45 to -0.28 | 56 / 25 / 69 |
| recp minus q4p | +0.78 | +0.04 to +1.48 | 25 / 58 / 67 |
| q4p minus f16p | +0.82 | +0.11 to +1.56 | 32 / 50 / 68 |
| alnp minus f16p | +0.73 | +0.18 to +1.28 | 22 / 45 / 83 |
| rawp minus q4p | +3.20 | +2.23 to +4.17 | 27 / 88 / 35 |

