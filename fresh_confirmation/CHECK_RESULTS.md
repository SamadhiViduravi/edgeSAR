# EdgeSAR fresh confirmation: results (check mode)

Protocol SHA-256 `None`; script SHA-256 `3241992ad203573dd75da7fe3db3426cfd5e8515e5f1b433c69fe7582242fe42`.

Evaluation set: `{"set": "development style B (400 reports; inspected many times)"}`

Records equal to the saved protocol-B predictions (of 400): {'recp': 400, 'alnp': 400, 'rawp': 400, 'q4p': 400, 'f16p': 400, 'rec': 400, 'aln': 400, 'raw': 400, 'q4': 400, 'f16': 400, 'rule': 400, 'tfidf': 400}

Mission shares equal to the saved wording-shift results (here, saved, equal): {'L_gold': [2.083, 2.083, True], 'L_f16p': [4.255, 4.255, True], 'L_q4p': [4.034, 4.034, True], 'L_recp': [5.408, 5.408, True], 'L_alnp': [4.167, 4.167, True], 'L_rawp': [11.436, 11.436, True], 'L_tfidf': [6.693, 6.693, True], 'L_rule': [11.924, 11.924, True], 'L_f16': [5.541, 5.541, True], 'L_q4': [5.585, 5.585, True], 'L_rec': [5.718, 5.718, True], 'L_aln': [4.832, 4.832, True], 'L_raw': [18.706, 18.706, True], 'M_gold': [5.895, 5.895, True], 'M_f16p': [8.2, 8.2, True], 'M_q4p': [8.333, 8.333, True], 'M_recp': [10.417, 10.417, True], 'M_alnp': [8.466, 8.466, True], 'M_rawp': [14.761, 14.761, True], 'M_tfidf': [10.638, 10.638, True], 'M_rule': [14.716, 14.716, True], 'M_f16': [9.087, 9.087, True], 'M_q4': [9.397, 9.397, True], 'M_rec': [10.106, 10.106, True], 'M_aln': [8.91, 8.91, True], 'M_raw': [21.144, 21.144, True], 'H_gold': [13.874, 13.874, True], 'H_f16p': [16.401, 16.401, True], 'H_q4p': [17.199, 17.199, True], 'H_recp': [18.307, 18.307, True], 'H_alnp': [16.8, 16.8, True], 'H_rawp': [21.41, 21.41, True], 'H_tfidf': [17.908, 17.908, True], 'H_rule': [20.878, 20.878, True], 'H_f16': [16.8, 16.8, True], 'H_q4': [17.598, 17.598, True], 'H_rec': [18.129, 18.129, True], 'H_aln': [17.332, 17.332, True], 'H_raw': [25.754, 25.754, True]}

**ALL CHECKS EQUAL: True**

Replay consistency: {'reports_checked': 56691, 'violations': 0}

## Primary family (B_M_pooled), Holm-adjusted

| Test | First minus second | Difference (pp) | 95% CI | p | p (Holm) | Confirmed |
|---|---|---|---|---|---|---|
| H1 | rawp minus f16p | +6.56 | +5.32 to +7.78 | 0.0001 | 0.0004 | YES |
| H2a | alnp minus rawp | -6.29 | -7.55 to -5.05 | 0.0001 | 0.0004 | YES |
| H2b | q4p minus rawp | -6.43 | -7.73 to -5.16 | 0.0001 | 0.0004 | YES |
| H3 | alnp minus q4p_n100 | -2.38 | -3.29 to -1.51 | 0.0001 | 0.0004 | YES |

Non-inferiority of the map against retraining with 1,000 labels (upper bound below the margin): {'margin_0.25pp': False, 'margin_0.5pp': False}

## B_L_s1 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.86% | 0.95 to 2.85 | - |
| FP16 reader | 3.99% | 2.27 to 5.81 | 71.8% |
| Q4, FP16 reader unchanged | 11.04% | 8.78 to 13.32 | 60.0% |
| Q4, recentred | 5.32% | 3.58 to 7.11 | 65.0% |
| Q4, label-free map | 4.39% | 2.72 to 6.23 | 71.2% |
| Q4, retrained (1,000 labels) | 4.26% | 2.61 to 6.09 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 5.51% | 4.19 to 6.84 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 4.20% | 2.83 to 5.65 | - |
| TF-IDF + LR (text) | 6.25% | 4.64 to 8.02 | 53.5% |
| Keyword rules (text) | 11.44% | 9.82 to 13.08 | 50.7% |
| Q4 retrained, gold sensor | 3.59% | 2.14 to 5.30 | 83.0% |
| Q4 map, gold sensor | 4.12% | 2.53 to 5.89 | 81.8% |
| FP16 reader (end) | 5.59% | 3.85 to 7.38 | 72.0% |
| Q4 unchanged (end) | 18.75% | 16.85 to 20.63 | 43.8% |
| Q4 recentred (end) | 5.72% | 4.04 to 7.57 | 60.8% |
| Q4 map (end) | 4.26% | 2.84 to 5.67 | 68.2% |
| Q4 retrained (end) | 5.98% | 4.38 to 7.61 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +7.05 | +5.09 to +8.94 | 0.0001 | 0 / 18 / 2 |
| H2a: alnp minus rawp | -6.65 | -9.10 to -4.27 | 0.0001 | 16 / 1 / 3 |
| H2b: q4p minus rawp | -6.78 | -9.10 to -4.50 | 0.0003 | 16 / 1 / 3 |
| H3: alnp minus q4p_n100 | -1.12 | -2.21 to +0.05 | 0.0778 | 14 / 5 / 1 |
| S1: alnp minus q4p | +0.13 | -1.11 to +1.18 | 1.0000 | 3 / 5 / 12 |
| S2: alnp minus q4p_n300 | +0.19 | -0.78 to +1.14 | 0.7473 | 8 / 7 / 5 |
| S3: alnp minus recp | -0.93 | -2.32 to +0.51 | 0.2874 | 10 / 6 / 4 |
| S4: recp minus q4p_n100 | -0.19 | -1.00 to +0.63 | 0.7036 | 10 / 8 / 2 |
| S5: q4p minus f16p | +0.27 | -1.10 to +1.66 | 0.8569 | 4 / 7 / 9 |
| S6: alnp minus f16p | +0.40 | -0.64 to +1.37 | 0.6286 | 3 / 6 / 11 |
| S7: tfidf minus f16p | +2.26 | +0.00 to +4.50 | 0.0844 | 4 / 12 / 4 |
| S8: tfidf minus alnp | +1.86 | -0.25 to +3.96 | 0.1318 | 5 / 12 / 3 |
| S9: rule minus alnp | +7.05 | +4.64 to +9.56 | 0.0002 | 0 / 16 / 4 |
| S10: q4p_goldS minus q4p | -0.66 | -1.66 to +0.13 | 0.2450 | 3 / 1 / 16 |
| S11: alnp_goldS minus alnp | -0.27 | -1.24 to +0.55 | 1.0000 | 2 / 1 / 17 |
| S12: raw minus f16 | +13.16 | +10.45 to +15.81 | 0.0001 | 0 / 19 / 1 |
| S13: aln minus q4 | -1.73 | -3.05 to -0.40 | 0.0424 | 10 / 2 / 8 |
| S14: q4p_n100 minus q4p | +1.25 | +0.19 to +2.27 | 0.0360 | 4 / 15 / 1 |
| S15: f16p minus gold | +2.13 | +0.67 to +3.98 | 0.0134 | 1 / 9 / 10 |

