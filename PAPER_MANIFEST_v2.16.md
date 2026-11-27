# Manuscript draft v2.16: where each result comes from

This file maps every table, figure and result section of manuscript draft v2.16 (*Adapting a Hidden-State Task Classifier to a 4-Bit
Language Model: Missed Incidents and a Label-Free Check in Simulated Multi-UAV Rescue*) to the files of this repository (git tag
`paper-v2.16`). Some older READMEs and result files inside the folders use the table numbers of earlier drafts; this manifest gives the
current numbers. No result file was changed for v2.16. Zenodo version 1.2 (23 Nov 2026) holds the files up to that date; the analyses
of Sections V-I, V-J.8, V-K and V-L (`deployment_check/`, `fresh_confirmation/review_r9.py`, `fresh_confirmation/review_r10*.py`,
`check_confirmation/`) and the files added with this tag are only in this repository.

| Manuscript v2.16 | Files | Notes |
|---|---|---|
| Section III (system), Appendix A (prompt) | `zenodo_v1/code/` (study code; prompt template in `zenodo_v1/code/edgesar_pilot/common.py`), `code/repair_package/` | Allocator, simulator, heads, recentering and the label-free map. |
| Table 1, Fig. 2 (left): development results by load | `development_study/repair_package/out_mission/`, `development_study/practical_advantage/out_levels/`, `out_text_baselines/` | Check: `python development_study/practical_advantage/verify_from_records.py ...` (see `development_study/README_SUPPLEMENT.md`). |
| Table 2: AUC and accuracy, development | `development_study/repair_package/diag_auc.py`, `out_diag/AUC_DIAG.md`, `out_diag/auc_diag.json` | Each AUC cell gives the value from class logits / from softmax probabilities, as in `AUC_DIAG.md` (style A, action head). |
| Table 3, Fig. 3 (dotted): development label budget | `development_study/practical_advantage/mission_gold_trace.py`, `out_trace/` (`TRACE_RESULTS.md`) | Also the development field diagnosis of Section V-F. |
| Fig. 3 (drawing) | `fresh_confirmation/figures/fig3_labels_v216.py`, `fig3_labels.pdf`, `fig3_labels.png` | Added in v2.16: the four reference levels are labeled with their values. The numbers and their source files are listed in the script. |
| Section V-A: generated JSON against hidden-state readout | `zenodo_v1/code/edgesar_pilot/results/pilot_report.md` (JSON, rules, TF-IDF), `zenodo_v1/code/edgesar_heads/results_heads/` (hidden-state heads) | |
| Section V-G: text baselines, new wording | `development_study/practical_advantage/out_text_baselines/`, `out_wording_shift/`; fresh: `fresh_confirmation/results.json` | |
| Section V-H: what did not help | `zenodo_v1/code/edgesar_shield/` (runtime check in `shield/`; importance-matrix files in `results/iter2/ITER2_SUMMARY.md`) | |
| Section V-I: cost and CPU deployment | `development_study/practical_advantage/bench_cost.py`, `out_cost/`; `deployment_check/` (see `deployment_check/MEMORY_FIELDS_NOTE.md`) | |
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
| Sections IV-G and V-L, Table 7 (check confirmation) | `check_confirmation/PROTOCOL_CHECK_CONFIRM.md` (tag `check-protocol-2026-11-26`), `results/check_results.json`, `results/check_episodes.json`, `results/RESULTS.md` | Pre-specified; one run. The reports and gold records existed when the protocol was pushed; no model output on them did. |
| Section V-L, post hoc analyses (six label-free options; label draws averaged) | `check_confirmation/posthoc_check_analyses.py`, `results/posthoc_check_analyses.md` | Not pre-specified; descriptive (added in v2.16). Part A is also in `posthoc_six_options.py`. |
| Fig. 4 | `check_confirmation/figures/fig4_check_v215.py` (from `results/check_results.json`), `fig4_check.pdf` | Same data as v2.13; larger labels (since v2.15). |
| Fig. 1 | (diagram; no data) | |
| Table 8 | (comparison with published studies; no data) | |
| Q3_K_M model file | `check_confirmation/DEVIATIONS.md` item 1, `zenodo_v1/code/edgesar_pilot/results/model_hashes.json` | SHA-256 of the laptop file checked on 26 Nov 2026: equal to the pilot record. |

**Earlier numbering.** Drafts v2.14 to v2.16 use the numbering of this manifest. Draft v2.13 called Tables B1 to B4 "Supplementary Tables S1 to S4" (`supplementary/`, same numbers). Drafts up to
v2.12 numbered the exploratory tables 6 to 11; `fresh_confirmation/REVIEW_RESULTS.md` keeps that numbering.

**Note on `development_study/README_SUPPLEMENT.md`.** Its "Protocol file note" says that line 3 of `PROTOCOL_PRACTICAL_ADVANTAGE.md` was
reworded in copies given to later mock reviews. That line mentions the score of an earlier mock review; it was reworded so that later
mock reviews were not anchored on that score. The file in this repository is the original, byte for byte (its checksum is unchanged).
