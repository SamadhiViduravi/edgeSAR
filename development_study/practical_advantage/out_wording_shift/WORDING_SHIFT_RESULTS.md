# Wording-shift check at mission level: results

Exploratory. Style B (new wording, 400 reports) has been inspected many times; nothing is chosen with it. Frozen predictions from heads and a TF-IDF classifier fitted on all 1,000 style-A reports; bounded CBBA, always commit; 20 episodes of 20 reports per level and arrival seed (60 per level); gaps set on style A. Protocol hash `efb54e7ca87658cb341b4abf49eebebca7f17b8659f1ba5e6a32bed92f4af4b3`.
Pooled intervals are optimistic (the three arrival seeds reuse the same 400 reports). Replay consistency: 27243 reports whose saved record equals gold were checked, 0 violations (PASS).

# PRIMARY panel: reading position `prefix`

## Level L

| Arm | Missed share, every incident once | 95% CI | Missed share, priority-weighted 3/2/1 | 95% CI |
|---|---|---|---|---|
| Gold records | 2.08% | 1.42 to 2.79 | 2.23% | 1.53 to 2.98 |
| TF-IDF + LR (text) | 6.69% | 5.58 to 7.93 | 7.73% | 6.40 to 9.10 |
| Keyword rule engine (text) | 11.92% | 10.84 to 13.08 | 13.54% | 12.35 to 14.80 |
| F16 reader | 4.26% | 3.40 to 5.18 | 4.61% | 3.80 to 5.49 |
| Q4 retrained, 1,000 labels | 4.03% | 3.18 to 5.00 | 4.36% | 3.52 to 5.28 |
| Q4 recentred | 5.41% | 4.52 to 6.37 | 6.02% | 5.00 to 7.12 |
| Q4 label-free map | 4.17% | 3.27 to 5.13 | 4.59% | 3.72 to 5.50 |
| Q4 unchanged transfer | 11.44% | 10.24 to 12.71 | 12.93% | 11.52 to 14.36 |

| First minus second (pp) | Every incident once (95% CI) | First better / worse / tied | Priority-weighted (95% CI) |
|---|---|---|---|
| tfidf minus f16p | +2.44 (+1.37 to +3.54) | 11 / 38 / 11 | +3.12 (+1.91 to +4.28) |
| tfidf minus q4p | +2.66 (+1.62 to +3.76) | 7 / 35 / 18 | +3.37 (+2.29 to +4.52) |
| tfidf minus recp | +1.29 (+0.24 to +2.35) | 13 / 29 / 18 | +1.71 (+0.48 to +2.93) |
| tfidf minus alnp | +2.53 (+1.50 to +3.57) | 9 / 37 / 14 | +3.14 (+2.05 to +4.25) |
| tfidf minus gold | +4.61 (+3.63 to +5.70) | 1 / 49 / 10 | +5.50 (+4.36 to +6.71) |
| rule minus f16p | +7.67 (+6.38 to +9.03) | 1 / 54 / 5 | +8.93 (+7.56 to +10.38) |
| rule minus q4p | +7.89 (+6.72 to +9.12) | 1 / 57 / 2 | +9.18 (+7.91 to +10.51) |
| rule minus recp | +6.52 (+5.21 to +7.86) | 3 / 51 / 6 | +7.52 (+6.03 to +9.05) |
| rule minus alnp | +7.76 (+6.56 to +9.01) | 0 / 55 / 5 | +8.95 (+7.71 to +10.26) |
| rule minus gold | +9.84 (+8.66 to +11.07) | 0 / 59 / 1 | +11.31 (+10.02 to +12.61) |
| tfidf minus rule | -5.23 (-6.36 to -4.09) | 51 / 4 / 5 | -5.81 (-7.24 to -4.41) |
| f16p minus q4p | +0.22 (-0.45 to +0.90) | 16 / 18 / 26 | +0.25 (-0.53 to +1.05) |
| alnp minus q4p | +0.13 (-0.44 to +0.69) | 8 / 10 / 42 | +0.23 (-0.37 to +0.80) |
| alnp minus recp | -1.24 (-1.96 to -0.53) | 29 / 10 / 21 | -1.43 (-2.28 to -0.63) |
| recp minus q4p | +1.37 (+0.65 to +2.11) | 7 / 26 / 27 | +1.66 (+0.89 to +2.49) |
| f16p minus gold | +2.17 (+1.49 to +2.95) | 2 / 35 / 23 | +2.38 (+1.63 to +3.20) |

