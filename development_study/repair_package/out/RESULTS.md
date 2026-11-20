# Readout-repair feasibility experiment: results

Exploratory, development data only (all 1,400 pilot reports have been used before). Protocol hash `289105a1aacce6a3f3c39d1a991d92e5619904ebce3606a1b6d430d6baf4f8af`.
Arms and tests: `PROTOCOL_REPAIR_FEASIBILITY.md`. Every number is computed from `predictions.csv` by `analyze_ppr.py`.

## 1. Protocol A: same wording style (1,000 style-A reports, 5 folds by template, 3 repeats)

Rates are pooled over the 3 repeats (3,000 report decisions per arm).

### 1.1 Accuracy on Q4 vectors (REF is on FP16 vectors)

| Arm | Whole record right | Action right | Sensor right (gold CREATE/UPDATE) | Priority right (gold CREATE/UPDATE) | Error by gold action: CREATE / UPDATE / CLOSE / NO_ACTION |
|---|---|---|---|---|---|
| REF | 78.9% | 99.4% | 77.9% | 71.9% | 36 / 58 / 3 / 0% |
| FROZEN | 49.2% | 68.4% | 21.0% | 24.7% | 97 / 81 / 12 / 21% |
| C1 | 69.7% | 94.5% | 58.8% | 65.0% | 57 / 64 / 16 / 2% |
| C2 | 75.7% | 97.9% | 73.6% | 69.5% | 42 / 60 / 8 / 2% |
| C3 | 74.4% | 96.6% | 72.4% | 68.7% | 42 / 62 / 11 / 3% |
| C4 | 73.4% | 95.0% | 72.1% | 70.4% | 41 / 59 / 15 / 6% |
| C5 | 74.1% | 96.8% | 69.3% | 70.1% | 43 / 64 / 9 / 2% |
| SHARED | 75.2% | 97.7% | 71.9% | 68.7% | 43 / 62 / 6 / 2% |
| MATCHED | 72.6% | 96.0% | 69.0% | 68.2% | 47 / 62 / 12 / 3% |
| ANCH | 72.9% | 96.5% | 65.9% | 67.7% | 48 / 66 / 10 / 1% |
| ANCH2 | 76.7% | 98.2% | 73.9% | 69.3% | 41 / 59 / 5 / 1% |
| TFIDF | 98.1% | 100.0% | 98.9% | 96.9% | 7 / 0 / 0 / 0% |
| RULES | 97.0% | 97.0% | 100.0% | 100.0% | 0 / 0 / 20 / 0% |
| GEN_FP16 | 30.3% | 59.1% | 48.7% | 49.1% | 93 / 88 / 81 / 42% |
| GEN_Q8 | 31.7% | 60.5% | 48.2% | 47.6% | 94 / 88 / 81 / 38% |
| GEN_Q4 | 32.1% | 60.1% | 48.7% | 41.8% | 93 / 92 / 100 / 29% |

### 1.2 Repair of the frozen cohort (unmodified Q4 = FP16 heads on raw Q4 vectors)

Per repeat: N = 1000 reports. Reference right and unmodified Q4 right: 469. **Harmful (reference right, Q4 wrong): 321 = 32.1%.** Beneficial (reference wrong, Q4 right): 23 = 2.3%. Both wrong: 188.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q4-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| C1 | 65.6% (631/962) | 7.0% (103/1475) | 50.6% (720/1424) | +20.6 |
| C2 | 84.3% (811/962) | 6.0% (89/1475) | 58.2% (886/1523) | +26.6 |
| C3 | 81.4% (783/962) | 7.1% (104/1475) | 56.1% (862/1537) | +25.3 |
| C4 | 79.2% (762/962) | 9.4% (139/1475) | 55.3% (866/1565) | +24.2 |
| C5 | 78.6% (756/962) | 7.1% (105/1475) | 56.1% (854/1521) | +25.0 |
| SHARED | 79.9% (769/962) | 5.5% (81/1475) | 57.1% (861/1509) | +26.0 |
| MATCHED | 74.7% (719/962) | 7.8% (115/1475) | 52.7% (818/1553) | +23.4 |
| ANCH | 74.5% (717/962) | 6.5% (96/1475) | 54.2% (807/1490) | +23.7 |
| ANCH2 | 84.9% (817/962) | 5.2% (77/1475) | 60.1% (904/1505) | +27.6 |

### 1.3 Repair of the matched cohort (unmodified Q4 = heads refitted on Q4 vectors)

