# Readout-repair experiment 2: protocol (written BEFORE the run, AFTER seeing experiment 1)

Status: FIXED. Written 14 Nov 2026 (morning, Colombo) by the research-design chat. Hashed before the run (`out2/PROTOCOL2.sha256`).

**This experiment was designed after the results of experiment 1 were seen** (`out/RESULTS.md`, protocol hash `289105a1…`). It is a test-informed revision. It is exploratory, on the same development data (the 1,400 pilot reports, all used before). Nothing here is confirmatory. No model is run: only saved vectors are read. The library `ppr_lib.py` is used unchanged (hash `cd2f1103…`).

## 1. Why this experiment (the changed hypothesis)

Experiment 1 gave three results that change the question:

* The candidate I proposed (ANCH: reference heads plus a correction learned from Q4 labels) was **not shown** to beat retraining (T2).
* The simpler, label-free affine map (C2) **was** better than recentring and than retraining at the `end` position (T1 supported).
* Reading at the `prefix` position was better than `end` for every precision (T4 supported), and more so for Q4.

The one evidence-based revision is: **drop the label-trained correction; keep the label-free affine map; test it at the better readout position.** If retraining at `prefix` already equals the reference, there is nothing left for the map to repair, and the method's use is limited to "no labels needed at Q4".

## 2. Arms (all fixed now)

Suffix `p` = read at `prefix` (the prompt followed by `{"action":"`). All `p` arms use the `prefix` vectors of both precisions.

| Arm | Offline needs | What it is |
|---|---|---|
| REFp | labels | FP16 heads on FP16 vectors, `prefix` |
| FROZENp | none | REFp heads on raw Q4 `prefix` vectors |
| C1p | unlabelled pairs | REFp heads on recentred Q4 vectors |
| **C2p** | unlabelled pairs | REFp heads on affine-mapped Q4 vectors (same map class and λ grid as experiment 1) |
| C3p | unlabelled pairs + REFp heads | student heads on Q4 vectors trained on REFp probabilities over the pair bank |
| MATCHEDp | labels at Q4 | heads refitted on Q4 `prefix` vectors |
| Q8_FROZENp, Q8_C1p, Q8_C2p, Q8_MATCHEDp | as above | the same four at Q8_0 (control at a higher precision) |
| REF, Q8_C2 | | `end` position: REF is recomputed as an integrity check against experiment 1; Q8_C2 is the affine map at Q8, which experiment 1 did not have |
| C1p_bankN, C2p_bankN | N unlabelled pairs | recentring and the affine map fitted on a random subset of N pairs of the training fold, N ∈ {50, 100, 200, 400}; REFp heads use all labels |

Head fitting, map fitting, folds, seeds, groups and the few-label draw are exactly those of experiment 1 (same functions, same seed 20261113), so every arm is paired with the experiment 1 arms report by report.

## 3. Splits

As in experiment 1: Protocol A (1,000 style-A reports, 5 folds by template, 3 repeats), Protocol B (fit on all style A, test on the 400 style-B reports), few labels (100 and 300 labelled reports; pair bank = whole training fold). Style B is never used to choose anything.

## 4. Tests and labels (fixed now)

Measure: joint-record accuracy on Q4. Paired differences with a 95% bootstrap interval over templates (2,000 resamples, averaged over the 3 repeats), Protocol A.

| Test | Comparison | SUPPORTED if |
|---|---|---|
| E2-T1 transfer beyond retraining at the better position | C2p vs MATCHEDp, all labels | interval of (C2p − MATCHEDp) above 0 |
| E2-T2 repair to the reference level | C2p vs REFp, all labels | point estimate of (C2p − REFp) ≥ −1.0 point |
| E2-T3 few labels | C2p vs MATCHEDp at 100 labels | interval above 0 |

Anything else is **NOT SHOWN**. Everything else is descriptive: Protocol B, C1p, C3p, the Q8 arms, the bank-size curve, the harmful/beneficial cohorts at `prefix` (reference = REFp), and the legacy single-record replay on style B.

Integrity checks (must pass, or the run is void): REF, REFp-as-`POS_prefix_FP16`, MATCHEDp-as-`POS_prefix_Q4`, FROZENp-as-`POSprefix_FROZEN_Q4` and C1p-as-`POSprefix_C1_Q4` must give exactly the records of experiment 1 for every report, repeat and fold.

## 5. Stopping rule and what follows

* One run. No arm, grid or rule is changed after results are seen. A code error is fixed, logged in `out2/RUN_LOG.md`, and everything is rerun; faulty outputs are kept.
* **No further readout-level experiment on these 1,400 reports after this one.** The next step is either a confirmatory test on fresh reports or the model-side lever, each under its own frozen plan.
* If E2-T1 is SUPPORTED: the confirmatory claim is superiority of the label-free map over retraining at `prefix`.
* If E2-T1 is NOT SHOWN: the confirmatory claim is limited to (a) non-inferiority of the label-free map to retraining, with a margin fixed before the fresh data exist, and (b) superiority with few labels if E2-T3 is supported.
