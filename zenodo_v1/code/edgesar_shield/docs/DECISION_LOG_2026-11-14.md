# Decision log (new file; no older file changed)

## D-20  Fresh test uses both readers (decided by Samadhi, 2026-11-14)
- The fresh test covers the competent Q4 reader (retrained on Q4 vectors) AND the unadapted reader (FP16 head on Q4 vectors).
- Disclosure for the paper: this choice was made after seeing the DEV results of iteration 1.
- Still not started: the fresh run (M8), OSF, slides, paper.

## D-21  Speed and memory measured on Samadhi's laptop (2026-11-14)
- Windows 11, Python 3.12.6, 15.7 GB RAM, RTX 2050 4 GB. Folders: `results/bench_20261114T090508` (GPU, -ngl 99) and `results/bench_20261114T091111` (CPU, -ngl 0).
- Tests on this machine: `tests/test_iter1.py` 17 passed; `tests/test_fresh.py` 14 passed, 1 skipped (the skip is the bit-for-bit test that applies only when the numerical environment matches the cache; by design).
- Numbers are in `SUPERVISOR_SUMMARY_2026-11-14.md` section 4.
- Finding: real allocator run 0.22 ms vs 20 ms charged in the simulation (D-12). The protocol forbids changing parameters, so iteration-1 results are NOT rerun. The simulation is cautious about allocator delay. A rerun at 0.2 ms would be a new sensitivity run and needs written approval.
- Finding (corrected 2026-11-14 after review): on the GPU, Q4 is only about 6% faster than FP16 (189 vs 202 ms) and slower than Q8 (176 ms); on CPU it is 1.8 times faster than FP16 (303 vs 549 ms).
- The "text to decision" times are the SUM of three medians (model + heads + Shield), not a measured end-to-end percentile. A true per-report end-to-end timing was not done.

## D-22  Repair arm for the fresh test (recommendation, needs Samadhi's OK)
- Source: the other chat's repair experiments on the same DEV data (project docs `EdgeSAR_REPAIR_results_exp1/exp2/mission`). Its mission run reproduced our package counts for gold, q4, f16, q8, rec and raw exactly, and its head refits matched the cache. We have NOT re-run its linear-map arm ourselves.
- Result there (level M): raw 16.49%, recentred 8.01%, retrained 7.41%, linear map 6.81%, FP16 6.30%.
- Recommendation: add the label-free linear map as the repair arm of the fresh test, next to the two readers of D-20. The fresh FP16 vectors are needed anyway for the FP16 reference, so it adds no extra generation. Shield stays a secondary result.
- DONE 2026-11-14 (Samadhi answered yes to D-22): the map was reproduced in this package by the other chat's code (identical counts) and by independent code (identical counts), with shuffled-pair and Q8 controls and a folding check. See `docs/REPRO_ALIGNMENT_PROTOCOL.md` and `results/repro_alignment/repro.json`.

## D-23  Gate readiness (2026-11-14)
- Mock supervisor gate (Claude, not official): novelty about 4 of 10, so FAIL; the alignment is prior art (Duan arXiv 2606.15980; Bysani NeurIPS 2026 workshop RoboPAD). See `docs/GATE_PACKAGE_2026-11-14.md`.
- Blockers: public dataset link; one verified IEEE Access reference; a second task or a setting where the check adds value.
- No new variant is run to obtain a PASS (stopping rule, protocol section 4).

## D-24  Iteration 2 (model-side round) and timing check approved (Samadhi, 2026-11-14)
- Approved: one model-side round on DEV with three new files (Q4 with in-domain imatrix, Q4 with generic imatrix, Q5_K_M). Protocol `docs/ITERATION2_PROTOCOL.md`, hashed `results/ITER2_PROTOCOL.sha256`. Calibration text: new generator seed 20261115, 300 prompts, text only, strictly disjoint in text from the 1,400 reports (hashes in `calib/CALIB_SHA256.txt`).
- Approved: allocator-time sensitivity check (0.22 ms instead of 20 ms), protocol `docs/ITERATION1_ALLOC_SENSITIVITY.md`; original 20 ms results unchanged.
- Gate route (Samadhi): he runs Steps 3 and 4 himself in another chat; if the result is above 70% he goes to Mr. Maninda. Claude's mock scores are not official.
- Still not started: fresh evaluation, OSF, slides, paper draft.

