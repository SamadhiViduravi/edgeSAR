# Readout-repair feasibility experiment: protocol (written BEFORE any run)

Status: FIXED. Written 13 Nov 2026 (evening, Colombo) by the research-design chat. Hashed before the first run (`out/PROTOCOL.sha256`).
Purpose: the cheapest experiment that can show that readout-level repair of Q4 decisions adds nothing beyond known fixes.

**This is a feasibility experiment on development data. It is exploratory.** All 1,400 pilot reports have been used before (style B many times). Nothing here is confirmatory. No new report is generated and no model is run: only saved vectors are read.

## 1. System under test (as verified from the files)

* Model: Llama 3.2 1B Instruct (GGUF from bartowski, file `Llama-3.2-1B-Instruct-f16.gguf`), llama.cpp build b11901.
* Precisions: f16 (reference), Q8_0, Q4_K_M. The two quantized files were made locally from the f16 file with `llama-quantize`, no importance matrix.
* Decision path tested here: **hidden-state readout**. One unit-length 2048-d vector per report (last token, `--pooling last`), then three logistic-regression heads (action 4 classes, sensor 3, priority 3). Location and incident link come from the pilot's deterministic parser, so they do not depend on precision. The record is assembled and validated with the pilot's own `_assemble` and `validate`.
* Two readout positions exist in the saved vectors: `end` (end of the prompt) and `prefix` (the prompt followed by `{"action":"`, 3 more tokens).

## 2. Definitions

For report i: y_i = gold record; r_i = record of the reference system; q_i = record of the unmodified Q4 system; m_i = record of a repair method. All methods here always answer (coverage 100%), so abstention metrics do not apply.

* H = {i : r_i = y_i and q_i ≠ y_i} (harmful change). C = {i : q_i = y_i}.
* Harmful incidence = |H| / N. Beneficial = {r_i ≠ y_i and q_i = y_i}.
* Repair rate = |{i in H : m_i = y_i}| / |H|.
* New-error rate = |{i in C : m_i ≠ y_i}| / |C|.
* Correction precision = |{i : m_i ≠ q_i and m_i = y_i}| / |{i : m_i ≠ q_i}|.
* Also: joint-record accuracy, action accuracy, sensor and priority accuracy (on reports whose gold action is CREATE or UPDATE), error by gold action.

Two cohorts are reported, because "unmodified Q4" has two honest meanings in a readout pipeline:
* **frozen**: q = the FP16-fitted heads applied to raw Q4 vectors (same readout, quantized backbone: the causal comparison).
* **matched**: q = heads refitted on Q4 vectors with the same labels (standard adaptation).