## Level M

| Arm | Missed share, every incident once | 95% CI | Missed share, priority-weighted 3/2/1 | 95% CI |
|---|---|---|---|---|
| Gold records | 5.90% | 4.52 to 7.34 | 6.23% | 4.83 to 7.78 |
| TF-IDF + LR (text) | 10.64% | 9.02 to 12.25 | 11.56% | 9.84 to 13.31 |
| Keyword rule engine (text) | 14.72% | 13.59 to 16.02 | 16.28% | 15.08 to 17.60 |
| F16 reader | 8.20% | 6.87 to 9.65 | 8.74% | 7.38 to 10.22 |
| Q4 retrained, 1,000 labels | 8.33% | 6.85 to 9.88 | 8.97% | 7.39 to 10.64 |
| Q4 recentred | 10.42% | 9.12 to 11.84 | 11.46% | 10.13 to 12.87 |
| Q4 label-free map | 8.47% | 7.02 to 10.08 | 9.45% | 7.92 to 11.14 |
| Q4 unchanged transfer | 14.76% | 13.49 to 16.10 | 16.76% | 15.31 to 18.22 |

| First minus second (pp) | Every incident once (95% CI) | First better / worse / tied | Priority-weighted (95% CI) |
|---|---|---|---|
| tfidf minus f16p | +2.44 (+1.04 to +3.84) | 17 / 37 / 6 | +2.82 (+1.19 to +4.43) |
| tfidf minus q4p | +2.30 (+0.98 to +3.67) | 15 / 34 / 11 | +2.59 (+1.14 to +4.05) |
| tfidf minus recp | +0.22 (-1.23 to +1.65) | 20 / 26 / 14 | +0.11 (-1.44 to +1.64) |
| tfidf minus alnp | +2.17 (+0.78 to +3.56) | 14 / 34 / 12 | +2.11 (+0.54 to +3.65) |
| tfidf minus gold | +4.74 (+3.30 to +6.24) | 6 / 45 / 9 | +5.33 (+3.83 to +6.87) |
| rule minus f16p | +6.52 (+5.25 to +7.80) | 3 / 49 / 8 | +7.54 (+6.17 to +8.94) |
| rule minus q4p | +6.38 (+5.02 to +7.77) | 6 / 50 / 4 | +7.31 (+5.74 to +8.84) |
| rule minus recp | +4.30 (+2.90 to +5.66) | 10 / 46 / 4 | +4.82 (+3.33 to +6.30) |
| rule minus alnp | +6.25 (+4.80 to +7.63) | 5 / 48 / 7 | +6.82 (+5.22 to +8.38) |
| rule minus gold | +8.82 (+7.43 to +10.23) | 3 / 56 / 1 | +10.04 (+8.47 to +11.56) |
| tfidf minus rule | -4.08 (-5.48 to -2.69) | 43 / 8 / 9 | -4.72 (-6.35 to -3.09) |
| f16p minus q4p | -0.13 (-1.00 to +0.67) | 14 / 18 / 28 | -0.23 (-1.29 to +0.75) |
| alnp minus q4p | +0.13 (-0.62 to +0.86) | 12 / 15 / 33 | +0.48 (-0.33 to +1.23) |
| alnp minus recp | -1.95 (-2.87 to -1.04) | 34 / 7 / 19 | -2.00 (-2.99 to -1.00) |
| recp minus q4p | +2.08 (+1.05 to +3.10) | 7 / 37 / 16 | +2.48 (+1.40 to +3.53) |
| f16p minus gold | +2.30 (+1.19 to +3.43) | 6 / 35 / 19 | +2.51 (+1.15 to +3.84) |

## Level H