## B_L_s2 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 1.46% | 0.42 to 2.64 | - |
| FP16 reader | 4.52% | 3.39 to 5.70 | 71.8% |
| Q4, FP16 reader unchanged | 11.44% | 9.76 to 13.27 | 60.0% |
| Q4, recentred | 5.32% | 3.85 to 6.89 | 65.0% |
| Q4, label-free map | 3.59% | 2.32 to 4.97 | 71.2% |
| Q4, retrained (1,000 labels) | 3.19% | 2.21 to 4.11 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 5.56% | 3.91 to 7.44 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 3.72% | 2.45 to 5.17 | - |
| TF-IDF + LR (text) | 7.05% | 4.52 to 9.69 | 53.5% |
| Keyword rules (text) | 11.57% | 9.83 to 13.65 | 50.7% |
| Q4 retrained, gold sensor | 3.19% | 2.03 to 4.44 | 83.0% |
| Q4 map, gold sensor | 3.46% | 2.16 to 4.81 | 81.8% |
| FP16 reader (end) | 5.05% | 3.74 to 6.45 | 72.0% |
| Q4 unchanged (end) | 18.48% | 16.58 to 20.40 | 43.8% |
| Q4 recentred (end) | 5.19% | 3.63 to 7.15 | 60.8% |
| Q4 map (end) | 4.26% | 3.14 to 5.41 | 68.2% |
| Q4 retrained (end) | 5.05% | 3.01 to 7.30 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +6.91 | +5.56 to +8.19 | 0.0001 | 0 / 19 / 1 |
| H2a: alnp minus rawp | -7.85 | -9.03 to -6.65 | 0.0001 | 19 / 0 / 1 |
| H2b: q4p minus rawp | -8.24 | -10.04 to -6.50 | 0.0001 | 19 / 0 / 1 |
| H3: alnp minus q4p_n100 | -1.97 | -3.32 to -0.89 | 0.0017 | 14 / 3 / 3 |
| S1: alnp minus q4p | +0.40 | -0.54 to +1.53 | 0.6549 | 3 / 3 / 14 |
| S2: alnp minus q4p_n300 | -0.13 | -1.22 to +1.00 | 0.8737 | 9 / 6 / 5 |
| S3: alnp minus recp | -1.73 | -2.66 to -0.82 | 0.0044 | 11 / 1 / 8 |
| S4: recp minus q4p_n100 | -0.24 | -1.18 to +0.68 | 0.6716 | 10 / 7 / 3 |
| S5: q4p minus f16p | -1.33 | -2.36 to -0.27 | 0.0541 | 10 / 3 / 7 |
| S6: alnp minus f16p | -0.93 | -1.85 to +0.00 | 0.1180 | 7 / 2 / 11 |
| S7: tfidf minus f16p | +2.53 | +0.66 to +4.52 | 0.0259 | 4 / 13 / 3 |
| S8: tfidf minus alnp | +3.46 | +1.65 to +5.28 | 0.0025 | 2 / 14 / 4 |
| S9: rule minus alnp | +7.98 | +6.42 to +9.78 | 0.0001 | 0 / 20 / 0 |
| S10: q4p_goldS minus q4p | +0.00 | -0.66 to +0.65 | 1.0000 | 3 / 3 / 14 |
| S11: alnp_goldS minus alnp | -0.13 | -0.82 to +0.54 | 1.0000 | 4 / 3 / 13 |
| S12: raw minus f16 | +13.43 | +11.72 to +15.09 | 0.0001 | 0 / 20 / 0 |
| S13: aln minus q4 | -0.80 | -2.39 to +0.54 | 0.4232 | 5 / 5 / 10 |
| S14: q4p_n100 minus q4p | +2.37 | +1.17 to +3.75 | 0.0008 | 3 / 15 / 2 |
| S15: f16p minus gold | +3.06 | +2.09 to +4.12 | 0.0001 | 0 / 16 / 4 |

