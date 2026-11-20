# EdgeSAR: moving a task-record classifier from FP16 to 4-bit

Code and data of the study *"Moving a Task-Record Classifier from FP16 to 4-Bit: Adaptation Choice, Label Budget and Missed Incidents in Simulated Multi-UAV Flood Rescue"* (S. V. Dissanayake and M. Edirisooriya, Informatics Institute of Technology / University of Westminster; draft for IEEE Access, 2026).

A classifier with three heads (action, sensor, priority) reads the last-token hidden vector of Llama 3.2 1B Instruct (llama.cpp GGUF files). Its task records drive a bounded CBBA allocator for three simulated UAVs in a flood rescue. The study measures how many incidents are verified late or never when the FP16 classifier is moved to the 4-bit Q4_K_M model: unchanged, recentred, with a label-free alignment map, or retrained with 100, 300 or 1,000 labels. All reports are synthetic.

**Dataset (permanent record):** EdgeSAR-Reports-1400, [doi:10.5281/zenodo.24218688](https://doi.org/10.5281/zenodo.24218688) (data CC BY 4.0, code MIT).

## What is in this repository

| Folder | What it is |
|---|---|
| `zenodo_v1/` | The Zenodo release v1, unchanged: 1,400 reports (`data/cases.jsonl`), the seeded generator, the study code (`code/edgesar_pilot`, `edgesar_heads`, `edgesar_shield`, `V1`), `DATA_CARD.md`, checksums. Check it with `python zenodo_v1/verify_dataset.py`. |
| `code/repair_package/` | `ppr_lib.py` and `run_ppr.py`: the classifier heads, recentring, alignment map and retraining used by the fresh confirmation. |
| `development_study/` | The development (exploratory) study: repair and label-budget experiments, mission ladder, AUC diagnosis, text baselines (TF-IDF, keyword rules), wording shift, cost and load levels, each with its hashed protocol and outputs. See `development_study/README_SUPPLEMENT.md`. |
| `fresh_confirmation/` | The pre-registered confirmation on 7,000 fresh reports: frozen protocol, scripts and SHA-256 hash file, timestamp record, fresh reports, episode manifest, per-episode outcomes of every arm, registered results, run notes, and the exploratory analyses added after review. See `fresh_confirmation/README.md`. |
| `make_root.py` | Builds the folder layout that the confirmation scripts expect (`--root`). |
| `app_v1_demo/` | The first web prototype of the project (Next.js + FastAPI mission-control app and an allocation demo page, October 2026). Kept for the project record; **not used for any result in the paper**. See `app_v1_demo/README_FIRST.md`. |

Not included (Llama 3.2 licence and size): the GGUF model files and the saved hidden-state vectors. The model build is llama.cpp b11901; file names and hashes are in `zenodo_v1/DATA_CARD.md`.

## Quick checks (Python 3.12+, numpy)

    python zenodo_v1/verify_dataset.py
    cd fresh_confirmation
    python rebuild_primary.py episode_outcomes.csv

The second command rebuilds the pre-registered primary table (four hypotheses, paired episode-bootstrap intervals, Holm-adjusted p-values) from the per-episode outcomes and checks every number against `results.json`. It should end with `ALL EQUAL TO results.json: True`.

## Full rerun

    python make_root.py ROOT
    # then follow fresh_confirmation/README.md (needs the three GGUF files, llama.cpp b11901 and a GPU or CPU for the vectors)

## Main pre-registered results (set A, medium load, 300 episodes, 11,480 incidents)

| Comparison | Missed share, difference in percentage points (95% CI) |
|---|---|
| Q4 with FP16 classifier unchanged minus FP16 | +3.43 (+2.98 to +3.88) |
| Label-free alignment map minus unchanged | -3.36 (-3.87 to -2.85) |
| Retrained with 1,000 labels minus unchanged | -3.11 (-3.62 to -2.60) |
| Map minus retrained with 100 labels (mean of 5 draws) | -2.72 (-3.14 to -2.30) |

The alignment map is an existing method (Duan, 2026), not a contribution of this work. Limits: synthetic, template-based reports; one model and one quantisation recipe; one simulator; no test on a real 2 GB device.

## Licence
Code: MIT (`LICENSE`). Data: CC BY 4.0 (`LICENSE-DATA.md`). Cite with `CITATION.cff` or the Zenodo DOI.