| Arm | Missed share, every incident once | 95% CI | Missed share, priority-weighted 3/2/1 | 95% CI |
|---|---|---|---|---|
| Gold records | 13.87% | 12.10 to 15.80 | 13.79% | 12.01 to 15.78 |
| TF-IDF + LR (text) | 17.91% | 16.28 to 19.56 | 18.97% | 17.26 to 20.82 |
| Keyword rule engine (text) | 20.88% | 19.23 to 22.59 | 22.78% | 21.04 to 24.62 |
| F16 reader | 16.40% | 14.48 to 18.41 | 17.46% | 15.43 to 19.50 |
| Q4 retrained, 1,000 labels | 17.20% | 15.17 to 19.22 | 18.09% | 15.91 to 20.26 |
| Q4 recentred | 18.31% | 16.47 to 20.23 | 19.84% | 17.93 to 21.75 |
| Q4 label-free map | 16.80% | 14.69 to 18.94 | 17.79% | 15.58 to 20.02 |
| Q4 unchanged transfer | 21.41% | 19.89 to 23.20 | 23.90% | 22.26 to 25.70 |

| First minus second (pp) | Every incident once (95% CI) | First better / worse / tied | Priority-weighted (95% CI) |
|---|---|---|---|
| tfidf minus f16p | +1.51 (+0.13 to +2.95) | 16 / 28 / 16 | +1.52 (+0.10 to +3.05) |
| tfidf minus q4p | +0.71 (-0.77 to +2.20) | 17 / 29 / 14 | +0.88 (-0.52 to +2.24) |
| tfidf minus recp | -0.40 (-1.90 to +1.12) | 25 / 26 / 9 | -0.86 (-2.42 to +0.70) |
| tfidf minus alnp | +1.11 (-0.52 to +2.72) | 15 / 29 / 16 | +1.18 (-0.41 to +2.77) |
| tfidf minus gold | +4.03 (+2.68 to +5.39) | 10 / 40 / 10 | +5.18 (+4.02 to +6.38) |
| rule minus f16p | +4.48 (+2.69 to +6.35) | 13 / 41 / 6 | +5.33 (+3.54 to +7.23) |
| rule minus q4p | +3.68 (+1.81 to +5.56) | 14 / 38 / 8 | +4.70 (+2.84 to +6.57) |
| rule minus recp | +2.57 (+0.82 to +4.35) | 15 / 38 / 7 | +2.95 (+1.31 to +4.65) |
| rule minus alnp | +4.08 (+2.07 to +6.14) | 15 / 39 / 6 | +4.99 (+3.05 to +6.99) |
| rule minus gold | +7.00 (+5.36 to +8.70) | 4 / 47 / 9 | +8.99 (+7.45 to +10.57) |
| tfidf minus rule | -2.97 (-4.41 to -1.49) | 35 / 13 / 12 | -3.81 (-5.34 to -2.29) |
| f16p minus q4p | -0.80 (-2.17 to +0.49) | 25 / 18 / 17 | -0.63 (-1.97 to +0.65) |
| alnp minus q4p | -0.40 (-1.42 to +0.53) | 16 / 17 / 27 | -0.29 (-1.23 to +0.58) |
| alnp minus recp | -1.51 (-2.62 to -0.43) | 29 / 13 / 18 | -2.04 (-3.14 to -1.00) |
| recp minus q4p | +1.11 (-0.26 to +2.43) | 17 / 29 / 14 | +1.75 (+0.40 to +3.08) |
| f16p minus gold | +2.53 (+1.44 to +3.63) | 11 / 36 / 13 | +3.66 (+2.61 to +4.73) |

# SECOND panel: reading position `end`

## Level L

| Arm | Missed share, every incident once | 95% CI | Missed share, priority-weighted 3/2/1 | 95% CI |
|---|---|---|---|---|
| Gold records | 2.08% | 1.42 to 2.79 | 2.23% | 1.53 to 2.98 |
| TF-IDF + LR (text) | 6.69% | 5.58 to 7.93 | 7.73% | 6.40 to 9.10 |
| Keyword rule engine (text) | 11.92% | 10.84 to 13.08 | 13.54% | 12.35 to 14.80 |
| F16 reader (end) | 5.54% | 4.53 to 6.57 | 6.38% | 5.27 to 7.53 |
| Q4 retrained (end) | 5.59% | 4.49 to 6.75 | 6.04% | 4.88 to 7.27 |
| Q4 recentred (end) | 5.72% | 4.74 to 6.75 | 6.46% | 5.37 to 7.58 |
| Q4 label-free map (end) | 4.83% | 3.96 to 5.81 | 5.31% | 4.34 to 6.29 |
| Q4 unchanged (end) | 18.71% | 17.59 to 19.80 | 20.21% | 19.09 to 21.29 |

