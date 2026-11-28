# EdgeSAR: moving a task-record classifier from FP16 to 4-bit

Code and data of the study *"Adapting a Hidden-State Task Classifier to a 4-Bit Language Model: Missed Incidents and a Label-Free Check in Simulated Multi-UAV Rescue"* (S. V. Dissanayake, A. Aponso and M. Edirisooriya; Informatics Institute of Technology, Colombo, and Curtin University; manuscript in preparation for IEEE Access, 2026).

A classifier with three heads (action, sensor, priority) reads the last-token hidden vector of Llama 3.2 1B Instruct (llama.cpp GGUF files). Its task records drive a bounded CBBA allocator for three simulated UAVs in a flood rescue. The study measures how many incidents are verified late or never when the FP16 classifier is moved to the 4-bit Q4_K_M model: unchanged, recentred, with a label-free alignment map, or retrained with 100, 300 or 1,000 labels. All reports are synthetic.

**Code and confirmation package (permanent record):** [doi:10.5281/zenodo.24454853](https://doi.org/10.5281/zenodo.24454853) (version 1.2, 23 Nov 2026). The analyses added after that version (Sections V-I, V-J.5, V-K, V-L and V-M of the manuscript, among them `deployment_check/`, `check_confirmation/` and `checklist_2026-11-28/`) are only in this repository; `PAPER_MANIFEST_v2.20.md` lists where each one is. That record's archive file is named `EdgeSAR_code_and_confirmation_v1.3_for_Zenodo.zip`; "v1.3" is our internal package number, the record's version is 1.2.

**Version that accompanies manuscript draft v2.20:** git tag `paper-v2.20` (https://github.com/SamadhiViduravi/edgeSAR/tree/paper-v2.20). `PAPER_MANIFEST_v2.20.md` maps every table (1 to 8, A1 and A2, and S1 to S6 of the online appendix), figure (1 to 4) and result section of that draft to the files here, and lists which head-fitting code and which cross-validation folds each result used. New in `paper-v2.20`, without changing any earlier result file: `ONLINE_APPENDIX_v2.20.pdf`, the online appendix of the shorter draft v2.20 (prompt template, Tables S1 to S6 and the definitions of Section V-M; made from the v2.19 source by `paper_v2.20_online_appendix/make_online_appendix_v220.py`), and `checklist_2026-11-28/checklist_k14.py` and `checklist_k14_post.py` with their outputs (Section V-M.3 and the lower rows of Table A1: the label-free map and pseudo-label retraining fitted only on reports that the FP16 classifier never saw). `paper-v2.18` added `checklist_2026-11-28/`, the exploratory analyses of Section V-M and Appendix C (stronger label-using adaptations with 20 label draws, the unlabeled budget of the map, all combinations of the field diagnosis with Shapley shares, decision margins, simulator variants, non-inferiority and equivalence, the CPU-changed records, and the scripts for a second model family). `paper-v2.17` (draft v2.17) added the manifest with the head-fitting code and folds and the Fig. 4 legend "Text baselines"; `paper-v2.16` added the post hoc analyses of Section V-L and the figure scripts; a tag `paper-v2.15` was prepared but never published. Earlier tags: `paper-v2.13` (results of the check confirmation), `check-protocol-2026-11-26` (the protocol, analysis script, reports and GPU script of the check confirmation, pushed before the new vectors were extracted), `paper-v2.12`, `paper-v2.10` and `paper-v2.8`.

**Dataset (permanent record):** EdgeSAR-Reports-1400, [doi:10.5281/zenodo.24218688](https://doi.org/10.5281/zenodo.24218688) (data CC BY 4.0, code MIT).

## What is in this repository

| Folder | What it is |
|---|---|
| `zenodo_v1/` | The Zenodo release v1, unchanged: 1,400 reports (`data/cases.jsonl`), the seeded generator, the study code (`code/edgesar_pilot`, `edgesar_heads`, `edgesar_shield`, `V1`), `DATA_CARD.md`, checksums. Check it with `python zenodo_v1/verify_dataset.py`. |
| `code/repair_package/` | `ppr_lib.py` and `run_ppr.py`: the classifier heads, recentring, alignment map and retraining used by Table 2, the development missions on style B and both confirmations (the development missions on style A used `zenodo_v1/code/edgesar_shield/shield/readout.py`). |
| `development_study/` | The development (exploratory) study: repair and label-budget experiments, mission ladder, AUC diagnosis, text baselines (TF-IDF with incident-context tokens, keyword rules), wording shift, cost and load levels, each with its hashed protocol and outputs. See `development_study/README_SUPPLEMENT.md`. |
| `fresh_confirmation/` | The pre-specified confirmation on 7,000 fresh reports: frozen protocol, scripts and SHA-256 hash file, timestamp record, fresh reports, episode manifest, per-episode outcomes of every arm, registered results, run notes, and the exploratory (not pre-specified) analyses, including the label accounting of Table 6 (`review_r7.py`), the overlap by development population (`review_overlap.py`), the decision-level recalibration comparator (`review_r9.py`) and the label-free mission check (`review_r10.py`, `review_r10_analysis.py`). See `fresh_confirmation/README.md`. |
| `check_confirmation/` | The pre-specified confirmation of the label-free mission check (set C, 5,000 new reports; 4-bit and 3-bit models; 39 candidate classifiers; 12 conditions): frozen protocol and hash file, analysis and extraction scripts, the new reports, the results (`results/check_results.json`, per-episode counts, run log, `results/RESULTS.md`), the extraction report and server logs, the exploratory run R11 on sets A and B, and `DEVIATIONS.md`. See `check_confirmation/README.md`. |
| `supplementary/` | Tables B1 to B4 of the manuscript (Appendix B; exploratory analyses of the first confirmation), as Markdown and Word; the files keep their draft-v2.13 names (S1 to S4). See `supplementary/README.md`. |
| `deployment_check/` | The CPU deployment runs of Section V-I (laptop CPU, llama.cpp b11901, four configurations A-D): scripts and exact commands, the folded classifier (`folded/folded_q4.npz`), per-report timings and records, memory samples and the `llama-server` logs. Used for memory and latency (and the service time of the delay analysis). Units are MiB; see `deployment_check/MEMORY_FIELDS_NOTE.md`. |
| `checklist_2026-11-28/` | Exploratory analyses of Section V-M and Appendix C (added 28 Nov 2026): scripts, results, per-episode counts, logs, and the scripts of the second-model-family replication. See `checklist_2026-11-28/README.md`. |
| `ONLINE_APPENDIX_v2.20.pdf` | The online appendix of manuscript draft v2.20: the prompt template, Tables S1 to S6 and the definitions of the analyses of Section V-M. |
| `PAPER_MANIFEST_v2.20.md` | Where each table, figure and result section of manuscript draft v2.20 comes from, and which head-fitting code and folds each result used. |
| `make_root.py` | Builds the folder layout that the confirmation scripts expect (`--root`). |
| `app_v1_demo/` | The first web prototype of the project (Next.js + FastAPI mission-control app and an allocation demo page, October 2026). Kept for the project record; **not used for any result in the paper**. See `app_v1_demo/README_FIRST.md`. |

Not included (Llama 3.2 licence and size): the GGUF model files and the saved hidden-state vectors. The model build is llama.cpp b11901; file names and hashes are in `zenodo_v1/DATA_CARD.md`.

## Quick checks (Python 3.12+, numpy)

    python zenodo_v1/verify_dataset.py
    cd fresh_confirmation
    python rebuild_primary.py episode_outcomes.csv

The second command rebuilds the pre-specified primary table (four hypotheses, paired episode-bootstrap intervals, Holm-adjusted p-values) from the per-episode outcomes and checks every number against `results.json`. It should end with `ALL EQUAL TO results.json: True`.

## Full rerun

    python make_root.py ROOT
    # then follow fresh_confirmation/README.md (needs the three GGUF files, llama.cpp b11901 and a GPU or CPU for the vectors)

## Main pre-specified results (set A, medium load, 300 episodes, 11,480 incidents)

| Comparison | Missed share, difference in percentage points (95% CI) |
|---|---|
| Q4 with FP16 classifier unchanged minus FP16 | +3.43 (+2.98 to +3.88) |
| Label-free alignment map minus unchanged | -3.36 (-3.87 to -2.85) |
| Retrained with 1,000 labels minus unchanged | -3.11 (-3.62 to -2.60) |
| Map minus retrained with 100 labels (mean of 5 draws) | -2.72 (-3.14 to -2.30) |

## Confirmation of the label-free mission check (set C, pre-specified)

| Hypothesis (frozen in advance) | Result |
|---|---|
| H1: check Spearman >= 0.80 in every condition | holds (0.91 to 1.00) |
| H2: check ranks better than the share of changed records in every condition | holds (changed records 0.24 to 0.82; accuracy drop with labels 0.55 to 0.88) |
| H3: label-free option chosen by the check within 0.25 pp of the best one in every condition | does not hold (10 of 12 conditions; largest loss 0.94 pp) |
| H4: check penalty above the true penalty in at least 95% of pairs | holds (468 of 468) |
| H5 (secondary): ranking >= 0.70 against the truth of four misspecified simulators | holds (0.74 to 0.97) |

The check counts as confirmed only if H1 to H4 all hold, so it is **not confirmed as a whole**: it ranked the candidates closely, and its penalty was above the true penalty in all 468 tested pairs (an observation in these simulations, not a proven bound), but it did not always pick the best label-free option. Post hoc (not pre-specified), over the six label-free options only, its Spearman correlation was 0.75 to 1.00 (median 0.99; `check_confirmation/results/posthoc_six_options.md`).

The adaptation techniques are not a contribution of this work: recentring is mean alignment, and the label-free map is a linear stitching layer that follows the label-free realignment idea of E. Duan (2026). The contribution is the measurement. Limits: synthetic, template-based reports; one model and one quantization recipe (4-bit; 3-bit only in the check confirmation); one simulator family; no test on a real 2 GB device.

## Licence
Code: MIT (`LICENSE`). Data: CC BY 4.0 (`LICENSE-DATA.md`). Cite with `CITATION.cff` or the Zenodo DOI.