## D-25 (2026-11-14, ~12:30) Amendment 1: matched-budget control file
* Seen after the first run (no result looked at): in-domain imatrix used 181 chunks (about 185k tokens); generic file is 279,515 bytes (about 70k tokens). Unequal budgets would confuse "in-domain" with "more text".
* Samadhi approved (his own answer): add ONE control file `Q4_IMX_DOMAIN_M` = same in-domain text, cut to the generic file's chunk count (`--chunks N`, N read from the generic imatrix log). Primary test and decision rule unchanged. Hash: `results/ITER2_AMENDMENT1.sha256`.
* Rule: no analysis is run on partial vectors. The analysis waits until all four files exist.
* Real flags of b11901 confirmed by the first run: `llama-imatrix -m F16 -f TEXT -o X.gguf -ngl 99 -c 1024 --parse-special` and `llama-quantize --imatrix X.gguf F16 OUT Q4_K_M` worked; identity check PASS (max abs diff 0.0, both positions). `--chunks` is checked in the help text before use.

## D-26 (2026-11-14, ~12:30) Literature facts brought back by Samadhi (Perplexity + ChatGPT)
* IEEE Access reviewer page (as quoted by Perplexity; I could not fetch it, please keep the link): "IEEE Access articles are not necessarily expected to have a high level of novelty, but they should be distinct from previous publications and technically sound." Four questions: contributes to knowledge, technically sound, comprehensive, references sufficient. https://ieeeaccess.ieee.org/reviewers/reviewer-guidelines/
  This does NOT replace the university supervisor gate (novelty >= 7).
* Related paper: Kharinaev et al., "Investigating the Impact of Quantization Methods on the Safety and Reliability of Large Language Models". It exists as arXiv 2502.15799 (checked by me: 66 quantized variants, 4 safety benchmarks, OpenMiniSafety dataset). ChatGPT states it appeared in IEEE Access 14, 96771-96793, 2026, DOI 10.1109/ACCESS.2026.3703899. The arXiv page lists no journal reference, so the IEEE Access details are NOT verified by me. Samadhi must open the DOI once and confirm title/volume before it is cited.
* imatrix prior (Perplexity): no controlled generic-vs-in-domain study found for 1B-3B models. Other numbers (4-6 points, 31% PPL error) come from different models and metrics and must not be used as an expected result for EdgeSAR.

## D-27 (2026-11-14, ~14:00) Iteration 2 result: NOT SHOWN
* All four vector sets verified (1400 x 2048, finite, distinct; imatrix logs: generic 62 chunks, matched domain 62 chunks, full domain 181 chunks). Analysis run once, 1135 s, integrity check True.
* Primary: in-domain imatrix minus plain Q4 at M, prefix, MATCHED = -0.15 pp (-0.68 to +0.40); half of gap needed -0.29. Label NOT SHOWN. In-domain-matters: not demonstrated (matched minus generic -0.13, -0.54 to +0.27). More-text: not demonstrated (+0.24, -0.16 to +0.66).
* Q5 is a cost reference only; a Q5-only gain is not a Q4 repair (ChatGPT's point, accepted).
* ChatGPT correction accepted: "more text helps" needs full-domain minus matched-domain CI below 0, not only failing to beat generic.
* No new variant is added to try to reach SUPPORTED. Full numbers: results/iter2/ITER2_SUMMARY.md.

## D-28 (2026-11-14, ~15:10) Record-level analysis finished (secondary outcome of protocol section 4)
* Done after ChatGPT's review, because the protocol listed repaired / newly-wrong counts and they had not been computed. Same models, splits and fitting code; no new tuning. Integrity: accuracies equal to the mission run. Family-clustered bootstrap (1,000 records, 100 families), not arrival seeds.
* Result: in-domain Q4 record accuracy +1.5 pp over plain Q4 (CI -0.5 to +3.6, not demonstrated); Q5 +3.7 pp (CI +2.0 to +5.4) and equal to FP16; in-domain vs generic +1.5 to +1.7 pp (exploratory, not stable across positions). Primary mission verdict unchanged: NOT SHOWN.
* Wording corrections accepted (ChatGPT): "no effect" -> "not demonstrated"; "0.5 pp detection limit" removed (precision depends on effect, variability and independent units); "no cheap repair works" -> "the tested methods did not demonstrate the required mission-level improvement under these conditions".
* Not started (standing rule): fresh run, OSF, slides, paper draft.

## D-29 (2026-11-14, ~16:00) Submission package written (Samadhi's own go-ahead given in his 15:13 message: stop looping, write now)
* Written from existing results only: `submission/EdgeSAR_PP_Proposal_2026-11-14.docx` (for Mr. Maninda and Dr. Achala; no slides), `submission/EdgeSAR_Paper_Draft_IEEE_Access_2026-11-14.docx` (draft v1), `submission/GATE_INPUT_EXACT_2026-11-14.md` (idea + 3 papers + the two original prompts word for word).
* No experiment, extraction, OSF registration or slides started. Every iteration-2 number was checked against ITER2_RESULTS.json and ITER2_RECORDS.json; DEV level-M numbers against DEV_main.json.
* Real blockers for the gate: public dataset link; verify the IEEE Access DOI. Open for the thesis: ethics form, fresh run, device/energy, extra evidence the supervisors choose.