## B_L_s3 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 2.93% | 1.44 to 4.49 | - |
| FP16 reader | 4.26% | 2.65 to 5.87 | 71.8% |
| Q4, FP16 reader unchanged | 11.84% | 9.48 to 14.25 | 60.0% |
| Q4, recentred | 5.59% | 4.21 to 7.09 | 65.0% |
| Q4, label-free map | 4.52% | 3.01 to 6.19 | 71.2% |
| Q4, retrained (1,000 labels) | 4.65% | 2.88 to 6.58 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 6.70% | 5.09 to 8.53 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 5.13% | 3.59 to 6.78 | - |
| TF-IDF + LR (text) | 6.78% | 4.95 to 8.55 | 53.5% |
| Keyword rules (text) | 12.77% | 10.47 to 14.95 | 50.7% |
| Q4 retrained, gold sensor | 4.26% | 2.79 to 5.83 | 83.0% |
| Q4 map, gold sensor | 4.52% | 2.93 to 6.23 | 81.8% |
| FP16 reader (end) | 5.98% | 3.88 to 7.94 | 72.0% |
| Q4 unchanged (end) | 18.88% | 16.84 to 20.66 | 43.8% |
| Q4 recentred (end) | 6.25% | 4.73 to 7.85 | 60.8% |
| Q4 map (end) | 5.98% | 3.97 to 8.15 | 68.2% |
| Q4 retrained (end) | 5.72% | 3.80 to 7.69 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +7.58 | +5.29 to +9.86 | 0.0003 | 1 / 17 / 2 |
| H2a: alnp minus rawp | -7.31 | -9.55 to -5.11 | 0.0002 | 18 / 1 / 1 |
| H2b: q4p minus rawp | -7.18 | -9.52 to -4.84 | 0.0002 | 18 / 2 / 0 |
| H3: alnp minus q4p_n100 | -2.18 | -3.18 to -1.28 | 0.0002 | 16 / 1 / 3 |
| S1: alnp minus q4p | -0.13 | -0.88 to +0.54 | 1.0000 | 2 / 2 / 16 |
| S2: alnp minus q4p_n300 | -0.61 | -1.27 to +0.03 | 0.1064 | 10 / 4 / 6 |
| S3: alnp minus recp | -1.06 | -2.37 to +0.26 | 0.1923 | 8 / 3 / 9 |
| S4: recp minus q4p_n100 | -1.12 | -2.43 to +0.03 | 0.1148 | 10 / 6 / 4 |
| S5: q4p minus f16p | +0.40 | -0.55 to +1.29 | 0.5965 | 4 / 6 / 10 |
| S6: alnp minus f16p | +0.27 | -0.44 to +0.95 | 0.7311 | 3 / 5 / 12 |
| S7: tfidf minus f16p | +2.53 | +1.14 to +3.88 | 0.0048 | 3 / 13 / 4 |
| S8: tfidf minus alnp | +2.26 | +0.95 to +3.63 | 0.0078 | 2 / 11 / 7 |
| S9: rule minus alnp | +8.24 | +6.20 to +10.38 | 0.0002 | 0 / 19 / 1 |
| S10: q4p_goldS minus q4p | -0.40 | -0.81 to +0.00 | 0.2562 | 3 / 0 / 17 |
| S11: alnp_goldS minus alnp | +0.00 | -0.40 to +0.39 | 1.0000 | 1 / 1 / 18 |
| S12: raw minus f16 | +12.90 | +11.02 to +14.93 | 0.0001 | 0 / 20 / 0 |
| S13: aln minus q4 | +0.27 | -0.64 to +1.18 | 0.7862 | 4 / 5 / 11 |
| S14: q4p_n100 minus q4p | +2.05 | +0.90 to +3.21 | 0.0021 | 2 / 15 / 3 |
| S15: f16p minus gold | +1.33 | +0.53 to +2.13 | 0.0110 | 1 / 10 / 9 |

## B_M_s1 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 6.38% | 3.83 to 9.11 | - |
| FP16 reader | 8.11% | 5.83 to 10.49 | 71.8% |
| Q4, FP16 reader unchanged | 14.89% | 12.17 to 17.88 | 60.0% |
| Q4, recentred | 10.90% | 8.65 to 13.61 | 65.0% |
| Q4, label-free map | 8.64% | 6.02 to 11.70 | 71.2% |
| Q4, retrained (1,000 labels) | 8.64% | 6.09 to 11.57 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 11.14% | 8.77 to 13.82 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.64% | 6.28 to 11.36 | - |
| TF-IDF + LR (text) | 12.23% | 9.52 to 15.27 | 53.5% |
| Keyword rules (text) | 14.89% | 12.79 to 17.02 | 50.7% |
| Q4 retrained, gold sensor | 7.71% | 5.21 to 10.52 | 83.0% |
| Q4 map, gold sensor | 7.18% | 5.14 to 9.39 | 81.8% |
| FP16 reader (end) | 9.44% | 7.36 to 11.86 | 72.0% |
| Q4 unchanged (end) | 21.68% | 19.29 to 24.39 | 43.8% |
| Q4 recentred (end) | 10.77% | 7.84 to 14.15 | 60.8% |
| Q4 map (end) | 9.44% | 7.00 to 12.27 | 68.2% |
| Q4 retrained (end) | 10.64% | 8.10 to 13.50 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +6.78 | +4.79 to +8.84 | 0.0001 | 0 / 18 / 2 |
| H2a: alnp minus rawp | -6.25 | -8.54 to -4.12 | 0.0001 | 16 / 1 / 3 |
| H2b: q4p minus rawp | -6.25 | -8.61 to -4.03 | 0.0001 | 16 / 2 / 2 |
| H3: alnp minus q4p_n100 | -2.50 | -3.80 to -1.30 | 0.0006 | 15 / 5 / 0 |
| S1: alnp minus q4p | +0.00 | -0.68 to +0.65 | 1.0000 | 3 / 3 / 14 |
| S2: alnp minus q4p_n300 | +0.00 | -0.73 to +0.74 | 1.0000 | 8 / 8 / 4 |
| S3: alnp minus recp | -2.26 | -3.56 to -1.15 | 0.0021 | 13 / 1 / 6 |
| S4: recp minus q4p_n100 | -0.24 | -1.88 to +1.42 | 0.8093 | 11 / 9 / 0 |
| S5: q4p minus f16p | +0.53 | -0.86 to +2.03 | 0.6138 | 6 / 6 / 8 |
| S6: alnp minus f16p | +0.53 | -0.91 to +2.10 | 0.6367 | 5 / 5 / 10 |
| S7: tfidf minus f16p | +4.12 | +1.94 to +6.29 | 0.0045 | 4 / 13 / 3 |
| S8: tfidf minus alnp | +3.59 | +1.74 to +5.53 | 0.0025 | 3 / 14 / 3 |
| S9: rule minus alnp | +6.25 | +3.34 to +8.91 | 0.0011 | 2 / 17 / 1 |
| S10: q4p_goldS minus q4p | -0.93 | -2.05 to +0.38 | 0.2280 | 8 / 1 / 11 |
| S11: alnp_goldS minus alnp | -1.46 | -3.13 to +0.14 | 0.1575 | 8 / 1 / 11 |
| S12: raw minus f16 | +12.23 | +9.92 to +14.62 | 0.0001 | 0 / 20 / 0 |
| S13: aln minus q4 | -1.20 | -3.61 to +1.09 | 0.4011 | 7 / 4 / 9 |
| S14: q4p_n100 minus q4p | +2.50 | +1.12 to +3.92 | 0.0022 | 4 / 16 / 0 |
| S15: f16p minus gold | +1.73 | -0.12 to +3.47 | 0.0995 | 3 / 11 / 6 |

