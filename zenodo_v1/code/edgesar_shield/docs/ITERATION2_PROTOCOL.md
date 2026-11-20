# Iteration 2 (model-side round): protocol (written BEFORE any model file is made)

Status: FIXED. Written 2026-11-14. Approved by Samadhi in chat on 2026-11-14 (all three files; calibration text from a new generator seed, text only). Hashed before the first command (`results/iter2/PROTOCOL.sha256`). Supersedes the draft `ITERATION2_PROTOCOL_PROPOSED.md`.
Data: DEVELOPMENT only. Primary: the 1,000 style-A reports (saved vectors, 5 family folds, overlay episodes, levels L/M/H, arrival seeds 1-3, always commit). Style B (400): exploratory only, examined many times before. No fresh evaluation case is generated or read.

## 1. Question

Does a 4-bit file made with an importance matrix calibrated on in-domain task text reduce the remaining Q4 decision gap (about 0.5 to 1.1 points missed incidents at level M) better than the plain Q4_K_M, an importance matrix on generic text, and one more bit (Q5_K_M)? This is also the "realistic stronger quantisation baseline" that the project's research prompt requires.

## 2. Files (all from the same Llama-3.2-1B-Instruct-f16.gguf, sha256 1f33ad43...ae146, llama.cpp b11901, same machine)

| Key | How made |
|---|---|
| Q4 (existing) | plain Q4_K_M, no imatrix (already extracted; unchanged) |
| Q4_IMX_DOMAIN | `llama-imatrix` on calib_domain (300 rendered prompts), then `llama-quantize --imatrix <it> ... Q4_K_M` |
| Q4_IMX_GENERIC | same with a standard generic calibration text (bartowski `calibration_datav3.txt` or wikitext-2 raw; the file used is hashed in the manifest) |
| Q5 | plain Q5_K_M, no imatrix |

Calibration text for the domain file: 300 rendered prompts (system prompt + open-incident table + report) from a new generator run (seed 20261115, 600 cases generated, strictly disjoint in text from all 1,400 evaluation reports, 300 chosen by a seeded shuffle). Text only: no gold labels are in the calibration files. Hashes: `calib/CALIB_SHA256.txt`. Special-token strings are used only if `llama-imatrix` supports parsing them; otherwise the plain version is used. This choice is made by the script and logged.

## 3. Vectors and readouts

Vectors: the unchanged extraction pipeline (`edgesar_heads/02_extract.py`, prompt P1, pooling last, positions `end` and `prefix`), run from a copy of that folder with the model directory changed by environment variable, so no frozen file changes. A check first: the same pipeline on the existing plain Q4_K_M file, 50 reports, must reproduce the saved vectors (maximum absolute difference reported).
Readouts per new file, as before: (a) MATCHED = heads retrained on that file's vectors on FIT reports; (b) ALIGNED = FP16 heads on the affine-mapped vectors (map fitted on FIT pairs only, the verified implementation `tools/verify_alignment.py`). Each at `end` and `prefix`. Heads use the package's `readout.Heads` unchanged.

## 4. Outcomes (fixed now)

* Primary: missed share (late + unverified) at level M, 3 seeds pooled, paired by episode, 95% episode-bootstrap CI. Readout MATCHED at `prefix`. Comparison: Q4_IMX_DOMAIN minus Q4 (plain).
* Secondary (all reported, none chosen later): levels L and H; `end`; ALIGNED; Q4_IMX_GENERIC minus Q4; Q4_IMX_DOMAIN minus Q4_IMX_GENERIC; Q5 minus Q4; each against FP16 at the same readout and position; whole-record accuracy on EVAL; repaired / newly wrong counts relative to plain Q4.

## 5. Decision rule (fixed now)

* **SUPPORTED on DEV**: CI(Q4_IMX_DOMAIN minus Q4) upper bound < 0 at M, point estimates <= 0 at L and H, AND the point estimate at M is at least half of (Q4 minus FP16) at the same readout and position.
* **NOT SHOWN**: anything else.
* "In-domain matters" additionally needs CI(Q4_IMX_DOMAIN minus Q4_IMX_GENERIC) upper bound < 0 at M; if the generic file does as well, only "an importance matrix helps" can be said, not "in-domain".
* Q4_IMX_GENERIC and Q5 are reported either way. Q5 is the cost reference (one more bit; larger file), not a competing method.

## 6. Stopping rule

Each file is made once with the settings above. No calibration size, context size, chunk count or quantisation type is changed after seeing results. A failed command is fixed and logged and the same step repeated; a changed setting needs a new protocol and written approval. After this round there is no further tuning round before the supervisors have seen the work. Results are kept whatever they are.

## 7. Not done here

Fresh evaluation, OSF, slides, paper, other bit-widths, AWQ/GPTQ/SpinQuant (different runtimes; separate system comparisons), a second IoT task.
