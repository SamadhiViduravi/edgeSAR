# Confirmation of the label-free mission check: results

Protocol `PROTOCOL_CHECK_CONFIRM.md` (frozen and pushed with tag `check-protocol-2026-11-26` before the GPU step). Analysis script `check_confirm.py` (SHA-256 `2ff5ee9e45d8abf6000a628f30b122b5d2fdd64044bf78bdc08c04a0725dc0ee`), run once, unchanged. Reports: `cases_C.jsonl` (SHA-256 `8f87d3f7d66bc2a57c0d0d9c01137fe38b675b030b3594b50e9cedb4f5cdd1b7`).

Run: 2026-11-26 07:19:28 +0530 to 2026-11-26 08:04:49 +0530 (2721 s). GPU step on the laptop: 2026-11-26 06:10:35 to 2026-11-26 06:47:18 (NVIDIA GeForce RTX 2050, llama.cpp build b11901).

Anchor check (20 development reports embedded again): f16 lowest cosine 1.000000 (pass), Q4_K_M lowest cosine 1.000000 (pass).

## Hypotheses

| Hypothesis | Rule | Result |
|---|---|---|
| H1 | check Spearman >= 0.80 in every condition | **holds** |
| H2 | check Spearman > flips Spearman in every condition | **holds** |
| H3 | label-free option chosen by the check within 0.25 pp of the best label-free option in every condition | **does not hold** |
| H4 | check penalty above the true penalty in at least 95% of candidate-condition pairs | **holds** |
| H5 | secondary: check from the default simulator vs true penalty in each perturbed simulator, Spearman >= 0.70 | **holds** |

**The check counts as confirmed only if H1 to H4 all hold: NOT CONFIRMED.**

## Every condition (target, set, load)

| Condition | Check Spearman (95% CI) | Flips | Accuracy drop (labels) | Pairs ordered | Label-free choice / best (loss, pp) | Check above true |
|---|---:|---:|---:|---:|---|---:|
| Q4_K_M C1 low | 0.99 (0.95 to 0.99) | 0.48 | 0.55 | 508 of 516 | map / Procrustes (0.05) | 39 of 39 |
| Q4_K_M C1 medium | 0.96 (0.91 to 0.98) | 0.61 | 0.72 | 497 of 506 | pseudo-label retraining / pseudo-label retraining (0.00) | 39 of 39 |
| Q4_K_M C1 high | 0.95 (0.89 to 0.98) | 0.73 | 0.81 | 543 of 553 | map / pseudo-label retraining (0.33) | 39 of 39 |
| Q4_K_M C2 low | 0.98 (0.96 to 0.99) | 0.24 | 0.55 | 595 of 597 | pseudo-label retraining / pseudo-label retraining (0.00) | 39 of 39 |
| Q4_K_M C2 medium | 0.97 (0.93 to 0.98) | 0.40 | 0.69 | 583 of 591 | map / pseudo-label retraining (0.18) | 39 of 39 |
| Q4_K_M C2 high | 0.91 (0.82 to 0.95) | 0.48 | 0.67 | 514 of 535 | map / pseudo-label retraining (0.94) | 39 of 39 |
| Q3_K_M C1 low | 1.00 (0.99 to 1.00) | 0.74 | 0.78 | 607 of 607 | map / map (0.00) | 39 of 39 |
| Q3_K_M C1 medium | 0.98 (0.95 to 0.99) | 0.80 | 0.85 | 543 of 544 | pseudo-label retraining / map (0.18) | 39 of 39 |
| Q3_K_M C1 high | 0.99 (0.96 to 0.99) | 0.82 | 0.88 | 589 of 595 | map / map (0.00) | 39 of 39 |
| Q3_K_M C2 low | 0.98 (0.93 to 0.99) | 0.69 | 0.80 | 584 of 595 | map / map (0.00) | 39 of 39 |
| Q3_K_M C2 medium | 0.97 (0.91 to 0.98) | 0.76 | 0.84 | 602 of 618 | map / map (0.00) | 39 of 39 |
| Q3_K_M C2 high | 0.94 (0.81 to 0.95) | 0.75 | 0.77 | 536 of 558 | map / map (0.00) | 39 of 39 |

## H5: misspecified simulators (C1, medium load)

