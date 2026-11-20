# Readout-repair experiment 2: results

Exploratory, development data only, designed after experiment 1 was seen. Protocol hash `1dbbefb0dd6e2716eedb3af2432a04d40f8387d42fe99948140e00a05ed87a55`.
Arms and tests: `PROTOCOL_REPAIR_EXP2.md`. Every number is computed from `out2/predictions.csv` (and `out/predictions.csv` for experiment 1 arms) by `analyze_ppr2.py`.

## 0. Integrity checks against experiment 1 (must be identical records)

* Protocol A: `REF` (experiment 2) against `REF` (experiment 1): 0 of 3000 records differ.
* Protocol A: `REFp` (experiment 2) against `POS_prefix_FP16` (experiment 1): 0 of 3000 records differ.
* Protocol A: `MATCHEDp` (experiment 2) against `POS_prefix_Q4` (experiment 1): 0 of 3000 records differ.
* Protocol A: `FROZENp` (experiment 2) against `POSprefix_FROZEN_Q4` (experiment 1): 0 of 3000 records differ.
* Protocol A: `C1p` (experiment 2) against `POSprefix_C1_Q4` (experiment 1): 0 of 3000 records differ.
* Protocol A: `Q8_MATCHEDp` (experiment 2) against `POS_prefix_Q8` (experiment 1): 0 of 3000 records differ.
* Protocol B: `REF` (experiment 2) against `REF` (experiment 1): 0 of 400 records differ.
* Protocol B: `REFp` (experiment 2) against `POS_prefix_FP16` (experiment 1): 0 of 400 records differ.
* Protocol B: `MATCHEDp` (experiment 2) against `POS_prefix_Q4` (experiment 1): 0 of 400 records differ.
* Protocol B: `FROZENp` (experiment 2) against `POSprefix_FROZEN_Q4` (experiment 1): 0 of 400 records differ.
* Protocol B: `C1p` (experiment 2) against `POSprefix_C1_Q4` (experiment 1): 0 of 400 records differ.
* Protocol B: `Q8_MATCHEDp` (experiment 2) against `POS_prefix_Q8` (experiment 1): 0 of 400 records differ.
* Few labels: the labelled reports are drawn with the same seeded call as in experiment 1; experiment 1 has no `prefix` arm at few labels, so there is nothing to compare record by record.

**Integrity: PASS.**

## 1. Protocol A: same wording style (1,000 style-A reports, 5 folds by template, 3 repeats)

Rates are pooled over the 3 repeats (3,000 report decisions per arm).

### 1.1 Accuracy (suffix p = `prefix` position; the last seven rows are the `end` position, from experiment 1 except Q8_C2)

| Arm | Whole record right | Action right | Sensor right (gold CREATE/UPDATE) | Priority right (gold CREATE/UPDATE) | Error by gold action: CREATE / UPDATE / CLOSE / NO_ACTION |
|---|---|---|---|---|---|
| REFp | 81.8% | 99.4% | 75.8% | 79.9% | 26 / 57 / 2 / 0% |
| FROZENp | 68.7% | 91.4% | 58.3% | 46.0% | 62 / 76 / 4 / 0% |
| C1p | 77.3% | 97.6% | 69.6% | 73.3% | 41 / 57 / 6 / 0% |
| C2p | 80.1% | 99.1% | 74.0% | 79.3% | 33 / 54 / 4 / 0% |
| C3p | 79.6% | 99.2% | 73.1% | 79.7% | 32 / 59 / 3 / 0% |
| MATCHEDp | 79.0% | 99.3% | 72.3% | 78.3% | 36 / 57 / 3 / 0% |
| Q8_FROZENp | 81.8% | 99.3% | 75.6% | 79.9% | 26 / 58 / 2 / 0% |
| Q8_C1p | 81.7% | 99.4% | 75.6% | 80.2% | 26 / 57 / 2 / 0% |
| Q8_C2p | 81.7% | 99.4% | 75.6% | 80.1% | 26 / 58 / 2 / 0% |
| Q8_MATCHEDp | 81.6% | 99.4% | 75.9% | 79.2% | 27 / 57 / 2 / 0% |
| REF | 78.9% | 99.4% | 77.9% | 71.9% | 36 / 58 / 3 / 0% |
| MATCHED | 72.6% | 96.0% | 69.0% | 68.2% | 47 / 62 / 12 / 3% |
| C2 | 75.7% | 97.9% | 73.6% | 69.5% | 42 / 60 / 8 / 2% |
| Q8_FROZEN | 73.7% | 96.1% | 71.6% | 71.9% | 41 / 61 / 23 / 1% |
| Q8_C1 | 78.1% | 99.2% | 75.4% | 72.1% | 36 / 61 / 4 / 0% |
| Q8_C2 | 77.9% | 99.4% | 76.0% | 71.2% | 37 / 62 / 3 / 0% |
| Q8_MATCHED | 77.7% | 99.0% | 75.7% | 71.8% | 37 / 62 / 5 / 0% |

