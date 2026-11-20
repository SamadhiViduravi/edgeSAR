# EdgeSAR fresh confirmation: results (fresh mode)

Protocol SHA-256 `dacfce61de3d86bfa0df3b93766a81d2167808c68f9a2b540990ff2bc5dc14d5`; script SHA-256 `3241992ad203573dd75da7fe3db3426cfd5e8515e5f1b433c69fe7582242fe42`.

Evaluation set: `{"set": "fresh", "cases_sha256": "115e09d8780771beb0e3721feb74ba8b83333e9a230b74dc863023e508e7414b", "reports": 7000, "text_also_in_development": 1432, "styles": {"A": 6000, "B": 1000}, "vectors_sha256": {"Q4_K_M_end.npy": "3bcc2ad91eb98fa1ec5fae143d4dd5ec673ca6fc1d2ead6dda04d1b92d91ce26", "Q4_K_M_prefix.npy": "7cd510d2b2893d6c13a738b2cb501f0db95131ba4b95b39ca7f7ad3925cc68ad", "f16_end.npy": "aa300ecbe162e593c632917cdb7f20dbf1162a2a40bf7e02cb8fb6d798481dbd", "f16_prefix.npy": "02aea0407b0e3c5ed1bedec630c9805fc330a3a2e6c055de0c3bf7f940a97641"}}`

Replay consistency: {'reports_checked': 1124307, 'violations': 0}

## Primary family (A_M_s11), Holm-adjusted

| Test | First minus second | Difference (pp) | 95% CI | p | p (Holm) | Confirmed |
|---|---|---|---|---|---|---|
| H1 | rawp minus f16p | +3.43 | +2.98 to +3.88 | 0.0001 | 0.0004 | YES |
| H2a | alnp minus rawp | -3.36 | -3.87 to -2.85 | 0.0001 | 0.0004 | YES |
| H2b | q4p minus rawp | -3.11 | -3.62 to -2.60 | 0.0001 | 0.0004 | YES |
| H3 | alnp minus q4p_n100 | -2.72 | -3.14 to -2.30 | 0.0001 | 0.0004 | YES |

Non-inferiority of the map against retraining with 1,000 labels (upper bound below the margin): {'margin_0.25pp': True, 'margin_0.5pp': True}

## A_L_s12 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.53% | 1.24 to 1.86 | - |
| FP16 reader | 2.20% | 1.85 to 2.56 | 83.6% |
| Q4, FP16 reader unchanged | 5.79% | 5.40 to 6.21 | 67.7% |
| Q4, recentred | 2.96% | 2.58 to 3.35 | 76.6% |
| Q4, label-free map | 2.26% | 1.91 to 2.63 | 81.8% |
| Q4, retrained (1,000 labels) | 2.26% | 1.88 to 2.66 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 4.09% | 3.69 to 4.50 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 2.87% | 2.53 to 3.24 | - |
| TF-IDF + LR (text) | 1.59% | 1.28 to 1.91 | 98.6% |
| Keyword rules (text) | 1.64% | 1.33 to 1.96 | 97.4% |
| Q4 retrained, gold sensor | 1.62% | 1.31 to 1.96 | 90.7% |
| Q4 map, gold sensor | 1.65% | 1.34 to 1.97 | 90.6% |
| FP16 reader (end) | 2.22% | 1.86 to 2.59 | 81.7% |
| Q4 unchanged (end) | 15.44% | 14.88 to 16.00 | 51.2% |
| Q4 recentred (end) | 3.57% | 3.14 to 4.04 | 70.7% |
| Q4 map (end) | 2.58% | 2.18 to 2.99 | 78.8% |
| Q4 retrained (end) | 2.54% | 2.19 to 2.93 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.60 | +3.20 to +3.98 | 0.0001 | 17 / 229 / 54 |
| H2a: alnp minus rawp | -3.54 | -3.90 to -3.16 | 0.0001 | 227 / 17 / 56 |
| H2b: q4p minus rawp | -3.53 | -3.91 to -3.13 | 0.0001 | 228 / 17 / 55 |
| H3: alnp minus q4p_n100 | -1.84 | -2.09 to -1.58 | 0.0001 | 236 / 39 / 25 |
| S1: alnp minus q4p | -0.01 | -0.20 to +0.18 | 1.0000 | 27 / 26 / 247 |
| S2: alnp minus q4p_n300 | -0.62 | -0.83 to -0.41 | 0.0001 | 162 / 53 / 85 |
| S3: alnp minus recp | -0.71 | -0.93 to -0.49 | 0.0001 | 92 / 23 / 185 |
| S4: recp minus q4p_n100 | -1.13 | -1.40 to -0.86 | 0.0001 | 198 / 63 / 39 |
| S5: q4p minus f16p | +0.07 | -0.10 to +0.25 | 0.4936 | 26 / 34 / 240 |
| S6: alnp minus f16p | +0.06 | -0.11 to +0.24 | 0.5607 | 20 / 25 / 255 |
| S7: tfidf minus f16p | -0.61 | -0.81 to -0.42 | 0.0001 | 66 / 11 / 223 |
| S8: tfidf minus alnp | -0.67 | -0.87 to -0.48 | 0.0001 | 75 / 13 / 212 |
| S9: rule minus alnp | -0.62 | -0.83 to -0.40 | 0.0001 | 73 / 19 / 208 |
| S10: q4p_goldS minus q4p | -0.64 | -0.85 to -0.45 | 0.0001 | 61 / 9 / 230 |
| S11: alnp_goldS minus alnp | -0.61 | -0.78 to -0.45 | 0.0001 | 59 / 4 / 237 |
| S12: raw minus f16 | +13.22 | +12.62 to +13.82 | 0.0001 | 0 / 298 / 2 |
| S13: aln minus q4 | +0.03 | -0.23 to +0.30 | 0.8451 | 41 / 46 / 213 |
| S14: q4p_n100 minus q4p | +1.83 | +1.56 to +2.09 | 0.0001 | 35 / 235 / 30 |
| S15: f16p minus gold | +0.66 | +0.46 to +0.87 | 0.0001 | 10 / 68 / 222 |

## A_L_s11 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.70% | 1.40 to 2.02 | - |
| FP16 reader | 2.45% | 2.08 to 2.85 | 83.6% |
| Q4, FP16 reader unchanged | 6.01% | 5.58 to 6.47 | 67.7% |
| Q4, recentred | 3.37% | 2.98 to 3.78 | 76.6% |
| Q4, label-free map | 2.43% | 2.07 to 2.82 | 81.8% |
| Q4, retrained (1,000 labels) | 2.58% | 2.18 to 3.01 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 4.36% | 3.97 to 4.74 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 3.20% | 2.85 to 3.58 | - |
| TF-IDF + LR (text) | 1.71% | 1.42 to 2.01 | 98.6% |
| Keyword rules (text) | 1.68% | 1.38 to 1.99 | 97.4% |
| Q4 retrained, gold sensor | 1.91% | 1.59 to 2.26 | 90.7% |
| Q4 map, gold sensor | 1.98% | 1.65 to 2.32 | 90.6% |
| FP16 reader (end) | 2.34% | 1.99 to 2.71 | 81.7% |
| Q4 unchanged (end) | 15.56% | 14.95 to 16.14 | 51.2% |
| Q4 recentred (end) | 3.69% | 3.28 to 4.11 | 70.7% |
| Q4 map (end) | 2.74% | 2.36 to 3.15 | 78.8% |
| Q4 retrained (end) | 2.78% | 2.40 to 3.21 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.56 | +3.18 to +3.94 | 0.0001 | 15 / 230 / 55 |
| H2a: alnp minus rawp | -3.58 | -3.96 to -3.19 | 0.0001 | 230 / 16 / 54 |
| H2b: q4p minus rawp | -3.43 | -3.83 to -3.04 | 0.0001 | 225 / 19 / 56 |
| H3: alnp minus q4p_n100 | -1.93 | -2.19 to -1.67 | 0.0001 | 238 / 36 / 26 |
| S1: alnp minus q4p | -0.15 | -0.35 to +0.05 | 0.1796 | 26 / 21 / 253 |
| S2: alnp minus q4p_n300 | -0.77 | -0.96 to -0.59 | 0.0001 | 168 / 48 / 84 |
| S3: alnp minus recp | -0.94 | -1.21 to -0.68 | 0.0001 | 92 / 18 / 190 |
| S4: recp minus q4p_n100 | -0.99 | -1.26 to -0.72 | 0.0001 | 196 / 68 / 36 |
| S5: q4p minus f16p | +0.13 | -0.07 to +0.33 | 0.2313 | 24 / 32 / 244 |
| S6: alnp minus f16p | -0.02 | -0.17 to +0.14 | 0.9146 | 22 / 22 / 256 |
| S7: tfidf minus f16p | -0.74 | -0.96 to -0.54 | 0.0001 | 70 / 7 / 223 |
| S8: tfidf minus alnp | -0.72 | -0.93 to -0.52 | 0.0001 | 76 / 10 / 214 |
| S9: rule minus alnp | -0.75 | -0.97 to -0.54 | 0.0001 | 80 / 11 / 209 |
| S10: q4p_goldS minus q4p | -0.67 | -0.92 to -0.43 | 0.0001 | 60 / 12 / 228 |
| S11: alnp_goldS minus alnp | -0.45 | -0.66 to -0.25 | 0.0001 | 52 / 13 / 235 |
| S12: raw minus f16 | +13.21 | +12.64 to +13.78 | 0.0001 | 0 / 299 / 1 |
| S13: aln minus q4 | -0.03 | -0.29 to +0.23 | 0.8473 | 51 / 48 / 201 |
| S14: q4p_n100 minus q4p | +1.79 | +1.52 to +2.05 | 0.0001 | 43 / 234 / 23 |
| S15: f16p minus gold | +0.75 | +0.56 to +0.96 | 0.0001 | 5 / 71 / 224 |

## A_L_s13 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.85% | 1.54 to 2.19 | - |
| FP16 reader | 2.53% | 2.13 to 2.96 | 83.6% |
| Q4, FP16 reader unchanged | 6.35% | 5.90 to 6.86 | 67.7% |
| Q4, recentred | 3.48% | 3.04 to 3.93 | 76.6% |
| Q4, label-free map | 2.48% | 2.10 to 2.89 | 81.8% |
| Q4, retrained (1,000 labels) | 2.66% | 2.27 to 3.11 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 4.60% | 4.20 to 5.03 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 3.37% | 2.98 to 3.79 | - |
| TF-IDF + LR (text) | 1.89% | 1.58 to 2.23 | 98.6% |
| Keyword rules (text) | 1.96% | 1.65 to 2.31 | 97.4% |
| Q4 retrained, gold sensor | 1.93% | 1.62 to 2.25 | 90.7% |
| Q4 map, gold sensor | 1.99% | 1.68 to 2.34 | 90.6% |
| FP16 reader (end) | 2.59% | 2.19 to 3.03 | 81.7% |
| Q4 unchanged (end) | 15.70% | 15.12 to 16.28 | 51.2% |
| Q4 recentred (end) | 3.89% | 3.42 to 4.34 | 70.7% |
| Q4 map (end) | 2.88% | 2.49 to 3.31 | 78.8% |
| Q4 retrained (end) | 3.04% | 2.63 to 3.48 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.82 | +3.45 to +4.20 | 0.0001 | 9 / 235 / 56 |
| H2a: alnp minus rawp | -3.87 | -4.24 to -3.49 | 0.0001 | 239 / 10 / 51 |
| H2b: q4p minus rawp | -3.69 | -4.10 to -3.29 | 0.0001 | 231 / 14 / 55 |
| H3: alnp minus q4p_n100 | -2.11 | -2.36 to -1.87 | 0.0001 | 247 / 31 / 22 |
| S1: alnp minus q4p | -0.17 | -0.38 to +0.03 | 0.1128 | 32 / 21 / 247 |
| S2: alnp minus q4p_n300 | -0.88 | -1.09 to -0.68 | 0.0001 | 177 / 42 / 81 |
| S3: alnp minus recp | -1.00 | -1.27 to -0.74 | 0.0001 | 102 / 16 / 182 |
| S4: recp minus q4p_n100 | -1.11 | -1.39 to -0.84 | 0.0001 | 201 / 64 / 35 |
| S5: q4p minus f16p | +0.13 | -0.08 to +0.34 | 0.2529 | 23 / 35 / 242 |
| S6: alnp minus f16p | -0.04 | -0.19 to +0.10 | 0.6495 | 21 / 20 / 259 |
| S7: tfidf minus f16p | -0.64 | -0.88 to -0.40 | 0.0001 | 58 / 15 / 227 |
| S8: tfidf minus alnp | -0.59 | -0.85 to -0.35 | 0.0001 | 66 / 19 / 215 |
| S9: rule minus alnp | -0.52 | -0.80 to -0.26 | 0.0005 | 63 / 28 / 209 |
| S10: q4p_goldS minus q4p | -0.73 | -0.97 to -0.51 | 0.0001 | 62 / 9 / 229 |
| S11: alnp_goldS minus alnp | -0.49 | -0.71 to -0.29 | 0.0001 | 51 / 13 / 236 |
| S12: raw minus f16 | +13.11 | +12.47 to +13.72 | 0.0001 | 2 / 294 / 4 |
| S13: aln minus q4 | -0.16 | -0.40 to +0.08 | 0.2260 | 52 / 41 / 207 |
| S14: q4p_n100 minus q4p | +1.94 | +1.65 to +2.23 | 0.0001 | 41 / 234 / 25 |
| S15: f16p minus gold | +0.68 | +0.44 to +0.93 | 0.0001 | 14 / 59 / 227 |