| First minus second (pp) | Every incident once (95% CI) | First better / worse / tied | Priority-weighted (95% CI) |
|---|---|---|---|
| tfidf minus f16 | +1.15 (+0.04 to +2.33) | 18 / 31 / 11 | +1.35 (+0.06 to +2.64) |
| tfidf minus q4 | +1.11 (+0.18 to +2.10) | 16 / 27 / 17 | +1.68 (+0.59 to +2.79) |
| tfidf minus rec | +0.98 (-0.17 to +2.15) | 18 / 27 / 15 | +1.26 (-0.02 to +2.50) |
| tfidf minus aln | +1.86 (+0.79 to +3.00) | 16 / 35 / 9 | +2.42 (+1.27 to +3.60) |
| rule minus f16 | +6.38 (+5.11 to +7.68) | 5 / 51 / 4 | +7.16 (+5.85 to +8.48) |
| rule minus q4 | +6.34 (+5.11 to +7.61) | 4 / 52 / 4 | +7.50 (+6.19 to +8.82) |
| rule minus rec | +6.21 (+4.87 to +7.56) | 3 / 49 / 8 | +7.08 (+5.60 to +8.56) |
| rule minus aln | +7.09 (+5.86 to +8.37) | 2 / 54 / 4 | +8.23 (+6.91 to +9.57) |
| aln minus q4 | -0.75 (-1.53 to +0.00) | 19 / 12 / 29 | -0.74 (-1.62 to +0.12) |
| aln minus rec | -0.89 (-1.71 to -0.09) | 22 / 11 / 27 | -1.16 (-2.14 to -0.21) |
| rec minus q4 | +0.13 (-0.79 to +1.06) | 16 / 22 / 22 | +0.42 (-0.64 to +1.48) |
| f16 minus q4 | -0.04 (-0.86 to +0.77) | 16 / 17 / 27 | +0.34 (-0.58 to +1.27) |

## Level M

| Arm | Missed share, every incident once | 95% CI | Missed share, priority-weighted 3/2/1 | 95% CI |
|---|---|---|---|---|
| Gold records | 5.90% | 4.52 to 7.34 | 6.23% | 4.83 to 7.78 |
| TF-IDF + LR (text) | 10.64% | 9.02 to 12.25 | 11.56% | 9.84 to 13.31 |
| Keyword rule engine (text) | 14.72% | 13.59 to 16.02 | 16.28% | 15.08 to 17.60 |
| F16 reader (end) | 9.09% | 7.71 to 10.58 | 9.81% | 8.33 to 11.29 |
| Q4 retrained (end) | 9.40% | 7.98 to 10.86 | 9.92% | 8.46 to 11.42 |
| Q4 recentred (end) | 10.11% | 8.56 to 11.80 | 10.84% | 9.18 to 12.67 |
| Q4 label-free map (end) | 8.91% | 7.48 to 10.49 | 9.48% | 7.96 to 11.15 |
| Q4 unchanged (end) | 21.14% | 19.67 to 22.65 | 22.76% | 21.23 to 24.37 |

