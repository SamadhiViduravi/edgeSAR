# Allocator-time sensitivity check (written BEFORE the run)

Status: FIXED. 2026-11-14. Approved by Samadhi in chat on 2026-11-14. Development data only.

Why: the simulation charges 0.02 s of decision time per allocator run (docs/DEVIATIONS.md D-12). On Samadhi's PC the allocator needed a median of 0.22 ms per run (bench 2026-11-14), about 90 times less. This check asks whether the iteration-1 conclusions depend on that assumption. It is a check of a simulation assumption, not a tuning round and not a novelty claim.

What changes: `--alloc-cost 0.00022` (seconds per allocator run). Nothing else: same arms, thresholds, alpha, K, b, d_v, seeds, folds, episodes, readouts.
Readouts: q4 (competent) and raw (unadapted). Output: results/iter1/alloc022_q4 and results/iter1/alloc022_raw. The original 20 ms results (results/iter1/q4, raw) are NOT changed and stay the headline.
Report: missed share per arm at L/M/H; the paired comparisons B3-G1, B3-A1, B3-A8, A8-A1; whether any CI status or sign flips, and by how much.
Rule: the finding is "ASSUMPTION MATTERS" if any of those four paired differences at level M changes by 0.3 pp or more, or changes its CI status (contains 0 or not); otherwise "ASSUMPTION DOES NOT MATTER". No new label (SUPPORTED etc.) is given.
Stopping: run once. No other setting is changed. The run writes nothing into results/iter1/q4 or raw.
