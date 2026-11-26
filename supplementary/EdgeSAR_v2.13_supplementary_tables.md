# EdgeSAR: supplementary tables (manuscript v2.13)

Exploratory analyses of the first confirmation (not pre-specified), moved from Section V-J of the manuscript to keep it within the page limit. The numbers are those of manuscript v2.12 (Tables 6, 8, 9 and 7 there); their scripts and outputs are in `fresh_confirmation/`.

| Overlap of the fresh reports with the development reports | Set A (familiar wording) | Set B (new wording) |
|:--------------------------------------------------|-------------------------:|-------------------------:|
| Fresh reports | 6,000 | 1,000 |
| Complete model input identical to a development input | 0 | 0 |
| Text identical to one of the 1,000 style-A fitting reports | 1,307 (21.8%) | 0 |
| Text identical to one of the 400 style-B development reports | 0 | 125 (12.5%) |
| Masked template among the 1,000 fitting reports | 4,185 (69.8%) | 0 |
| Masked template among the 400 style-B development reports | 0 | 608 (60.8%) |
| Distinct masked templates / of these not among any of the 1,400 | 1,512 / 1,309 | 391 / 308 |

: TABLE S1. Overlap between the fresh reports and the 1,400 development reports (exploratory; not pre-specified). The classifiers, maps and baselines were fitted only on the 1,000 style-A reports; the 400 style-B development reports were used only for evaluation. Masked template: the report text with landmarks, incident identifiers, sources and numbers masked.

| Position, head | Reports | FP16 accuracy / AUC | Q4 unchanged accuracy / AUC | Change in accuracy, pp (95% CI) | Change in AUC (95% CI) | Q4 map accuracy / AUC |
|:---------------|----------:|-------------:|-------------:|-------------------------:|--------------------------:|-------------:|
| *prefix*, action | 6,000 | 99.7 / 1.000 | 91.8 / 0.997 | -7.9 (-8.5 to -7.2) | -0.003 (-0.003 to -0.002) | 99.4 / 1.000 |
| *prefix*, sensor | 2,700 | 78.3 / 0.926 | 73.2 / 0.891 | -5.1 (-6.4 to -3.7) | -0.034 (-0.040 to -0.029) | 76.1 / 0.911 |
| *prefix*, priority | 2,700 | 81.6 / 0.938 | 46.5 / 0.860 | -35.1 (-37.4 to -32.9) | -0.078 (-0.086 to -0.070) | 80.0 / 0.931 |
| *end*, action | 6,000 | 99.9 / 1.000 | 51.8 / 0.968 | -48.1 (-49.4 to -46.8) | -0.032 (-0.034 to -0.030) | 99.4 / 1.000 |
| *end*, sensor | 2,700 | 79.0 / 0.935 | 46.4 / 0.786 | -32.6 (-34.7 to -30.3) | -0.149 (-0.159 to -0.138) | 75.0 / 0.915 |
| *end*, priority | 2,700 | 76.1 / 0.909 | 39.9 / 0.817 | -36.3 (-38.7 to -33.7) | -0.092 (-0.102 to -0.084) | 73.4 / 0.893 |

: TABLE S2. Accuracy (%) and macro one-vs-rest AUC of the FP16 heads on fresh set-A reports (exploratory; not pre-specified), given FP16 vectors, raw Q4 vectors or mapped Q4 vectors.

| Load, time per report | Gold | FP16 | Q4 unchanged | Q4 map | Q4 retrained | TF-IDF | Delay effect on map, pp (95% CI) | Map minus unchanged, pp (95% CI) |
|:---------------|-------:|-------:|------------:|-------:|----------:|-------:|------------------------:|------------------------:|
| medium, 0 s (pre-specified) | 5.71 | 6.84 | 10.27 | 6.91 | 7.16 | 5.83 | - | -3.36 (-3.87 to -2.85) |
| medium, 2 s | 5.71 | 7.27 | 10.42 | 7.26 | 7.41 | 5.83 | +0.36 (+0.09 to +0.63) | -3.15 (-3.71 to -2.58) |
| medium, 5 s | 5.71 | 7.51 | 10.57 | 7.39 | 7.41 | 5.83 | +0.48 (+0.11 to +0.83) | -3.19 (-3.74 to -2.62) |
| high, 0 s (pre-specified) | 14.43 | 16.02 | 19.48 | 16.44 | 16.55 | 14.53 | - | -3.04 (-3.66 to -2.42) |
| high, 2 s | 14.43 | 16.09 | 19.88 | 16.32 | 16.37 | 14.53 | -0.11 (-0.43 to +0.20) | -3.55 (-4.19 to -2.92) |
| high, 5 s | 14.43 | 16.69 | 20.15 | 16.80 | 16.86 | 14.53 | +0.37 (-0.09 to +0.83) | -3.34 (-3.98 to -2.70) |

: TABLE S3. Missed incidents (%) with the gateway's inference time inside the mission (exploratory; not pre-specified): set A, arrival seed 11, 300 episodes per load, single-server queue. Gold records and TF-IDF were run without delay. Delay effect: the map arm with minus without the delay. The retrained arm missed the same number of incidents (851) at 2 s and 5 s.

| Episodes at medium load (episodes / incidents) | Gold (%) | Unchanged minus FP16 | Map minus FP16 | Map minus 100-label retraining | TF-IDF minus map |
|:----------------------|---------:|--------------------------:|--------------------------:|-------------------------:|-------------------------:|
| Set A, pre-specified episodes of Table 4 (300 / 11,480) | 5.71 | +3.43 (+2.98 to +3.88) | +0.07 (-0.23 to +0.36) | -2.72 (-3.14 to -2.30) | -1.08 (-1.50 to -0.67) |
| Set A, all reports regrouped (300 / 11,480) | 5.56 | +3.34 (+2.82 to +3.86) | +0.14 (-0.13 to +0.41) | -2.53 (-2.90 to -2.15) | -1.45 (-1.81 to -1.09) |
| Set A, unseen text only (234 / 9,166) | 6.35 | +4.21 (+3.59 to +4.81) | +0.16 (-0.21 to +0.54) | -3.27 (-3.76 to -2.80) | -1.61 (-2.10 to -1.12) |
| Set A, unseen template only (90 / 4,323) | 11.61 | +4.44 (+3.37 to +5.54) | +0.83 (+0.05 to +1.67) | -3.89 (-4.74 to -3.03) | -2.48 (-3.49 to -1.45) |
| Set B, all reports regrouped (50 / 1,878) | 5.32 | +3.57 (+2.15 to +4.98) | -0.48 (-1.18 to +0.16) | -2.35 (-3.38 to -1.28) | +2.18 (+0.82 to +3.56) |
| Set B, unseen text only (43 / 1,652) | 5.02 | +5.81 (+4.49 to +7.15) | -0.36 (-1.25 to +0.49) | -2.74 (-3.65 to -1.86) | +2.97 (+1.57 to +4.47) |
| Set B, unseen template only (19 / 878) | 10.71 | +4.10 (+1.66 to +6.91) | -0.11 (-2.11 to +1.95) | -3.49 (-5.37 to -1.52) | +2.96 (-0.33 to +6.15) |

: TABLE S4. Sensitivity to unseen text and unseen templates (exploratory; not pre-specified): paired differences in missed share, pp (95% episode-bootstrap interval), *prefix* position. In brackets: episodes / incidents. Unseen: occurring in none of the 1,400 development reports. Gold: missed share (%) with gold records. Episodes were regrouped at random (seed 4343 for all reports and unseen templates, 4242 for unseen text), so the shares differ from Table 5.