| First minus second (pp) | Every incident once (95% CI) | First better / worse / tied | Priority-weighted (95% CI) |
|---|---|---|---|
| tfidf minus f16 | +1.55 (+0.04 to +3.07) | 17 / 34 / 9 | +1.75 (+0.09 to +3.39) |
| tfidf minus q4 | +1.24 (-0.13 to +2.65) | 22 / 30 / 8 | +1.64 (+0.11 to +3.17) |
| tfidf minus rec | +0.53 (-0.85 to +1.95) | 23 / 28 / 9 | +0.72 (-0.90 to +2.33) |
| tfidf minus aln | +1.73 (+0.40 to +3.11) | 20 / 32 / 8 | +2.08 (+0.52 to +3.66) |
| rule minus f16 | +5.63 (+4.12 to +7.15) | 9 / 46 / 5 | +6.46 (+4.95 to +8.01) |
| rule minus q4 | +5.32 (+3.95 to +6.71) | 7 / 48 / 5 | +6.36 (+4.92 to +7.79) |
| rule minus rec | +4.61 (+3.07 to +6.16) | 9 / 40 / 11 | +5.43 (+3.68 to +7.11) |
| rule minus aln | +5.81 (+4.33 to +7.25) | 8 / 48 / 4 | +6.80 (+5.19 to +8.39) |
| aln minus q4 | -0.49 (-1.50 to +0.49) | 19 / 16 / 25 | -0.44 (-1.59 to +0.68) |
| aln minus rec | -1.20 (-2.28 to -0.13) | 26 / 14 / 20 | -1.37 (-2.60 to -0.14) |
| rec minus q4 | +0.71 (-0.41 to +1.88) | 18 / 22 / 20 | +0.93 (-0.48 to +2.44) |
| f16 minus q4 | -0.31 (-1.33 to +0.67) | 18 / 16 / 26 | -0.11 (-1.11 to +0.93) |

## Level H

| Arm | Missed share, every incident once | 95% CI | Missed share, priority-weighted 3/2/1 | 95% CI |
|---|---|---|---|---|
| Gold records | 13.87% | 12.10 to 15.80 | 13.79% | 12.01 to 15.78 |
| TF-IDF + LR (text) | 17.91% | 16.28 to 19.56 | 18.97% | 17.26 to 20.82 |
| Keyword rule engine (text) | 20.88% | 19.23 to 22.59 | 22.78% | 21.04 to 24.62 |
| F16 reader (end) | 16.80% | 14.80 to 18.90 | 17.79% | 15.74 to 19.98 |
| Q4 retrained (end) | 17.60% | 15.62 to 19.56 | 18.61% | 16.56 to 20.65 |
| Q4 recentred (end) | 18.13% | 15.97 to 20.35 | 19.41% | 17.19 to 21.65 |
| Q4 label-free map (end) | 17.33% | 15.60 to 19.19 | 18.34% | 16.53 to 20.29 |
| Q4 unchanged (end) | 25.75% | 24.29 to 27.34 | 27.73% | 26.20 to 29.35 |

| First minus second (pp) | Every incident once (95% CI) | First better / worse / tied | Priority-weighted (95% CI) |
|---|---|---|---|
| tfidf minus f16 | +1.11 (-0.44 to +2.69) | 20 / 28 / 12 | +1.18 (-0.38 to +2.79) |
| tfidf minus q4 | +0.31 (-0.88 to +1.56) | 24 / 22 / 14 | +0.36 (-0.82 to +1.57) |
| tfidf minus rec | -0.22 (-1.88 to +1.29) | 21 / 24 / 15 | -0.44 (-1.98 to +1.02) |
| tfidf minus aln | +0.58 (-0.83 to +2.00) | 24 / 26 / 10 | +0.63 (-0.90 to +2.15) |
| rule minus f16 | +4.08 (+2.22 to +5.97) | 16 / 39 / 5 | +4.99 (+3.10 to +6.89) |
| rule minus q4 | +3.28 (+1.58 to +5.02) | 14 / 36 / 10 | +4.17 (+2.38 to +5.99) |
| rule minus rec | +2.75 (+0.82 to +4.60) | 16 / 37 / 7 | +3.37 (+1.46 to +5.24) |
| rule minus aln | +3.55 (+1.78 to +5.37) | 14 / 37 / 9 | +4.44 (+2.62 to +6.29) |
| aln minus q4 | -0.27 (-1.33 to +0.80) | 19 / 18 / 23 | -0.27 (-1.34 to +0.84) |
| aln minus rec | -0.80 (-2.24 to +0.58) | 27 / 17 / 16 | -1.07 (-2.59 to +0.36) |
| rec minus q4 | +0.53 (-0.80 to +1.96) | 19 / 27 / 14 | +0.80 (-0.58 to +2.22) |
| f16 minus q4 | -0.80 (-1.86 to +0.27) | 25 / 17 / 18 | -0.82 (-1.98 to +0.33) |

Total run time 71 s.