## B_M_s2 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 5.45% | 2.95 to 8.29 | - |
| FP16 reader | 7.45% | 4.95 to 10.15 | 71.8% |
| Q4, FP16 reader unchanged | 14.23% | 12.23 to 16.37 | 60.0% |
| Q4, recentred | 10.37% | 7.82 to 13.08 | 65.0% |
| Q4, label-free map | 8.11% | 5.30 to 11.11 | 71.2% |
| Q4, retrained (1,000 labels) | 7.98% | 5.05 to 11.15 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 10.48% | 7.95 to 13.21 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.64% | 5.88 to 11.56 | - |
| TF-IDF + LR (text) | 9.84% | 6.98 to 12.92 | 53.5% |
| Keyword rules (text) | 14.23% | 11.94 to 17.03 | 50.7% |
| Q4 retrained, gold sensor | 6.65% | 4.10 to 9.53 | 83.0% |
| Q4 map, gold sensor | 6.12% | 4.27 to 8.02 | 81.8% |
| FP16 reader (end) | 9.44% | 6.66 to 12.33 | 72.0% |
| Q4 unchanged (end) | 20.35% | 17.95 to 22.98 | 43.8% |
| Q4 recentred (end) | 9.84% | 7.31 to 12.69 | 60.8% |
| Q4 map (end) | 9.04% | 6.39 to 11.80 | 68.2% |
| Q4 retrained (end) | 8.64% | 6.01 to 11.22 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +6.78 | +4.37 to +8.81 | 0.0002 | 3 / 17 / 0 |
| H2a: alnp minus rawp | -6.12 | -8.40 to -3.44 | 0.0008 | 17 / 2 / 1 |
| H2b: q4p minus rawp | -6.25 | -8.53 to -3.91 | 0.0002 | 16 / 3 / 1 |
| H3: alnp minus q4p_n100 | -2.37 | -3.75 to -0.89 | 0.0072 | 14 / 4 / 2 |
| S1: alnp minus q4p | +0.13 | -1.81 to +1.90 | 1.0000 | 4 / 7 / 9 |
| S2: alnp minus q4p_n300 | -0.53 | -2.05 to +1.06 | 0.5510 | 9 / 7 / 4 |
| S3: alnp minus recp | -2.26 | -3.79 to -0.67 | 0.0224 | 13 / 4 / 3 |
| S4: recp minus q4p_n100 | -0.11 | -1.42 to +1.18 | 0.9072 | 9 / 10 / 1 |
| S5: q4p minus f16p | +0.53 | -1.05 to +2.35 | 0.7041 | 6 / 5 / 9 |
| S6: alnp minus f16p | +0.66 | -0.64 to +2.05 | 0.4699 | 5 / 5 / 10 |
| S7: tfidf minus f16p | +2.39 | +0.00 to +4.67 | 0.0826 | 5 / 14 / 1 |
| S8: tfidf minus alnp | +1.73 | -0.93 to +4.19 | 0.2566 | 5 / 11 / 4 |
| S9: rule minus alnp | +6.12 | +3.59 to +8.44 | 0.0003 | 2 / 15 / 3 |
| S10: q4p_goldS minus q4p | -1.33 | -2.48 to -0.28 | 0.0515 | 7 / 1 / 12 |
| S11: alnp_goldS minus alnp | -1.99 | -3.70 to -0.53 | 0.0399 | 7 / 1 / 12 |
| S12: raw minus f16 | +10.90 | +8.23 to +13.68 | 0.0001 | 0 / 17 / 3 |
| S13: aln minus q4 | +0.40 | -0.95 to +1.77 | 0.7128 | 5 / 7 / 8 |
| S14: q4p_n100 minus q4p | +2.50 | +1.19 to +3.79 | 0.0024 | 3 / 15 / 2 |
| S15: f16p minus gold | +1.99 | -0.27 to +4.06 | 0.1161 | 2 / 12 / 6 |

## B_M_s3 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 5.85% | 3.96 to 7.97 | - |
| FP16 reader | 9.04% | 6.94 to 11.07 | 71.8% |
| Q4, FP16 reader unchanged | 15.16% | 13.46 to 16.92 | 60.0% |
| Q4, recentred | 9.97% | 8.05 to 11.89 | 65.0% |
| Q4, label-free map | 8.64% | 6.69 to 10.65 | 71.2% |
| Q4, retrained (1,000 labels) | 8.38% | 6.37 to 10.67 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 10.90% | 8.63 to 13.42 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.78% | 6.96 to 10.75 | - |
| TF-IDF + LR (text) | 9.84% | 7.23 to 12.52 | 53.5% |
| Keyword rules (text) | 15.03% | 13.43 to 16.52 | 50.7% |
| Q4 retrained, gold sensor | 7.45% | 5.18 to 9.99 | 83.0% |
| Q4 map, gold sensor | 7.05% | 5.20 to 9.20 | 81.8% |
| FP16 reader (end) | 8.38% | 5.92 to 10.80 | 72.0% |
| Q4 unchanged (end) | 21.41% | 18.60 to 23.94 | 43.8% |
| Q4 recentred (end) | 9.71% | 7.25 to 12.18 | 60.8% |
| Q4 map (end) | 8.24% | 6.12 to 10.73 | 68.2% |
| Q4 retrained (end) | 8.91% | 6.88 to 11.32 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +6.12 | +4.12 to +8.21 | 0.0003 | 1 / 17 / 2 |
| H2a: alnp minus rawp | -6.52 | -8.45 to -4.68 | 0.0002 | 17 / 0 / 3 |
| H2b: q4p minus rawp | -6.78 | -8.82 to -4.79 | 0.0002 | 16 / 0 / 4 |
| H3: alnp minus q4p_n100 | -2.26 | -4.37 to -0.67 | 0.0096 | 16 / 4 / 0 |
| S1: alnp minus q4p | +0.27 | -0.72 to +1.35 | 0.8118 | 5 / 5 / 10 |
| S2: alnp minus q4p_n300 | -0.13 | -1.28 to +0.84 | 0.8635 | 8 / 10 / 2 |
| S3: alnp minus recp | -1.33 | -3.23 to +0.53 | 0.2624 | 8 / 2 / 10 |
| S4: recp minus q4p_n100 | -0.93 | -2.47 to +0.39 | 0.2635 | 12 / 8 / 0 |
| S5: q4p minus f16p | -0.66 | -1.63 to +0.27 | 0.3183 | 6 / 3 / 11 |
| S6: alnp minus f16p | -0.40 | -1.53 to +0.56 | 0.6752 | 5 / 4 / 11 |
| S7: tfidf minus f16p | +0.80 | -1.57 to +3.35 | 0.6172 | 8 / 10 / 2 |
| S8: tfidf minus alnp | +1.20 | -1.33 to +3.83 | 0.4338 | 6 / 9 / 5 |
| S9: rule minus alnp | +6.38 | +4.23 to +8.47 | 0.0004 | 1 / 16 / 3 |
| S10: q4p_goldS minus q4p | -0.93 | -2.69 to +0.76 | 0.3924 | 6 / 2 / 12 |
| S11: alnp_goldS minus alnp | -1.60 | -3.11 to -0.37 | 0.0634 | 6 / 1 / 13 |
| S12: raw minus f16 | +13.03 | +10.32 to +15.82 | 0.0001 | 0 / 18 / 2 |
| S13: aln minus q4 | -0.66 | -1.96 to +0.51 | 0.4187 | 7 / 5 / 8 |
| S14: q4p_n100 minus q4p | +2.53 | +0.95 to +4.45 | 0.0040 | 4 / 16 / 0 |
| S15: f16p minus gold | +3.19 | +1.58 to +4.92 | 0.0020 | 1 / 12 / 7 |

