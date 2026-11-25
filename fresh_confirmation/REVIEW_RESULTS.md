# Exploratory analyses added after review (not pre-registered)

Run on 19 Nov 2026 with review_analyses.py, review_r2b.py and review_r2c.py, after the registered results were known. They do not change results.json. Same text and tables as Section V-J of the paper (Tables 6 to 9).

After a mock review of an earlier draft (Section IV-E), we ran further analyses on the same fresh data. They were **not** in the protocol and were run after the registered results were known, so they are exploratory; they do not change Tables 4 and 5. Before them, the refitted classifiers, maps and label draws reproduced the registered missed counts of the primary analysis exactly (gold 655, FP16 785, unchanged 1,179, map 793 and retrained 822 of 11,480 incidents). The code and outputs are in the confirmation package (see Data and Code Availability).

**1. How new is the fresh text? (Table 6.)** No fresh model input was identical to a development input, because the open-incident list always differed. 1,307 of the 6,000 set-A texts (21.8%) and 125 of the 1,000 set-B texts were identical to a development text, and 4,185 set-A reports (69.8%) came from a template family (the text with landmarks, identifiers and numbers masked) that also occurs in the development set. The fresh confirmation therefore tests new draws of mostly familiar templates, as the protocol stated.

| Overlap with the 1,000 development reports | Set A (familiar wording) | Set B (new wording) |
|:--------------------------------------------------|-------------------------:|-------------------------:|
| Fresh reports | 6,000 | 1,000 |
| Complete model input identical to a development input | 0 | 0 |
| Report text identical to a development text | 1,307 (21.8%) | 125 (12.5%) |
| Template family seen in development | 4,185 (69.8%) | 608 (60.8%) |
| Distinct template families / of these not seen in development | 1,512 / 1,309 | 391 / 308 |

: TABLE 6. Overlap between the fresh reports and the development reports (exploratory, added after review). Set-B development reports are not part of the fitting data; overlap is counted against the 1,000 style-A fitting reports.

**2. Episodes made only of unseen text or unseen templates (Table 7).** We rebuilt medium-load episodes of 20 reports from (i) all fresh reports, (ii) only reports whose text never occurs in development and (iii) only reports whose template family never occurs in development, and reran every arm on the same episodes. Regrouping changes the mix of reports: unseen templates are mostly incident-bearing reports (90% CREATE or UPDATE in set A, against 45% overall), so their episodes contain more incidents and even gold records miss more (11.61% against 5.56%). Only the paired differences within each row group should therefore be compared, not the shares across groups.

| Episodes at medium load (episodes / incidents) | Gold (%) | Unchanged minus FP16 | Map minus FP16 | Map minus 100-label retraining | TF-IDF minus map |
|:----------------------|---------:|--------------------------:|--------------------------:|-------------------------:|-------------------------:|
| Set A, registered episodes of Table 4 (300 / 11,480) | 5.71 | +3.43 (+2.98 to +3.88) | +0.07 (-0.23 to +0.36) | -2.72 (-3.14 to -2.30) | -1.08 (-1.50 to -0.67) |
| Set A, all reports regrouped (300 / 11,480) | 5.56 | +3.34 (+2.82 to +3.86) | +0.14 (-0.13 to +0.41) | -2.53 (-2.90 to -2.15) | -1.45 (-1.81 to -1.09) |
| Set A, unseen text only (234 / 9,166) | 6.35 | +4.21 (+3.59 to +4.81) | +0.16 (-0.21 to +0.54) | -3.27 (-3.76 to -2.80) | -1.61 (-2.10 to -1.12) |
| Set A, unseen template only (90 / 4,323) | 11.61 | +4.44 (+3.37 to +5.54) | +0.83 (+0.05 to +1.67) | -3.89 (-4.74 to -3.03) | -2.48 (-3.49 to -1.45) |
| Set B, all reports regrouped (50 / 1,878) | 5.32 | +3.57 (+2.15 to +4.98) | -0.48 (-1.18 to +0.16) | -2.35 (-3.38 to -1.28) | +2.18 (+0.82 to +3.56) |
| Set B, unseen text only (43 / 1,652) | 5.02 | +5.81 (+4.49 to +7.15) | -0.36 (-1.25 to +0.49) | -2.74 (-3.65 to -1.86) | +2.97 (+1.57 to +4.47) |
| Set B, unseen template only (19 / 878) | 10.71 | +4.10 (+1.66 to +6.91) | -0.11 (-2.11 to +1.95) | -3.49 (-5.37 to -1.52) | +2.96 (-0.33 to +6.15) |