## A_M_s11 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 5.71% | 5.14 to 6.30 | - |
| FP16 reader | 6.84% | 6.22 to 7.48 | 83.6% |
| Q4, FP16 reader unchanged | 10.27% | 9.64 to 10.90 | 67.7% |
| Q4, recentred | 7.87% | 7.20 to 8.54 | 76.6% |
| Q4, label-free map | 6.91% | 6.26 to 7.57 | 81.8% |
| Q4, retrained (1,000 labels) | 7.16% | 6.49 to 7.83 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 9.63% | 9.02 to 10.24 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.05% | 7.44 to 8.65 | - |
| TF-IDF + LR (text) | 5.83% | 5.24 to 6.41 | 98.6% |
| Keyword rules (text) | 5.78% | 5.18 to 6.37 | 97.4% |
| Q4 retrained, gold sensor | 5.84% | 5.26 to 6.45 | 90.7% |
| Q4 map, gold sensor | 5.83% | 5.23 to 6.43 | 90.6% |
| FP16 reader (end) | 7.06% | 6.40 to 7.73 | 81.7% |
| Q4 unchanged (end) | 17.87% | 17.22 to 18.54 | 51.2% |
| Q4 recentred (end) | 8.28% | 7.63 to 8.95 | 70.7% |
| Q4 map (end) | 7.07% | 6.42 to 7.72 | 78.8% |
| Q4 retrained (end) | 7.56% | 6.90 to 8.23 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.43 | +2.98 to +3.88 | 0.0001 | 29 / 216 / 55 |
| H2a: alnp minus rawp | -3.36 | -3.87 to -2.85 | 0.0001 | 217 / 38 / 45 |
| H2b: q4p minus rawp | -3.11 | -3.62 to -2.60 | 0.0001 | 209 / 41 / 50 |
| H3: alnp minus q4p_n100 | -2.72 | -3.14 to -2.30 | 0.0001 | 230 / 55 / 15 |
| S1: alnp minus q4p | -0.25 | -0.60 to +0.08 | 0.1602 | 46 / 36 / 218 |
| S2: alnp minus q4p_n300 | -1.14 | -1.49 to -0.80 | 0.0001 | 188 / 73 / 39 |
| S3: alnp minus recp | -0.96 | -1.35 to -0.56 | 0.0001 | 111 / 50 / 139 |
| S4: recp minus q4p_n100 | -1.76 | -2.16 to -1.37 | 0.0001 | 207 / 75 / 18 |
| S5: q4p minus f16p | +0.32 | +0.00 to +0.65 | 0.0679 | 45 / 53 / 202 |
| S6: alnp minus f16p | +0.07 | -0.23 to +0.36 | 0.6846 | 46 / 48 / 206 |
| S7: tfidf minus f16p | -1.01 | -1.39 to -0.62 | 0.0001 | 108 / 31 / 161 |
| S8: tfidf minus alnp | -1.08 | -1.50 to -0.67 | 0.0001 | 102 / 36 / 162 |
| S9: rule minus alnp | -1.13 | -1.57 to -0.70 | 0.0001 | 110 / 44 / 146 |
| S10: q4p_goldS minus q4p | -1.32 | -1.73 to -0.91 | 0.0001 | 97 / 29 / 174 |
| S11: alnp_goldS minus alnp | -1.08 | -1.45 to -0.70 | 0.0001 | 92 / 25 / 183 |
| S12: raw minus f16 | +10.81 | +10.14 to +11.50 | 0.0001 | 5 / 285 / 10 |
| S13: aln minus q4 | -0.49 | -0.83 to -0.14 | 0.0089 | 86 / 50 / 164 |
| S14: q4p_n100 minus q4p | +2.47 | +2.08 to +2.86 | 0.0001 | 54 / 230 / 16 |
| S15: f16p minus gold | +1.13 | +0.74 to +1.52 | 0.0001 | 30 / 115 / 155 |

## A_M_s12 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 5.88% | 5.24 to 6.48 | - |
| FP16 reader | 6.89% | 6.23 to 7.60 | 83.6% |
| Q4, FP16 reader unchanged | 10.58% | 9.94 to 11.26 | 67.7% |
| Q4, recentred | 8.14% | 7.45 to 8.83 | 76.6% |
| Q4, label-free map | 7.02% | 6.39 to 7.69 | 81.8% |
| Q4, retrained (1,000 labels) | 7.08% | 6.42 to 7.77 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 9.96% | 9.32 to 10.58 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.16% | 7.51 to 8.79 | - |
| TF-IDF + LR (text) | 5.89% | 5.24 to 6.49 | 98.6% |
| Keyword rules (text) | 5.98% | 5.35 to 6.60 | 97.4% |
| Q4 retrained, gold sensor | 6.04% | 5.40 to 6.67 | 90.7% |
| Q4 map, gold sensor | 6.03% | 5.41 to 6.64 | 90.6% |
| FP16 reader (end) | 7.18% | 6.52 to 7.84 | 81.7% |
| Q4 unchanged (end) | 18.07% | 17.39 to 18.70 | 51.2% |
| Q4 recentred (end) | 8.38% | 7.71 to 9.07 | 70.7% |
| Q4 map (end) | 7.69% | 6.98 to 8.40 | 78.8% |
| Q4 retrained (end) | 7.82% | 7.07 to 8.57 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.69 | +3.13 to +4.25 | 0.0001 | 35 / 227 / 38 |
| H2a: alnp minus rawp | -3.56 | -4.12 to -3.02 | 0.0001 | 210 / 36 / 54 |
| H2b: q4p minus rawp | -3.50 | -4.06 to -2.94 | 0.0001 | 213 / 36 / 51 |
| H3: alnp minus q4p_n100 | -2.94 | -3.35 to -2.53 | 0.0001 | 245 / 41 / 14 |
| S1: alnp minus q4p | -0.06 | -0.41 to +0.29 | 0.7716 | 50 / 54 / 196 |
| S2: alnp minus q4p_n300 | -1.14 | -1.47 to -0.82 | 0.0001 | 181 / 70 / 49 |
| S3: alnp minus recp | -1.12 | -1.54 to -0.72 | 0.0001 | 126 / 48 / 126 |
| S4: recp minus q4p_n100 | -1.82 | -2.21 to -1.40 | 0.0001 | 203 / 74 / 23 |
| S5: q4p minus f16p | +0.19 | -0.17 to +0.53 | 0.3159 | 47 / 59 / 194 |
| S6: alnp minus f16p | +0.13 | -0.20 to +0.45 | 0.4738 | 32 / 49 / 219 |
| S7: tfidf minus f16p | -1.00 | -1.36 to -0.65 | 0.0001 | 97 / 41 / 162 |
| S8: tfidf minus alnp | -1.13 | -1.51 to -0.75 | 0.0001 | 112 / 42 / 146 |
| S9: rule minus alnp | -1.04 | -1.41 to -0.67 | 0.0001 | 108 / 44 / 148 |
| S10: q4p_goldS minus q4p | -1.05 | -1.41 to -0.70 | 0.0001 | 86 / 25 / 189 |
| S11: alnp_goldS minus alnp | -0.99 | -1.33 to -0.67 | 0.0001 | 90 / 24 / 186 |
| S12: raw minus f16 | +10.89 | +10.22 to +11.55 | 0.0001 | 5 / 286 / 9 |
| S13: aln minus q4 | -0.13 | -0.56 to +0.29 | 0.5736 | 80 / 72 / 148 |
| S14: q4p_n100 minus q4p | +2.88 | +2.44 to +3.32 | 0.0001 | 44 / 243 / 13 |
| S15: f16p minus gold | +1.01 | +0.68 to +1.36 | 0.0001 | 37 / 97 / 166 |

## A_M_s13 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 5.95% | 5.37 to 6.56 | - |
| FP16 reader | 7.21% | 6.56 to 7.95 | 83.6% |
| Q4, FP16 reader unchanged | 10.65% | 10.04 to 11.33 | 67.7% |
| Q4, recentred | 8.36% | 7.69 to 9.07 | 76.6% |
| Q4, label-free map | 7.21% | 6.55 to 7.92 | 81.8% |
| Q4, retrained (1,000 labels) | 7.42% | 6.76 to 8.13 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 10.26% | 9.64 to 10.90 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.62% | 7.98 to 9.31 | - |
| TF-IDF + LR (text) | 6.14% | 5.56 to 6.75 | 98.6% |
| Keyword rules (text) | 6.03% | 5.44 to 6.62 | 97.4% |
| Q4 retrained, gold sensor | 6.26% | 5.66 to 6.91 | 90.7% |
| Q4 map, gold sensor | 6.23% | 5.62 to 6.88 | 90.6% |
| FP16 reader (end) | 7.25% | 6.60 to 8.00 | 81.7% |
| Q4 unchanged (end) | 18.28% | 17.62 to 18.95 | 51.2% |
| Q4 recentred (end) | 8.91% | 8.24 to 9.66 | 70.7% |
| Q4 map (end) | 7.72% | 7.04 to 8.48 | 78.8% |
| Q4 retrained (end) | 7.88% | 7.20 to 8.62 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.44 | +2.92 to +3.96 | 0.0001 | 34 / 212 / 54 |
| H2a: alnp minus rawp | -3.44 | -3.96 to -2.92 | 0.0001 | 212 / 32 / 56 |
| H2b: q4p minus rawp | -3.23 | -3.75 to -2.71 | 0.0001 | 202 / 43 / 55 |
| H3: alnp minus q4p_n100 | -3.05 | -3.45 to -2.64 | 0.0001 | 250 / 39 / 11 |
| S1: alnp minus q4p | -0.21 | -0.52 to +0.10 | 0.2078 | 56 / 45 / 199 |
| S2: alnp minus q4p_n300 | -1.41 | -1.77 to -1.04 | 0.0001 | 193 / 70 / 37 |
| S3: alnp minus recp | -1.15 | -1.56 to -0.74 | 0.0001 | 116 / 51 / 133 |
| S4: recp minus q4p_n100 | -1.90 | -2.31 to -1.48 | 0.0001 | 206 / 83 / 11 |
| S5: q4p minus f16p | +0.21 | -0.09 to +0.51 | 0.1894 | 39 / 57 / 204 |
| S6: alnp minus f16p | +0.00 | -0.28 to +0.27 | 1.0000 | 46 / 50 / 204 |
| S7: tfidf minus f16p | -1.07 | -1.48 to -0.68 | 0.0001 | 100 / 41 / 159 |
| S8: tfidf minus alnp | -1.07 | -1.49 to -0.67 | 0.0001 | 96 / 38 / 166 |
| S9: rule minus alnp | -1.18 | -1.62 to -0.75 | 0.0001 | 105 / 41 / 154 |
| S10: q4p_goldS minus q4p | -1.16 | -1.55 to -0.77 | 0.0001 | 102 / 26 / 172 |
| S11: alnp_goldS minus alnp | -0.98 | -1.39 to -0.60 | 0.0001 | 88 / 26 / 186 |
| S12: raw minus f16 | +11.03 | +10.34 to +11.72 | 0.0001 | 7 / 285 / 8 |
| S13: aln minus q4 | -0.17 | -0.50 to +0.17 | 0.3785 | 81 / 72 / 147 |
| S14: q4p_n100 minus q4p | +2.84 | +2.45 to +3.22 | 0.0001 | 44 / 245 / 11 |
| S15: f16p minus gold | +1.26 | +0.86 to +1.67 | 0.0001 | 36 / 105 / 159 |

