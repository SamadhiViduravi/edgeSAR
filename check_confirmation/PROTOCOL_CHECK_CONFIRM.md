# Confirmation of the label-free mission check: protocol (frozen 26 Nov 2026)

Samadhi V. Dissanayake, with Dr. Achala Aponso and Mr. Maninda Edirisooriya (supervisors). AI assistance: Claude (Anthropic) drafted this
protocol and the scripts; the authors checked them.

## 1. Purpose

Section V-K of manuscript v2.12 reported an exploratory finding on the reports of the first confirmation: replaying the missions with the
old classifier's records as the truth (the *label-free mission check*) ranked 36 candidate classifiers by their true mission harm with
Spearman correlations of 0.94 to 0.99, while record flips and the labeled accuracy drop did not. This protocol tests that finding on
**new reports whose model outputs do not exist when this file is frozen**, for the same migration (FP16 to Q4_K_M) and a second one
(FP16 to Q3_K_M), with three more label-free adaptations added to the candidates.

## 2. What is frozen

`FROZEN.sha256` lists the SHA-256 of every file below. The files are pushed to the public repository (folder `check_confirmation/`,
tag `check-protocol-2026-11-26`) **before** the GPU step is run; the tag on GitHub is the public timestamp.

| File | Role |
|---|---|
| `PROTOCOL_CHECK_CONFIRM.md` | this protocol |
| `check_confirm.py` | the analysis, run once, unchanged |
| `gen_set_c.py`, `cases_C.jsonl`, `generation_manifest_C.json` | the new reports (inputs only: texts, open tables, gold records) |
| `extract_c.py`, `RUN_EXTRACT_C.bat` | the GPU step |

Code root: built by `make_root.py` from repository tag `paper-v2.12` (commit 3dbadc6), the code of the first confirmation.

## 3. Data

**Set C**: 5,000 new reports from the same generator and rules as the first confirmation. C1: 3,000 reports in the development wording
(150 episodes of 20; seed 20261126). C2: 2,000 reports in the new wording (100 episodes of 20; seed 20261127). A report already among the
1,400 development or 7,000 fresh reports was thrown away and drawn again.

**Vectors**: prefix position, llama.cpp b11901, laptop GPU, the same code and server settings as the saved vectors. FP16, Q4_K_M and
Q3_K_M for set C; Q3_K_M for the 1,400 development reports (FP16 and Q4_K_M development vectors are the saved ones). Q3_K_M is made from
the FP16 file with `llama-quantize` (same tool and recipe as Q4_K_M, no importance matrix) if the file does not exist yet. For FP16 and
Q4_K_M, 20 development reports are embedded again and must match the saved vectors (cosine at least 0.9999), as in the first confirmation.

## 4. Candidates (39 per migration target)

For each target T in {Q4_K_M, Q3_K_M}, fitted on the 1,000 development fitting reports exactly as in R10 (Section V-K):

- unchanged (FP16 classifier on T vectors), recentering and the affine map of the paper;
- three label-free rivals added now: **pseudo-label retraining** (the three heads retrained on T vectors with the FP16 classifier's own
  predictions on the FP16 vectors as labels; the sensor and priority heads on the reports it predicts as CREATE or UPDATE), **CORAL**
  (Sun, Feng and Saenko, AAAI 2016; in the FP16-standardized space, s' = s_q (C_q + I)^(-1/2) (C_f + I)^(1/2)), and **orthogonal
  Procrustes** (in the FP16-standardized space, R = U V' from the SVD of S_q' S_f);
- retraining with all 1,000 labels; retraining with 100 and 300 labels; bias recalibration and vector scaling with 100 and 300 labels
  (five label draws each, the same draws as R10);
- TF-IDF and the rule engine (the same for both targets).

The six **label-free options** are: unchanged, recentering, map, pseudo-label retraining, CORAL and Procrustes.

## 5. Measures

Missions: the registered simulator (three UAVs, bounded CBBA, default settings), arrival seed 11, loads low, medium and high.

- **True penalty**: candidate missed share minus the FP16 classifier's missed share, gold records.
- **Check penalty**: the same difference with the FP16 classifier's records as the truth. No label is used.
- **Flips**: share of reports whose record differs from the FP16 classifier's record. No label is used.

A *condition* is one target, one set and one load: 2 x 2 x 3 = 12 conditions with 39 candidates each (468 candidate-condition pairs).

## 6. Hypotheses

Each is tested once. The check counts as **confirmed** only if H1 to H4 all hold.

- **H1 (ranking)**: in every condition, the Spearman correlation between the check penalty and the true penalty over the 39 candidates is
  at least 0.80.
- **H2 (better than flips)**: in every condition, the check's Spearman correlation is higher than that of the flips.
- **H3 (choice without labels)**: in every condition, the label-free option with the smallest check penalty has a true penalty at most
  0.25 pp above the smallest true penalty among the six label-free options.
- **H4 (direction)**: the check penalty is above the true penalty in at least 95% of the 468 candidate-condition pairs.

Secondary hypothesis, reported separately (it does not decide H1 to H4):

- **H5 (wrong simulator)**: on C1 at medium load, for each target and each of four perturbed simulators, the Spearman correlation between
  the check penalty computed in the **default** simulator and the true penalty in the **perturbed** simulator is at least 0.70. The
  perturbed simulators: (i) the earlier greedy single-task allocator instead of the bounded CBBA, (ii) a thermal camera also on UAV-03,
  (iii) every UAV 25% slower, (iv) every deadline 25% shorter.

Why these thresholds: 0.80 is a strong rank correlation that is still well below the 0.94 to 0.99 of the exploratory analysis, so the test
is not tuned to that result; 0.25 pp is the non-inferiority margin of the first confirmation; 95% allows for noise in a property that held
in all 216 exploratory pairs; H5 uses a lower bar because a perturbed simulator changes the target itself.

## 7. Descriptive results (no test)

95% episode-bootstrap intervals of the check's Spearman correlation (2,000 resamples); pairwise ordering (pairs whose true penalties differ
by more than 0.5 pp); true penalties with 95% episode-bootstrap intervals for the six label-free options, the 1,000-label retrain, TF-IDF
and rules, for both targets (this repeats the main result of the paper for Q3_K_M); the check in each perturbed simulator against that
simulator's truth; the check on random subsets of 10, 25 and 50 C1 episodes against the true penalties on all C1 episodes.

## 8. Procedure

1. Push this folder to the public repository with tag `check-protocol-2026-11-26`.
2. Run `RUN_EXTRACT_C.bat` on the laptop. Copy `vectors_C/` to the analysis machine unchanged (SHA-256 in `vectors_C/extraction_report.json`).
3. Run once: `python check_confirm.py --root ROOT --cases cases_C.jsonl --vectors vectors_C --dev-vectors vectors_C --out out_checkC --workers 2`.
4. Publish the outputs (`check_results.json`, `check_episodes.json`) and the run log with the paper. Report every hypothesis, whether it
   holds or not.

Any change after freezing is listed in `DEVIATIONS.md` with its reason. Before freezing, the script was only smoke-tested (3 episodes per
task, with copies of the Q4_K_M vectors standing in for Q3_K_M). A full run of the same script on the first confirmation's sets A and B
(Q4_K_M only; exploratory analysis R11) was started before freezing, and its results were not looked at before this file was frozen.
