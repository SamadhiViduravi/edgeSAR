# EdgeSAR heads: exploratory controls (step 4), plan

Written: Thu 12 Nov 2026, BEFORE the controls are run. Keep this file as it is. If you change a rule below, change it BEFORE you run, and write the change and the reason in your log.

## 1. Status (be honest about this in the paper)

* This is **exploratory**. It was decided on 12 Nov 2026, after the held-out B results of attempt 1 were seen.
* Nothing is tuned on held-out B. The settings (C grid, folds, seed) are the same as in step 3. The reading rules are fixed here.
* Attempt 1 stays as it is: its files in `results_heads\` are not touched, and its numbers and rules do not change.
* Later, a real claim needs fresh cases (a new generator seed) and settings frozen before the run.

## 2. The question

In attempt 1, "Heads Q4 vs Heads FP16" disagreed on 110 of 400 held-out reports (27.5%). Two things changed at the same time: the vectors (the model was shrunk) and the head (a new head was trained on the new vectors). We do not know which one moved the answers. Also, 27.5% counts a change in ANY field (sensor, priority, location, link), not only the action.

## 3. The five controls

| # | Control | What changes | What stays the same | Why we run it |
|---|---|---|---|---|
| 1 | Separate heads | vector AND head | nothing | This is attempt 1. It must give the same numbers again. If not, something is wrong and we stop. |
| 2 | Fixed head | the vector only | the FP16 head | Shows the effect of shrinking alone. |
| 3 | Noise floor | the training sample only (bootstrap, families resampled) | the FP16 vectors | Shows how much a head moves just because it was trained on slightly different data. 20 heads. |
| 4 | Fixed head + offset fix | the vector, minus its average shift | the FP16 head | Tests the simplest repair. The shift is measured on dev A, with NO labels. |
| 5 | Shared head | one head trained on FP16 + Q8 + Q4 vectors together | the head is the same for every precision | Tests if one head is steadier. All three copies of a report stay in the same fold. |

## 4. What is measured (all against the gold answers, held-out B first)

* Disagreement with the FP16 pipeline: table-changing, any field, and the **action field only**.
* Direction of the changes: right to wrong, wrong to right, both wrong.
* Accuracy: action, whole record, and each field (sensor, priority, location, link).
* Danger errors (my rough proxies, counted as reports out of 400): missed alarm, wrong close, priority too low, and the sum of these three. False alarms are counted separately (a wasted trip, less serious).
* Every answer of every system for every report is saved in `predictions_end.csv`. So any number can be checked by hand, and the harm test can use the same answers.

## 5. Reading rules (set now)

These are reading aids. They are not a registered test. They decide nothing alone.

* **V1, noise floor.** The noise floor is the average disagreement of the 20 bootstrap heads with the full FP16 head. Compare it with the separate-heads disagreement (control 1).
  * floor is **half or more** of the separate-heads number: "TRAINING NOISE IS BIG". Then the 27.5% mostly shows that the head is unstable on style B. It does not show a quantization effect.
  * floor is **less than half**: "TRAINING NOISE IS SMALL". Then the shrunk vectors themselves matter.
  * Reason: the bootstrap heads are a little weaker than the real head, so the floor is a slightly high estimate. That is why the line is at one half and not at one.
* **V2, shared head (Q4).** HELPS only if all three are true: it disagrees less than separate heads, whole-record accuracy is not lower by more than 2 points, and the danger total is not higher. If it disagrees less but one of the other two fails: MIXED. If it does not disagree less: DOES NOT HELP.
  * Reason: agreeing is not the goal. All heads can agree and be wrong together. ChatGPT's review said this clearly.
* **V3, offset fix (Q4).** HELPS only if, for at least 90% of the 20 bootstrap heads, the fixed-head disagreement drops by 5 points or more, the average drop is also 5 points or more, and whole-record accuracy does not get worse. Otherwise NO CLEAR HELP.
  * Reason: one head is only one draw. Twenty heads show if the effect is steady.

## 6. How to run it (Windows PowerShell)

1. Copy the new files into your `edgesar_heads` folder. Do NOT replace `heads_config.json` or your edited `HEADS_TEST_PLAN.md`. (`heads_report.py` is replaced too: only one sentence of the guide text changed, no number.)
   * New: `controls_config.json`, `heads_controls.py`, `controls_report.py`, `04_controls.py`, `CONTROLS_PLAN.md`, `tests\test_controls.py`.
2. `python 04_controls.py`
   * Reason: it uses the feature files you already have (no model, no server). It takes about 1.5 to 2 times as long as step 3 (my estimate).
   * The first thing it checks is "Same numbers as attempt 1". The answer must be MATCH.
3. Open `results_controls\controls_report.md` and send it to me, with the text from the PowerShell window.

## 7. What each result would change

* V1 BIG: stop talking about "quantization damage" for the heads. First make the head steadier (more training families, or one shared head). Then measure again on fresh cases.
* V1 SMALL and the fixed head is bad: the vectors move. Then the offset fix and the shared head are worth a fair test on fresh cases.
* V2 or V3 HELPS: it is a candidate repair. It is NOT a result yet. Test it on fresh cases with settings frozen first, and recalibrate Shield after it.
* Nothing helps: the heads line stays as a documented negative result. The simulator and the allocator test stay the core of the project.

## 8. Your guess before you run (optional, 2 minutes, write it in your log)

1. The noise floor on held-out B will be: (a) under 10%, (b) 10 to 20%, (c) over 20%.
   * Help: Q8 vectors are almost the same as FP16 vectors (cosine 0.9987), but the two separate heads still disagreed on 17.8%.
2. One shared head will help for Q4: yes / no.

## 9. The note for your pilot registration log (use these words)

> 11 Nov 2026, after the results: bullets 1 and 3 of section 6 of HEADS_TEST_PLAN.md contradict each other for this outcome (O1 BETTER, O2 NOT SHOWN LOWER, O3 USEFUL). This was found after the results were seen. The decision to continue the heads line was made after the results, so all further heads work is EXPLORATORY. The reported numbers and the outcome rules are unchanged. The report generator's guide text was corrected on 12 Nov 2026 (text only, no number changed).

Do not write "bullet 3 applies" as if the plan had settled it. It did not.

## 10. Wording correction (added Thu 12 Nov 2026, after run 1; sections 1 to 9 above are unchanged)

* In sections 3 and 5 the control called "noise floor" is **bootstrap-sample heads**: heads trained on family-resampled dev samples of the SAME FP16 vectors. Its number (19.6% on B in run 1) is **bootstrap training-sample variability**, not a pure random-seed floor. Head training has no random seed (it is deterministic); only the bootstrap sampling is random.
* The 22.8% in run 1 compares two bootstrap heads with each other (consecutive pairs), so it is head against head.
* These numbers are **not additive**. Do not subtract 19.6% from 27.5% and call the rest the quantization effect.
* The reading codes of V1 are renamed "TRAINING-SAMPLE VARIABILITY IS BIG / SMALL". The rule (half of the separate-heads disagreement) is the same. It is a reading aid, not a test.
* The 27-number MATCH check is a consistency check only. The "93% / 73%" figures are shares of vector change energy, not shares of errors repaired.
* From run 2 on, outputs go to `results_controls\run_NN\` and the run also writes `bootstrap_predictions_end.csv`, `bootstrap_samples.json` and `provenance.json`, and checks that it reproduces the run-1 records. The run-1 files are not touched.