## A_H_s11 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 14.43% | 13.66 to 15.21 | - |
| FP16 reader | 16.02% | 15.18 to 16.91 | 83.6% |
| Q4, FP16 reader unchanged | 19.48% | 18.67 to 20.32 | 67.7% |
| Q4, recentred | 17.76% | 16.91 to 18.61 | 76.6% |
| Q4, label-free map | 16.44% | 15.60 to 17.33 | 81.8% |
| Q4, retrained (1,000 labels) | 16.55% | 15.73 to 17.43 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.93% | 19.20 to 20.64 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 17.99% | 17.21 to 18.79 | - |
| TF-IDF + LR (text) | 14.53% | 13.75 to 15.32 | 98.6% |
| Keyword rules (text) | 14.73% | 13.93 to 15.52 | 97.4% |
| Q4 retrained, gold sensor | 14.81% | 14.07 to 15.58 | 90.7% |
| Q4 map, gold sensor | 14.77% | 14.02 to 15.57 | 90.6% |
| FP16 reader (end) | 16.06% | 15.23 to 16.93 | 81.7% |
| Q4 unchanged (end) | 24.51% | 23.77 to 25.31 | 51.2% |
| Q4 recentred (end) | 17.43% | 16.61 to 18.27 | 70.7% |
| Q4 map (end) | 16.63% | 15.81 to 17.51 | 78.8% |
| Q4 retrained (end) | 16.72% | 15.94 to 17.55 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.46 | +2.83 to +4.07 | 0.0001 | 51 / 203 / 46 |
| H2a: alnp minus rawp | -3.04 | -3.66 to -2.42 | 0.0001 | 190 / 53 / 57 |
| H2b: q4p minus rawp | -2.93 | -3.56 to -2.28 | 0.0001 | 191 / 58 / 51 |
| H3: alnp minus q4p_n100 | -3.49 | -4.00 to -2.99 | 0.0001 | 233 / 52 / 15 |
| S1: alnp minus q4p | -0.11 | -0.45 to +0.22 | 0.5487 | 65 / 55 / 180 |
| S2: alnp minus q4p_n300 | -1.55 | -1.96 to -1.14 | 0.0001 | 196 / 82 / 22 |
| S3: alnp minus recp | -1.32 | -1.85 to -0.81 | 0.0001 | 137 / 60 / 103 |
| S4: recp minus q4p_n100 | -2.16 | -2.68 to -1.67 | 0.0001 | 201 / 80 / 19 |
| S5: q4p minus f16p | +0.53 | +0.14 to +0.93 | 0.0093 | 59 / 84 / 157 |
| S6: alnp minus f16p | +0.42 | +0.09 to +0.75 | 0.0153 | 45 / 72 / 183 |
| S7: tfidf minus f16p | -1.49 | -1.98 to -1.03 | 0.0001 | 120 / 52 / 128 |
| S8: tfidf minus alnp | -1.91 | -2.45 to -1.36 | 0.0001 | 139 / 49 / 112 |
| S9: rule minus alnp | -1.71 | -2.24 to -1.16 | 0.0001 | 139 / 58 / 103 |
| S10: q4p_goldS minus q4p | -1.74 | -2.18 to -1.32 | 0.0001 | 111 / 20 / 169 |
| S11: alnp_goldS minus alnp | -1.66 | -2.09 to -1.24 | 0.0001 | 104 / 17 / 179 |
| S12: raw minus f16 | +8.45 | +7.70 to +9.20 | 0.0001 | 17 / 259 / 24 |
| S13: aln minus q4 | -0.09 | -0.50 to +0.33 | 0.7152 | 88 / 75 / 137 |
| S14: q4p_n100 minus q4p | +3.37 | +2.88 to +3.87 | 0.0001 | 50 / 232 / 18 |
| S15: f16p minus gold | +1.59 | +1.13 to +2.08 | 0.0001 | 50 / 123 / 127 |

## A_H_s12 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 14.67% | 13.88 to 15.51 | - |
| FP16 reader | 16.18% | 15.36 to 17.04 | 83.6% |
| Q4, FP16 reader unchanged | 19.36% | 18.50 to 20.17 | 67.7% |
| Q4, recentred | 17.62% | 16.79 to 18.50 | 76.6% |
| Q4, label-free map | 16.32% | 15.50 to 17.18 | 81.8% |
| Q4, retrained (1,000 labels) | 16.55% | 15.72 to 17.41 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.87% | 19.11 to 20.63 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 17.92% | 17.15 to 18.74 | - |
| TF-IDF + LR (text) | 14.84% | 14.06 to 15.71 | 98.6% |
| Keyword rules (text) | 14.96% | 14.17 to 15.83 | 97.4% |
| Q4 retrained, gold sensor | 15.15% | 14.36 to 15.95 | 90.7% |
| Q4 map, gold sensor | 14.87% | 14.05 to 15.71 | 90.6% |
| FP16 reader (end) | 16.75% | 15.88 to 17.62 | 81.7% |
| Q4 unchanged (end) | 24.66% | 23.81 to 25.46 | 51.2% |
| Q4 recentred (end) | 17.94% | 17.10 to 18.79 | 70.7% |
| Q4 map (end) | 16.87% | 16.04 to 17.73 | 78.8% |
| Q4 retrained (end) | 16.96% | 16.15 to 17.82 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.18 | +2.62 to +3.74 | 0.0001 | 46 / 197 / 57 |
| H2a: alnp minus rawp | -3.04 | -3.62 to -2.47 | 0.0001 | 186 / 53 / 61 |
| H2b: q4p minus rawp | -2.81 | -3.40 to -2.22 | 0.0001 | 186 / 60 / 54 |
| H3: alnp minus q4p_n100 | -3.55 | -4.07 to -3.05 | 0.0001 | 239 / 50 / 11 |
| S1: alnp minus q4p | -0.23 | -0.57 to +0.11 | 0.1987 | 67 / 41 / 192 |
| S2: alnp minus q4p_n300 | -1.60 | -2.04 to -1.17 | 0.0001 | 197 / 81 / 22 |
| S3: alnp minus recp | -1.30 | -1.77 to -0.86 | 0.0001 | 127 / 60 / 113 |
| S4: recp minus q4p_n100 | -2.25 | -2.78 to -1.73 | 0.0001 | 212 / 77 / 11 |
| S5: q4p minus f16p | +0.37 | -0.05 to +0.77 | 0.0964 | 55 / 89 / 156 |
| S6: alnp minus f16p | +0.14 | -0.20 to +0.46 | 0.4382 | 49 / 60 / 191 |
| S7: tfidf minus f16p | -1.34 | -1.80 to -0.90 | 0.0001 | 113 / 45 / 142 |
| S8: tfidf minus alnp | -1.48 | -1.95 to -1.01 | 0.0001 | 116 / 49 / 135 |
| S9: rule minus alnp | -1.37 | -1.85 to -0.88 | 0.0001 | 116 / 57 / 127 |
| S10: q4p_goldS minus q4p | -1.40 | -1.82 to -0.97 | 0.0001 | 107 / 25 / 168 |
| S11: alnp_goldS minus alnp | -1.45 | -1.86 to -1.05 | 0.0001 | 100 / 20 / 180 |
| S12: raw minus f16 | +7.91 | +7.13 to +8.67 | 0.0001 | 25 / 248 / 27 |
| S13: aln minus q4 | -0.09 | -0.54 to +0.37 | 0.7384 | 88 / 79 / 133 |
| S14: q4p_n100 minus q4p | +3.32 | +2.82 to +3.83 | 0.0001 | 60 / 226 / 14 |
| S15: f16p minus gold | +1.52 | +1.06 to +1.99 | 0.0001 | 40 / 119 / 141 |

## B_L_s11 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.22% | 0.69 to 1.85 | - |
| FP16 reader | 2.40% | 1.75 to 3.09 | 72.8% |
| Q4, FP16 reader unchanged | 8.47% | 7.09 to 9.90 | 62.0% |
| Q4, recentred | 4.15% | 3.10 to 5.27 | 66.6% |
| Q4, label-free map | 2.56% | 1.81 to 3.36 | 73.0% |
| Q4, retrained (1,000 labels) | 2.40% | 1.72 to 3.13 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 4.15% | 3.21 to 5.16 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 3.00% | 2.26 to 3.78 | - |
| TF-IDF + LR (text) | 4.95% | 3.95 to 5.99 | 50.3% |
| Keyword rules (text) | 10.22% | 9.03 to 11.54 | 49.9% |
| Q4 retrained, gold sensor | 2.13% | 1.37 to 2.91 | 83.3% |
| Q4 map, gold sensor | 2.34% | 1.54 to 3.18 | 83.4% |
| FP16 reader (end) | 3.62% | 2.90 to 4.35 | 70.7% |
| Q4 unchanged (end) | 16.83% | 15.38 to 18.30 | 43.5% |
| Q4 recentred (end) | 4.05% | 3.08 to 5.08 | 59.7% |
| Q4 map (end) | 3.57% | 2.72 to 4.46 | 68.4% |
| Q4 retrained (end) | 2.77% | 2.08 to 3.49 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +6.07 | +4.89 to +7.28 | 0.0001 | 1 / 44 / 5 |
| H2a: alnp minus rawp | -5.91 | -7.17 to -4.73 | 0.0001 | 44 / 0 / 6 |
| H2b: q4p minus rawp | -6.07 | -7.32 to -4.85 | 0.0001 | 43 / 1 / 6 |
| H3: alnp minus q4p_n100 | -1.60 | -2.27 to -0.95 | 0.0001 | 32 / 7 / 11 |
| S1: alnp minus q4p | +0.16 | -0.27 to +0.59 | 0.6391 | 6 / 8 / 36 |
| S2: alnp minus q4p_n300 | -0.45 | -0.92 to +0.02 | 0.0771 | 22 / 9 / 19 |
| S3: alnp minus recp | -1.60 | -2.44 to -0.86 | 0.0002 | 25 / 5 / 20 |
| S4: recp minus q4p_n100 | +0.00 | -0.74 to +0.75 | 1.0000 | 19 / 19 / 12 |
| S5: q4p minus f16p | +0.00 | -0.43 to +0.48 | 1.0000 | 8 / 6 / 36 |
| S6: alnp minus f16p | +0.16 | -0.33 to +0.69 | 0.6904 | 8 / 8 / 34 |
| S7: tfidf minus f16p | +2.56 | +1.54 to +3.57 | 0.0001 | 7 / 30 / 13 |
| S8: tfidf minus alnp | +2.40 | +1.51 to +3.28 | 0.0001 | 5 / 31 / 14 |
| S9: rule minus alnp | +7.67 | +6.44 to +8.95 | 0.0001 | 0 / 47 / 3 |
| S10: q4p_goldS minus q4p | -0.27 | -0.84 to +0.32 | 0.4964 | 9 / 5 / 36 |
| S11: alnp_goldS minus alnp | -0.21 | -0.85 to +0.44 | 0.6458 | 7 / 5 / 38 |
| S12: raw minus f16 | +13.21 | +11.68 to +14.70 | 0.0001 | 0 / 49 / 1 |
| S13: aln minus q4 | +0.80 | +0.05 to +1.54 | 0.0609 | 6 / 15 / 29 |
| S14: q4p_n100 minus q4p | +1.76 | +1.11 to +2.42 | 0.0001 | 4 / 34 / 12 |
| S15: f16p minus gold | +1.17 | +0.44 to +1.88 | 0.0032 | 4 / 22 / 24 |

