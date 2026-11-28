# Manuscript draft v2.18: where each result comes from

This file maps every table, figure and result section of manuscript draft v2.18 (*Adapting a Hidden-State Task Classifier to a 4-Bit
Language Model: Missed Incidents and a Label-Free Check in Simulated Multi-UAV Rescue*) to the files of this repository (git tag
`paper-v2.18`). Some older READMEs and result files inside the folders use the table numbers of earlier drafts; this manifest gives the
current numbers. No earlier result file was changed for v2.18; the new exploratory analyses of Section V-M and Appendix C are in
`checklist_2026-11-28/`. Zenodo version 1.2 (23 Nov 2026) holds the files up
to that date; the analyses of Sections V-I, V-J.8, V-K and V-L (`deployment_check/`, `fresh_confirmation/review_r9.py`,
`fresh_confirmation/review_r10*.py`, `check_confirmation/`) and the files added with the tags `paper-v2.16`, `paper-v2.17` and
`paper-v2.18` are only in this repository.

**Zenodo file name.** The Zenodo record of the code and confirmation package (doi:10.5281/zenodo.24454853, version 1.2) holds one archive,
`EdgeSAR_code_and_confirmation_v1.3_for_Zenodo.zip`. "v1.3" in the file name is our internal package number; the record's version is 1.2.