## B_H_s1 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 13.16% | 10.30 to 16.23 | - |
| FP16 reader | 17.15% | 13.54 to 20.40 | 71.8% |
| Q4, FP16 reader unchanged | 21.28% | 18.93 to 24.06 | 60.0% |
| Q4, recentred | 18.75% | 15.90 to 21.57 | 65.0% |
| Q4, label-free map | 17.55% | 13.96 to 21.25 | 71.2% |
| Q4, retrained (1,000 labels) | 17.29% | 13.74 to 20.95 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.15% | 16.54 to 21.88 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 18.22% | 15.18 to 21.46 | - |
| TF-IDF + LR (text) | 17.95% | 15.53 to 20.36 | 53.5% |
| Keyword rules (text) | 19.28% | 17.39 to 21.17 | 50.7% |
| Q4 retrained, gold sensor | 15.16% | 12.04 to 18.52 | 83.0% |
| Q4 map, gold sensor | 15.29% | 12.04 to 18.72 | 81.8% |
| FP16 reader (end) | 17.69% | 14.40 to 21.02 | 72.0% |
| Q4 unchanged (end) | 25.53% | 22.82 to 27.96 | 43.8% |
| Q4 recentred (end) | 17.95% | 15.07 to 20.63 | 60.8% |
| Q4 map (end) | 18.22% | 15.56 to 20.84 | 68.2% |
| Q4 retrained (end) | 17.82% | 14.78 to 20.88 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +4.12 | +1.26 to +7.06 | 0.0167 | 4 / 13 / 3 |
| H2a: alnp minus rawp | -3.72 | -6.68 to -0.80 | 0.0296 | 14 / 5 / 1 |
| H2b: q4p minus rawp | -3.99 | -6.49 to -1.49 | 0.0078 | 14 / 5 / 1 |
| H3: alnp minus q4p_n100 | -1.60 | -3.43 to +0.20 | 0.1073 | 14 / 6 / 0 |
| S1: alnp minus q4p | +0.27 | -0.96 to +1.47 | 0.8410 | 4 / 6 / 10 |
| S2: alnp minus q4p_n300 | -0.66 | -2.04 to +0.56 | 0.3606 | 13 / 7 / 0 |
| S3: alnp minus recp | -1.20 | -3.26 to +0.65 | 0.3252 | 10 / 6 / 4 |
| S4: recp minus q4p_n100 | -0.40 | -2.19 to +1.37 | 0.6958 | 10 / 10 / 0 |
| S5: q4p minus f16p | +0.13 | -1.70 to +1.98 | 1.0000 | 6 / 7 / 7 |
| S6: alnp minus f16p | +0.40 | -0.98 to +1.71 | 0.7101 | 4 / 6 / 10 |
| S7: tfidf minus f16p | +0.80 | -1.65 to +3.45 | 0.6193 | 7 / 7 / 6 |
| S8: tfidf minus alnp | +0.40 | -1.95 to +2.92 | 0.8286 | 7 / 7 / 6 |
| S9: rule minus alnp | +1.73 | -1.04 to +4.64 | 0.2962 | 8 / 12 / 0 |
| S10: q4p_goldS minus q4p | -2.13 | -3.59 to -0.83 | 0.0082 | 8 / 0 / 12 |
| S11: alnp_goldS minus alnp | -2.26 | -3.38 to -1.19 | 0.0018 | 10 / 0 / 10 |
| S12: raw minus f16 | +7.85 | +4.53 to +11.42 | 0.0004 | 2 / 17 / 1 |
| S13: aln minus q4 | +0.40 | -1.15 to +2.18 | 0.7648 | 6 / 6 / 8 |
| S14: q4p_n100 minus q4p | +1.86 | +0.51 to +3.38 | 0.0165 | 5 / 14 / 1 |
| S15: f16p minus gold | +3.99 | +2.13 to +5.80 | 0.0012 | 2 / 14 / 4 |