## B_L_s12 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 0.59% | 0.22 to 1.01 | - |
| FP16 reader | 2.45% | 1.66 to 3.39 | 72.8% |
| Q4, FP16 reader unchanged | 7.93% | 6.62 to 9.27 | 62.0% |
| Q4, recentred | 4.10% | 3.16 to 5.10 | 66.6% |
| Q4, label-free map | 2.24% | 1.56 to 2.93 | 73.0% |
| Q4, retrained (1,000 labels) | 2.24% | 1.53 to 2.92 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 3.47% | 2.76 to 4.25 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 2.73% | 2.06 to 3.48 | - |
| TF-IDF + LR (text) | 4.90% | 3.87 to 5.98 | 50.3% |
| Keyword rules (text) | 9.96% | 8.75 to 11.31 | 49.9% |
| Q4 retrained, gold sensor | 1.60% | 0.99 to 2.28 | 83.3% |
| Q4 map, gold sensor | 1.65% | 1.01 to 2.32 | 83.4% |
| FP16 reader (end) | 3.51% | 2.64 to 4.51 | 70.7% |
| Q4 unchanged (end) | 16.72% | 15.27 to 18.27 | 43.5% |
| Q4 recentred (end) | 4.47% | 3.53 to 5.45 | 59.7% |
| Q4 map (end) | 2.77% | 1.91 to 3.65 | 68.4% |
| Q4 retrained (end) | 2.66% | 1.70 to 3.78 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +5.48 | +4.19 to +6.74 | 0.0001 | 1 / 42 / 7 |
| H2a: alnp minus rawp | -5.70 | -6.89 to -4.55 | 0.0001 | 43 / 0 / 7 |
| H2b: q4p minus rawp | -5.70 | -6.90 to -4.53 | 0.0001 | 43 / 0 / 7 |
| H3: alnp minus q4p_n100 | -1.24 | -1.77 to -0.69 | 0.0001 | 33 / 9 / 8 |
| S1: alnp minus q4p | +0.00 | -0.33 to +0.32 | 1.0000 | 5 / 5 / 40 |
| S2: alnp minus q4p_n300 | -0.49 | -0.97 to -0.01 | 0.0617 | 23 / 13 / 14 |
| S3: alnp minus recp | -1.86 | -2.65 to -1.08 | 0.0001 | 27 / 6 / 17 |
| S4: recp minus q4p_n100 | +0.63 | -0.02 to +1.31 | 0.0808 | 17 / 22 / 11 |
| S5: q4p minus f16p | -0.21 | -0.91 to +0.44 | 0.6690 | 10 / 9 / 31 |
| S6: alnp minus f16p | -0.21 | -0.90 to +0.43 | 0.6544 | 9 / 8 / 33 |
| S7: tfidf minus f16p | +2.45 | +1.36 to +3.57 | 0.0003 | 5 / 27 / 18 |
| S8: tfidf minus alnp | +2.66 | +1.68 to +3.68 | 0.0001 | 5 / 31 / 14 |
| S9: rule minus alnp | +7.72 | +6.41 to +9.10 | 0.0001 | 1 / 47 / 2 |
| S10: q4p_goldS minus q4p | -0.64 | -1.08 to -0.22 | 0.0087 | 10 / 1 / 39 |
| S11: alnp_goldS minus alnp | -0.59 | -1.03 to -0.21 | 0.0189 | 9 / 1 / 40 |
| S12: raw minus f16 | +13.21 | +11.63 to +14.79 | 0.0001 | 0 / 49 / 1 |
| S13: aln minus q4 | +0.11 | -0.63 to +0.85 | 0.8918 | 8 / 10 / 32 |
| S14: q4p_n100 minus q4p | +1.24 | +0.65 to +1.82 | 0.0002 | 9 / 32 / 9 |
| S15: f16p minus gold | +1.86 | +1.21 to +2.59 | 0.0001 | 0 / 24 / 26 |

## B_L_s13 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.33% | 0.61 to 2.21 | - |
| FP16 reader | 3.30% | 2.14 to 4.61 | 72.8% |
| Q4, FP16 reader unchanged | 8.63% | 7.16 to 10.10 | 62.0% |
| Q4, recentred | 4.47% | 3.28 to 5.77 | 66.6% |
| Q4, label-free map | 3.19% | 2.09 to 4.47 | 73.0% |
| Q4, retrained (1,000 labels) | 2.66% | 1.72 to 3.78 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 4.27% | 3.28 to 5.30 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 3.32% | 2.41 to 4.25 | - |
| TF-IDF + LR (text) | 5.43% | 4.17 to 6.78 | 50.3% |
| Keyword rules (text) | 10.76% | 9.33 to 12.43 | 49.9% |
| Q4 retrained, gold sensor | 2.29% | 1.38 to 3.30 | 83.3% |
| Q4 map, gold sensor | 2.40% | 1.45 to 3.45 | 83.4% |
| FP16 reader (end) | 3.73% | 2.65 to 4.91 | 70.7% |
| Q4 unchanged (end) | 17.09% | 15.60 to 18.53 | 43.5% |
| Q4 recentred (end) | 4.74% | 3.64 to 5.87 | 59.7% |
| Q4 map (end) | 3.35% | 2.39 to 4.43 | 68.4% |
| Q4 retrained (end) | 3.19% | 2.22 to 4.30 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +5.32 | +4.17 to +6.53 | 0.0001 | 3 / 41 / 6 |
| H2a: alnp minus rawp | -5.43 | -6.72 to -4.14 | 0.0001 | 40 / 4 / 6 |
| H2b: q4p minus rawp | -5.96 | -7.05 to -4.87 | 0.0001 | 43 / 0 / 7 |
| H3: alnp minus q4p_n100 | -1.08 | -1.94 to -0.24 | 0.0190 | 30 / 13 / 7 |
| S1: alnp minus q4p | +0.53 | -0.11 to +1.24 | 0.1978 | 4 / 10 / 36 |
| S2: alnp minus q4p_n300 | -0.13 | -1.00 to +0.74 | 0.8025 | 23 / 15 / 12 |
| S3: alnp minus recp | -1.28 | -2.26 to -0.32 | 0.0198 | 23 / 8 / 19 |
| S4: recp minus q4p_n100 | +0.20 | -0.63 to +1.00 | 0.6674 | 21 / 18 / 11 |
| S5: q4p minus f16p | -0.64 | -1.42 to +0.11 | 0.1510 | 12 / 6 / 32 |
| S6: alnp minus f16p | -0.11 | -1.03 to +0.78 | 0.9121 | 10 / 10 / 30 |
| S7: tfidf minus f16p | +2.13 | +1.09 to +3.19 | 0.0006 | 8 / 27 / 15 |
| S8: tfidf minus alnp | +2.24 | +1.09 to +3.35 | 0.0003 | 8 / 28 / 14 |
| S9: rule minus alnp | +7.56 | +6.28 to +8.92 | 0.0001 | 1 / 48 / 1 |
| S10: q4p_goldS minus q4p | -0.37 | -0.86 to +0.05 | 0.1842 | 8 / 4 / 38 |
| S11: alnp_goldS minus alnp | -0.80 | -1.72 to -0.05 | 0.0919 | 9 / 5 / 36 |
| S12: raw minus f16 | +13.37 | +11.85 to +14.87 | 0.0001 | 0 / 48 / 2 |
| S13: aln minus q4 | +0.16 | -0.54 to +0.81 | 0.7774 | 9 / 13 / 28 |
| S14: q4p_n100 minus q4p | +1.61 | +0.98 to +2.24 | 0.0001 | 7 / 36 / 7 |
| S15: f16p minus gold | +1.97 | +1.09 to +2.99 | 0.0001 | 1 / 23 / 26 |

## B_M_s11 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 4.53% | 3.33 to 5.84 | - |
| FP16 reader | 7.03% | 5.41 to 8.77 | 72.8% |
| Q4, FP16 reader unchanged | 11.87% | 10.31 to 13.39 | 62.0% |
| Q4, recentred | 8.73% | 7.18 to 10.32 | 66.6% |
| Q4, label-free map | 6.76% | 5.39 to 8.10 | 73.0% |
| Q4, retrained (1,000 labels) | 7.19% | 5.56 to 8.91 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 9.09% | 7.64 to 10.52 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 7.45% | 6.17 to 8.73 | - |
| TF-IDF + LR (text) | 9.48% | 7.77 to 11.25 | 50.3% |
| Keyword rules (text) | 13.63% | 12.10 to 15.28 | 49.9% |
| Q4 retrained, gold sensor | 5.64% | 4.21 to 7.16 | 83.3% |
| Q4 map, gold sensor | 5.54% | 4.24 to 6.85 | 83.4% |
| FP16 reader (end) | 8.79% | 7.01 to 10.79 | 70.7% |
| Q4 unchanged (end) | 19.17% | 17.46 to 21.09 | 43.5% |
| Q4 recentred (end) | 9.05% | 7.54 to 10.68 | 59.7% |
| Q4 map (end) | 7.83% | 6.39 to 9.34 | 68.4% |
| Q4 retrained (end) | 8.04% | 6.35 to 9.80 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +4.85 | +3.40 to +6.19 | 0.0001 | 2 / 44 / 4 |
| H2a: alnp minus rawp | -5.11 | -6.38 to -3.86 | 0.0001 | 42 / 2 / 6 |
| H2b: q4p minus rawp | -4.69 | -6.03 to -3.31 | 0.0001 | 41 / 3 / 6 |
| H3: alnp minus q4p_n100 | -2.33 | -3.30 to -1.37 | 0.0001 | 39 / 8 / 3 |
| S1: alnp minus q4p | -0.43 | -1.35 to +0.42 | 0.4239 | 10 / 10 / 30 |
| S2: alnp minus q4p_n300 | -0.69 | -1.52 to +0.14 | 0.1230 | 28 / 15 / 7 |
| S3: alnp minus recp | -1.97 | -2.89 to -1.04 | 0.0006 | 30 / 7 / 13 |
| S4: recp minus q4p_n100 | -0.36 | -1.31 to +0.65 | 0.4901 | 29 / 17 / 4 |
| S5: q4p minus f16p | +0.16 | -1.44 to +1.65 | 0.8954 | 9 / 13 / 28 |
| S6: alnp minus f16p | -0.27 | -1.46 to +0.83 | 0.7214 | 12 / 14 / 24 |
| S7: tfidf minus f16p | +2.45 | +0.69 to +4.19 | 0.0099 | 12 / 31 / 7 |
| S8: tfidf minus alnp | +2.72 | +1.27 to +4.26 | 0.0012 | 11 / 29 / 10 |
| S9: rule minus alnp | +6.87 | +5.47 to +8.36 | 0.0001 | 1 / 44 / 5 |
| S10: q4p_goldS minus q4p | -1.54 | -2.38 to -0.79 | 0.0004 | 20 / 4 / 26 |
| S11: alnp_goldS minus alnp | -1.22 | -1.97 to -0.49 | 0.0031 | 17 / 4 / 29 |
| S12: raw minus f16 | +10.38 | +7.97 to +12.55 | 0.0001 | 4 / 45 / 1 |
| S13: aln minus q4 | -0.21 | -1.18 to +0.76 | 0.7539 | 16 / 14 / 20 |
| S14: q4p_n100 minus q4p | +1.91 | +0.53 to +3.20 | 0.0079 | 11 / 37 / 2 |
| S15: f16p minus gold | +2.50 | +0.96 to +4.13 | 0.0027 | 7 / 26 / 17 |