Per repeat: N = 1000 reports. Reference right and unmodified Q4 right: 687. **Harmful (reference right, Q4 wrong): 102 = 10.2%.** Beneficial (reference wrong, Q4 right): 39 = 3.9%. Both wrong: 172.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q4-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| C1 | 44.0% (135/307) | 13.1% (286/2178) | 25.9% (200/772) | -2.9 |
| C2 | 57.0% (175/307) | 5.0% (109/2178) | 42.7% (203/475) | +3.1 |
| C3 | 41.0% (126/307) | 4.6% (100/2178) | 37.6% (155/412) | +1.8 |
| C4 | 45.3% (139/307) | 7.5% (163/2178) | 36.2% (187/516) | +0.8 |
| C5 | 47.6% (146/307) | 7.3% (160/2178) | 37.3% (206/552) | +1.5 |
| SHARED | 40.4% (124/307) | 3.4% (74/2178) | 46.6% (151/324) | +2.6 |
| ANCH | 44.3% (136/307) | 8.0% (175/2178) | 32.9% (183/556) | +0.3 |
| ANCH2 | 62.9% (193/307) | 5.1% (110/2178) | 46.2% (234/506) | +4.1 |

### 1.4 Paired differences in whole-record accuracy (percentage points, 95% template-bootstrap interval)

| Comparison | Difference |
|---|---|
| C2 minus C1 | +6.0 (+3.8 to +8.6) |
| C2 minus MATCHED | +3.1 (+1.4 to +5.0) |
| C1 minus MATCHED | -2.9 (-5.6 to -0.5) |
| ANCH minus MATCHED | +0.3 (-1.8 to +2.2) |
| ANCH2 minus MATCHED | +4.1 (+2.2 to +6.2) |
| C3 minus MATCHED | +1.8 (+0.5 to +3.3) |
| C4 minus MATCHED | +0.8 (-0.9 to +2.7) |
| C5 minus MATCHED | +1.5 (-0.1 to +3.2) |
| SHARED minus MATCHED | +2.6 (+1.1 to +4.1) |
| MATCHED minus REF | -6.3 (-8.9 to -4.0) |
| ANCH minus REF | -6.1 (-8.4 to -4.0) |
| FROZEN minus REF | -29.8 (-39.6 to -21.8) |
| C1 minus REF | -9.2 (-12.4 to -6.6) |
| Q8_MATCHED minus REF | -1.2 (-2.4 to -0.2) |
| Q8_FROZEN minus REF | -5.2 (-8.0 to -2.9) |
| Q8_C1 minus REF | -0.9 (-1.9 to +0.1) |
| TFIDF minus MATCHED | +25.5 (+20.1 to +32.9) |
| GEN_Q4 minus GEN_FP16 | +1.8 (-2.2 to +5.4) |

### 1.5 Readout position (matched heads; REF, Q8_MATCHED and MATCHED read at `end`)

| Arm | Whole record right | Action right | Sensor right (gold CREATE/UPDATE) | Priority right (gold CREATE/UPDATE) | Error by gold action: CREATE / UPDATE / CLOSE / NO_ACTION |
|---|---|---|---|---|---|
| REF | 78.9% | 99.4% | 77.9% | 71.9% | 36 / 58 / 3 / 0% |
| POS_prefix_FP16 | 81.8% | 99.4% | 75.8% | 79.9% | 26 / 57 / 2 / 0% |
| POS_both_FP16 | 81.4% | 99.6% | 78.2% | 77.5% | 28 / 56 / 3 / 0% |
| Q8_MATCHED | 77.7% | 99.0% | 75.7% | 71.8% | 37 / 62 / 5 / 0% |
| POS_prefix_Q8 | 81.6% | 99.4% | 75.9% | 79.2% | 27 / 57 / 2 / 0% |
| POS_both_Q8 | 80.6% | 99.3% | 78.3% | 76.4% | 30 / 57 / 4 / 0% |
| MATCHED | 72.6% | 96.0% | 69.0% | 68.2% | 47 / 62 / 12 / 3% |
| POS_prefix_Q4 | 79.0% | 99.3% | 72.3% | 78.3% | 36 / 57 / 3 / 0% |
| POS_both_Q4 | 77.9% | 98.7% | 73.2% | 75.5% | 37 / 59 / 4 / 1% |
| POSprefix_FROZEN_Q4 | 68.7% | 91.4% | 58.3% | 46.0% | 62 / 76 / 4 / 0% |
| POSprefix_C1_Q4 | 77.3% | 97.6% | 69.6% | 73.3% | 41 / 57 / 6 / 0% |

