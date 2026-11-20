# Iteration 2: model-side round, result (development data)

**Label by the fixed rule: NOT SHOWN.** Protocol `docs/ITERATION2_PROTOCOL.md` (hash ac3cd73a...) and Amendment 1 (hash e491afac...). Run date 2026-11-14. The package-count integrity check passed (gold, Q4 and FP16 counts equal the earlier run). Outputs: `ITER2_RESULTS.md/.json`, `analysis_run.log`, `MANIFEST.json`.

## What was tested
All files come from the same FP16 file (hash pinned). Calibration: in-domain text (full, 181 chunks), generic text (62 chunks), in-domain text cut to the same 62 chunks (control, Amendment 1), and a plain Q5_K_M (reference only, 0.91 GB, not a Q4 repair). Reading position `prefix`, readout retrained on each file's vectors (MATCHED), level M, 3 seeds pooled (intervals are optimistic because seeds reuse reports).

## Main result (level M, missed share = late + unverified)
| system | missed | minus plain Q4 (pp) | 95% CI | minus FP16 (pp) |
|---|---|---|---|---|
| FP16 | 5.98% | | | |
| plain Q4 | 6.56% | | | +0.58 (+0.09 to +1.10) |
| Q4 + in-domain imatrix (primary) | 6.41% | -0.15 | -0.68 to +0.40 | +0.44 (-0.02 to +0.88) |
| Q4 + generic imatrix | 6.30% | -0.25 | -0.75 to +0.22 | +0.33 (-0.09 to +0.76) |
| Q4 + in-domain, matched chunks (control) | 6.18% | -0.38 | -0.90 to +0.11 | +0.20 (-0.21 to +0.62) |
| Q5_K_M (reference) | 6.18% | -0.38 | -0.92 to +0.14 | +0.20 (-0.11 to +0.53) |

## Rule check (fixed before the run)
* CI upper bound of (in-domain minus plain Q4) below 0 at M: **NO** (upper bound +0.40).
* Point estimate at most 0 at L and H: yes (both).
* At least half of the Q4-FP16 gap (needs -0.29 pp, got -0.15 pp): **NO**.
* Result: **NOT SHOWN**. Kept as a result, as the protocol says.

## What can and cannot be said
* "In-domain text matters": **not demonstrated.** Matched in-domain minus generic = -0.13 pp (-0.54 to +0.27). The unmatched comparison (budgets differ) is +0.11 (-0.31 to +0.53).
* "More text helps" (full in-domain minus matched in-domain, needs CI below 0): **not demonstrated.** +0.24 (-0.16 to +0.66). The evidence is inconclusive: it does not show zero effect, it fails to show one. (Correction accepted from ChatGPT: "more text helps" needs this comparison; failing to beat generic does not by itself prove it. The Amendment 1 sentence was looser; this stricter reading is the one used.)
* An importance matrix of any kind: every point estimate is below plain Q4 (-0.15 to -0.38 pp), but no interval excludes 0. The data are compatible with a small real gain and with none.
* Q5 is not a Q4 repair. At the same reading it is also not reliably better than plain Q4 (-0.38, CI -0.92 to +0.14). Its only clear gain is with the linear map (aligned reading, q5ap minus q4ap -0.64, CI -1.05 to -0.24), which is a secondary comparison.
* The control file looks better than the primary file at the point-estimate level (-0.38 vs -0.15). That difference is within noise and was not the pre-set primary, so it is NOT a finding. Do not use it.

## Precision of this test (important for the paper)
The Q4-vs-FP16 gap at the best position is 0.58 pp (CI +0.09 to +1.10) and the paired intervals above are each about 1 pp wide. So the test is not precise enough to separate effects of a few tenths of a point from zero. This is not a fixed detection limit: precision depends on the true effect, the variability, and the number of independent units (here the 20-report episodes are built from the same 1,400 reports and seeds reuse them, so the real precision is lower than the intervals suggest). A larger independent test would narrow the intervals; it would not by itself make the contribution more novel. Many secondary comparisons are printed (about 44 per level), so a few p < 0.05 are expected by chance (for example dxm-genm at `end`, -0.69, p = 0.017).