## B_M_s12 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 4.42% | 3.27 to 5.69 | - |
| FP16 reader | 7.29% | 5.82 to 8.88 | 72.8% |
| Q4, FP16 reader unchanged | 12.41% | 10.69 to 14.20 | 62.0% |
| Q4, recentred | 8.79% | 7.30 to 10.31 | 66.6% |
| Q4, label-free map | 7.08% | 5.59 to 8.59 | 73.0% |
| Q4, retrained (1,000 labels) | 7.24% | 5.84 to 8.70 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 9.18% | 7.90 to 10.58 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 7.83% | 6.50 to 9.20 | - |
| TF-IDF + LR (text) | 8.20% | 6.74 to 9.99 | 50.3% |
| Keyword rules (text) | 14.00% | 12.37 to 15.92 | 49.9% |
| Q4 retrained, gold sensor | 5.54% | 4.12 to 7.05 | 83.3% |
| Q4 map, gold sensor | 5.32% | 3.98 to 6.72 | 83.4% |
| FP16 reader (end) | 7.67% | 6.17 to 9.31 | 70.7% |
| Q4 unchanged (end) | 19.01% | 17.41 to 20.74 | 43.5% |
| Q4 recentred (end) | 7.83% | 6.49 to 9.17 | 59.7% |
| Q4 map (end) | 7.51% | 5.88 to 9.23 | 68.4% |
| Q4 retrained (end) | 7.08% | 5.57 to 8.66 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +5.11 | +3.67 to +6.57 | 0.0001 | 5 / 41 / 4 |
| H2a: alnp minus rawp | -5.32 | -6.74 to -3.96 | 0.0001 | 41 / 3 / 6 |
| H2b: q4p minus rawp | -5.17 | -6.40 to -3.94 | 0.0001 | 41 / 3 / 6 |
| H3: alnp minus q4p_n100 | -2.10 | -2.96 to -1.25 | 0.0001 | 35 / 13 / 2 |
| S1: alnp minus q4p | -0.16 | -1.08 to +0.74 | 0.8278 | 9 / 8 / 33 |
| S2: alnp minus q4p_n300 | -0.75 | -1.55 to +0.08 | 0.0945 | 28 / 16 / 6 |
| S3: alnp minus recp | -1.70 | -2.62 to -0.80 | 0.0009 | 26 / 7 / 17 |
| S4: recp minus q4p_n100 | -0.39 | -1.33 to +0.56 | 0.4439 | 23 / 21 / 6 |
| S5: q4p minus f16p | -0.05 | -1.14 to +1.04 | 1.0000 | 14 / 14 / 22 |
| S6: alnp minus f16p | -0.21 | -0.98 to +0.53 | 0.6877 | 13 / 10 / 27 |
| S7: tfidf minus f16p | +0.91 | -0.54 to +2.41 | 0.2681 | 19 / 21 / 10 |
| S8: tfidf minus alnp | +1.12 | -0.37 to +2.65 | 0.1781 | 18 / 21 / 11 |
| S9: rule minus alnp | +6.92 | +5.44 to +8.42 | 0.0001 | 3 / 43 / 4 |
| S10: q4p_goldS minus q4p | -1.70 | -2.82 to -0.57 | 0.0067 | 21 / 3 / 26 |
| S11: alnp_goldS minus alnp | -1.76 | -2.78 to -0.84 | 0.0009 | 20 / 4 / 26 |
| S12: raw minus f16 | +11.34 | +9.20 to +13.36 | 0.0001 | 1 / 48 / 1 |
| S13: aln minus q4 | +0.43 | -0.41 to +1.32 | 0.4032 | 11 / 14 / 25 |
| S14: q4p_n100 minus q4p | +1.94 | +1.04 to +2.82 | 0.0002 | 13 / 35 / 2 |
| S15: f16p minus gold | +2.88 | +1.61 to +4.19 | 0.0001 | 7 / 27 / 16 |

## B_M_s13 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 5.27% | 3.88 to 6.77 | - |
| FP16 reader | 7.72% | 6.01 to 9.51 | 72.8% |
| Q4, FP16 reader unchanged | 12.46% | 10.68 to 14.26 | 62.0% |
| Q4, recentred | 10.01% | 8.10 to 11.97 | 66.6% |
| Q4, label-free map | 7.29% | 5.83 to 8.79 | 73.0% |
| Q4, retrained (1,000 labels) | 7.29% | 5.70 to 9.03 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 9.53% | 7.97 to 11.18 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.57% | 7.00 to 10.27 | - |
| TF-IDF + LR (text) | 9.53% | 7.82 to 11.39 | 50.3% |
| Keyword rules (text) | 13.63% | 12.13 to 15.46 | 49.9% |
| Q4 retrained, gold sensor | 6.02% | 4.62 to 7.55 | 83.3% |
| Q4 map, gold sensor | 6.28% | 4.84 to 7.89 | 83.4% |
| FP16 reader (end) | 9.74% | 7.83 to 11.86 | 70.7% |
| Q4 unchanged (end) | 19.91% | 18.37 to 21.46 | 43.5% |
| Q4 recentred (end) | 9.85% | 7.92 to 11.99 | 59.7% |
| Q4 map (end) | 8.52% | 6.81 to 10.38 | 68.4% |
| Q4 retrained (end) | 8.52% | 6.87 to 10.41 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +4.74 | +3.17 to +6.21 | 0.0001 | 5 / 39 / 6 |
| H2a: alnp minus rawp | -5.17 | -6.64 to -3.66 | 0.0001 | 40 / 4 / 6 |
| H2b: q4p minus rawp | -5.17 | -6.63 to -3.63 | 0.0001 | 40 / 6 / 4 |
| H3: alnp minus q4p_n100 | -2.24 | -3.25 to -1.21 | 0.0001 | 38 / 9 / 3 |
| S1: alnp minus q4p | +0.00 | -0.81 to +0.74 | 1.0000 | 6 / 9 / 35 |
| S2: alnp minus q4p_n300 | -1.28 | -2.33 to -0.29 | 0.0167 | 29 / 13 / 8 |
| S3: alnp minus recp | -2.72 | -3.90 to -1.58 | 0.0001 | 27 / 6 / 17 |
| S4: recp minus q4p_n100 | +0.48 | -0.51 to +1.53 | 0.3889 | 20 / 28 / 2 |
| S5: q4p minus f16p | -0.43 | -1.44 to +0.48 | 0.4538 | 11 / 11 / 28 |
| S6: alnp minus f16p | -0.43 | -1.29 to +0.37 | 0.4081 | 13 / 12 / 25 |
| S7: tfidf minus f16p | +1.81 | +0.69 to +2.89 | 0.0037 | 13 / 30 / 7 |
| S8: tfidf minus alnp | +2.24 | +0.90 to +3.55 | 0.0024 | 12 / 29 / 9 |
| S9: rule minus alnp | +6.34 | +4.81 to +7.98 | 0.0001 | 4 / 38 / 8 |
| S10: q4p_goldS minus q4p | -1.28 | -2.12 to -0.48 | 0.0032 | 17 / 3 / 30 |
| S11: alnp_goldS minus alnp | -1.01 | -1.81 to -0.26 | 0.0183 | 17 / 6 / 27 |
| S12: raw minus f16 | +10.17 | +8.35 to +11.99 | 0.0001 | 2 / 45 / 3 |
| S13: aln minus q4 | +0.00 | -0.85 to +0.90 | 1.0000 | 15 / 13 / 22 |
| S14: q4p_n100 minus q4p | +2.24 | +1.23 to +3.22 | 0.0001 | 11 / 38 / 1 |
| S15: f16p minus gold | +2.45 | +1.54 to +3.38 | 0.0001 | 4 / 29 / 17 |

## B_H_s11 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 13.37% | 11.50 to 15.19 | - |
| FP16 reader | 15.65% | 13.59 to 17.64 | 72.8% |
| Q4, FP16 reader unchanged | 19.44% | 17.44 to 21.47 | 62.0% |
| Q4, recentred | 17.89% | 15.92 to 19.91 | 66.6% |
| Q4, label-free map | 16.51% | 14.62 to 18.40 | 73.0% |
| Q4, retrained (1,000 labels) | 16.13% | 14.16 to 18.08 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.12% | 17.29 to 20.93 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 17.37% | 15.50 to 19.16 | - |
| TF-IDF + LR (text) | 18.96% | 16.68 to 21.07 | 50.3% |
| Keyword rules (text) | 21.19% | 19.49 to 22.99 | 49.9% |
| Q4 retrained, gold sensor | 13.74% | 11.95 to 15.46 | 83.3% |
| Q4 map, gold sensor | 14.00% | 12.18 to 15.78 | 83.4% |
| FP16 reader (end) | 18.00% | 15.78 to 20.31 | 70.7% |
| Q4 unchanged (end) | 24.39% | 22.52 to 26.45 | 43.5% |
| Q4 recentred (end) | 17.84% | 15.58 to 20.04 | 59.7% |
| Q4 map (end) | 17.52% | 15.29 to 19.78 | 68.4% |
| Q4 retrained (end) | 16.51% | 14.46 to 18.69 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.78 | +2.23 to +5.41 | 0.0001 | 7 / 34 / 9 |
| H2a: alnp minus rawp | -2.93 | -4.50 to -1.41 | 0.0004 | 30 / 8 / 12 |
| H2b: q4p minus rawp | -3.30 | -4.99 to -1.65 | 0.0001 | 32 / 7 / 11 |
| H3: alnp minus q4p_n100 | -2.61 | -3.64 to -1.60 | 0.0001 | 38 / 11 / 1 |
| S1: alnp minus q4p | +0.37 | -0.42 to +1.12 | 0.4328 | 6 / 12 / 32 |
| S2: alnp minus q4p_n300 | -0.86 | -1.84 to +0.10 | 0.0911 | 30 / 18 / 2 |
| S3: alnp minus recp | -1.38 | -2.55 to -0.21 | 0.0321 | 25 / 10 / 15 |
| S4: recp minus q4p_n100 | -1.22 | -2.25 to -0.17 | 0.0307 | 28 / 19 / 3 |
| S5: q4p minus f16p | +0.48 | -0.64 to +1.61 | 0.4720 | 15 / 17 / 18 |
| S6: alnp minus f16p | +0.85 | -0.16 to +1.89 | 0.1367 | 11 / 17 / 22 |
| S7: tfidf minus f16p | +3.30 | +1.53 to +5.15 | 0.0008 | 13 / 31 / 6 |
| S8: tfidf minus alnp | +2.45 | +0.74 to +4.17 | 0.0099 | 12 / 27 / 11 |
| S9: rule minus alnp | +4.69 | +3.41 to +5.97 | 0.0001 | 5 / 37 / 8 |
| S10: q4p_goldS minus q4p | -2.40 | -3.48 to -1.32 | 0.0001 | 26 / 2 / 22 |
| S11: alnp_goldS minus alnp | -2.50 | -3.43 to -1.60 | 0.0001 | 28 / 2 / 20 |
| S12: raw minus f16 | +6.39 | +3.99 to +8.65 | 0.0001 | 7 / 40 / 3 |
| S13: aln minus q4 | +1.01 | -0.16 to +2.24 | 0.1355 | 12 / 19 / 19 |
| S14: q4p_n100 minus q4p | +2.98 | +1.79 to +4.23 | 0.0001 | 10 / 39 / 1 |
| S15: f16p minus gold | +2.29 | +1.26 to +3.34 | 0.0002 | 7 / 24 / 19 |