## B_H_s2 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 13.96% | 10.82 to 17.02 | - |
| FP16 reader | 15.43% | 12.27 to 18.53 | 71.8% |
| Q4, FP16 reader unchanged | 21.28% | 18.18 to 24.62 | 60.0% |
| Q4, recentred | 17.69% | 14.23 to 21.73 | 65.0% |
| Q4, label-free map | 16.22% | 12.87 to 19.82 | 71.2% |
| Q4, retrained (1,000 labels) | 16.89% | 13.32 to 20.81 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.71% | 16.52 to 23.03 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 17.29% | 14.27 to 20.19 | - |
| TF-IDF + LR (text) | 17.69% | 14.48 to 20.94 | 53.5% |
| Keyword rules (text) | 20.88% | 17.56 to 24.37 | 50.7% |
| Q4 retrained, gold sensor | 14.89% | 11.54 to 18.14 | 83.0% |
| Q4 map, gold sensor | 13.56% | 10.70 to 16.23 | 81.8% |
| FP16 reader (end) | 15.69% | 12.28 to 19.26 | 72.0% |
| Q4 unchanged (end) | 26.60% | 24.04 to 29.43 | 43.8% |
| Q4 recentred (end) | 18.48% | 13.85 to 23.55 | 60.8% |
| Q4 map (end) | 15.96% | 12.64 to 19.26 | 68.2% |
| Q4 retrained (end) | 16.36% | 12.68 to 20.00 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +5.85 | +2.64 to +9.22 | 0.0034 | 3 / 16 / 1 |
| H2a: alnp minus rawp | -5.05 | -7.81 to -2.53 | 0.0019 | 15 / 3 / 2 |
| H2b: q4p minus rawp | -4.39 | -7.56 to -1.08 | 0.0200 | 14 / 4 / 2 |
| H3: alnp minus q4p_n100 | -3.48 | -6.04 to -1.10 | 0.0113 | 14 / 6 / 0 |
| S1: alnp minus q4p | -0.66 | -2.66 to +1.05 | 0.6101 | 5 / 5 / 10 |
| S2: alnp minus q4p_n300 | -1.06 | -3.21 to +1.11 | 0.3703 | 11 / 8 / 1 |
| S3: alnp minus recp | -1.46 | -3.59 to +0.53 | 0.2439 | 9 / 4 / 7 |
| S4: recp minus q4p_n100 | -2.02 | -4.41 to +0.18 | 0.1033 | 14 / 5 / 1 |
| S5: q4p minus f16p | +1.46 | -1.11 to +4.23 | 0.3667 | 6 / 9 / 5 |
| S6: alnp minus f16p | +0.80 | -1.74 to +3.42 | 0.6481 | 5 / 9 / 6 |
| S7: tfidf minus f16p | +2.26 | +0.00 to +4.69 | 0.1085 | 5 / 11 / 4 |
| S8: tfidf minus alnp | +1.46 | -1.81 to +4.44 | 0.4301 | 3 / 10 / 7 |
| S9: rule minus alnp | +4.65 | +0.66 to +8.79 | 0.0439 | 4 / 12 / 4 |
| S10: q4p_goldS minus q4p | -1.99 | -4.52 to -0.13 | 0.1072 | 7 / 3 / 10 |
| S11: alnp_goldS minus alnp | -2.66 | -5.15 to -0.42 | 0.0451 | 10 / 1 / 9 |
| S12: raw minus f16 | +10.90 | +8.22 to +13.63 | 0.0001 | 0 / 19 / 1 |
| S13: aln minus q4 | -0.40 | -2.53 to +1.51 | 0.8121 | 5 / 7 / 8 |
| S14: q4p_n100 minus q4p | +2.82 | +1.02 to +4.84 | 0.0059 | 4 / 15 / 1 |
| S15: f16p minus gold | +1.46 | -0.50 to +3.29 | 0.2017 | 6 / 11 / 3 |

## B_H_s3 (20 episodes, 752 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 14.49% | 11.16 to 17.91 | - |
| FP16 reader | 16.62% | 13.29 to 19.82 | 71.8% |
| Q4, FP16 reader unchanged | 21.68% | 18.93 to 24.64 | 60.0% |
| Q4, recentred | 18.48% | 15.65 to 21.33 | 65.0% |
| Q4, label-free map | 16.62% | 13.24 to 20.21 | 71.2% |
| Q4, retrained (1,000 labels) | 17.42% | 13.81 to 20.85 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.73% | 17.04 to 22.31 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 18.43% | 15.43 to 21.14 | - |
| TF-IDF + LR (text) | 18.09% | 15.23 to 20.69 | 53.5% |
| Keyword rules (text) | 22.47% | 19.84 to 25.20 | 50.7% |
| Q4 retrained, gold sensor | 15.29% | 12.02 to 18.57 | 83.0% |
| Q4 map, gold sensor | 14.49% | 11.06 to 18.02 | 81.8% |
| FP16 reader (end) | 17.02% | 13.33 to 21.06 | 72.0% |
| Q4 unchanged (end) | 25.13% | 22.24 to 27.93 | 43.8% |
| Q4 recentred (end) | 17.95% | 14.35 to 21.64 | 60.8% |
| Q4 map (end) | 17.82% | 14.69 to 20.92 | 68.2% |
| Q4 retrained (end) | 18.62% | 15.24 to 21.67 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +5.05 | +2.54 to +7.89 | 0.0019 | 4 / 15 / 1 |
| H2a: alnp minus rawp | -5.05 | -8.14 to -2.40 | 0.0014 | 14 / 2 / 4 |
| H2b: q4p minus rawp | -4.26 | -7.92 to -1.24 | 0.0163 | 11 / 5 / 4 |
| H3: alnp minus q4p_n100 | -3.11 | -4.93 to -1.24 | 0.0062 | 14 / 6 / 0 |
| S1: alnp minus q4p | -0.80 | -2.73 to +1.05 | 0.5294 | 7 / 6 / 7 |
| S2: alnp minus q4p_n300 | -1.81 | -3.62 to -0.03 | 0.0709 | 13 / 5 / 2 |
| S3: alnp minus recp | -1.86 | -3.71 to -0.25 | 0.0692 | 10 / 3 / 7 |
| S4: recp minus q4p_n100 | -1.25 | -2.75 to +0.29 | 0.1370 | 12 / 8 / 0 |
| S5: q4p minus f16p | +0.80 | -1.59 to +3.14 | 0.5889 | 6 / 9 / 5 |
| S6: alnp minus f16p | +0.00 | -2.10 to +1.90 | 1.0000 | 7 / 6 / 7 |
| S7: tfidf minus f16p | +1.46 | -0.81 to +3.83 | 0.2905 | 4 / 10 / 6 |
| S8: tfidf minus alnp | +1.46 | -1.31 to +4.09 | 0.3604 | 5 / 12 / 3 |
| S9: rule minus alnp | +5.85 | +2.75 to +9.09 | 0.0024 | 3 / 15 / 2 |
| S10: q4p_goldS minus q4p | -2.13 | -3.83 to -0.59 | 0.0248 | 9 / 2 / 9 |
| S11: alnp_goldS minus alnp | -2.13 | -3.22 to -1.10 | 0.0021 | 10 / 0 / 10 |
| S12: raw minus f16 | +8.11 | +5.87 to +10.23 | 0.0001 | 1 / 18 / 1 |
| S13: aln minus q4 | -0.80 | -2.63 to +0.93 | 0.4773 | 8 / 5 / 7 |
| S14: q4p_n100 minus q4p | +2.31 | +0.18 to +4.57 | 0.0548 | 8 / 12 / 0 |
| S15: f16p minus gold | +2.13 | +0.41 to +3.91 | 0.0469 | 3 / 11 / 6 |