| Comparison | Difference in whole-record accuracy |
|---|---|
| POS_prefix_Q4 minus MATCHED | +6.4 (+3.9 to +9.4) |
| POS_both_Q4 minus MATCHED | +5.3 (+3.2 to +7.5) |
| POS_prefix_FP16 minus REF | +2.8 (+0.7 to +5.3) |
| POS_both_FP16 minus REF | +2.4 (+1.0 to +4.0) |
| POS_prefix_Q8 minus Q8_MATCHED | +3.8 (+1.5 to +6.6) |
| POS_both_Q8 minus Q8_MATCHED | +2.9 (+1.4 to +4.6) |
| POS_prefix_Q4 minus POS_prefix_FP16 | -2.7 (-4.3 to -1.4) |
| POS_both_Q4 minus POS_both_FP16 | -3.5 (-5.1 to -1.9) |
| POS_both_Q4 minus REF | -1.0 (-2.9 to +0.8) |

## 2. Few labels (Protocol A folds; pair bank = whole training fold, no labels)

| Labels | REF (FP16) | FROZEN | C1 | C2 | C3 | C4 | MATCHED | ANCH | TFIDF | ANCH minus MATCHED | C3 minus MATCHED | C2 minus MATCHED |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 58.5% | 47.6% | 54.4% | 58.4% | 58.7% | 57.9% | 52.6% | 55.3% | 68.6% | +2.7 (+1.3 to +4.4) | +6.1 (+3.9 to +8.5) | +5.9 (+4.0 to +7.9) |
| 300 | 70.3% | 49.4% | 63.6% | 68.6% | 68.4% | 67.6% | 63.2% | 65.1% | 87.4% | +1.9 (+0.3 to +3.7) | +5.2 (+3.4 to +7.3) | +5.5 (+3.6 to +7.7) |
| all | 78.9% | 49.2% | 69.7% | 75.7% | 74.4% | 73.4% | 72.6% | 72.9% | 98.1% | +0.3 (-1.8 to +2.2) | +1.8 (+0.5 to +3.3) | +3.1 (+1.4 to +5.0) |

## 3. Protocol B: new wording (fit on all 1,000 style-A reports, test on the 400 style-B reports)

Style B was seen many times before with other methods, so this is exploratory. One run, no repeats.

### 3.1 Accuracy

| Arm | Whole record right | Action right | Sensor right (gold CREATE/UPDATE) | Priority right (gold CREATE/UPDATE) | Error by gold action: CREATE / UPDATE / CLOSE / NO_ACTION |
|---|---|---|---|---|---|
| REF | 72.0% | 91.8% | 60.6% | 65.0% | 50 / 62 / 17 / 1% |
| FROZEN | 43.8% | 61.5% | 20.0% | 13.3% | 95 / 90 / 35 / 23% |
| C1 | 60.8% | 85.0% | 45.6% | 58.3% | 58 / 81 / 48 / 3% |
| C2 | 68.2% | 90.2% | 55.0% | 64.4% | 56 / 65 / 28 / 1% |
| C3 | 70.0% | 90.2% | 56.1% | 65.6% | 54 / 57 / 28 / 2% |
| C4 | 69.5% | 91.2% | 56.1% | 64.4% | 53 / 66 / 25 / 1% |
| C5 | 67.5% | 91.2% | 52.8% | 68.9% | 55 / 69 / 30 / 1% |
| SHARED | 68.0% | 90.5% | 56.1% | 66.7% | 56 / 64 / 30 / 2% |
| MATCHED | 67.0% | 89.2% | 56.1% | 64.4% | 56 / 66 / 32 / 3% |
| ANCH | 63.0% | 87.2% | 48.3% | 61.1% | 64 / 74 / 38 / 1% |
| ANCH2 | 67.2% | 89.0% | 49.4% | 62.2% | 60 / 69 / 23 / 1% |
| Q8_FROZEN | 69.2% | 89.0% | 68.3% | 68.9% | 49 / 52 / 52 / 1% |
| Q8_C1 | 68.8% | 90.8% | 60.0% | 61.7% | 57 / 68 / 22 / 1% |
| Q8_MATCHED | 70.2% | 92.2% | 57.2% | 62.8% | 55 / 68 / 15 / 1% |
| POS_prefix_FP16 | 71.8% | 94.5% | 66.7% | 64.4% | 46 / 71 / 17 / 0% |
| POS_both_FP16 | 76.0% | 94.8% | 71.1% | 68.3% | 39 / 61 / 12 / 1% |
| POS_prefix_Q4 | 72.8% | 94.5% | 63.9% | 70.0% | 46 / 65 / 15 / 1% |
| POS_both_Q4 | 72.8% | 94.0% | 70.6% | 68.3% | 45 / 61 / 22 / 1% |
| TFIDF | 53.5% | 76.2% | 52.8% | 51.7% | 82 / 49 / 55 / 20% |
| RULES | 50.7% | 55.0% | 25.6% | 26.7% | 94 / 57 / 88 / 3% |
| GEN_FP16 | 27.3% | 58.8% | 48.3% | 45.6% | 90 / 94 / 88 / 46% |
| GEN_Q8 | 28.2% | 60.0% | 47.2% | 47.8% | 90 / 94 / 87 / 44% |
| GEN_Q4 | 32.8% | 62.5% | 46.1% | 42.8% | 92 / 90 / 98 / 29% |