## B_H_s12 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 13.10% | 11.02 to 15.24 | - |
| FP16 reader | 16.45% | 14.42 to 18.58 | 72.8% |
| Q4, FP16 reader unchanged | 19.81% | 17.81 to 21.68 | 62.0% |
| Q4, recentred | 17.57% | 15.48 to 19.74 | 66.6% |
| Q4, label-free map | 15.44% | 13.38 to 17.50 | 73.0% |
| Q4, retrained (1,000 labels) | 15.92% | 13.77 to 18.26 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 18.84% | 16.99 to 20.73 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 17.37% | 15.44 to 19.35 | - |
| TF-IDF + LR (text) | 18.26% | 15.98 to 20.64 | 50.3% |
| Keyword rules (text) | 21.19% | 19.26 to 23.32 | 49.9% |
| Q4 retrained, gold sensor | 13.95% | 11.91 to 15.97 | 83.3% |
| Q4 map, gold sensor | 13.90% | 11.82 to 16.00 | 83.4% |
| FP16 reader (end) | 17.25% | 15.14 to 19.39 | 70.7% |
| Q4 unchanged (end) | 24.55% | 22.78 to 26.53 | 43.5% |
| Q4 recentred (end) | 17.78% | 15.72 to 19.98 | 59.7% |
| Q4 map (end) | 17.36% | 15.11 to 19.51 | 68.4% |
| Q4 retrained (end) | 16.67% | 14.50 to 18.82 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.35 | +1.67 to +4.98 | 0.0005 | 10 / 31 / 9 |
| H2a: alnp minus rawp | -4.37 | -5.99 to -2.65 | 0.0001 | 35 / 8 / 7 |
| H2b: q4p minus rawp | -3.89 | -5.51 to -2.18 | 0.0001 | 35 / 8 / 7 |
| H3: alnp minus q4p_n100 | -3.40 | -4.48 to -2.28 | 0.0001 | 39 / 10 / 1 |
| S1: alnp minus q4p | -0.48 | -1.40 to +0.37 | 0.3725 | 9 / 5 / 36 |
| S2: alnp minus q4p_n300 | -1.93 | -2.79 to -1.06 | 0.0001 | 36 / 10 / 4 |
| S3: alnp minus recp | -2.13 | -3.22 to -1.07 | 0.0006 | 27 / 9 / 14 |
| S4: recp minus q4p_n100 | -1.27 | -2.50 to -0.05 | 0.0517 | 29 / 17 / 4 |
| S5: q4p minus f16p | -0.53 | -1.42 to +0.38 | 0.3107 | 15 / 9 / 26 |
| S6: alnp minus f16p | -1.01 | -2.11 to +0.05 | 0.0938 | 17 / 8 / 25 |
| S7: tfidf minus f16p | +1.81 | +0.11 to +3.47 | 0.0492 | 18 / 27 / 5 |
| S8: tfidf minus alnp | +2.82 | +1.08 to +4.58 | 0.0036 | 15 / 28 / 7 |
| S9: rule minus alnp | +5.75 | +4.20 to +7.32 | 0.0001 | 4 / 43 / 3 |
| S10: q4p_goldS minus q4p | -1.97 | -2.91 to -1.08 | 0.0001 | 23 / 3 / 24 |
| S11: alnp_goldS minus alnp | -1.54 | -2.42 to -0.70 | 0.0016 | 19 / 5 / 26 |
| S12: raw minus f16 | +7.29 | +5.03 to +9.51 | 0.0001 | 7 / 38 / 5 |
| S13: aln minus q4 | +0.69 | -0.64 to +2.06 | 0.3662 | 15 / 21 / 14 |
| S14: q4p_n100 minus q4p | +2.92 | +1.81 to +3.98 | 0.0001 | 11 / 38 / 1 |
| S15: f16p minus gold | +3.35 | +2.33 to +4.37 | 0.0001 | 6 / 35 / 9 |

## B_H_s13 (50 episodes, 1878 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 13.84% | 11.69 to 16.02 | - |
| FP16 reader | 17.15% | 15.21 to 19.01 | 72.8% |
| Q4, FP16 reader unchanged | 20.45% | 18.36 to 22.50 | 62.0% |
| Q4, recentred | 19.01% | 16.76 to 21.25 | 66.6% |
| Q4, label-free map | 16.88% | 14.58 to 19.07 | 73.0% |
| Q4, retrained (1,000 labels) | 17.84% | 15.58 to 20.09 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.57% | 17.47 to 21.72 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 18.53% | 16.51 to 20.43 | - |
| TF-IDF + LR (text) | 18.74% | 16.46 to 21.07 | 50.3% |
| Keyword rules (text) | 21.46% | 19.45 to 23.64 | 49.9% |
| Q4 retrained, gold sensor | 14.96% | 12.99 to 16.94 | 83.3% |
| Q4 map, gold sensor | 15.23% | 13.08 to 17.34 | 83.4% |
| FP16 reader (end) | 17.89% | 15.76 to 20.16 | 70.7% |
| Q4 unchanged (end) | 25.72% | 23.86 to 27.71 | 43.5% |
| Q4 recentred (end) | 18.32% | 16.19 to 20.51 | 59.7% |
| Q4 map (end) | 17.36% | 15.02 to 19.74 | 68.4% |
| Q4 retrained (end) | 17.36% | 14.92 to 19.73 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.30 | +1.98 to +4.63 | 0.0001 | 6 / 35 / 9 |
| H2a: alnp minus rawp | -3.57 | -5.07 to -2.06 | 0.0003 | 32 / 8 / 10 |
| H2b: q4p minus rawp | -2.61 | -4.14 to -1.05 | 0.0025 | 31 / 11 / 8 |
| H3: alnp minus q4p_n100 | -2.69 | -3.97 to -1.34 | 0.0005 | 37 / 11 / 2 |
| S1: alnp minus q4p | -0.96 | -2.07 to +0.00 | 0.1070 | 10 / 8 / 32 |
| S2: alnp minus q4p_n300 | -1.65 | -2.67 to -0.63 | 0.0032 | 33 / 12 / 5 |
| S3: alnp minus recp | -2.13 | -3.45 to -0.87 | 0.0031 | 29 / 11 / 10 |
| S4: recp minus q4p_n100 | -0.56 | -2.00 to +0.89 | 0.4614 | 24 / 25 / 1 |
| S5: q4p minus f16p | +0.69 | -0.48 to +1.96 | 0.3270 | 15 / 16 / 19 |
| S6: alnp minus f16p | -0.27 | -1.18 to +0.67 | 0.6627 | 15 / 12 / 23 |
| S7: tfidf minus f16p | +1.60 | -0.21 to +3.48 | 0.1127 | 14 / 26 / 10 |
| S8: tfidf minus alnp | +1.86 | +0.00 to +3.84 | 0.0670 | 14 / 26 / 10 |
| S9: rule minus alnp | +4.58 | +2.98 to +6.17 | 0.0001 | 6 / 38 / 6 |
| S10: q4p_goldS minus q4p | -2.88 | -4.30 to -1.58 | 0.0001 | 25 / 4 / 21 |
| S11: alnp_goldS minus alnp | -1.65 | -2.64 to -0.80 | 0.0006 | 21 / 4 / 25 |
| S12: raw minus f16 | +7.83 | +5.84 to +9.76 | 0.0001 | 4 / 43 / 3 |
| S13: aln minus q4 | +0.00 | -1.42 to +1.55 | 1.0000 | 15 / 17 / 18 |
| S14: q4p_n100 minus q4p | +1.74 | +0.45 to +3.00 | 0.0147 | 17 / 32 / 1 |
| S15: f16p minus gold | +3.30 | +1.94 to +4.67 | 0.0001 | 5 / 31 / 14 |

## A_H_s13 (300 episodes, 11480 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 15.24% | 14.41 to 16.17 | - |
| FP16 reader | 16.70% | 15.78 to 17.71 | 83.6% |
| Q4, FP16 reader unchanged | 19.83% | 18.94 to 20.79 | 67.7% |
| Q4, recentred | 17.91% | 16.99 to 18.84 | 76.6% |
| Q4, label-free map | 16.90% | 16.02 to 17.86 | 81.8% |
| Q4, retrained (1,000 labels) | 16.79% | 15.94 to 17.69 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 20.32% | 19.51 to 21.14 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 18.35% | 17.53 to 19.21 | - |
| TF-IDF + LR (text) | 15.30% | 14.48 to 16.23 | 98.6% |
| Keyword rules (text) | 15.44% | 14.59 to 16.33 | 97.4% |
| Q4 retrained, gold sensor | 15.56% | 14.72 to 16.44 | 90.7% |
| Q4 map, gold sensor | 15.38% | 14.55 to 16.28 | 90.6% |
| FP16 reader (end) | 16.99% | 16.10 to 17.96 | 81.7% |
| Q4 unchanged (end) | 24.76% | 23.96 to 25.57 | 51.2% |
| Q4 recentred (end) | 18.05% | 17.17 to 19.00 | 70.7% |
| Q4 map (end) | 17.24% | 16.32 to 18.19 | 78.8% |
| Q4 retrained (end) | 17.39% | 16.48 to 18.33 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.14 | +2.57 to +3.69 | 0.0001 | 49 / 194 / 57 |
| H2a: alnp minus rawp | -2.94 | -3.51 to -2.35 | 0.0001 | 188 / 54 / 58 |
| H2b: q4p minus rawp | -3.05 | -3.64 to -2.45 | 0.0001 | 195 / 53 / 52 |
| H3: alnp minus q4p_n100 | -3.42 | -3.93 to -2.93 | 0.0001 | 229 / 55 / 16 |
| S1: alnp minus q4p | +0.11 | -0.24 to +0.48 | 0.5667 | 61 / 62 / 177 |
| S2: alnp minus q4p_n300 | -1.45 | -1.88 to -1.02 | 0.0001 | 199 / 84 / 17 |
| S3: alnp minus recp | -1.01 | -1.51 to -0.51 | 0.0004 | 120 / 65 / 115 |
| S4: recp minus q4p_n100 | -2.41 | -2.94 to -1.88 | 0.0001 | 201 / 81 / 18 |
| S5: q4p minus f16p | +0.09 | -0.33 to +0.51 | 0.7133 | 64 / 76 / 160 |
| S6: alnp minus f16p | +0.20 | -0.17 to +0.57 | 0.3141 | 53 / 68 / 179 |
| S7: tfidf minus f16p | -1.39 | -1.87 to -0.93 | 0.0001 | 122 / 50 / 128 |
| S8: tfidf minus alnp | -1.59 | -2.09 to -1.10 | 0.0001 | 127 / 52 / 121 |
| S9: rule minus alnp | -1.45 | -1.95 to -0.96 | 0.0001 | 124 / 56 / 120 |
| S10: q4p_goldS minus q4p | -1.23 | -1.63 to -0.83 | 0.0001 | 100 / 33 / 167 |
| S11: alnp_goldS minus alnp | -1.52 | -1.93 to -1.12 | 0.0001 | 103 / 25 / 172 |
| S12: raw minus f16 | +7.77 | +7.06 to +8.50 | 0.0001 | 20 / 256 / 24 |
| S13: aln minus q4 | -0.15 | -0.64 to +0.36 | 0.5846 | 96 / 72 / 132 |
| S14: q4p_n100 minus q4p | +3.54 | +3.07 to +4.02 | 0.0001 | 48 / 231 / 21 |
| S15: f16p minus gold | +1.45 | +0.98 to +1.93 | 0.0001 | 51 / 127 / 122 |

