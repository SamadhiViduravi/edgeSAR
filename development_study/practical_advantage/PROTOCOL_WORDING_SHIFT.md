# Wording-shift check at mission level: protocol (written and hashed BEFORE the run)

Written 14 Nov 2026 (evening, Colombo). **Exploratory.** Style B (400 reports, new wording) has been looked at many times in this study, so it is not a clean test set and nothing is chosen with it. No decision rule is attached to any number: every result is reported, including results that favour the simple methods on style A (those stay in `TEXT_BASELINES_RESULTS.md`, unchanged).

## 1. Question

Do the style-B predictions that were saved earlier support a fair mission-level comparison of the TF-IDF classifier, the keyword rules, the F16 reader, Q4 retraining, Q4 recentring and the Q4 label-free alignment map? If they do, what do the frozen predictions do to the missed share when they are put through the same mission episodes at the three load levels?

## 2. Frozen inputs (nothing is refitted, nothing is extracted, nothing is tuned)

The predictions are read from `repair_package/out/predictions.csv` (reading position `end`) and `repair_package/out2/predictions.csv` (reading position `prefix`), rows with `protocol = B`, `labels = all`. They were written by `run_ppr.py` / `run_ppr2.py` (code and hashes in `repair_package/MANIFEST.sha256`) from heads fitted on all 1,000 style-A reports and tested once on the 400 style-B reports. The records are used exactly as saved.

| Arm in this check | Saved arm name | Reading position | What it is |
|---|---|---|---|
| tfidf | `TFIDF` | text only | the pilot TF-IDF + logistic regression, fitted on the 1,000 style-A reports |
| rule | `RULES` | text only | the pilot keyword rule engine (no fitting) |
| f16p | `REFp` | prefix | F16 reader: heads fitted on F16 vectors |
| q4p | `MATCHEDp` | prefix | Q4 retrained: heads fitted on Q4 vectors, all 1,000 labels |
| recp | `C1p` | prefix | Q4 recentred: F16 heads on Q4 vectors minus the mean F16-Q4 shift (no labels) |
| alnp | `C2p` | prefix | Q4 label-free affine map: F16 heads on mapped Q4 vectors (no labels) |
| rawp | `FROZENp` | prefix | Q4 unchanged transfer: F16 heads on raw Q4 vectors |
| f16, q4, rec, aln, raw | `REF`, `MATCHED`, `C1`, `C2`, `FROZEN` | end | the same five arms at the other reading position (second panel) |

Primary panel: `prefix`, because the style-A mission analysis used `prefix`. Second panel: `end`. Both are reported in full; neither is chosen after seeing results. Not included (they exist in the files but were not asked for and are not part of the comparison): C3, C4, C5, ANCH, SHARED, Q8 arms, generated text, bank-size arms. There are no 100- or 300-label arms for style B (only `labels = all`); a label-budget curve on style B is therefore not available.

## 3. Preconditions (checked by the script before any mission is run; a failure stops the run and is reported as the missing prerequisite)

| # | Check | Pass when |
|---|---|---|
| P1 | file integrity | `cases.jsonl` (published hash), both `predictions.csv` files and both `fold_log.json` files equal the SHA-256 in the supplement's `CHECKSUMS.sha256` |
| P2 | coverage | every arm above has exactly one row for each of the 400 style-B reports, and no style-A report |
| P3 | training data and label budget | in both fold logs the style-B task has `n_lab = n_bank = 1000` and `n_test = 400`; the 1,000 training reports are exactly the 1,000 style-A reports; TF-IDF is refitted on those same 1,000 reports and its saved predictions are compared (information; the saved ones are the ones used) |
| P4 | duplicate handling | no style-B report text equals any style-A report text (so no purge is needed); style-B internal duplicate groups are counted and reported |
| P5 | record parity | each saved record rebuilds as a valid record for its report (`validate` returns it unchanged, status ok) and has the saved key; the committed record in the simulator therefore equals the saved prediction |
| P6 | assembler parity | for the hidden-vector arms the saved record equals what the common assembler gives for the saved action, sensor and priority (the mission arms of the style-A analysis use that assembler); for `tfidf` and `rule` the number of records that differ from the common assembler is counted and reported (information) |
| P7 | input information | printed as a table (not pass/fail): what each arm sees (see section 4) |

## 4. What each arm sees (stated so the reader can judge fairness; not pass/fail)

* Hidden-vector arms: the pilot prompt P1 (instructions, the full list of open incidents, the report text), read at the last token (`end`) or after `{"action":"` (`prefix`).
* TF-IDF: the report text plus a small summary of the open table (number of open incidents, whether a target incident is found, its current sensor and priority, whether an incident id is mentioned).
* Rules: the report text and the open table (target incident found by string matching).
* All arms: landmark and incident link come from the same string-matching assembler.
* Labels: TF-IDF, F16 reader and Q4 retrained use the 1,000 style-A labels; recentring and the map use the F16 reader (1,000 labels) plus unlabelled F16-Q4 pairs of the 1,000 style-A reports; the rule engine uses none. Heads for style B come from `ppr_lib.fit_head` (grouped by template); the style-A mission arms used `shield/readout.py` (grouped by family): same recipe (standardise, logistic regression, C by grouped cross-validation), different code path.
* The pilot code (`baselines.py`, hash `e410b94c...`) was frozen on 28 Oct 2026, before any style-B result was looked at.

## 5. Mission replay

* Simulator, allocator and settings exactly as in the style-A mission analysis (`edgesar_shield`, bounded CBBA, always commit, no gate), reused unchanged.
* Episodes: the style-B reports are partitioned at random into episodes of 20 reports by the same function (`make_episodes`) with the same mean gaps (L 60 s, M 30 s, H 8 s; set on style A), arrival seeds 1, 2, 3, episode seed = 1000 x arrival seed. 20 episodes per level and seed, 60 per level. Every arm runs the same episodes; the gold-record arm runs too.
* The gaps were tuned on style A so that gold records miss about 1%, 5%, 15%; on style B the gold miss rate may differ and is reported.

## 6. Outcomes and comparisons

* Missed share = (late + unverified) / incidents, pooled over episodes; 95% episode-bootstrap interval (2,000 resamples, seed 11). Priority-weighted version (weights 3/2/1, `resolved_external` excluded). Pooled intervals are optimistic because the three arrival seeds reuse the same 400 reports.
* Paired differences on the same episodes (10,000 resamples, seed 7): tfidf and rule against f16p, q4p, recp, alnp, gold; f16p against q4p; alnp against q4p and recp; recp against q4p; tfidf against rule. Same for the `end` panel (tfidf and rule against f16, q4, rec, aln, gold; aln against q4 and rec; f16 against q4).
* Decision accuracy on the 400 style-B reports (whole record, action) for every arm, as counts and percentages.
* Wording rule for the report: a difference is called "shown" only if its 95% interval excludes zero in both measures; otherwise "not shown". No p-values are used.

## 7. What this check can and cannot say

It can say whether the wording-shift advantage seen at the record level (pilot: whole record right, F16 heads 70.8%, Q4 heads 66.5%, TF-IDF 53.5%, rules 50.7%) survives at mission level for one training protocol (1,000 labels). It cannot say anything about real human-written reports, about fewer labels, or about a held-out test of anything, and a nonzero or zero result here does not select a method.

## 8. Out of scope

Refitting any head or map; new model extraction; tuning; adding or dropping arms after the results are seen; any change of the proposal or the gate text; running a gate.