### 3.2 Repair of the frozen cohort

Per repeat: N = 400 reports. Reference right and unmodified Q4 right: 168. **Harmful (reference right, Q4 wrong): 120 = 30.0%.** Beneficial (reference wrong, Q4 right): 7 = 1.8%. Both wrong: 105.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q4-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| C1 | 56.7% (68/120) | 8.0% (14/175) | 43.6% (82/188) | +17.0 |
| C2 | 80.8% (97/120) | 4.6% (8/175) | 52.7% (106/201) | +24.5 |
| C3 | 79.2% (95/120) | 4.0% (7/175) | 53.3% (112/210) | +26.2 |
| C4 | 74.2% (89/120) | 4.0% (7/175) | 52.9% (110/208) | +25.8 |
| C5 | 71.7% (86/120) | 4.6% (8/175) | 50.0% (103/206) | +23.8 |
| SHARED | 74.2% (89/120) | 6.3% (11/175) | 50.7% (108/213) | +24.2 |
| MATCHED | 75.0% (90/120) | 7.4% (13/175) | 49.5% (106/214) | +23.2 |
| ANCH | 61.7% (74/120) | 6.3% (11/175) | 42.9% (88/205) | +19.2 |
| ANCH2 | 74.2% (89/120) | 4.0% (7/175) | 51.8% (101/195) | +23.5 |

### 3.3 Repair of the matched cohort

Per repeat: N = 400 reports. Reference right and unmodified Q4 right: 251. **Harmful (reference right, Q4 wrong): 37 = 9.2%.** Beneficial (reference wrong, Q4 right): 17 = 4.2%. Both wrong: 95.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q4-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| C1 | 32.4% (12/37) | 17.5% (47/268) | 17.7% (22/124) | -6.2 |
| C2 | 54.1% (20/37) | 7.8% (21/268) | 32.1% (26/81) | +1.2 |
| C3 | 29.7% (11/37) | 3.4% (9/268) | 33.3% (21/63) | +3.0 |
| C4 | 43.2% (16/37) | 7.8% (21/268) | 37.3% (31/83) | +2.5 |
| C5 | 43.2% (16/37) | 9.3% (25/268) | 30.0% (27/90) | +0.5 |
| SHARED | 24.3% (9/37) | 4.5% (12/268) | 28.6% (16/56) | +1.0 |
| ANCH | 27.0% (10/37) | 11.6% (31/268) | 17.6% (15/85) | -4.0 |
| ANCH2 | 43.2% (16/37) | 9.0% (24/268) | 29.1% (25/86) | +0.2 |

### 3.4 Paired differences in whole-record accuracy (percentage points, 95% template-bootstrap interval)

| Comparison | Difference |
|---|---|
| C2 minus C1 | +7.5 (+3.3 to +12.0) |
| C2 minus MATCHED | +1.2 (-2.0 to +4.5) |
| ANCH minus MATCHED | -4.0 (-7.6 to -0.9) |
| ANCH2 minus MATCHED | +0.2 (-3.4 to +3.7) |
| C3 minus MATCHED | +3.0 (+0.7 to +5.7) |
| C4 minus MATCHED | +2.5 (-1.0 to +6.3) |
| C5 minus MATCHED | +0.5 (-2.8 to +3.8) |
| SHARED minus MATCHED | +1.0 (-1.2 to +3.3) |
| MATCHED minus REF | -5.0 (-9.2 to -1.4) |
| ANCH minus REF | -9.0 (-13.9 to -4.5) |
| POS_prefix_Q4 minus MATCHED | +5.8 (+1.5 to +10.2) |
| POS_both_Q4 minus MATCHED | +5.8 (+2.0 to +10.3) |
| POS_both_FP16 minus REF | +4.0 (+0.0 to +8.7) |
| POS_both_Q4 minus POS_both_FP16 | -3.2 (-7.2 to +0.3) |
| TFIDF minus MATCHED | -13.5 (-24.9 to -3.1) |