## B_L_pooled (60 episodes, 2256 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 2.08% | 1.42 to 2.79 | - |
| FP16 reader | 4.26% | 3.40 to 5.18 | 71.8% |
| Q4, FP16 reader unchanged | 11.44% | 10.24 to 12.71 | 60.0% |
| Q4, recentred | 5.41% | 4.52 to 6.37 | 65.0% |
| Q4, label-free map | 4.17% | 3.27 to 5.13 | 71.2% |
| Q4, retrained (1,000 labels) | 4.03% | 3.18 to 5.00 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 5.92% | 5.05 to 6.93 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 4.35% | 3.56 to 5.26 | - |
| TF-IDF + LR (text) | 6.69% | 5.58 to 7.93 | 53.5% |
| Keyword rules (text) | 11.92% | 10.84 to 13.08 | 50.7% |
| Q4 retrained, gold sensor | 3.68% | 2.90 to 4.61 | 83.0% |
| Q4 map, gold sensor | 4.03% | 3.16 to 4.99 | 81.8% |
| FP16 reader (end) | 5.54% | 4.53 to 6.57 | 72.0% |
| Q4 unchanged (end) | 18.71% | 17.59 to 19.80 | 43.8% |
| Q4 recentred (end) | 5.72% | 4.74 to 6.75 | 60.8% |
| Q4 map (end) | 4.83% | 3.96 to 5.81 | 68.2% |
| Q4 retrained (end) | 5.59% | 4.49 to 6.75 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +7.18 | +6.08 to +8.26 | 0.0001 | 1 / 54 / 5 |
| H2a: alnp minus rawp | -7.27 | -8.42 to -6.11 | 0.0001 | 53 / 2 / 5 |
| H2b: q4p minus rawp | -7.40 | -8.65 to -6.15 | 0.0001 | 53 / 3 / 4 |
| H3: alnp minus q4p_n100 | -1.76 | -2.41 to -1.12 | 0.0001 | 44 / 9 / 7 |
| S1: alnp minus q4p | +0.13 | -0.44 to +0.69 | 0.7679 | 8 / 10 / 42 |
| S2: alnp minus q4p_n300 | -0.19 | -0.72 to +0.35 | 0.5199 | 27 / 17 / 16 |
| S3: alnp minus recp | -1.24 | -1.96 to -0.53 | 0.0025 | 29 / 10 / 21 |
| S4: recp minus q4p_n100 | -0.51 | -1.14 to +0.07 | 0.1028 | 30 / 21 / 9 |
| S5: q4p minus f16p | -0.22 | -0.90 to +0.45 | 0.6175 | 18 / 16 / 26 |
| S6: alnp minus f16p | -0.09 | -0.64 to +0.43 | 0.8740 | 13 / 13 / 34 |
| S7: tfidf minus f16p | +2.44 | +1.37 to +3.54 | 0.0002 | 11 / 38 / 11 |
| S8: tfidf minus alnp | +2.53 | +1.50 to +3.57 | 0.0001 | 9 / 37 / 14 |
| S9: rule minus alnp | +7.76 | +6.56 to +9.01 | 0.0001 | 0 / 55 / 5 |
| S10: q4p_goldS minus q4p | -0.35 | -0.77 to +0.00 | 0.1355 | 9 / 4 / 47 |
| S11: alnp_goldS minus alnp | -0.13 | -0.53 to +0.26 | 0.6629 | 7 / 5 / 48 |
| S12: raw minus f16 | +13.16 | +11.94 to +14.45 | 0.0001 | 0 / 59 / 1 |
| S13: aln minus q4 | -0.75 | -1.53 to +0.00 | 0.0719 | 19 / 12 / 29 |
| S14: q4p_n100 minus q4p | +1.89 | +1.22 to +2.59 | 0.0001 | 9 / 45 / 6 |
| S15: f16p minus gold | +2.17 | +1.49 to +2.95 | 0.0001 | 2 / 35 / 23 |

