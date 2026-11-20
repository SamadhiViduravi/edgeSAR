# Wording-shift check: audit of the saved style-B predictions

Protocol hash `efb54e7ca87658cb341b4abf49eebebca7f17b8659f1ba5e6a32bed92f4af4b3` (PROTOCOL_WORDING_SHIFT.md). Exploratory; style B has been inspected many times.

## P1 File integrity

| File | SHA-256 (first 16) | Equals CHECKSUMS.sha256 |
|---|---|---|
| repair_package/out/predictions.csv | 89a22a8c2b994aa2 | yes |
| repair_package/out2/predictions.csv | 75948a71c2d7895f | yes |
| repair_package/out/fold_log.json | f40d5d6700006363 | yes |
| repair_package/out2/fold_log.json | 274ef3f7ef16eb9c | yes |
| data/cases.jsonl (release; CRLF form is the pinned experiment file) | 833fafe2fb47af9a | yes (checked by release_only.py) |

## P2 Coverage (one row per style-B report, no style-A report)

| Arm in this check | Saved name | Rows | Covers exactly the 400 style-B reports |
|---|---|---|---|
| tfidf | TFIDF (text only) | 400 | yes |
| rule | RULES (text only) | 400 | yes |
| f16p | REFp (prefix) | 400 | yes |
| q4p | MATCHEDp (prefix) | 400 | yes |
| recp | C1p (prefix) | 400 | yes |
| alnp | C2p (prefix) | 400 | yes |
| rawp | FROZENp (prefix) | 400 | yes |
| f16 | REF (end) | 400 | yes |
| q4 | MATCHED (end) | 400 | yes |
| rec | C1 (end) | 400 | yes |
| aln | C2 (end) | 400 | yes |
| raw | FROZEN (end) | 400 | yes |

## P3 Training data and label budget

* fold log `out` (end): style-B task has n_lab 1000, n_bank 1000, n_test 400 (as required).
* fold log `out2` (prefix): style-B task has n_lab 1000, n_bank 1000, n_test 400 (as required).
* The 1,000 training reports are the 1,000 style-A reports (script `run_ppr.py`: `A = split == dev`, `tr = A`, `lab = tr` for protocol B; all supervised arms use `lab`). The test reports are the 400 style-B reports (`B = split == held`). 1000 style-A and 400 style-B reports in the release.
* Consistency check: refitting the pilot TF-IDF classifier on the 1,000 style-A reports and predicting the 400 style-B reports reproduces the saved TF-IDF records in 400 of 400 reports. The rule engine has no fitted part; recomputing it reproduces the saved rule records in 400 of 400.
* Label budget: TF-IDF, F16 reader and Q4 retrained each use all 1,000 style-A labels. Recentring and the map reuse the F16 reader (1,000 labels) and add unlabelled F16-Q4 pairs of the same 1,000 reports. The rule engine uses no labels. **No 100- or 300-label arms exist for style B** (only `labels = all`), so a label-budget curve on style B is not available.

## P4 Duplicate handling

* Style-B reports whose text equals any style-A report text: **0** (so training on style A cannot have seen a style-B text; no purge is needed).
* Style-B internal duplicate texts: 26 groups covering 54 reports (they count twice in style-B totals; they are all in the test side, never used for fitting).

## P5 / P6 Record parity and assembler parity

| Arm | Records rebuilt as valid and equal to the saved key | Equal to the common assembler's record from the saved action / sensor / priority |
|---|---|---|
| tfidf | 400 / 400 | 400 / 400 |
| rule | 400 / 400 | 400 / 400 |
| f16p | 400 / 400 | 400 / 400 |
| q4p | 400 / 400 | 400 / 400 |
| recp | 400 / 400 | 400 / 400 |
| alnp | 400 / 400 | 400 / 400 |
| rawp | 400 / 400 | 400 / 400 |
| f16 | 400 / 400 | 400 / 400 |
| q4 | 400 / 400 | 400 / 400 |
| rec | 400 / 400 | 400 / 400 |
| aln | 400 / 400 | 400 / 400 |
| raw | 400 / 400 | 400 / 400 |

(P5 must be 400 / 400 for every arm. P6 is information for the two text arms; for the hidden-vector arms the saved records were built with the same assembler.)

## P7 What each arm sees (information)

| Arm | Report text | Open-incident table | Labels used | Fitting / adaptation data |
|---|---|---|---|---|
| hidden-vector arms | in the prompt | the full list, in the prompt | F16 reader, Q4 retrained: 1,000 | F16 / Q4 vectors of the 1,000 style-A reports |
| TF-IDF | yes | a summary: number open, target found, its sensor and priority, id mentioned | 1,000 | the 1,000 style-A texts |
| rules | yes | target found by string matching | 0 | none (code frozen 28 Oct 2026, hash e410b94c...) |
| recentring, map | in the prompt | in the prompt | 1,000 (through the F16 reader) | unlabelled F16-Q4 pairs of the 1,000 style-A reports |

Landmark and incident link come from the same string-matching assembler for every arm. Heads for style B were fitted by `ppr_lib.fit_head` (grouped by template); the style-A mission arms used `shield/readout.py` (grouped by family): same recipe, different code path.

## Decision accuracy on the 400 style-B reports (saved predictions)

| Arm | Whole record right | Action right |
|---|---|---|
| TF-IDF + LR (text) | 214 / 400 (53.5%) | 305 / 400 (76.2%) |
| Keyword rule engine (text) | 203 / 400 (50.8%) | 220 / 400 (55.0%) |
| F16 reader | 287 / 400 (71.8%) | 378 / 400 (94.5%) |
| Q4 retrained, 1,000 labels | 291 / 400 (72.8%) | 378 / 400 (94.5%) |
| Q4 recentred | 260 / 400 (65.0%) | 363 / 400 (90.8%) |
| Q4 label-free map | 285 / 400 (71.2%) | 377 / 400 (94.2%) |
| Q4 unchanged transfer | 240 / 400 (60.0%) | 317 / 400 (79.2%) |
| F16 reader (end) | 288 / 400 (72.0%) | 367 / 400 (91.8%) |
| Q4 retrained (end) | 268 / 400 (67.0%) | 357 / 400 (89.2%) |
| Q4 recentred (end) | 243 / 400 (60.8%) | 340 / 400 (85.0%) |
| Q4 label-free map (end) | 273 / 400 (68.2%) | 361 / 400 (90.2%) |
| Q4 unchanged (end) | 175 / 400 (43.8%) | 246 / 400 (61.5%) |

Cross-check with the earlier record-level report (heads package attempt 1 and the pilot, same 400 reports; `audit04_report.md` in the release): TF-IDF 53.5%, F16 heads 70.8%, Q4 heads 66.5% whole record right; rule engine 50.7% (pilot). TF-IDF and rules reproduce. The F16 and Q4 heads of this check (`ppr_lib.fit_head`, refitted in the repair experiment) give 72.0% and 67.0% at `end`, i.e. +1.2 and +0.5 points: a different fitting code path (template-grouped selection of C, different folds); the cause of the difference was not investigated. The mission check uses the repair-experiment records, because they are the ones that contain the recentring and map arms.

## Result of the preconditions

P1 to P5 hold. P6 and P7 are information. The mission run follows (20 episodes of 20 reports per level and arrival seed; the three arrival seeds reuse the same 400 reports, so the 60 episodes per level are not independent).

