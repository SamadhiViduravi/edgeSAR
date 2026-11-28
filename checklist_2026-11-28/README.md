# Exploratory analyses for the co-author checklist (28 Nov 2026)

These analyses answer the checklist that a co-author wrote after manuscript draft v2.17 (items 3, 5, 7, 9, 10, 11, 12 and 13). They are
reported in Section V-M and Appendix C of draft v2.18 (and, for `checklist_k14*.py`, of draft v2.19). Draft v2.20 keeps Tables C2 and C4 as Tables A1 and A2 and moves C1 and C3 to the online appendix (`ONLINE_APPENDIX_v2.20.pdf`, Tables S5 and S6). **None of them is pre-specified.** They were run after every pre-specified result
was known and change no pre-specified result. Every outcome is reported.

| File | What it is |
|---|---|
| `checklist_analyses.py` | One script for items 3, 7, 9, 10, 11 (part), 12 and 13 (sections K0 to K13 in its docstring). |
| `checklist_k3b.py` | Sensitivity of the L2-SP corrections to a fixed penalty strength (five pre-specified draws). |
| `qwen_replication.py` | Item 5: the main comparisons with a second model family (Qwen2.5-1.5B-Instruct). |
| `make_appendix_c.py` | Builds the LaTeX tables C1 to C4 of draft v2.18 and `out/digest.txt` (every number used in the text) from the result files. |
| `qwen_kit/` | The Windows scripts that downloaded the Qwen FP16 GGUF file (SHA-256 checked), made the Q4_K_M file with `llama-quantize` (llama.cpp b11901, no importance matrix) and extracted the hidden vectors with the same server settings as the Llama study. |
| `out/checklist_results.json` | All results of `checklist_analyses.py` (with the SHA-256 of the script that made them). |
| `out/checklist_episode_counts.json.gz` | Missed and total incidents per episode for every arm and simulator variant (key `variant|arm`). |
| `out/checklist_k3b_results.json` | Results of `checklist_k3b.py`. |
| `out/qwen_results_prefix.json`, `out/qwen_results_end.json` | Results of `qwen_replication.py` at the two reading positions (with the SHA-256 of the script and of the Qwen vector files). |
| `checklist_k14.py`, `checklist_k14_post.py` | Added for draft v2.19 (Section V-M.10 and lower rows of Table C2 there; Section V-M.3 and lower rows of Table A1 in draft v2.20): the label-free map and pseudo-label retraining fitted only on reports that the FP16 classifier never saw (the other half of fresh set A by episode, fresh set B, the 400 development style-B reports), and the never-verified and late counts of Section V-E. `checklist_k14_post.py` computes two quoted numbers from the saved per-episode counts. |
| `out/checklist_k14_results.json`, `out/checklist_k14_post_results.json`, `out/checklist_k14_episode_counts.json.gz`, `out/checklist_k14_run.log` | Their results (with the SHA-256 of `checklist_k14.py`), per-episode missed and total incidents for every arm, the episode halves, and the run log. |
| `qwen_extraction/` | The Qwen run records from the laptop: model files and hashes (`model_files.json`; FP16 file SHA-256 as published by the Qwen team), the quick check (`check_report.json`: prompt format, deterministic repeat, timing), the extraction report and one `.meta.json` per vector file (model hash, llama.cpp build, server settings, number of reports, SHA-256 of the vector file), the report order (`case_ids_*.json`) and the `llama-quantize` log. |
| `out/*.log` | Run logs. |

## Checks made before any new result was used
* The four fresh vector files matched the SHA-256 values in `fresh_confirmation/extraction_report.json`.
* The ten pre-specified label draws were reproduced report for report (`K0_label_draws_equal_registered`).
* The refitted arms (gold, FP16, unchanged, recentred, map, all-label retraining, both gold-sensor arms, and the five 100-label and five
  300-label draws) reproduced the registered missed count of **every episode** of set A at medium load, arrival seed 11
  (`K0_sanity_per_episode_equal`, `K0_sanity_missed`).
* Replacing all three fields by their gold values reproduces the gold records of all 6,000 set-A reports and the gold arm's missed counts.
* Qwen: both model files and all eight vector files matched their recorded SHA-256 values; the label draws equal those of the Llama study;
  the check embedded 20 reports twice with identical vectors (lowest cosine 1.0000000). The first quantization attempt failed for lack of
  memory and left an incomplete file; the fixed `qwen_download.py` renamed it and made the Q4_K_M file again (1.12 GB) before any vector was
  extracted. One extraction step was interrupted and resumed (the script saves every 100 reports and continues from the saved rows).

## How to run (Linux, Python 3.12+, numpy, scipy, scikit-learn; about 25 minutes on 2 CPU cores)

    python make_root.py ROOT          # repository root; then copy the saved development vectors into ROOT/edgesar_heads/features
    python checklist_analyses.py --root ROOT --cases fresh_confirmation/cases_fresh.jsonl --vectors <fresh vector folder> \
        --fresh-out fresh_confirmation --deploy deployment_check --out checklist_2026-11-28/out --workers 2
    python checklist_k3b.py --root ROOT --cases fresh_confirmation/cases_fresh.jsonl --vectors <fresh vector folder> \
        --fresh-out fresh_confirmation --out checklist_2026-11-28/out
    python qwen_replication.py --root ROOT --cases fresh_confirmation/cases_fresh.jsonl --qwen-vectors <qwen vector folder> \
        --fresh-out fresh_confirmation --out checklist_2026-11-28/out --workers 2
    python qwen_replication.py ... --position end --out <other folder>       # the end position (second Qwen results file)
    python make_appendix_c.py checklist_2026-11-28/out/checklist_results.json checklist_2026-11-28/out/qwen_results_prefix.json \
        checklist_2026-11-28/out/qwen_results_end.json tables

    python checklist_k14.py --root ROOT --cases fresh_confirmation/cases_fresh.jsonl --vectors <fresh vector folder> \
        --fresh-out fresh_confirmation --out checklist_2026-11-28/out --workers 2          # about 7 minutes
    python checklist_k14_post.py checklist_2026-11-28/out/checklist_k14_episode_counts.json.gz checklist_2026-11-28/out/checklist_k14_post_results.json

The hidden vectors are not in the repository (Llama 3.2 and size); `fresh_confirmation/fresh_extract.py` and `qwen_kit/` re-create them.
