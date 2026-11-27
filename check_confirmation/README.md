# Confirmation of the label-free mission check (set C)

This folder tests the label-free mission check of the manuscript (Sections IV-F, IV-G, V-K and V-L) on **new reports whose model
outputs did not exist when the protocol was frozen**. The protocol, the analysis script, the new reports and the GPU extraction script
were pushed to this repository with the tag `check-protocol-2026-11-26` (commit 36fd21e, 26 Nov 2026, 06:07 +05:30) **before** the
hidden vectors were extracted on the laptop (06:10 to 06:47 +05:30). The analysis was then run once, unchanged.

**The check:** replay the mission episodes with the old (FP16) classifier's records as the truth of the simulator. The check penalty of
a candidate classifier is its missed share minus that of the old classifier, both computed with the old records as the truth; the true
penalty is the same difference computed with the gold records. The check needs no labels.

## Files

| File or folder | What it is |
|---|---|
| `PROTOCOL_CHECK_CONFIRM.md` | The frozen protocol: data, 39 candidates per target, measures, hypotheses H1 to H4 (all must hold) and H5 (secondary). |
| `FROZEN.sha256` | SHA-256 of every frozen file. |
| `check_confirm.py` | The analysis (run once, unchanged; SHA-256 `2ff5ee9e...`). |
| `gen_set_c.py`, `cases_C.jsonl`, `generation_manifest_C.json` | The 5,000 new reports (C1: 3,000, development wording; C2: 2,000, new wording) and how they were generated. |
| `extract_c.py`, `RUN_EXTRACT_C.bat` | The GPU step (llama.cpp b11901; FP16, Q4_K_M and Q3_K_M). |
| `results/check_results.json` | All results: hypotheses, every condition, every candidate, the misspecified simulators, the unlabeled-budget analysis. |
| `results/check_episodes.json` | Missed counts per episode, arm, truth and simulator (the input of every number). |
| `results/check_run_log.txt` | The log of the single analysis run (start, end, timing of each task, hypothesis lines). |
| `results/RESULTS.md` | A readable summary of `check_results.json`. |
| `logs/` | The extraction report (anchor check, model file sizes, SHA-256 of the vector files), the vector metadata and the `llama-server` logs of the GPU step. The vectors themselves are not redistributed (Llama 3.2 licence); `extract_c.py` re-creates them. |
| `exploratory_R11_setsAB/` | The same frozen script run on the first confirmation's sets A and B (Q4_K_M only; exploratory analysis R11, started before the protocol was frozen and not looked at before freezing). |
| `DEVIATIONS.md` | Notes on how the run relates to the protocol. |
| `posthoc_check_analyses.py`, `results/posthoc_check_analyses.md` | Post hoc and descriptive (not pre-specified, added with tag `paper-v2.16`; Section V-L): (A) the check over the six label-free options only, per condition; (B) the five label draws of each method-and-budget combination averaged (15 options per condition), with the Spearman correlation of the check, of the record flips and of the labeled accuracy drop. `python posthoc_check_analyses.py results/check_results.json > results/posthoc_check_analyses.md` |
| `posthoc_six_options.py`, `results/posthoc_six_options.md` | Part A alone, as prepared for draft v2.15 (same numbers). |
| `figures/fig4_check_v215.py`, `figures/fig4_check.pdf`, `figures/fig4_check.png` | Fig. 4 of the manuscript (drafts v2.15 and v2.16), drawn from `results/check_results.json` (`python figures/fig4_check_v215.py results/check_results.json figures`). |

## Rerun

    python make_root.py ROOT            # from the repository root; add the saved development vectors (not redistributed)
    python check_confirm.py --root ROOT --cases cases_C.jsonl --vectors vectors_C --dev-vectors vectors_C --out out_checkC --workers 2

The vectors in `vectors_C/` come from `RUN_EXTRACT_C.bat` (needs the three GGUF files, llama.cpp b11901 and a GPU or CPU). The 3-bit file
`Llama-3.2-1B-Instruct-Q3_K_M.gguf` was made from the FP16 file with `llama-quantize` without an importance matrix
(`zenodo_v1/code/edgesar_pilot/make_quants.py`; size and SHA-256 in `zenodo_v1/code/edgesar_pilot/results/model_hashes.json`).