### 3.5 Downstream check on style B: real incidents left unverified in the legacy single-record replay

V1 greedy allocator, 3 UAVs, 600 s horizon, one report per mission. This replay only sees action errors (audit 03).

| Arm | Unverified of real incidents | Share |
|---|---|---|
| REF | 18 of 752 | 2.4% |
| FROZEN | 126 of 752 | 16.8% |
| C1 | 21 of 752 | 2.8% |
| C2 | 15 of 752 | 2.0% |
| C3 | 14 of 752 | 1.9% |
| C4 | 13 of 752 | 1.7% |
| C5 | 13 of 752 | 1.7% |
| SHARED | 14 of 752 | 1.9% |
| MATCHED | 15 of 752 | 2.0% |
| ANCH | 21 of 752 | 2.8% |
| ANCH2 | 22 of 752 | 2.9% |
| POS_prefix_Q4 | 8 of 752 | 1.1% |
| POS_both_Q4 | 6 of 752 | 0.8% |
| POS_both_FP16 | 10 of 752 | 1.3% |
| TFIDF | 30 of 752 | 4.0% |
| GEN_FP16 | 83 of 752 | 11.0% |
| GEN_Q4 | 69 of 752 | 9.2% |

## 4. Tests fixed in the protocol

| Test | Numbers | Label |
|---|---|---|
| T1 label-free transfer (C2) | C2 minus C1 +6.0 (+3.8 to +8.6); C2 minus MATCHED +3.1 (+1.4 to +5.0) | **SUPPORTED** |
| T2 repair beyond retraining (ANCH) | Protocol A: ANCH minus MATCHED +0.3 (-1.8 to +2.2); Protocol B: -4.0 (-7.6 to -0.9) | **NOT SHOWN** |
| T3 few labels (ANCH, 100 labels) | ANCH minus MATCHED +2.7 (+1.3 to +4.4) | **SUPPORTED** |
| T4 readout position, Q4 (general change, not a repair) | prefix minus end +6.4 (+3.9 to +9.4); both minus end +5.3 (+3.2 to +7.5); FP16 control: prefix +2.8 (+0.7 to +5.3), both +2.4 (+1.0 to +4.0) | prefix **SUPPORTED**, both **SUPPORTED** |

## 5. Chosen settings (Protocol A, all labels, 15 folds)

* C_REF: {'action': {'3': 12, '0.3': 3}, 'sensor': {'0.03': 13, '0.003': 2}, 'prio': {'0.003': 14, '0.03': 1}}
* C_MATCHED: {'action': {'0.3': 9, '3': 3, '0.03': 3}, 'sensor': {'0.003': 13, '0.03': 2}, 'prio': {'0.003': 15}}
* C_C3: {'action': {'3': 15}, 'sensor': {'3': 15}, 'prio': {'3': 14, '0.3': 1}}
* C_C4: {'action': {'3': 15}, 'sensor': {'3': 10, '0.3': 5}, 'prio': {'3': 11, '0.3': 4}}
* C_C5: {'action': {'0.3': 7, '3': 5, '0.03': 3}, 'sensor': {'0.003': 15}, 'prio': {'0.003': 15}}
* C_ANCH: {'action': {'0.0003': 10, '0.003': 2, '0.03': 3}, 'sensor': {'0.0003': 15}, 'prio': {'0.0003': 15}}
* C_ANCH2: {'action': {'0.0003': 15}, 'sensor': {'0.0003': 15}, 'prio': {'0.0003': 15}}
* C_SHARED: {'action': {'3': 11, '0.3': 4}, 'sensor': {'0.03': 13, '0.003': 2}, 'prio': {'0.003': 14, '0.03': 1}}
* C2 lambda multiplier chosen: {'0.1': 15}. Held-out pair reconstruction error of the chosen map / recentring only: mean 0.228 (min 0.222, max 0.232).
* Run time: 4413 s of fold time in total.
