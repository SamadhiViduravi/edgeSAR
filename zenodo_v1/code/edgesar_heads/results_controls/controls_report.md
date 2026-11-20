# EdgeSAR heads: exploratory controls

Made: 2026-11-12 15:06:42. Variant: `end`. Reports: 1400 (development style A: 1000, held-out style B: 400). Heads settings fingerprint: `d5e2e49d`.

**Status: EXPLORATORY.** These controls were decided on 12 Nov 2026, AFTER the held-out B results of attempt 1 were seen. Nothing here was tuned on B, and the settings are the same as in step 3. The goal is to find out WHAT moved the answers, not to show a win. Every per-report answer is in `predictions_end.csv`.

## 0. Does this run give the same numbers as attempt 1?

**MATCH.** 27 numbers checked: the same as attempt 1.

## 1. What was the 27.5%? (the audit)

The row is **Heads Q4 vs Heads FP16** (each head trained on its own vectors), held-out B, 400 reports.

| Question | Reports | Share |
|---|---|---|
| The task table would be different (the number used in attempt 1) | 110 | 27.5% |
| Any field of the decision is different | 110 | 27.5% |
| The ACTION is different | 37 | 9.2% |
| Same action, but sensor, priority, location or link is different | 73 | 18.2% |

Upper limit for action changes: two readers can disagree on the action in at most (errors of the FP16 heads) + (errors of the Q4 heads) = 31 + 44 = **75** reports (18.8%). The measured action changes are **37**, so the numbers are consistent.

Most common changes: CREATE: priority (20); CREATE: sensor (16); UPDATE: sensor (13); UPDATE: priority (12); CLOSE->UPDATE (12).

## 2. The controls: how much do the answers move? (table-changing disagreement with the FP16 pipeline, held-out B)

Read each row as: 'if the model is shrunk, in how many reports does the task table change?' The rows differ in WHAT is allowed to change.

| Comparison | Table changes (95% interval or spread over 20 heads) | Action changed | Right -> wrong | Wrong -> right | Both wrong, different |
|---|---|---|---|---|---|
| Separate heads: Q8 (vector AND head change) | 17.8% (14.3 to 21.8) | 18 (4.5%) | 24 | 14 | 33 |
| Separate heads: Q4 (vector AND head change) | 27.5% (23.4 to 32.1) | 37 (9.2%) | 41 | 24 | 45 |
| Fixed FP16 head: Q8 (only the vector changes) | 28.2% (24.1 to 32.9) | 58 (14.5%) | 48 | 28 | 37 |
| Fixed FP16 head: Q4 (only the vector changes) | 47.2% (42.4 to 52.1) | 142 (35.5%) | 100 | 7 | 83 |
| Fixed FP16 head, offset removed: Q8 | 15.0% (11.8 to 18.8) | 18 (4.5%) | 20 | 15 | 25 |
| Fixed FP16 head, offset removed: Q4 | 34.8% (30.2 to 39.5) | 56 (14.0%) | 71 | 19 | 51 |
| Shared head (one head, all precisions): Q8 | 10.2% (7.6 to 13.6) | 13 (3.2%) | 12 | 15 | 14 |
| Shared head (one head, all precisions): Q4 | 25.0% (21.0 to 29.5) | 34 (8.5%) | 47 | 21 | 32 |
| Generative text (for comparison): Q8 | 6.5% (4.5 to 9.4) | 18 (4.5%) | 2 | 6 | 25 |
| Generative text (for comparison): Q4 | 27.0% (22.9 to 31.6) | 81 (20.2%) | 13 | 35 | 91 |
| **Noise floor**: 20 heads on bootstrap samples, FP16 vectors only (nothing but the training sample changes) | 19.6% (lowest 16.2%, highest 23.0%) | mean 5.0% | - | - | - |
| Noise floor, bootstrap head vs bootstrap head | 22.8% (lowest 20.0%, highest 26.5%) | - | - | - | - |

'Right' means the whole record equals the gold answer. Dev A and all-1400 numbers are in controls_summary.json.

### Spread over the 20 bootstrap heads (held-out B)

| Measure | Mean | Median | Lowest | Highest |
|---|---|---|---|---|
| Noise floor: bootstrap head vs reference FP16 head (table changes) | 19.6% | 19.8% | 16.2% | 23.0% |
| Noise floor, action field only | 5.0% | 5.2% | 3.2% | 6.5% |
| Same bootstrap head, Q8 vectors vs FP16 vectors | 25.0% | 24.9% | 18.8% | 28.7% |
| Same bootstrap head, Q4 vectors vs FP16 vectors | 50.6% | 51.2% | 46.2% | 54.8% |
| Same, Q8 vectors with offset removed | 11.8% | 11.8% | 9.5% | 14.2% |
| Same, Q4 vectors with offset removed | 32.8% | 32.8% | 27.8% | 38.0% |
| Bootstrap head accuracy on FP16 vectors: action | 91.1% | 91.0% | 89.2% | 93.2% |
| Bootstrap head accuracy on FP16 vectors: whole record | 69.5% | 69.2% | 66.8% | 72.2% |

A bootstrap sample holds about 64% of the dev families (the rest are repeated), so a bootstrap head is a little weaker than the full-data head. That makes the noise floor a slightly HIGH estimate of pure training noise.

## 3. Are the answers right? (against the gold answers, held-out B)