The reference r is always the FP16-fitted heads on FP16 vectors at the `end` position (the project's reference so far).

## 3. Arms (all fixed now)

| Arm | Offline needs | What it is |
|---|---|---|
| REF | labels | FP16 heads on FP16 vectors |
| FROZEN | none | FP16 heads on raw Q4 vectors |
| MATCHED | labels at Q4 | heads refitted on Q4 vectors |
| C1 recentre | unlabelled pairs | FP16 heads on x_Q − δ, δ = mean(x_Q − x_F) over the pair bank |
| C2 affine | unlabelled pairs | FP16 heads on g(x_Q) = μ_F + σ ⊙ ((I + D) s_Q); D = ridge fit of s_F − s_Q on s_Q, shrunk to zero (so the map shrinks to the identity); s = standardised with the bank's FP16 mean/scale and the bank's own Q4 mean. λ ∈ {0.01, 0.1, 1, 10, 100} × mean eigenvalue, chosen by held-out reconstruction error on pairs (3 folds). **No labels.** |
| C3 distil | unlabelled pairs + REF heads | student heads on Q4 vectors trained on the REF heads' probabilities over the pair bank (soft cross-entropy, temperature 1). **No labels at Q4.** Sensor and priority students use bank reports that REF calls CREATE/UPDATE. |
| C4 privileged distil | labels + pairs | student on Q4 vectors; labelled reports: target 0.5·label + 0.5·REF out-of-fold probability (5 folds); unlabelled bank reports: REF probability |
| C5 residual bank | labels at FP16 + pairs | heads trained on FP16 vectors plus real displacements: x_F,i + (x_Q,j − x_F,j) for 4 random j per i (seeded); applied to raw Q4 vectors |
| ANCH anchored (candidate method) | labels at Q4 + pairs | REF heads on recentred Q4 vectors give an offset logit; a correction ΔW, Δb is learned on Q4 labels with an L2 penalty on ΔW (so it shrinks to C1 when labels are weak) |
| ANCH2 | labels at Q4 + pairs | the same with the C2 map instead of recentring |
| SHARED | labels, both precisions | one set of heads fitted on FP16 and Q4 vectors together, applied to raw Q4 |
| POS-prefix, POS-both | labels | matched heads read at `prefix`, or at `end` and `prefix` together (features joined). **General readout change, not a quantization repair**: run at FP16, Q8 and Q4 as a control |
| Q8 arms | | FROZEN, C1, MATCHED at Q8_0 |
| TF-IDF, RULES | labels / none | the pilot's non-LLM baselines (`baselines.LRBaseline`, `rule_decision`) |

Head fitting, same for every arm: StandardScaler, multinomial logistic regression with L2 (the scikit-learn objective), C ∈ {0.0003, 0.003, 0.03, 0.3, 3} chosen by 3-fold inner cross-validation (log-loss; for C3 the soft cross-entropy to REF, which needs no labels), solver L-BFGS to tolerance 1e-9 in the row space of the training matrix (same optimum, faster). One solver for hard and soft targets.

## 4. Splits (leakage controls)

* **Group = template**: the report text with landmarks, incident ids, sources and numbers masked (same function as audit 04). Exact and same-text duplicates share a template, so they stay together. Folds never split a template.
* **Protocol A (same wording style)**: style-A reports only (1,000). 5 folds by template, repeated with 3 different seeded template-to-fold assignments. In each fold everything (heads, δ, maps, students, C, λ) is fitted on the 4 training folds only.
* **Protocol B (new wording)**: fit on all 1,000 style-A reports, test on the 400 style-B reports. Choices are made on style A only. No style-B label or vector is used for fitting.
* **Few labels**: inside each Protocol A training fold, n_L ∈ {100, 300} labelled reports are drawn at random (seeded; redrawn until all 4 actions occur). The pair bank is the whole training fold (no labels). REF, MATCHED, C1, C2, C3, C4, ANCH are refitted with those labels only.
* Style B is never used to choose anything.

## 5. Tests and labels (fixed now)

Primary measure: joint-record accuracy on Q4, Protocol A, all labels. Differences are paired by report, with a 95% bootstrap interval over templates (2,000 resamples, averaged over the 3 repeats).

| Test | Comparison | SUPPORTED if |
|---|---|---|
| T1 label-free transfer | C2 vs C1, and C2 vs MATCHED | interval of (C2 − C1) above 0 **and** C2 − MATCHED ≥ −1.0 point |
| T2 repair beyond retraining (candidate: ANCH) | ANCH vs MATCHED | interval of (ANCH − MATCHED) above 0 in Protocol A **and** point estimate ≥ 0 in Protocol B |
| T3 few labels | ANCH vs MATCHED at n_L = 100 | interval above 0 |
| T4 readout position (general, not a repair) | POS-prefix and POS-both vs `end`, MATCHED heads at Q4 | interval above 0; FP16 control reported beside it |

Anything else is **NOT SHOWN**. C3, C4, C5, ANCH2, SHARED are secondary and descriptive.

Downstream check (secondary): real incidents left unverified in the legacy single-record replay (V1 greedy allocator, 600 s horizon; it only sees action errors, see audit 03), for REF, FROZEN, C1, C2, MATCHED, ANCH on Protocol B.

## 6. Stopping rule

* The protocol is run once. No grid, arm or rule is changed after results are seen.
* A code error is fixed, logged in `out/RUN_LOG.md`, and all arms are rerun; outputs of the faulty run are kept.
* If T1, T2 and T3 are all NOT SHOWN: readout-level repair stops here. The result is reported as negative. The next lever (model-side: importance-matrix quantization, one more bit, mixed precision) needs the laptop GPU and its own protocol.
* If T2 or T3 is SUPPORTED: ANCH goes to one confirmatory test on fresh reports (new seed, new vectors), with its targets fixed before the fresh data exist.
* T4, if supported, changes the baseline readout for every precision. It is not counted as quantization repair.