## A_L_pooled (900 episodes, 34440 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.69% | 1.51 to 1.88 | - |
| FP16 reader | 2.39% | 2.16 to 2.63 | 83.6% |
| Q4, FP16 reader unchanged | 6.05% | 5.80 to 6.32 | 67.7% |
| Q4, recentred | 3.27% | 3.03 to 3.50 | 76.6% |
| Q4, label-free map | 2.39% | 2.17 to 2.61 | 81.8% |
| Q4, retrained (1,000 labels) | 2.50% | 2.26 to 2.74 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 4.35% | 4.11 to 4.59 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 3.15% | 2.93 to 3.37 | - |
| TF-IDF + LR (text) | 1.73% | 1.54 to 1.92 | 98.6% |
| Keyword rules (text) | 1.76% | 1.57 to 1.95 | 97.4% |
| Q4 retrained, gold sensor | 1.82% | 1.63 to 2.01 | 90.7% |
| Q4 map, gold sensor | 1.87% | 1.69 to 2.07 | 90.6% |
| FP16 reader (end) | 2.38% | 2.17 to 2.61 | 81.7% |
| Q4 unchanged (end) | 15.57% | 15.22 to 15.90 | 51.2% |
| Q4 recentred (end) | 3.72% | 3.46 to 3.98 | 70.7% |
| Q4 map (end) | 2.74% | 2.50 to 2.97 | 78.8% |
| Q4 retrained (end) | 2.79% | 2.55 to 3.03 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.66 | +3.44 to +3.88 | 0.0001 | 41 / 694 / 165 |
| H2a: alnp minus rawp | -3.66 | -3.88 to -3.44 | 0.0001 | 696 / 43 / 161 |
| H2b: q4p minus rawp | -3.55 | -3.77 to -3.32 | 0.0001 | 684 / 50 / 166 |
| H3: alnp minus q4p_n100 | -1.96 | -2.11 to -1.81 | 0.0001 | 721 / 106 / 73 |
| S1: alnp minus q4p | -0.11 | -0.23 to +0.01 | 0.0649 | 85 / 68 / 747 |
| S2: alnp minus q4p_n300 | -0.76 | -0.88 to -0.64 | 0.0001 | 507 / 143 / 250 |
| S3: alnp minus recp | -0.88 | -1.03 to -0.74 | 0.0001 | 286 / 57 / 557 |
| S4: recp minus q4p_n100 | -1.08 | -1.24 to -0.92 | 0.0001 | 595 / 195 / 110 |
| S5: q4p minus f16p | +0.11 | +0.00 to +0.22 | 0.0604 | 73 / 101 / 726 |
| S6: alnp minus f16p | +0.00 | -0.09 to +0.10 | 1.0000 | 63 / 67 / 770 |
| S7: tfidf minus f16p | -0.66 | -0.79 to -0.54 | 0.0001 | 194 / 33 / 673 |
| S8: tfidf minus alnp | -0.66 | -0.79 to -0.54 | 0.0001 | 217 / 42 / 641 |
| S9: rule minus alnp | -0.63 | -0.77 to -0.49 | 0.0001 | 216 / 58 / 626 |
| S10: q4p_goldS minus q4p | -0.68 | -0.81 to -0.55 | 0.0001 | 183 / 30 / 687 |
| S11: alnp_goldS minus alnp | -0.52 | -0.63 to -0.40 | 0.0001 | 162 / 30 / 708 |
| S12: raw minus f16 | +13.18 | +12.84 to +13.53 | 0.0001 | 2 / 891 / 7 |
| S13: aln minus q4 | -0.05 | -0.20 to +0.09 | 0.5014 | 144 / 135 / 621 |
| S14: q4p_n100 minus q4p | +1.85 | +1.69 to +2.01 | 0.0001 | 119 / 703 / 78 |
| S15: f16p minus gold | +0.70 | +0.57 to +0.82 | 0.0001 | 29 / 198 / 673 |

## A_M_pooled (900 episodes, 34440 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 5.84% | 5.51 to 6.21 | - |
| FP16 reader | 6.98% | 6.58 to 7.38 | 83.6% |
| Q4, FP16 reader unchanged | 10.50% | 10.13 to 10.89 | 67.7% |
| Q4, recentred | 8.12% | 7.71 to 8.53 | 76.6% |
| Q4, label-free map | 7.05% | 6.65 to 7.45 | 81.8% |
| Q4, retrained (1,000 labels) | 7.22% | 6.82 to 7.61 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 9.95% | 9.55 to 10.33 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.28% | 7.90 to 8.65 | - |
| TF-IDF + LR (text) | 5.95% | 5.61 to 6.32 | 98.6% |
| Keyword rules (text) | 5.93% | 5.60 to 6.29 | 97.4% |
| Q4 retrained, gold sensor | 6.05% | 5.68 to 6.42 | 90.7% |
| Q4 map, gold sensor | 6.03% | 5.68 to 6.40 | 90.6% |
| FP16 reader (end) | 7.16% | 6.77 to 7.56 | 81.7% |
| Q4 unchanged (end) | 18.07% | 17.67 to 18.46 | 51.2% |
| Q4 recentred (end) | 8.52% | 8.13 to 8.95 | 70.7% |
| Q4 map (end) | 7.49% | 7.08 to 7.91 | 78.8% |
| Q4 retrained (end) | 7.76% | 7.35 to 8.18 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.52 | +3.22 to +3.82 | 0.0001 | 98 / 655 / 147 |
| H2a: alnp minus rawp | -3.46 | -3.75 to -3.15 | 0.0001 | 639 / 106 / 155 |
| H2b: q4p minus rawp | -3.28 | -3.59 to -2.97 | 0.0001 | 624 / 120 / 156 |
| H3: alnp minus q4p_n100 | -2.90 | -3.14 to -2.67 | 0.0001 | 725 / 135 / 40 |
| S1: alnp minus q4p | -0.17 | -0.37 to +0.02 | 0.0838 | 152 / 135 / 613 |
| S2: alnp minus q4p_n300 | -1.23 | -1.43 to -1.03 | 0.0001 | 562 / 213 / 125 |
| S3: alnp minus recp | -1.08 | -1.31 to -0.85 | 0.0001 | 353 / 149 / 398 |
| S4: recp minus q4p_n100 | -1.83 | -2.06 to -1.59 | 0.0001 | 616 / 232 / 52 |
| S5: q4p minus f16p | +0.24 | +0.05 to +0.43 | 0.0123 | 131 / 169 / 600 |
| S6: alnp minus f16p | +0.07 | -0.10 to +0.24 | 0.4684 | 124 / 147 / 629 |
| S7: tfidf minus f16p | -1.03 | -1.25 to -0.81 | 0.0001 | 305 / 113 / 482 |
| S8: tfidf minus alnp | -1.09 | -1.33 to -0.86 | 0.0001 | 310 / 116 / 474 |
| S9: rule minus alnp | -1.12 | -1.36 to -0.88 | 0.0001 | 323 / 129 / 448 |
| S10: q4p_goldS minus q4p | -1.17 | -1.39 to -0.95 | 0.0001 | 285 / 80 / 535 |
| S11: alnp_goldS minus alnp | -1.02 | -1.23 to -0.81 | 0.0001 | 270 / 75 / 555 |
| S12: raw minus f16 | +10.91 | +10.52 to +11.30 | 0.0001 | 17 / 856 / 27 |
| S13: aln minus q4 | -0.26 | -0.48 to -0.05 | 0.0217 | 247 / 194 / 459 |
| S14: q4p_n100 minus q4p | +2.73 | +2.50 to +2.96 | 0.0001 | 142 / 718 / 40 |
| S15: f16p minus gold | +1.14 | +0.92 to +1.35 | 0.0001 | 103 / 317 / 480 |

## A_H_pooled (900 episodes, 34440 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 14.78% | 14.29 to 15.26 | - |
| FP16 reader | 16.30% | 15.79 to 16.82 | 83.6% |
| Q4, FP16 reader unchanged | 19.56% | 19.04 to 20.07 | 67.7% |
| Q4, recentred | 17.76% | 17.23 to 18.28 | 76.6% |
| Q4, label-free map | 16.55% | 16.03 to 17.09 | 81.8% |
| Q4, retrained (1,000 labels) | 16.63% | 16.11 to 17.14 | 81.1% |
| Q4, retrained (100 labels; mean of 5 draws) | 20.04% | 19.58 to 20.49 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 18.08% | 17.61 to 18.59 | - |
| TF-IDF + LR (text) | 14.89% | 14.42 to 15.39 | 98.6% |
| Keyword rules (text) | 15.04% | 14.56 to 15.53 | 97.4% |
| Q4 retrained, gold sensor | 15.17% | 14.68 to 15.66 | 90.7% |
| Q4 map, gold sensor | 15.01% | 14.54 to 15.50 | 90.6% |
| FP16 reader (end) | 16.60% | 16.10 to 17.11 | 81.7% |
| Q4 unchanged (end) | 24.65% | 24.17 to 25.12 | 51.2% |
| Q4 recentred (end) | 17.81% | 17.31 to 18.32 | 70.7% |
| Q4 map (end) | 16.91% | 16.39 to 17.43 | 78.8% |
| Q4 retrained (end) | 17.02% | 16.52 to 17.54 | 77.2% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.26 | +2.92 to +3.60 | 0.0001 | 146 / 594 / 160 |
| H2a: alnp minus rawp | -3.01 | -3.35 to -2.65 | 0.0001 | 564 / 160 / 176 |
| H2b: q4p minus rawp | -2.93 | -3.28 to -2.58 | 0.0001 | 572 / 171 / 157 |
| H3: alnp minus q4p_n100 | -3.49 | -3.77 to -3.19 | 0.0001 | 701 / 157 / 42 |
| S1: alnp minus q4p | -0.08 | -0.27 to +0.12 | 0.4690 | 193 / 158 / 549 |
| S2: alnp minus q4p_n300 | -1.53 | -1.78 to -1.28 | 0.0001 | 592 / 247 / 61 |
| S3: alnp minus recp | -1.21 | -1.50 to -0.92 | 0.0001 | 384 / 185 / 331 |
| S4: recp minus q4p_n100 | -2.28 | -2.57 to -1.98 | 0.0001 | 614 / 238 / 48 |
| S5: q4p minus f16p | +0.33 | +0.09 to +0.56 | 0.0082 | 178 / 249 / 473 |
| S6: alnp minus f16p | +0.25 | +0.05 to +0.45 | 0.0134 | 147 / 200 / 553 |
| S7: tfidf minus f16p | -1.41 | -1.68 to -1.13 | 0.0001 | 355 / 147 / 398 |
| S8: tfidf minus alnp | -1.66 | -1.96 to -1.37 | 0.0001 | 382 / 150 / 368 |
| S9: rule minus alnp | -1.51 | -1.80 to -1.22 | 0.0001 | 379 / 171 / 350 |
| S10: q4p_goldS minus q4p | -1.46 | -1.70 to -1.21 | 0.0001 | 318 / 78 / 504 |
| S11: alnp_goldS minus alnp | -1.54 | -1.78 to -1.31 | 0.0001 | 307 / 62 / 531 |
| S12: raw minus f16 | +8.04 | +7.61 to +8.48 | 0.0001 | 62 / 763 / 75 |
| S13: aln minus q4 | -0.11 | -0.37 to +0.16 | 0.4475 | 272 / 226 / 402 |
| S14: q4p_n100 minus q4p | +3.41 | +3.12 to +3.69 | 0.0001 | 158 / 689 / 53 |
| S15: f16p minus gold | +1.52 | +1.24 to +1.79 | 0.0001 | 141 / 369 / 390 |

