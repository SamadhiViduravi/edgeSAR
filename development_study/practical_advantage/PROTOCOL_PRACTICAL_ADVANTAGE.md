# Practical-advantage check: protocol (written BEFORE any run), 14 Nov 2026

Trigger: gate review 60% (REVISE): "why choose alignment over Q4 retraining?" The development results cannot answer it: the cost of the map was never measured, and no result tests the map where labels are scarce at mission level. This is the specific issue; the standing rules (no tuning round, no confirmation data, no new model run) stay in force.

Data: the 1,000 style-A development reports, the saved vectors (`prefix` position), the same 5 outer folds, 3 arrival seeds, level M, bounded CBBA allocator, always-commit policy, the same episodes as `mission_ladder.py`. Everything here is EXPLORATORY development evidence. No new model extraction. No hyper-parameter is changed: heads use `readout.fit_head` (C grid 0.0003..3, 3-fold grouped CV, tol 1e-6); the map uses `ppr_lib.AffineMap` (lambda by held-out pair error, no labels).

## Part A. Cost (measured here, on the cloud CPU, 1 thread; not the laptop, not the target device)
For each outer fold (FIT reports only) and 3 repeats, each step in a fresh process:
1. Retrain Q4 heads (3 heads) on the FIT reports' Q4 vectors with gold labels.
2. Train FP16 heads (needed by the map path; shared prerequisite, reported separately).
3. Fit the affine map on FIT pairs (F16, Q4), no labels.
Report: wall-clock seconds, CPU seconds, peak process memory (maximum resident set), artifact size (numbers and bytes at float32), and inference per report (microseconds, median of 20,000 calls) for: retrained heads as shipped (folded), map unfolded, map folded. Check folding numerically (max absolute logit difference).
Extraction is charged to BOTH paths using the earlier laptop medians (GPU F16 202 ms, Q4 189 ms; CPU F16 549 ms, Q4 303 ms per report), never free for one path.
Two reuse conditions:
- (a) labelled reports and both precisions' vectors already exist: only fit costs count.
- (b) new reports are available and cannot be labelled (or only N can): the map needs paired extraction of the bank; retraining needs labels for N reports plus Q4 extraction of them.
Setup cost (from scratch) and migration cost (an FP16 reader already exists, the model moves to Q4) are reported separately.

## Part B. Mission outcome with scarce labels (level M, `prefix`)
Arms: gold; f16p; q4p (all FIT labels); alnp (map, FP16 heads); recp (recentring); rawp (frozen, diagnostic); q4p_n100 and q4p_n300 (retrained on 100 or 300 FIT reports, drawn by a seeded permutation, seed 20261114 + fold; the heads are otherwise identical).
Pre-set comparisons (paired by episode): alnp - q4p_n100; alnp - q4p_n300; alnp - q4p; recp - q4p_n100; alnp - recp.
Decision rule (set now): the map shows a mission-level advantage over retraining with N labels only if the upper bound of the 95% episode-bootstrap interval of (alnp - q4p_nN) is below 0. Otherwise: NOT SHOWN. The same rule is used for 100 and 300; both are reported.
Integrity: gold, f16p, q4p, alnp, recp, rawp must reproduce the earlier counts (late, unverified, incidents) at level M exactly; if not, the run is void.

## Part C. Gold-field replacement (exploratory trace)
Bases: q4p and alnp. Variants: replace the predicted action (A), sensor (S) or priority (P) probability by the gold value, alone or combined (A, S, P, AS, AP, SP, ASP). Where gold has no sensor or priority (no-record reports), the model's own probabilities are kept. Everything else (parser, candidates, allocator, episodes) is unchanged. Report: missed share per variant, the change against the base arm and against gold (pp, paired, 95% interval), and episodes where a replacement made things WORSE. Also, per report: which fields are wrong, and whether the committed plan equals the gold plan (`pg`), for each base. This is a diagnosis inside the simulator, not evidence about real rescue operations.

## Part D. Draft confirmation design (no data generated)
Estimand, weighting, dependence structure, decision rule and sample size from the paired per-episode differences of Part B at level M. Margins 0.15, 0.25, 0.5 pp as a sensitivity set; the margin stays provisional.

## Not done here
No new extraction, no confirmation data, no tuning, no OSF registration, no change to the protocols already hashed.