| Target, simulator | Check from the default simulator vs. true penalty in the perturbed one | Check computed in the perturbed simulator itself |
|---|---:|---:|
| Q4_K_M, greedy single-task allocator | 0.93 | 0.95 |
| Q4_K_M, thermal camera also on UAV-03 | 0.74 | 1.00 |
| Q4_K_M, UAVs 25% slower | 0.89 | 0.96 |
| Q4_K_M, deadlines 25% shorter | 0.93 | 0.96 |
| Q3_K_M, greedy single-task allocator | 0.91 | 0.99 |
| Q3_K_M, thermal camera also on UAV-03 | 0.80 | 1.00 |
| Q3_K_M, UAVs 25% slower | 0.97 | 0.98 |
| Q3_K_M, deadlines 25% shorter | 0.96 | 0.97 |

## True mission penalties (descriptive; missed share minus that of the FP16 classifier, pp, 95% episode-bootstrap interval)

| Condition | FP16 missed (%) | unchanged | recentering | map | pseudo-label retraining | CORAL | Procrustes | retrain, 1,000 labels | TF-IDF | rules |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q4_K_M C1 low | 2.24 | +3.55 (+2.92 to +4.14) | +0.49 (+0.08 to +0.86) | +0.02 (-0.24 to +0.30) | +0.05 (-0.32 to +0.42) | +0.99 (+0.57 to +1.41) | -0.03 (-0.31 to +0.25) | +0.12 (-0.18 to +0.40) | -0.69 (-0.97 to -0.40) | -0.64 (-0.93 to -0.34) |
| Q4_K_M C1 medium | 6.97 | +2.93 (+2.16 to +3.73) | +0.75 (+0.26 to +1.25) | +0.25 (-0.07 to +0.60) | +0.07 (-0.35 to +0.49) | +1.05 (+0.57 to +1.57) | +0.37 (-0.03 to +0.78) | -0.03 (-0.46 to +0.37) | -1.31 (-1.85 to -0.81) | -1.16 (-1.66 to -0.68) |
| Q4_K_M C1 high | 16.16 | +3.60 (+2.69 to +4.47) | +1.66 (+1.00 to +2.37) | +0.17 (-0.35 to +0.67) | -0.17 (-0.76 to +0.39) | +0.79 (+0.12 to +1.44) | +0.55 (-0.03 to +1.12) | -0.07 (-0.61 to +0.43) | -1.17 (-1.91 to -0.45) | -1.05 (-1.70 to -0.34) |
| Q4_K_M C2 low | 3.38 | +5.97 (+5.22 to +6.76) | +1.23 (+0.65 to +1.82) | +0.16 (-0.23 to +0.52) | +0.03 (-0.44 to +0.40) | +2.62 (+2.04 to +3.18) | +0.05 (-0.36 to +0.45) | -0.03 (-0.47 to +0.45) | +2.56 (+1.88 to +3.26) | +7.01 (+6.06 to +8.03) |
| Q4_K_M C2 medium | 7.64 | +4.79 (+3.71 to +5.82) | +1.10 (+0.24 to +1.87) | +0.05 (-0.72 to +0.77) | -0.13 (-0.95 to +0.65) | +1.91 (+1.10 to +2.71) | +0.31 (-0.60 to +1.18) | +0.31 (-0.38 to +1.04) | +2.43 (+1.38 to +3.40) | +6.20 (+4.96 to +7.36) |
| Q4_K_M C2 high | 16.33 | +4.27 (+3.25 to +5.30) | +2.36 (+1.41 to +3.42) | +0.55 (-0.05 to +1.23) | -0.39 (-1.31 to +0.50) | +2.20 (+1.17 to +3.25) | +0.08 (-0.88 to +1.08) | +0.47 (-0.33 to +1.23) | +2.20 (+1.10 to +3.38) | +4.19 (+2.92 to +5.50) |
| Q3_K_M C1 low | 2.24 | +11.17 (+10.44 to +11.93) | +3.47 (+2.86 to +4.05) | +0.23 (-0.07 to +0.53) | +0.23 (-0.10 to +0.55) | +3.55 (+3.00 to +4.08) | +1.93 (+1.42 to +2.41) | +0.08 (-0.22 to +0.39) | -0.69 (-1.00 to -0.40) | -0.64 (-0.94 to -0.35) |
| Q3_K_M C1 medium | 6.97 | +10.53 (+9.57 to +11.45) | +3.01 (+2.25 to +3.76) | +0.30 (-0.20 to +0.79) | +0.49 (-0.00 to +1.00) | +3.32 (+2.58 to +3.98) | +1.56 (+0.87 to +2.25) | +0.70 (+0.15 to +1.23) | -1.31 (-1.83 to -0.77) | -1.16 (-1.66 to -0.66) |
| Q3_K_M C1 high | 16.16 | +10.03 (+8.93 to +11.18) | +3.20 (+2.36 to +4.11) | +0.12 (-0.59 to +0.83) | +0.37 (-0.34 to +1.06) | +3.25 (+2.35 to +4.10) | +2.18 (+1.42 to +2.93) | +0.69 (-0.05 to +1.43) | -1.17 (-1.93 to -0.50) | -1.05 (-1.77 to -0.35) |
| Q3_K_M C2 low | 3.38 | +10.26 (+9.33 to +11.14) | +4.19 (+3.54 to +4.85) | +0.29 (-0.21 to +0.78) | +0.42 (-0.13 to +0.99) | +4.74 (+3.93 to +5.47) | +2.54 (+1.87 to +3.24) | +0.79 (+0.11 to +1.40) | +2.56 (+1.84 to +3.25) | +7.01 (+6.04 to +7.93) |
| Q3_K_M C2 medium | 7.64 | +9.50 (+8.16 to +10.74) | +3.98 (+2.87 to +5.02) | -0.03 (-0.91 to +0.85) | +0.31 (-0.53 to +1.16) | +4.53 (+3.51 to +5.52) | +2.30 (+1.35 to +3.20) | +0.79 (-0.24 to +1.75) | +2.43 (+1.41 to +3.48) | +6.20 (+5.01 to +7.39) |
| Q3_K_M C2 high | 16.33 | +8.74 (+7.31 to +10.06) | +3.74 (+2.51 to +4.97) | +0.13 (-0.88 to +1.24) | +0.89 (-0.30 to +1.96) | +4.08 (+2.87 to +5.26) | +1.81 (+0.69 to +2.94) | +1.57 (+0.57 to +2.57) | +2.20 (+1.07 to +3.36) | +4.19 (+2.92 to +5.34) |