| System | Action | Whole record | Sensor | Priority | Location | Link | Missed alarm | Wrong close | Priority too low | Danger total | False alarm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TF-IDF + LR | 76.2% | 53.5% | 52.8% | 51.7% | 83.3% | 100.0% | 26 | 4 | 22 | 52 | 8 |
| Rule engine | 55.0% | 50.7% | 25.6% | 26.7% | 31.7% | 29.3% | 123 | 0 | 5 | 128 | 4 |
| Generative FP16 | 58.8% | 27.3% | 48.3% | 45.6% | 53.9% | 71.4% | 2 | 3 | 49 | 54 | 38 |
| Generative Q4 | 62.5% | 32.8% | 46.1% | 42.8% | 54.4% | 53.6% | 5 | 0 | 55 | 60 | 27 |
| Heads FP16 | 92.2% | 70.8% | 61.7% | 62.2% | 90.6% | 93.6% | 10 | 8 | 36 | 54 | 7 |
| Heads Q8 | 91.8% | 68.2% | 57.2% | 62.8% | 90.6% | 94.3% | 12 | 7 | 30 | 49 | 11 |
| Heads Q4 | 89.0% | 66.5% | 57.8% | 65.6% | 92.2% | 90.0% | 13 | 2 | 20 | 35 | 19 |
| FP16-trained heads on Q8 vectors | 86.8% | 65.8% | 70.0% | 66.7% | 95.0% | 95.7% | 9 | 1 | 31 | 41 | 36 |
| FP16-trained heads on Q4 vectors | 62.5% | 47.5% | 15.6% | 11.7% | 38.9% | 100.0% | 92 | 49 | 37 | 178 | 8 |
| FP16-trained heads on Q4 vectors, offset removed | 83.5% | 57.8% | 47.8% | 57.2% | 91.1% | 87.9% | 9 | 10 | 45 | 64 | 32 |
| Shared head on FP16 vectors | 93.2% | 73.0% | 63.3% | 66.7% | 91.7% | 95.7% | 10 | 7 | 23 | 40 | 6 |
| Shared head on Q8 vectors | 93.2% | 73.8% | 63.9% | 66.7% | 91.1% | 95.7% | 10 | 7 | 22 | 39 | 6 |
| Shared head on Q4 vectors | 89.8% | 66.5% | 58.9% | 65.6% | 94.4% | 90.0% | 9 | 2 | 26 | 37 | 23 |
| Bootstrap heads on FP16 vectors (mean of 20) | 91.1% | 69.5% | - | - | - | - | - | - | - | 46.8 | - |

Sensor, priority and location are counted on the 180 reports whose gold answer is CREATE or UPDATE; link on the 140 whose gold answer is UPDATE or CLOSE. The four error columns are COUNTS of reports (out of 400). They are my own rough proxies: 'missed alarm' = gold says CREATE/UPDATE and the system does nothing; 'wrong close' = the system closes an incident gold does not close; 'priority too low' = right action but a lower priority number (3 is most urgent); 'danger total' = the first three added (no report is counted twice); 'false alarm' = the system starts or changes a record when gold does not (a wasted trip, less serious). The allocator harm test will replace them.

## 4. How to read it (rules written in CONTROLS_PLAN.md before this run)

* **V1, noise floor, Q4: TRAINING NOISE IS BIG.** The noise floor is 71% of the Q4 separate-heads disagreement (19.6% vs 27.5%). Retraining a head on a slightly different sample of the SAME vectors already moves the answers about as much. So a large part of the separate-heads number is the head being unstable on style B. This number alone cannot show a quantization effect.
* **V1, noise floor, Q8: TRAINING NOISE IS BIG.** The noise floor is 110% of the Q8 separate-heads disagreement (19.6% vs 17.8%). Retraining a head on a slightly different sample of the SAME vectors already moves the answers about as much. So a large part of the separate-heads number is the head being unstable on style B. This number alone cannot show a quantization effect.
* **V2, one shared head, Q4: MIXED.** Lower disagreement than separate heads: yes. Whole-record accuracy kept (within 2 points): yes. Danger errors not higher: no.
* **V3, offset removed from the Q4 vectors: HELPS.** In 100% of the 20 bootstrap heads the fixed-head disagreement dropped by at least 5 points (mean drop 17.9%).

These codes are reading aids. They are not a registered test, and they decide nothing alone.

## 5. Sanity checks

* The average shift of the vectors (dev A, no labels) explains 73.4% of the Q8 change and 93.0% of the Q4 change. A LOW number means the change is not a simple constant shift, so an offset fix cannot do much.
* Fits: 132; stopped at the iteration limit: 0. Chosen regularisation C: 0.003 x55, 0.03 x49, 0.3 x6, 3 x22.
* Family leak check: passed (the code stops if a family is in both training and test).

## 6. What this cannot say

* B was already seen in attempt 1, so everything here is exploratory. A claim needs fresh cases from a new generator seed and settings frozen before the run.
* Style B comes from the same generator as style A. It is a harder wording style, not independently written language.
* The bootstrap heads are trained on resampled data, so the noise floor is a slightly high estimate of pure training noise.
* Fewer disagreements are not the goal by themselves: all heads can agree and still be wrong together. Look at section 3.
* 'Danger errors' are rough proxies. Which errors really cause late or missed victims is decided by the allocator harm test.
* Only Q8 and Q4_K_M were looked at. Nothing here says what happens at another bit width.
* Any repair changes the scores Shield uses, so Shield must be recalibrated on separate data after it.