### 1.2 Repair of the frozen cohort at `prefix` (unmodified Q4 = REFp heads on raw Q4 vectors)

Per repeat: N = 1000 reports. Reference right and unmodified Q right: 659. **Harmful (reference right, Q wrong): 159 = 15.9%.** Beneficial (reference wrong, Q right): 28 = 2.8%. Both wrong: 154.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| C1p | 56.1% (267/476) | 3.0% (62/2061) | 47.7% (321/673) | +8.6 |
| C2p | 80.5% (383/476) | 4.3% (88/2061) | 52.5% (430/819) | +11.4 |
| C3p | 78.8% (375/476) | 4.6% (95/2061) | 49.8% (422/847) | +10.9 |
| MATCHEDp | 73.5% (350/476) | 4.9% (102/2061) | 48.6% (412/848) | +10.3 |

### 1.3 Repair of the matched cohort at `prefix` (unmodified Q4 = heads refitted on Q4 vectors)

Per repeat: N = 1000 reports. Reference right and unmodified Q right: 761. **Harmful (reference right, Q wrong): 57 = 5.7%.** Beneficial (reference wrong, Q right): 30 = 3.0%. Both wrong: 153.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| C1p | 43.3% (74/171) | 8.3% (196/2371) | 28.9% (145/501) | -1.7 |
| C2p | 52.0% (89/171) | 3.9% (92/2371) | 41.9% (124/296) | +1.1 |
| C3p | 45.0% (77/171) | 3.6% (85/2371) | 37.1% (102/275) | +0.6 |

### 1.4 Control at Q8, `prefix`: frozen cohort (unmodified Q8 = REFp heads on raw Q8 vectors)

Per repeat: N = 1000 reports. Reference right and unmodified Q right: 805. **Harmful (reference right, Q wrong): 13 = 1.3%.** Beneficial (reference wrong, Q right): 13 = 1.3%. Both wrong: 169.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| Q8_C1p | 52.6% (20/38) | 1.5% (37/2455) | 33.0% (33/100) | -0.1 |
| Q8_C2p | 50.0% (19/38) | 1.3% (32/2455) | 30.0% (27/90) | -0.2 |
| Q8_MATCHEDp | 52.6% (20/38) | 1.7% (42/2455) | 29.8% (34/114) | -0.3 |

### 1.5 Control at Q8, `end`: frozen cohort

Per repeat: N = 1000 reports. Reference right and unmodified Q right: 702. **Harmful (reference right, Q wrong): 88 = 8.8%.** Beneficial (reference wrong, Q right): 36 = 3.6%. Both wrong: 175.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| Q8_C1 | 76.4% (201/263) | 4.5% (100/2212) | 53.0% (230/434) | +4.3 |
| Q8_C2 | 77.6% (204/263) | 4.7% (105/2212) | 50.9% (230/452) | +4.2 |
| Q8_MATCHED | 78.3% (206/263) | 5.6% (123/2212) | 49.6% (243/490) | +4.0 |