## B_L_pooled (150 episodes, 5634 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.05% | 0.71 to 1.41 | - |
| FP16 reader | 2.72% | 2.19 to 3.29 | 72.8% |
| Q4, FP16 reader unchanged | 8.34% | 7.58 to 9.15 | 62.0% |
| Q4, recentred | 4.24% | 3.61 to 4.87 | 66.6% |
| Q4, label-free map | 2.66% | 2.16 to 3.17 | 73.0% |
| Q4, retrained (1,000 labels) | 2.43% | 1.97 to 2.92 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 3.97% | 3.47 to 4.49 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 3.02% | 2.57 to 3.48 | - |
| TF-IDF + LR (text) | 5.09% | 4.46 to 5.72 | 50.3% |
| Keyword rules (text) | 10.31% | 9.52 to 11.13 | 49.9% |
| Q4 retrained, gold sensor | 2.01% | 1.56 to 2.50 | 83.3% |
| Q4 map, gold sensor | 2.13% | 1.64 to 2.63 | 83.4% |
| FP16 reader (end) | 3.62% | 3.12 to 4.21 | 70.7% |
| Q4 unchanged (end) | 16.88% | 16.04 to 17.73 | 43.5% |
| Q4 recentred (end) | 4.42% | 3.85 to 5.01 | 59.7% |
| Q4 map (end) | 3.23% | 2.71 to 3.77 | 68.4% |
| Q4 retrained (end) | 2.88% | 2.36 to 3.42 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +5.63 | +4.92 to +6.34 | 0.0001 | 5 / 127 / 18 |
| H2a: alnp minus rawp | -5.68 | -6.40 to -4.97 | 0.0001 | 127 / 4 / 19 |
| H2b: q4p minus rawp | -5.91 | -6.60 to -5.24 | 0.0001 | 129 / 1 / 20 |
| H3: alnp minus q4p_n100 | -1.30 | -1.71 to -0.90 | 0.0001 | 95 / 29 / 26 |
| S1: alnp minus q4p | +0.23 | -0.05 to +0.53 | 0.1636 | 15 / 23 / 112 |
| S2: alnp minus q4p_n300 | -0.35 | -0.72 to +0.01 | 0.0631 | 68 / 37 / 45 |
| S3: alnp minus recp | -1.58 | -2.07 to -1.09 | 0.0001 | 75 / 19 / 56 |
| S4: recp minus q4p_n100 | +0.28 | -0.17 to +0.70 | 0.2276 | 57 / 59 / 34 |
| S5: q4p minus f16p | -0.28 | -0.67 to +0.09 | 0.1790 | 30 / 21 / 99 |
| S6: alnp minus f16p | -0.05 | -0.46 to +0.35 | 0.8768 | 27 / 26 / 97 |
| S7: tfidf minus f16p | +2.38 | +1.77 to +3.01 | 0.0001 | 20 / 84 / 46 |
| S8: tfidf minus alnp | +2.43 | +1.86 to +3.03 | 0.0001 | 18 / 90 / 42 |
| S9: rule minus alnp | +7.65 | +6.92 to +8.40 | 0.0001 | 2 / 142 / 6 |
| S10: q4p_goldS minus q4p | -0.43 | -0.72 to -0.14 | 0.0045 | 27 / 10 / 113 |
| S11: alnp_goldS minus alnp | -0.53 | -0.93 to -0.16 | 0.0062 | 25 / 11 / 114 |
| S12: raw minus f16 | +13.26 | +12.37 to +14.16 | 0.0001 | 0 / 146 / 4 |
| S13: aln minus q4 | +0.35 | -0.07 to +0.78 | 0.1201 | 23 / 38 / 89 |
| S14: q4p_n100 minus q4p | +1.53 | +1.19 to +1.89 | 0.0001 | 20 / 102 / 28 |
| S15: f16p minus gold | +1.67 | +1.22 to +2.15 | 0.0001 | 5 / 69 / 76 |

## B_M_pooled (150 episodes, 5634 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 4.74% | 3.98 to 5.53 | - |
| FP16 reader | 7.35% | 6.40 to 8.32 | 72.8% |
| Q4, FP16 reader unchanged | 12.25% | 11.27 to 13.30 | 62.0% |
| Q4, recentred | 9.18% | 8.19 to 10.15 | 66.6% |
| Q4, label-free map | 7.05% | 6.20 to 7.88 | 73.0% |
| Q4, retrained (1,000 labels) | 7.24% | 6.31 to 8.17 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 9.27% | 8.44 to 10.10 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 7.95% | 7.15 to 8.79 | - |
| TF-IDF + LR (text) | 9.07% | 8.07 to 10.10 | 50.3% |
| Keyword rules (text) | 13.76% | 12.78 to 14.74 | 49.9% |
| Q4 retrained, gold sensor | 5.73% | 4.88 to 6.59 | 83.3% |
| Q4 map, gold sensor | 5.72% | 4.91 to 6.52 | 83.4% |
| FP16 reader (end) | 8.73% | 7.72 to 9.81 | 70.7% |
| Q4 unchanged (end) | 19.36% | 18.38 to 20.36 | 43.5% |
| Q4 recentred (end) | 8.91% | 7.96 to 9.88 | 59.7% |
| Q4 map (end) | 7.95% | 7.05 to 8.90 | 68.4% |
| Q4 retrained (end) | 7.88% | 6.89 to 8.87 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +4.90 | +4.04 to +5.72 | 0.0001 | 12 / 124 / 14 |
| H2a: alnp minus rawp | -5.20 | -5.98 to -4.39 | 0.0001 | 123 / 9 / 18 |
| H2b: q4p minus rawp | -5.01 | -5.79 to -4.20 | 0.0001 | 122 / 12 / 16 |
| H3: alnp minus q4p_n100 | -2.22 | -2.76 to -1.68 | 0.0001 | 112 / 30 / 8 |
| S1: alnp minus q4p | -0.20 | -0.70 to +0.29 | 0.4886 | 25 / 27 / 98 |
| S2: alnp minus q4p_n300 | -0.91 | -1.43 to -0.37 | 0.0010 | 85 / 44 / 21 |
| S3: alnp minus recp | -2.13 | -2.71 to -1.56 | 0.0001 | 83 / 20 / 47 |
| S4: recp minus q4p_n100 | -0.09 | -0.66 to +0.49 | 0.7588 | 72 / 66 / 12 |
| S5: q4p minus f16p | -0.11 | -0.83 to +0.59 | 0.7992 | 34 / 38 / 78 |
| S6: alnp minus f16p | -0.30 | -0.86 to +0.22 | 0.3105 | 38 / 36 / 76 |
| S7: tfidf minus f16p | +1.72 | +0.88 to +2.58 | 0.0006 | 44 / 82 / 24 |
| S8: tfidf minus alnp | +2.02 | +1.19 to +2.86 | 0.0001 | 41 / 79 / 30 |
| S9: rule minus alnp | +6.71 | +5.85 to +7.57 | 0.0001 | 8 / 125 / 17 |
| S10: q4p_goldS minus q4p | -1.51 | -2.04 to -0.98 | 0.0001 | 58 / 10 / 82 |
| S11: alnp_goldS minus alnp | -1.33 | -1.83 to -0.85 | 0.0001 | 54 / 14 / 82 |
| S12: raw minus f16 | +10.63 | +9.41 to +11.81 | 0.0001 | 7 / 138 / 5 |
| S13: aln minus q4 | +0.07 | -0.45 to +0.60 | 0.8385 | 42 / 41 / 67 |
| S14: q4p_n100 minus q4p | +2.03 | +1.40 to +2.65 | 0.0001 | 35 / 110 / 5 |
| S15: f16p minus gold | +2.61 | +1.88 to +3.37 | 0.0001 | 18 / 82 / 50 |

## B_H_pooled (150 episodes, 5634 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 13.44% | 12.22 to 14.62 | - |
| FP16 reader | 16.42% | 15.26 to 17.60 | 72.8% |
| Q4, FP16 reader unchanged | 19.90% | 18.75 to 21.04 | 62.0% |
| Q4, recentred | 18.16% | 16.95 to 19.37 | 66.6% |
| Q4, label-free map | 16.28% | 15.10 to 17.51 | 73.0% |
| Q4, retrained (1,000 labels) | 16.63% | 15.38 to 17.95 | 73.2% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.18% | 18.06 to 20.30 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 17.76% | 16.62 to 18.91 | - |
| TF-IDF + LR (text) | 18.65% | 17.34 to 19.96 | 50.3% |
| Keyword rules (text) | 21.28% | 20.09 to 22.43 | 49.9% |
| Q4 retrained, gold sensor | 14.22% | 13.05 to 15.35 | 83.3% |
| Q4 map, gold sensor | 14.38% | 13.20 to 15.53 | 83.4% |
| FP16 reader (end) | 17.71% | 16.42 to 18.98 | 70.7% |
| Q4 unchanged (end) | 24.88% | 23.72 to 26.02 | 43.5% |
| Q4 recentred (end) | 17.98% | 16.71 to 19.24 | 59.7% |
| Q4 map (end) | 17.41% | 16.06 to 18.69 | 68.4% |
| Q4 retrained (end) | 16.84% | 15.55 to 18.12 | 69.8% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +3.48 | +2.57 to +4.39 | 0.0001 | 23 / 100 / 27 |
| H2a: alnp minus rawp | -3.62 | -4.54 to -2.67 | 0.0001 | 97 / 24 / 29 |
| H2b: q4p minus rawp | -3.27 | -4.22 to -2.30 | 0.0001 | 98 / 26 / 26 |
| H3: alnp minus q4p_n100 | -2.90 | -3.57 to -2.24 | 0.0001 | 114 / 32 / 4 |
| S1: alnp minus q4p | -0.35 | -0.89 to +0.14 | 0.2148 | 25 / 25 / 100 |
| S2: alnp minus q4p_n300 | -1.48 | -2.05 to -0.94 | 0.0001 | 99 / 40 / 11 |
| S3: alnp minus recp | -1.88 | -2.56 to -1.19 | 0.0001 | 81 / 30 / 39 |
| S4: recp minus q4p_n100 | -1.02 | -1.75 to -0.31 | 0.0064 | 81 / 61 / 8 |
| S5: q4p minus f16p | +0.21 | -0.41 to +0.86 | 0.5630 | 45 / 42 / 63 |
| S6: alnp minus f16p | -0.14 | -0.74 to +0.45 | 0.6826 | 43 / 37 / 70 |
| S7: tfidf minus f16p | +2.24 | +1.20 to +3.26 | 0.0001 | 45 / 84 / 21 |
| S8: tfidf minus alnp | +2.38 | +1.34 to +3.40 | 0.0002 | 41 / 81 / 28 |
| S9: rule minus alnp | +5.01 | +4.15 to +5.85 | 0.0001 | 15 / 118 / 17 |
| S10: q4p_goldS minus q4p | -2.41 | -3.08 to -1.76 | 0.0001 | 74 / 9 / 67 |
| S11: alnp_goldS minus alnp | -1.90 | -2.43 to -1.38 | 0.0001 | 68 / 11 / 71 |
| S12: raw minus f16 | +7.17 | +5.88 to +8.43 | 0.0001 | 18 / 121 / 11 |
| S13: aln minus q4 | +0.57 | -0.19 to +1.35 | 0.1774 | 42 / 57 / 51 |
| S14: q4p_n100 minus q4p | +2.55 | +1.85 to +3.26 | 0.0001 | 38 / 109 / 3 |
| S15: f16p minus gold | +2.98 | +2.32 to +3.64 | 0.0001 | 18 / 90 / 42 |

Total run time 1696 s.