: TABLE 7. Sensitivity to unseen text and unseen templates (exploratory, added after review): paired differences in missed share, pp (95% episode-bootstrap interval), *prefix* position. In brackets: episodes / incidents. Gold: missed share (%) with gold records. Episodes were regrouped at random (seed 4343 for all reports and unseen templates, 4242 for unseen text), so the shares differ from Table 5.

On unseen templates of set A, the mismatch effect was at least as large (unchanged minus FP16 +4.44 pp, +3.37 to +5.54) and the map still removed most of it (-3.61 pp, -4.69 to -2.55) and beat 100-label retraining (-3.89 pp, -4.74 to -3.03); the map was slightly worse than the FP16 classifier (+0.83 pp, +0.05 to +1.67), unlike in the registered analysis. TF-IDF still missed fewer incidents than the map on set-A wording, including unseen templates (-2.48 pp, -3.49 to -1.45). On unseen set-B templates (19 episodes) the intervals are wide: unchanged minus FP16 +4.10 pp (+1.66 to +6.91), map minus FP16 -0.11 pp (-2.11 to +1.95), TF-IDF minus map +2.96 pp (-0.33 to +6.15). The pattern of the confirmation therefore holds on unseen templates of the same generator, but the reversal between TF-IDF and the map remains tied to the wording set, and only independently written reports can show which choice transfers to real language.

**3. Ranking quality and decisions on the fresh reports (Table 8).** For each head we computed accuracy and macro one-vs-rest AUC on the fresh set-A reports (sensor and priority on the reports that carry them), with 95% intervals from 1,000 episode-cluster bootstrap resamples for the change from FP16 to unchanged Q4.

| Position, head | Reports | FP16 accuracy / AUC | Q4 unchanged accuracy / AUC | Change in accuracy, pp (95% CI) | Change in AUC (95% CI) | Q4 map accuracy / AUC |
|:---------------|----------:|-------------:|-------------:|-------------------------:|--------------------------:|-------------:|
| *prefix*, action | 6,000 | 99.7 / 1.000 | 91.8 / 0.997 | -7.9 (-8.5 to -7.2) | -0.003 (-0.003 to -0.002) | 99.4 / 1.000 |
| *prefix*, sensor | 2,700 | 78.3 / 0.926 | 73.2 / 0.891 | -5.1 (-6.4 to -3.7) | -0.034 (-0.040 to -0.029) | 76.1 / 0.911 |
| *prefix*, priority | 2,700 | 81.6 / 0.938 | 46.5 / 0.860 | -35.1 (-37.4 to -32.9) | -0.078 (-0.086 to -0.070) | 80.0 / 0.931 |
| *end*, action | 6,000 | 99.9 / 1.000 | 51.8 / 0.968 | -48.1 (-49.4 to -46.8) | -0.032 (-0.034 to -0.030) | 99.4 / 1.000 |
| *end*, sensor | 2,700 | 79.0 / 0.935 | 46.4 / 0.786 | -32.6 (-34.7 to -30.3) | -0.149 (-0.159 to -0.138) | 75.0 / 0.915 |
| *end*, priority | 2,700 | 76.1 / 0.909 | 39.9 / 0.817 | -36.3 (-38.7 to -33.7) | -0.092 (-0.102 to -0.084) | 73.4 / 0.893 |

: TABLE 8. Accuracy (%) and macro one-vs-rest AUC of the FP16 heads on fresh set-A reports (exploratory, added after review), given FP16 vectors, raw Q4 vectors or mapped Q4 vectors.

At *prefix*, the action head's AUC changed by only -0.003 while its accuracy fell by 7.9 points; the priority head lost 35.1 points of accuracy and 0.078 of AUC, and the sensor head 5.1 points and 0.034. At *end* the same pattern is stronger (action: accuracy 99.9% to 51.8%, AUC 1.000 to 0.968). AUC therefore falls far less than accuracy, so a check based on AUC, particularly of the action head, understates the damage; it is not blind to it. The map brought every head at *prefix* back to within about 2 points of accuracy and 0.015 of AUC of FP16.

**4. Variation between label draws.** H3 averages five 100-label draws, and its interval resamples episodes only. Map minus each single 100-label draw was -2.80, -4.89, -2.12, -2.03, -1.77 pp; map minus each 300-label draw was -1.07, -0.95, -1.11, -1.53, -1.05 pp. A two-level bootstrap that also resamples the five draws gave -2.72 pp (-3.91 to -1.77) for 100 labels and -1.14 pp (-1.56 to -0.74) for 300 labels. The advantage of the map over 100-label retraining therefore holds for every draw we made, and the wider interval still excludes zero; five draws remain a small sample of what a team's next 100 labels may give.