### 1.6 Paired differences

| Comparison | Difference in whole-record accuracy (points, 95% template-bootstrap interval) |
|---|---|
| C2p minus MATCHEDp | +1.1 (-0.3 to +2.5) |
| C2p minus REFp | -1.7 (-3.1 to -0.5) |
| C2p minus C1p | +2.8 (+1.2 to +4.7) |
| C3p minus MATCHEDp | +0.6 (-0.6 to +1.8) |
| C3p minus REFp | -2.2 (-3.5 to -1.0) |
| C1p minus MATCHEDp | -1.7 (-3.6 to -0.0) |
| MATCHEDp minus REFp | -2.7 (-4.3 to -1.4) |
| FROZENp minus REFp | -13.1 (-17.5 to -9.9) |
| C2p minus REF | +1.2 (-1.1 to +3.5) |
| C2p minus MATCHED | +7.5 (+4.8 to +10.6) |
| C2p minus C2 | +4.4 (+2.1 to +6.9) |
| Q8_C2p minus Q8_MATCHEDp | +0.1 (-0.4 to +0.6) |
| Q8_C2p minus REFp | -0.1 (-0.7 to +0.5) |
| Q8_MATCHEDp minus REFp | -0.2 (-0.9 to +0.5) |
| Q8_FROZENp minus REFp | +0.1 (-0.6 to +0.7) |
| Q8_C2 minus Q8_MATCHED | +0.2 (-0.7 to +1.1) |
| Q8_C2 minus REF | -1.0 (-2.1 to -0.1) |
| Q8_C2 minus Q8_C1 | -0.2 (-0.8 to +0.5) |

### 1.7 How many unlabelled pairs does the map need? (`prefix`, Q4; REFp heads use all labels)

| Pairs in the bank | Recentring (C1p) | Affine map (C2p) | C2p minus MATCHEDp | C2p minus REFp |
|---|---|---|---|---|
| 50 | 76.8% | 77.8% | -1.3 (-2.8 to +0.0) | -4.0 (-5.9 to -2.5) |
| 100 | 77.1% | 78.7% | -0.4 (-1.7 to +0.8) | -3.1 (-4.8 to -1.7) |
| 200 | 77.3% | 78.9% | -0.2 (-1.6 to +1.1) | -2.9 (-4.6 to -1.5) |
| 400 | 77.5% | 79.7% | +0.7 (-0.7 to +2.1) | -2.0 (-3.6 to -0.7) |
| about 800 (whole training fold) | 77.3% | 80.1% | +1.1 (-0.3 to +2.5) | -1.7 (-3.1 to -0.5) |

## 2. Few labels at `prefix` (Protocol A folds; pair bank = whole training fold, no labels)

| Labels | REFp (FP16) | FROZENp | C1p | C2p | C3p | MATCHEDp | C2p minus MATCHEDp | C3p minus MATCHEDp | C2p minus REFp |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 63.8% | 60.1% | 62.2% | 63.9% | 64.0% | 62.4% | +1.5 (+0.5 to +2.5) | +1.6 (+0.6 to +2.7) | +0.1 (-1.2 to +1.7) |
| 300 | 74.4% | 67.1% | 71.7% | 73.6% | 74.2% | 73.5% | +0.1 (-0.9 to +1.1) | +0.7 (-0.3 to +1.8) | -0.9 (-1.9 to +0.1) |
| all | 81.8% | 68.7% | 77.3% | 80.1% | 79.6% | 79.0% | +1.1 (-0.3 to +2.5) | +0.6 (-0.6 to +1.8) | -1.7 (-3.1 to -0.5) |

## 3. Protocol B: new wording (fit on all 1,000 style-A reports, test on the 400 style-B reports)

Style B was seen many times before, so this is exploratory. One run, no repeats.

### 3.1 Accuracy