| Manuscript v2.18 | Files | Notes |
|---|---|---|
| Section III (system), Appendix A (prompt) | `zenodo_v1/code/` (study code; prompt template in `zenodo_v1/code/edgesar_pilot/common.py`), `code/repair_package/` | Allocator, simulator, heads, recentering and the label-free map. |
| Section III, allocator tests | `zenodo_v1/code/edgesar_shield/results/M1_cbba_report.md`, `zenodo_v1/code/edgesar_shield/IMPLEMENTATION_EVIDENCE.md` (row M1) | Three separate tests: convergence on 10,000 random instances (up to 4 UAVs and 12 tasks; bundle length 3, full graph); total score against brute force on 150 small instances (2-3 UAVs, 2-6 tasks; mean 0.986, worst 0.836 for bundle length 3); first assignments with bundle length 1 against the greedy single-task allocator on the 1,400 gold tables (1,400 of 1,400 equal). The bundle limit applies per auction pass (`shield/alloc.py`, docstring). |
| Section IV-A, text baselines | `zenodo_v1/code/edgesar_pilot/baselines.py` (`rule_decision`, `find_target`, `lr_text`, `LRBaseline`) | The TF-IDF classifier reads the report text plus five incident-context tokens (`lr_text`): number of open incidents, target matched or not, the matched incident's current sensor and priority, incident identifier written. TF-IDF word 1-2 grams, sublinear tf, min_df 2; logistic regression C = 10. The same code is used in every study. |
| Table 1, Fig. 2 (left): development results by load | `development_study/repair_package/out_mission/`, `development_study/practical_advantage/out_levels/`, `out_text_baselines/` | Check: `python development_study/practical_advantage/verify_from_records.py ...` (see `development_study/README_SUPPLEMENT.md`). Heads: see "Head fitting" below. |
| Table 2: AUC and accuracy, development | `development_study/repair_package/diag_auc.py`, `out_diag/AUC_DIAG.md`, `out_diag/auc_diag.json` | Each AUC cell gives the value from class logits / from softmax probabilities, as in `AUC_DIAG.md` (style A, action head). Own split: see "Head fitting" below. |
| Table 3, Fig. 3 (dotted): development label budget | `development_study/practical_advantage/mission_gold_trace.py`, `out_trace/` (`TRACE_RESULTS.md`) | Also the development field diagnosis of Section V-F. |
| Fig. 3 (drawing) | `fresh_confirmation/figures/fig3_labels_v216.py`, `fig3_labels.pdf`, `fig3_labels.png` | The four reference levels are labeled with their values. Fresh points: 100 and 300 labels are the mean of five label draws; 1,000 labels is one fit on all development reports. |
| Section V-A: generated JSON against hidden-state readout | `zenodo_v1/code/edgesar_pilot/results/pilot_report.md` (JSON, rules, TF-IDF), `zenodo_v1/code/edgesar_heads/results_heads/` (hidden-state heads) | |
| Section V-G: text baselines, new wording | `development_study/practical_advantage/out_text_baselines/`, `out_wording_shift/`; fresh: `fresh_confirmation/results.json` | |
| Section V-H: what did not help | `zenodo_v1/code/edgesar_shield/` (runtime check in `shield/`; importance-matrix files in `results/iter2/ITER2_SUMMARY.md`) | |
| Section V-I: cost and CPU deployment | `development_study/practical_advantage/bench_cost.py`, `out_cost/`; `deployment_check/` (see `deployment_check/MEMORY_FIELDS_NOTE.md`) | The timed heads are the scikit-learn heads of `shield/readout.py`. |
| Section V-E, run checks of the first confirmation | `fresh_confirmation/RUN_NOTES_AND_DEVIATIONS.md` (items 2 to 5), `fresh_confirmation/FROZEN.sha256` | Vector files: SHA-256 after joining equal to the values recorded at extraction (all four); frozen script hash checked with `sha256sum -c` just before the single run. |
| Table 4 (pre-specified primary analysis) | `fresh_confirmation/results.json`, `episode_outcomes.csv`, `rebuild_primary.py` | `python rebuild_primary.py episode_outcomes.csv` ends with `ALL EQUAL TO results.json: True`. |
| Table 5, Fig. 2 (right), Fig. 3 (solid), fresh field diagnosis | `fresh_confirmation/results.json`, `RESULTS.md`, `records/` | The scarce-label whole-record accuracies (A / B) are the means of the five draws in `results.json` (`accuracy/A_all` and `accuracy/B_all`, arms `q4p_n100_d0..d4` and `q4p_n300_d0..d4`): 64.1 / 60.6 (100 labels) and 74.3 / 69.3 (300 labels; set A is exactly 74.25, rounded half up). |
| Section V-J.1, Table B1 | `fresh_confirmation/review_analyses.py` (`REVIEW_RESULTS.md` item 1, "Table 6" there), `review_overlap.py` (`review_overlap_by_population.json`, R8) | Exploratory. |
| Section V-J.2, Table B4 | `fresh_confirmation/review_analyses.py`, `review_r2b.py`, `review_r2c.py` (`REVIEW_RESULTS.md` item 2, "Table 7" there) | Exploratory. |
| Section V-J.3, Table B2 | `fresh_confirmation/review_analyses.py` (`REVIEW_RESULTS.md` item 3, "Table 8" there) | Exploratory. AUC from softmax probabilities. |
| Sections V-J.4 and V-J.5 | `fresh_confirmation/review_analyses.py` (`REVIEW_RESULTS.md` items 4 and 5) | Exploratory. |
| Section V-J.6, Table B3 | `fresh_confirmation/review_analyses.py` (`REVIEW_RESULTS.md` item 6, "Table 9" there) | Exploratory. |
| Section V-J.7, Table 6 (label accounting) | `fresh_confirmation/review_r7.py`, `review_results_r7.json` (`REVIEW_RESULTS.md` R7) | Exploratory. |
| Section V-J.8 (recalibration comparator) | `fresh_confirmation/review_r9.py`, `review_results_r9.json` (`REVIEW_RESULTS.md` R9) | Exploratory. |
| Section V-K (exploratory check) | `fresh_confirmation/review_r10.py`, `review_r10_analysis.py`, `review_results_r10*.json` (R10); rerun with the frozen script: `check_confirmation/exploratory_R11_setsAB/` | Exploratory. |
| Section IV-G, set C texts | `check_confirmation/generation_manifest_C.json`, `gen_set_c.py` (`case_key`) | No set-C case (text, open incidents and gold record) repeats a development, first-confirmation or earlier set-C case. Texts identical to a first-confirmation text: 1,319 of 3,000 (C1), 423 of 2,000 (C2); to a development text: 649 (C1), 244 (C2). |
| Sections IV-G and V-L, Table 7 (check confirmation) | `check_confirmation/PROTOCOL_CHECK_CONFIRM.md` (tag `check-protocol-2026-11-26`), `results/check_results.json`, `results/check_episodes.json`, `results/RESULTS.md` | Pre-specified; one run. The reports and gold records existed when the protocol was pushed; no model output on them did. |
| Section V-L, post hoc analyses (six label-free options; label draws averaged) | `check_confirmation/posthoc_check_analyses.py`, `results/posthoc_check_analyses.md` | Not pre-specified; descriptive (added in v2.16). Part A is also in `posthoc_six_options.py`. |
| Fig. 4 | `check_confirmation/figures/fig4_check_v217.py` (from `results/check_results.json`), `fig4_check.pdf`, `fig4_check.png` | Same data as v2.13; v2.17 only renames the legend entry "Text only" to "Text baselines". It shows two conditions: set C1 at medium load for the 4-bit and the 3-bit model. |
| Section V-M (further exploratory checks) and Appendix C, Tables C1 to C4 | `checklist_2026-11-28/checklist_analyses.py`, `out/checklist_results.json`, `out/checklist_episode_counts.json.gz`, `out/digest.txt`; tables made by `make_appendix_c.py` | Exploratory (added 28 Nov 2026 after a co-author's checklist). K0: refitted arms equal to the registered per-episode missed counts. |
| Section V-M.1, Table C1 (label-using adaptations, 20 draws) | `checklist_analyses.py` (K3), `out/checklist_results.json` (`K3_K10_label_arms`, `K3_C_chosen`); fixed-penalty sensitivity: `checklist_k3b.py`, `out/checklist_k3b_results.json` | L2-SP warm start = `ppr_lib.fit_head` with the FP16 logits as offsets and the FP16 scaler (anchored fit); draws 0-4 are the registered draws, 5-19 use the same rule. |
| Section V-M.2 (20 label draws) and V-M.7 (non-inferiority, equivalence, relative effects, precision) | `out/checklist_results.json` (`K3_K10_label_arms`, `K10_statistics`) | |
| Section V-M.3, Table C2 (unlabeled budget) | `out/checklist_results.json` (`K9_maps`, `K9_unlabelled_budget`) | Pairs drawn from the 1,000 development fitting reports only. |
| Section V-M.4 and V-M.5, Table C3 (field combinations, Shapley, margins) | `out/checklist_results.json` (`K12_propagation`) | |
| Section V-M.6, Table C4 (simulator variants) | `out/checklist_results.json` (`K13_simulator_variants`) | Same records replayed in every variant. |
| Section V-M.9, Table C4 (Qwen2.5-1.5B rows) | `checklist_2026-11-28/qwen_replication.py`, `out/qwen_results_prefix.json`, `out/qwen_results_end.json`; vectors made with `qwen_kit/`, run records in `qwen_extraction/` | Exploratory. Same development reports, code, folds, seeds and label draws as the Llama study. |
| Section V-M.8 (CPU-changed records) | `out/checklist_results.json` (`K11_cpu_margins`), from `deployment_check/folded/folded_q4.npz` and `deployment_check/out/A_cpu_mmap_ctx4096_400reports/` | |
| Section III, incident accounting | `out/checklist_results.json` (`K7_incident_accounting`) | 10,880 open incidents + 1,500 CREATE - 900 CLOSE = 11,480. |
| Fig. 1 | (diagram; no data) | |
| Table 8 | (comparison with published studies; no data) | |
| Q3_K_M model file | `check_confirmation/DEVIATIONS.md` item 1, `zenodo_v1/code/edgesar_pilot/results/model_hashes.json` | SHA-256 of the laptop file checked on 26 Nov 2026: equal to the pilot record. |

## Head fitting: which code, which folds (Section IV-A and IV-B of v2.18)

All heads are multinomial logistic regressions with an L2 penalty on standardized vectors, with C chosen from
{0.0003, 0.003, 0.03, 0.3, 3} by three-fold grouped cross-validation on held-out cross-entropy. Two implementations were used:

| Results | Heads (code) | Folds that choose C | Fitting and scoring reports |
|---|---|---|---|
| Table 1 (hidden-state arms), Fig. 2 (left), Table 3, Fig. 3 (dotted), development field diagnosis (Section V-F), cost measurement (Section V-I) | `zenodo_v1/code/edgesar_shield/shield/readout.py` (`Heads`, `fit_head`): scikit-learn `LogisticRegression` (L-BFGS, tol 1e-6, max_iter 3000) after `StandardScaler`; used by `development_study/repair_package/mission_ladder.py`, `development_study/practical_advantage/mission_gold_trace.py` and `bench_cost.py` | `GroupKFold(3)` over generation blocks (`DevData.group`, the generator's "families" of ten consecutive reports) | `shield/data.py`, `DevData.split`: five folds of the 1,000 style-A reports by generation block; per outer fold k: evaluation = fold k, calibration = fold k+1, fitting = the other three after removing exact duplicates of calibration or evaluation texts (about 520 remain) |
| Table 2 | `development_study/repair_package/ppr_lib.py` (`fit_head`; L-BFGS in the row space of the standardized training matrix) via `run_ppr.fit_heads` | three folds grouped by masked template (`template_key`) | `diag_auc.py`: five folds of the 1,000 style-A reports grouped by masked template (`group_folds`, seed of repeat 0); heads fitted on four folds and scored on the fifth; values averaged over the folds |
| Section V-G, development missions on style B (new wording) | `ppr_lib.fit_head` (see the note in `development_study/practical_advantage/wording_shift_mission.py`) | masked template | fitted on style A, scored on style B |
| First confirmation (Tables 4 to 6, B1 to B4, Fig. 2 right, Fig. 3 solid) and its exploratory analyses (V-J, V-K); check confirmation (Table 7, Fig. 4) | `ppr_lib.fit_head` via `run_ppr.fit_heads` (`fresh_confirmation/fresh_confirm.py`, `review_*.py`, `check_confirmation/check_confirm.py`) | masked template | fitted on the 1,000 development style-A reports (all of them, or the drawn label subsets) |

The label-free map (`ppr_lib.AffineMap`) chooses its ridge strength with three folds grouped by masked template in every study. Its means
and scales are computed once from all its fitting reports.

**Earlier numbering.** Drafts v2.14 to v2.18 use the numbering of this manifest (v2.18 adds Tables C1 to C4). Draft v2.13 called Tables B1 to B4 "Supplementary Tables S1 to S4" (`supplementary/`, same numbers). Drafts up to
v2.12 numbered the exploratory tables 6 to 11; `fresh_confirmation/REVIEW_RESULTS.md` keeps that numbering.

**Note on `development_study/README_SUPPLEMENT.md`.** Its "Protocol file note" says that line 3 of `PROTOCOL_PRACTICAL_ADVANTAGE.md` was
reworded in copies given to later mock reviews. That line mentions the score of an earlier mock review; it was reworded so that later
mock reviews were not anchored on that score. The file in this repository is the original, byte for byte (its checksum is unchanged).