## The check with fewer unlabeled episodes (random C1 subsets, against the true penalties of all C1 episodes)

| Target, load, episodes | Median Spearman | 5th percentile | Share of subsets whose label-free choice is within 0.25 pp |
|---|---:|---:|---:|
| Q4_K_M, low, 10 | 0.86 | 0.60 | 0.937 |
| Q4_K_M, low, 25 | 0.93 | 0.84 | 0.995 |
| Q4_K_M, low, 50 | 0.96 | 0.92 | 1.000 |
| Q4_K_M, medium, 10 | 0.74 | 0.46 | 0.755 |
| Q4_K_M, medium, 25 | 0.86 | 0.73 | 0.895 |
| Q4_K_M, medium, 50 | 0.92 | 0.85 | 0.962 |
| Q4_K_M, high, 10 | 0.69 | 0.38 | 0.306 |
| Q4_K_M, high, 25 | 0.83 | 0.64 | 0.313 |
| Q4_K_M, high, 50 | 0.89 | 0.80 | 0.263 |
| Q3_K_M, low, 10 | 0.91 | 0.75 | 0.997 |
| Q3_K_M, low, 25 | 0.96 | 0.90 | 1.000 |
| Q3_K_M, low, 50 | 0.98 | 0.96 | 1.000 |
| Q3_K_M, medium, 10 | 0.82 | 0.63 | 0.936 |
| Q3_K_M, medium, 25 | 0.90 | 0.81 | 0.995 |
| Q3_K_M, medium, 50 | 0.94 | 0.89 | 1.000 |
| Q3_K_M, high, 10 | 0.80 | 0.58 | 0.598 |
| Q3_K_M, high, 25 | 0.90 | 0.78 | 0.629 |
| Q3_K_M, high, 50 | 0.95 | 0.90 | 0.719 |