| Arm | Whole record right | Action right | Sensor right (gold CREATE/UPDATE) | Priority right (gold CREATE/UPDATE) | Error by gold action: CREATE / UPDATE / CLOSE / NO_ACTION |
|---|---|---|---|---|---|
| REFp | 71.8% | 94.5% | 66.7% | 64.4% | 46 / 71 / 17 / 0% |
| FROZENp | 60.0% | 79.2% | 45.6% | 22.2% | 79 / 91 / 13 / 0% |
| C1p | 65.0% | 90.8% | 58.9% | 48.3% | 61 / 80 / 23 / 1% |
| C2p | 71.2% | 94.2% | 62.2% | 65.6% | 45 / 78 / 10 / 1% |
| C3p | 73.2% | 94.5% | 65.0% | 70.0% | 42 / 68 / 15 / 1% |
| MATCHEDp | 72.8% | 94.5% | 63.9% | 70.0% | 46 / 65 / 15 / 1% |
| Q8_FROZENp | 73.0% | 93.8% | 68.3% | 65.0% | 41 / 71 / 17 / 0% |
| Q8_C1p | 71.5% | 94.2% | 66.1% | 63.3% | 43 / 76 / 17 / 0% |
| Q8_C2p | 71.5% | 94.0% | 66.1% | 62.2% | 43 / 76 / 17 / 0% |
| Q8_MATCHEDp | 72.2% | 94.2% | 66.1% | 65.0% | 42 / 74 / 17 / 0% |
| REF | 72.0% | 91.8% | 60.6% | 65.0% | 50 / 62 / 17 / 1% |
| MATCHED | 67.0% | 89.2% | 56.1% | 64.4% | 56 / 66 / 32 / 3% |
| C2 | 68.2% | 90.2% | 55.0% | 64.4% | 56 / 65 / 28 / 1% |
| Q8_C2 | 70.2% | 91.5% | 62.2% | 62.2% | 54 / 64 / 20 / 1% |
| Q8_MATCHED | 70.2% | 92.2% | 57.2% | 62.8% | 55 / 68 / 15 / 1% |

### 3.2 Repair of the frozen cohort at `prefix`

Per repeat: N = 400 reports. Reference right and unmodified Q right: 232. **Harmful (reference right, Q wrong): 55 = 13.8%.** Beneficial (reference wrong, Q right): 8 = 2.0%. Both wrong: 105.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| C1p | 47.3% (26/55) | 4.6% (11/240) | 29.5% (31/105) | +5.0 |
| C2p | 76.4% (42/55) | 2.9% (7/240) | 38.8% (52/134) | +11.2 |
| C3p | 78.2% (43/55) | 4.2% (10/240) | 43.8% (63/144) | +13.2 |
| MATCHEDp | 76.4% (42/55) | 5.8% (14/240) | 43.6% (65/149) | +12.8 |

### 3.3 Repair of the matched cohort at `prefix`

Per repeat: N = 400 reports. Reference right and unmodified Q right: 264. **Harmful (reference right, Q wrong): 23 = 5.8%.** Beneficial (reference wrong, Q right): 27 = 6.8%. Both wrong: 86.

| Method | Repair rate (share of harmful cases now right) | New errors (share of Q-right cases now wrong) | Correction precision (changed records that are right) | Net change in right records per 100 reports |
|---|---|---|---|---|
| C1p | 39.1% (9/23) | 15.1% (44/291) | 13.1% (13/99) | -7.8 |
| C2p | 52.2% (12/23) | 7.2% (21/291) | 25.9% (15/58) | -1.5 |
| C3p | 47.8% (11/23) | 4.1% (12/291) | 36.8% (14/38) | +0.5 |

### 3.4 Paired differences