## Not done
* The record-level counts (repaired / newly wrong, precision, net, clustered intervals) are in `ITER2_RECORDS.md` (secondary outcome, protocol section 4).
* (superseded by ITER2_RECORDS.md, secondary outcome with counts and intervals) Whole-record accuracy on EVAL (prefix): FP16 81.7, plain Q4 78.2, in-domain 79.7, generic 78.2, matched-domain 79.9, Q5 81.9. No intervals computed. Imatrix with in-domain text gains about 1.5 pp, generic 0 pp.

## Effect on the project
The tested methods (retraining, linear map, importance matrix with generic or in-domain text, one more bit) did not demonstrate the required mission-level improvement under these conditions. This does not show that no repair exists. What the data do show: at the best reading position the measured Q4 cost is +0.58 pp (CI +0.09 to +1.10, optimistic because of repeated reports), and the tested fixes are not distinguishable from zero at mission level. This round does not by itself raise novelty. No further tuning round is run before the supervisors have seen the work (protocol section 6).

## Addendum: whole-record results (SECONDARY outcome of protocol section 4; added after ChatGPT's review)
Source: `ITER2_RECORDS.md` (1,000 evaluation records from 100 families; intervals by bootstrap over families, so repeated records of one family are not counted as independent; accuracies equal to the mission run, integrity True). Status of everything below: **secondary or exploratory. The primary mission-level verdict stays NOT SHOWN.** About 30 comparisons were printed; some intervals will exclude 0 by chance.

| comparison (prefix, retrained heads) | repaired | newly wrong | net | difference | 95% CI |
|---|---|---|---|---|---|
| in-domain Q4 minus plain Q4 (78.2 -> 79.7%) | 52 | 37 | +15 | +1.5 pp | -0.5 to +3.6 |
| generic Q4 minus plain Q4 (78.2 -> 78.2%) | 44 | 44 | 0 | 0.0 pp | -1.9 to +1.9 |
| matched in-domain Q4 minus plain Q4 (-> 79.9%) | 52 | 35 | +17 | +1.7 pp | -0.2 to +3.6 |
| Q5 minus plain Q4 (-> 81.9%) | 66 | 29 | +37 | +3.7 pp | +2.0 to +5.4 |
| plain Q4 minus FP16 (81.7%) | 34 | 69 | -35 | -3.5 pp | -5.4 to -1.7 |
| in-domain Q4 minus FP16 | 23 | 43 | -20 | -2.0 pp | -3.6 to -0.3 |
| Q5 minus FP16 | 32 | 30 | +2 | +0.2 pp | -1.3 to +1.7 |

What this supports (careful wording):
* The primary-file record gain (+1.5 pp) is a point estimate whose interval includes 0. Not demonstrated.
* Matched in-domain minus generic: +1.7 pp (+0.3 to +3.1); full in-domain minus generic: +1.5 pp (+0.1 to +3.0). Exploratory, suggestive only. Not confirmed, because (a) it is secondary, (b) many comparisons were printed, and (c) the direction is not stable across reading positions: at `end` the in-domain file is worse than plain Q4 (-3.5 pp, -5.8 to -1.2) and worse than generic (-2.7 pp, -5.3 to -0.2). A real effect of calibration text would be expected to show at both positions.
* Even with in-domain calibration, Q4 stays below FP16 at record level (-2.0 pp, -3.6 to -0.3).
* Q5 is the only variant with a clear record-level gain over plain Q4 (+3.7 pp, +2.0 to +5.4) and it is statistically indistinguishable from FP16 (+0.2 pp). It costs about 0.1 GB more (0.91 vs 0.81 GB). This is a cost trade-off, not a Q4 repair.
* Linear map at `end` (q4a minus q4): 74.3 -> 76.7%, +2.4 pp (+0.7 to +4.2), consistent with the earlier repair result (secondary).
* Record accuracy and mission harm are not the same thing: Q5 recovers about 3.7 pp of records yet moves the missed share by only -0.38 pp (CI -0.92 to +0.14). This gap between the two outcomes is a result worth reporting in its own right.