## B_M_pooled (60 episodes, 2256 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 5.90% | 4.52 to 7.34 | - |
| FP16 reader | 8.20% | 6.87 to 9.65 | 71.8% |
| Q4, FP16 reader unchanged | 14.76% | 13.49 to 16.10 | 60.0% |
| Q4, recentred | 10.42% | 9.12 to 11.84 | 65.0% |
| Q4, label-free map | 8.47% | 7.02 to 10.08 | 71.2% |
| Q4, retrained (1,000 labels) | 8.33% | 6.85 to 9.88 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 10.84% | 9.43 to 12.39 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 8.69% | 7.34 to 10.15 | - |
| TF-IDF + LR (text) | 10.64% | 9.02 to 12.25 | 53.5% |
| Keyword rules (text) | 14.72% | 13.59 to 16.02 | 50.7% |
| Q4 retrained, gold sensor | 7.27% | 5.88 to 8.80 | 83.0% |
| Q4 map, gold sensor | 6.78% | 5.71 to 8.03 | 81.8% |
| FP16 reader (end) | 9.09% | 7.71 to 10.58 | 72.0% |
| Q4 unchanged (end) | 21.14% | 19.67 to 22.65 | 43.8% |
| Q4 recentred (end) | 10.11% | 8.56 to 11.80 | 60.8% |
| Q4 map (end) | 8.91% | 7.48 to 10.49 | 68.2% |
| Q4 retrained (end) | 9.40% | 7.98 to 10.86 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +6.56 | +5.32 to +7.78 | 0.0001 | 4 / 52 / 4 |
| H2a: alnp minus rawp | -6.29 | -7.55 to -5.05 | 0.0001 | 50 / 3 / 7 |
| H2b: q4p minus rawp | -6.43 | -7.73 to -5.16 | 0.0001 | 48 / 5 / 7 |
| H3: alnp minus q4p_n100 | -2.38 | -3.29 to -1.51 | 0.0001 | 45 / 13 / 2 |
| S1: alnp minus q4p | +0.13 | -0.62 to +0.86 | 0.8253 | 12 / 15 / 33 |
| S2: alnp minus q4p_n300 | -0.22 | -0.91 to +0.44 | 0.5472 | 25 / 25 / 10 |
| S3: alnp minus recp | -1.95 | -2.87 to -1.04 | 0.0002 | 34 / 7 / 19 |
| S4: recp minus q4p_n100 | -0.43 | -1.29 to +0.43 | 0.3453 | 32 / 27 / 1 |
| S5: q4p minus f16p | +0.13 | -0.67 to +1.00 | 0.8382 | 18 / 14 / 28 |
| S6: alnp minus f16p | +0.27 | -0.49 to +1.05 | 0.5792 | 15 / 14 / 31 |
| S7: tfidf minus f16p | +2.44 | +1.04 to +3.84 | 0.0018 | 17 / 37 / 6 |
| S8: tfidf minus alnp | +2.17 | +0.78 to +3.56 | 0.0047 | 14 / 34 / 12 |
| S9: rule minus alnp | +6.25 | +4.80 to +7.63 | 0.0001 | 5 / 48 / 7 |
| S10: q4p_goldS minus q4p | -1.06 | -1.86 to -0.28 | 0.0132 | 21 / 4 / 35 |
| S11: alnp_goldS minus alnp | -1.68 | -2.60 to -0.83 | 0.0007 | 21 / 3 / 36 |
| S12: raw minus f16 | +12.06 | +10.55 to +13.62 | 0.0001 | 0 / 55 / 5 |
| S13: aln minus q4 | -0.49 | -1.50 to +0.49 | 0.4049 | 19 / 16 / 25 |
| S14: q4p_n100 minus q4p | +2.51 | +1.67 to +3.40 | 0.0001 | 11 / 47 / 2 |
| S15: f16p minus gold | +2.30 | +1.19 to +3.43 | 0.0003 | 6 / 35 / 19 |

## B_H_pooled (60 episodes, 2256 incidents)

| Arm | Missed share | 95% CI | Whole record right |
|---|---|---|---|
| Gold records (reference) | 13.87% | 12.10 to 15.80 | - |
| FP16 reader | 16.40% | 14.48 to 18.41 | 71.8% |
| Q4, FP16 reader unchanged | 21.41% | 19.89 to 23.20 | 60.0% |
| Q4, recentred | 18.31% | 16.47 to 20.23 | 65.0% |
| Q4, label-free map | 16.80% | 14.69 to 18.94 | 71.2% |
| Q4, retrained (1,000 labels) | 17.20% | 15.17 to 19.22 | 72.8% |
| Q4, retrained (100 labels; mean of 5 draws) | 19.53% | 17.91 to 21.17 | - |
| Q4, retrained (300 labels; mean of 5 draws) | 17.98% | 16.21 to 19.75 | - |
| TF-IDF + LR (text) | 17.91% | 16.28 to 19.56 | 53.5% |
| Keyword rules (text) | 20.88% | 19.23 to 22.59 | 50.7% |
| Q4 retrained, gold sensor | 15.12% | 13.24 to 17.04 | 83.0% |
| Q4 map, gold sensor | 14.45% | 12.61 to 16.39 | 81.8% |
| FP16 reader (end) | 16.80% | 14.80 to 18.90 | 72.0% |
| Q4 unchanged (end) | 25.75% | 24.29 to 27.34 | 43.8% |
| Q4 recentred (end) | 18.13% | 15.97 to 20.35 | 60.8% |
| Q4 map (end) | 17.33% | 15.60 to 19.19 | 68.2% |
| Q4 retrained (end) | 17.60% | 15.62 to 19.56 | 67.0% |

| Comparison | Difference (pp) | 95% CI | p (sign-flip) | first better / worse / tied |
|---|---|---|---|---|
| H1: rawp minus f16p | +5.01 | +3.29 to +6.75 | 0.0001 | 11 / 44 / 5 |
| H2a: alnp minus rawp | -4.61 | -6.28 to -3.00 | 0.0001 | 43 / 10 / 7 |
| H2b: q4p minus rawp | -4.21 | -5.98 to -2.49 | 0.0001 | 39 / 14 / 7 |
| H3: alnp minus q4p_n100 | -2.73 | -3.97 to -1.53 | 0.0001 | 42 / 18 / 0 |
| S1: alnp minus q4p | -0.40 | -1.42 to +0.53 | 0.4805 | 16 / 17 / 27 |
| S2: alnp minus q4p_n300 | -1.18 | -2.23 to -0.14 | 0.0337 | 37 / 20 / 3 |
| S3: alnp minus recp | -1.51 | -2.62 to -0.43 | 0.0118 | 29 / 13 / 18 |
| S4: recp minus q4p_n100 | -1.22 | -2.37 to -0.15 | 0.0330 | 36 / 23 / 1 |
| S5: q4p minus f16p | +0.80 | -0.49 to +2.17 | 0.2858 | 18 / 25 / 17 |
| S6: alnp minus f16p | +0.40 | -0.75 to +1.60 | 0.5763 | 16 / 21 / 23 |
| S7: tfidf minus f16p | +1.51 | +0.13 to +2.95 | 0.0487 | 16 / 28 / 16 |
| S8: tfidf minus alnp | +1.11 | -0.52 to +2.72 | 0.2024 | 15 / 29 / 16 |
| S9: rule minus alnp | +4.08 | +2.07 to +6.14 | 0.0001 | 15 / 39 / 6 |
| S10: q4p_goldS minus q4p | -2.08 | -3.17 to -1.14 | 0.0001 | 24 / 5 / 31 |
| S11: alnp_goldS minus alnp | -2.35 | -3.31 to -1.47 | 0.0001 | 30 / 1 / 29 |
| S12: raw minus f16 | +8.95 | +7.31 to +10.65 | 0.0001 | 3 / 54 / 3 |
| S13: aln minus q4 | -0.27 | -1.33 to +0.80 | 0.6855 | 19 / 18 / 23 |
| S14: q4p_n100 minus q4p | +2.33 | +1.27 to +3.42 | 0.0001 | 17 / 41 / 2 |
| S15: f16p minus gold | +2.53 | +1.44 to +3.63 | 0.0001 | 11 / 36 / 13 |

Total run time 165 s.