| Comparison | Difference in whole-record accuracy (points, 95% template-bootstrap interval) |
|---|---|
| C2p minus MATCHEDp | -1.5 (-4.5 to +1.6) |
| C2p minus REFp | -0.5 (-3.4 to +2.4) |
| C2p minus C1p | +6.2 (+3.0 to +10.1) |
| C3p minus MATCHEDp | +0.5 (-2.3 to +3.2) |
| C3p minus REFp | +1.5 (-2.1 to +5.0) |
| MATCHEDp minus REFp | +1.0 (-2.6 to +4.5) |
| C2p minus REF | -0.8 (-5.3 to +3.8) |
| C2p minus MATCHED | +4.2 (-0.2 to +9.0) |
| Q8_C2p minus Q8_MATCHEDp | -0.8 (-1.9 to +0.3) |
| Q8_C2p minus REFp | -0.2 (-2.0 to +1.3) |
| Q8_C2 minus Q8_MATCHED | +0.0 (-3.1 to +3.0) |
| Q8_C2 minus REF | -1.8 (-4.2 to +0.5) |

### 3.5 Bank-size curve on style B (`prefix`, Q4)

| Pairs in the bank | Recentring (C1p) | Affine map (C2p) |
|---|---|---|
| 50 | 65.0% | 70.0% |
| 100 | 64.0% | 69.5% |
| 200 | 64.8% | 68.8% |
| 400 | 65.2% | 71.2% |
| 1,000 (all style A) | 65.0% | 71.2% |

### 3.6 Downstream check on style B: real incidents left unverified in the legacy single-record replay

V1 greedy allocator, 3 UAVs, 600 s horizon, one report per mission. This replay only sees action errors (audit 03).

| Arm | Unverified of real incidents | Share |
|---|---|---|
| REFp | 9 of 752 | 1.2% |
| FROZENp | 71 of 752 | 9.4% |
| C1p | 17 of 752 | 2.3% |
| C2p | 10 of 752 | 1.3% |
| C3p | 8 of 752 | 1.1% |
| MATCHEDp | 8 of 752 | 1.1% |
| Q8_C2p | 10 of 752 | 1.3% |
| Q8_MATCHEDp | 9 of 752 | 1.2% |
| REF | 18 of 752 | 2.4% |
| MATCHED | 15 of 752 | 2.0% |
| C2 | 15 of 752 | 2.0% |

## 4. Tests fixed in the protocol

| Test | Numbers (Protocol A; Protocol B beside it, descriptive) | Label |
|---|---|---|
| E2-T1 transfer beyond retraining at `prefix` | C2p minus MATCHEDp +1.1 (-0.3 to +2.5); style B -1.5 (-4.5 to +1.6) | **NOT SHOWN** |
| E2-T2 repair to the reference level | C2p minus REFp -1.7 (-3.1 to -0.5); style B -0.5 (-3.4 to +2.4) | **NOT SHOWN** |
| E2-T3 few labels (100 labels) | C2p minus MATCHEDp +1.5 (+0.5 to +2.5) | **SUPPORTED** |

## 5. Chosen settings (Protocol A, all labels, 15 folds)

* C_REFp: {'action': {'3': 12, '0.3': 2, '0.03': 1}, 'sensor': {'0.03': 2, '0.003': 13}, 'prio': {'0.03': 10, '0.003': 5}}
* C_MATCHEDp: {'action': {'3': 13, '0.3': 2}, 'sensor': {'0.003': 15}, 'prio': {'0.003': 7, '0.03': 8}}
* C_C3p: {'action': {'3': 15}, 'sensor': {'3': 13, '0.3': 2}, 'prio': {'3': 13, '0.3': 2}}
* Affine map, Q4 `prefix`: lambda multiplier chosen {'0.1': 15}. Held-out pair reconstruction error of the chosen map / recentring only: mean 0.268 (min 0.259, max 0.277).
* Affine map, Q8 `prefix`: lambda multiplier chosen {'1.0': 15}. Held-out pair reconstruction error of the chosen map / recentring only: mean 0.842 (min 0.834, max 0.849).
* Affine map, Q8 `end`: lambda multiplier chosen {'0.1': 15}. Held-out pair reconstruction error of the chosen map / recentring only: mean 0.849 (min 0.845, max 0.855).
* Run time: 1250 s of fold time in total.