**5. A second thermal camera.** With one thermal UAV, a wrong sensor can cost much. We reran the primary episodes with thermal cameras on two of the three UAVs. Misses then almost disappeared for every adapted arm (gold 0.26%, FP16 0.43%, map 0.51%, retrained 0.46%), which shows that the single thermal camera is the main bottleneck of the registered setting at medium load. The unchanged classifier still missed 4.22%: the mismatch effect remained (unchanged minus FP16 +3.80 pp, +3.47 to +4.13) and the map removed almost all of it (-3.72 pp, -4.04 to -3.40; map minus FP16 +0.08 pp, -0.03 to +0.22). Substituting the gold sensor no longer made a clear difference (retrained arm -0.08 pp, -0.19 to +0.03, map arm -0.10 pp, -0.24 to +0.02), because the adapted arms were only 0.20 and 0.24 pp above gold. The sensor diagnosis therefore depends on how scarce the thermal camera is; the mismatch effect and the recovery by the map do not.

**6. Inference time inside the mission.** The registered missions apply a record as soon as its report arrives (plus the allocator's own time). We replayed the primary episodes with a single gateway that needs a fixed time per report, measured on the laptop CPU (2 s) and a stress value (5 s), with reports queueing when they arrive faster than the gateway can process them. The text baselines were run without delay.

| Load, time per report | Gold | FP16 | Q4 unchanged | Q4 map | Q4 retrained | TF-IDF | Delay effect on map, pp (95% CI) | Map minus unchanged, pp (95% CI) |
|:---------------|-------:|-------:|------------:|-------:|----------:|-------:|------------------------:|------------------------:|
| medium, 0 s (registered) | 5.71 | 6.84 | 10.27 | 6.91 | 7.16 | 5.83 | - | -3.36 (-3.87 to -2.85) |
| medium, 2 s | 5.71 | 7.27 | 10.42 | 7.26 | 7.41 | 5.83 | +0.36 (+0.09 to +0.63) | -3.15 (-3.71 to -2.58) |
| medium, 5 s | 5.71 | 7.51 | 10.57 | 7.39 | 7.41 | 5.83 | +0.48 (+0.11 to +0.83) | -3.19 (-3.74 to -2.62) |
| high, 0 s (registered) | 14.43 | 16.02 | 19.48 | 16.44 | 16.55 | 14.53 | - | -3.04 (-3.66 to -2.42) |
| high, 2 s | 14.43 | 16.09 | 19.88 | 16.32 | 16.37 | 14.53 | -0.11 (-0.43 to +0.20) | -3.55 (-4.19 to -2.92) |
| high, 5 s | 14.43 | 16.69 | 20.15 | 16.80 | 16.86 | 14.53 | +0.37 (-0.09 to +0.83) | -3.34 (-3.98 to -2.70) |

: TABLE 9. Missed incidents (%) with the gateway's inference time inside the mission (exploratory, added after review): set A, arrival seed 11, 300 episodes per load, single-server queue. Gold records and TF-IDF were run without delay. Delay effect: the map arm with minus without the delay.

A 2 s service time changed the map arm by +0.36 pp (+0.09 to +0.63) at medium load and by -0.11 pp (-0.43 to +0.20) at high load; with 5 s the changes were +0.48 (+0.11 to +0.83) and +0.37 pp (-0.09 to +0.83). In every setting the unchanged classifier remained clearly worst (map minus unchanged between -3.55 and -3.15 pp), and FP16, map and retrained stayed within 0.28 pp of each other. Because the text baselines need almost no time, the delay widens their lead on the familiar wording (TF-IDF without delay minus map with a 2 s delay: -1.44 pp, -1.89 to -1.00 at medium load). This is a simulated queue with a constant service time, not a field measurement.



## R7. Label accounting (added 22 Nov 2026, after the second review; exploratory)

Set A, medium load, registered episodes (300 episodes, 11,480 incidents), *prefix*; the five registered 100- and 300-label draws. Before R7, the refitted arms reproduced the registered missed counts exactly (gold 655, FP16 785, unchanged 1,179, map 793, retrained 822).

| Arm | Missed (%) |
|---|---:|
| FP16 classifier | 6.84 |
| Q4 unchanged | 10.27 |
| Q4 map, 1,000 pairs (registered) | 6.91 |
| Q4 map, 100 pairs (full FP16 classifier) | 6.99 |
| Q4 map, 300 pairs | 6.92 |
| Q4 retrained, all labels | 7.16 |
| Q4 retrained, 100 / 300 labels | 9.63 / 8.05 |
| FP16 classifier on 100 / 300 labels, on FP16 | 9.26 / 7.51 |
| ... unchanged on Q4 | 13.95 / 12.07 |
| ... + map fitted on the same 100 / 300 reports | 9.54 / 7.80 |
| ... + map fitted on all 1,000 unlabelled pairs | 9.29 / 7.68 |

Key paired differences (pp, 95% episode-bootstrap interval):
- map from 100 pairs minus registered map: +0.08 (-0.13 to +0.29); minus 100-label retraining: -2.64 (-2.98 to -2.30)
- 100-label FP16 classifier unchanged on Q4 minus on FP16: +4.69 (+4.34 to +5.04)
- equal supervision, 100: FP16 classifier + map on the same reports minus Q4 retrained on them: -0.09 (-0.27 to +0.09); 300: -0.25 (-0.42 to -0.09)


## R8. Overlap by development population (added 23 Nov 2026; exploratory)

`review_overlap.py`. Corrects the population label of the R1 overlap table: R1 counted overlap against all 1,400 development reports, not only the 1,000 style-A fitting reports. The classifiers, maps and baselines were fitted only on the 1,000 style-A reports.

| Overlap | Set A (6,000) | Set B (1,000) |
|---|---:|---:|
| Text identical to one of the 1,000 style-A fitting reports | 1,307 | 0 |
| Text identical to one of the 400 style-B development (evaluation-only) reports | 0 | 125 |
| Masked template among the 1,000 fitting reports | 4,185 | 0 |
| Masked template among the 400 style-B development reports | 0 | 608 |
| Distinct masked templates / not among any of the 1,400 | 1,512 / 1,309 | 391 / 308 |

So set B is entirely unseen relative to the fitting data; the "unseen" subsets of R2 (Table 7) are defined against all 1,400 development reports, which for set A is the same as against the fitting reports.


## R9. Decision-level recalibration comparator (added 23 Nov 2026; exploratory)

`review_r9.py`. The FP16 heads are kept; only per-class offsets (bias recalibration) or per-class scales and offsets (vector scaling) are refitted on Q4 vectors of the same five 100- and 300-label draws as the retraining arms (cross-entropy, L2 penalty 0.01). Set A, medium load, registered episodes; the refitted reference arms reproduced the registered counts exactly.

| Arm | Missed (%) |
|---|---:|
| FP16 classifier | 6.84 |
| Q4 unchanged | 10.27 |
| Q4 map (no labels) | 6.91 |
| Q4 retrained, 100 / 300 labels | 9.63 / 8.05 |
| Q4 bias recalibration, 100 / 300 labels | 8.87 / 8.82 |
| Q4 vector scaling, 100 / 300 labels | 8.19 / 8.05 |

Paired differences (pp, 95% episode-bootstrap interval): vector scaling 100 minus retrained 100: -1.44 (-1.81 to -1.07); vector scaling 100 minus map: +1.28 (+0.88 to +1.67); bias 100 minus map: +1.97 (+1.56 to +2.38); vector scaling 300 minus retrained 300: -0.01 (-0.35 to +0.35); bias 300 minus retrained 300: +0.77 (+0.41 to +1.13). Recalibration recovered 1.40 (bias) and 2.08 (vector scaling) of the 3.43 pp mismatch penalty with 100 labels; the map recovered 3.36.

## R10. Label-free mission check (added 25 Nov 2026, after the fourth review; exploratory)

Question: before deploying the Q4 model, can a team rank candidate classifiers by their mission harm without labels? The check replays the
missions with the OLD classifier's records (FP16 classifier on FP16 vectors, *prefix*) as the truth ("referee") instead of the gold records,
and scores each candidate by its missed share minus the old classifier's missed share under that truth. This is compared with the true
penalty (gold truth: candidate minus FP16 classifier) for 36 candidate classifiers (unchanged, recentred, map, retraining with 100/300/1,000
labels, bias recalibration and vector scaling with 100/300 labels, five label draws where labels are drawn, TF-IDF and rules) on fresh sets A
(300 episodes) and B (50 episodes) at three loads (arrival seed 11), i.e. 216 candidate-condition pairs. Sanity: the gold-truth replays
reproduce all 48 registered missed counts of `results.json` exactly.

    python review_r10.py --root ROOT --cases cases_fresh.jsonl --vectors <vector folder> --fresh-out <folder with results.json> --out out_review --workers 2
    python review_r10_analysis.py --out out_review
    python review_r10_fig4.py out_review/review_results_r10.json        # Fig. 4 of the paper

Without the vectors, Table 11 and Fig. 4 can be recomputed from the archived outputs in this folder (the analysis is
deterministic and reproduces `review_results_r10_analysis.json` byte for byte):

    python review_r10_analysis.py --out .
    python review_r10_fig4.py review_results_r10.json

Spearman correlation with the true penalty over the 36 candidates of each condition (in brackets: 95% episode bootstrap, 2,000 resamples),
pairwise ordering (pairs whose true penalties differ by more than 0.5 pp) and selection (Table 11 of the paper):

| Set, load | Check | Flips (any field) | Sensor flips | Accuracy drop (labels) | Check: pairs ordered | Flips: pairs ordered | Check minus true penalty, pp: mean (min to max) | Label-free pick (true best) |
|---|---|---|---|---|---|---|---|---|
| A, low | 0.986 (0.951 to 0.993) | 0.346 | 0.428 | 0.388 | 99.1% | 67.6% | +0.45 (+0.17 to +1.38) | alnp (alnp) |
| A, medium | 0.959 (0.915 to 0.984) | 0.544 | 0.653 | 0.568 | 99.1% | 81.2% | +0.78 (+0.46 to +2.33) | alnp (alnp) |
| A, high | 0.970 (0.913 to 0.983) | 0.880 | 0.883 | 0.907 | 98.7% | 93.8% | +1.02 (+0.47 to +3.26) | alnp (alnp) |
| B, low | 0.975 (0.948 to 0.987) | 0.130 | 0.332 | 0.250 | 98.6% | 59.5% | +1.26 (+0.61 to +2.49) | alnp (alnp) |
| B, medium | 0.938 (0.779 to 0.973) | 0.226 | 0.420 | 0.361 | 97.9% | 59.5% | +1.86 (+0.82 to +3.39) | alnp (alnp) |
| B, high | 0.939 (0.690 to 0.957) | 0.390 | 0.583 | 0.437 | 97.8% | 67.7% | +1.78 (+0.36 to +4.53) | alnp (alnp) |

The check never underestimated the harm (all 216 pairs above the true penalty) and cannot credit a candidate that is better than the old
classifier (TF-IDF and rules on set A). As an absolute gate at 0.5 pp it flagged all 195 harmful pairs and 19 of the 21 harmless ones.

How many unlabeled reports: the check recomputed on random subsets of set-A episodes (1,000 subsets per size), against the true penalties on
all 300 episodes:

| Load | Episodes (about 20 reports each) | Median Spearman | 5th percentile | Map chosen among label-free options | Median loss vs. best hidden-state candidate (pp) |
|---|---|---|---|---|---|
| L | 5 | 0.754 | 0.260 | 78.8% | 0.00 |
| L | 10 | 0.836 | 0.526 | 92.4% | 0.00 |
| L | 25 | 0.913 | 0.759 | 99.6% | 0.00 |
| L | 50 | 0.948 | 0.870 | 100.0% | 0.00 |
| L | 100 | 0.972 | 0.942 | 100.0% | 0.00 |
| M | 5 | 0.597 | 0.176 | 73.4% | 0.25 |
| M | 10 | 0.709 | 0.401 | 81.7% | 0.25 |
| M | 25 | 0.834 | 0.651 | 96.3% | 0.00 |
| M | 50 | 0.891 | 0.784 | 99.6% | 0.00 |
| M | 100 | 0.930 | 0.874 | 100.0% | 0.00 |
| H | 5 | 0.527 | 0.168 | 70.6% | 0.83 |
| H | 10 | 0.646 | 0.376 | 83.7% | 0.11 |
| H | 25 | 0.793 | 0.613 | 95.6% | 0.00 |
| H | 50 | 0.869 | 0.750 | 99.5% | 0.00 |
| H | 100 | 0.927 | 0.862 | 100.0% | 0.00 |

Files: `review_r10.py`, `review_r10_analysis.py`, `review_r10_fig4.py`, `review_r10_log.txt` (log of the run whose outputs are archived; a
first run without the per-episode file gave identical values), `review_results_r10.json` (one row per candidate and condition, validity
summaries, sanity check), `review_results_r10_episodes.json` (missed and incident counts per episode for every arm under both truths),
`review_results_r10_analysis.json`. The docstring of `review_r10.py` was corrected after the run (34 -> 36 candidates); no code changed.
