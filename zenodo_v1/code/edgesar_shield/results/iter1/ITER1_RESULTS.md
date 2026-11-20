# Iteration 1: development results

Protocol: `docs/ITERATION1_PROTOCOL.md` (SHA-256 1ccce486d3935d6a7c5b49567648ee807973962ca55ccc99b15a00dcb43f7795). Development data only (1,000 style-A reports, saved vectors, 5 family folds, overlay episodes of 20 reports, 3 arrival seeds pooled). Nothing here is a confirmation. Pooled intervals are optimistic because seeds reuse the same reports.

## Label by the fixed rule (protocol section 3)

**NOT SHOWN.** B3-G1 +0.07 pp (CI -0.44 to +0.61); B3-A1 +0.40 pp (CI -0.32 to +1.15); at L/H: L: G1 +0.15, A1 +0.65, H: G1 -0.13, A1 +0.82

## Readout `q4`  (q4)

### Level L: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 1.34% | 0.91% to 1.86% | 0.000 | 0.000 | 0 | 0 | 1193 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 2.42% | 1.89% to 2.97% | 0.000 | 0.075 | 0 | 0 | 1250 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 1.82% | 1.32% to 2.37% | 0.000 | 0.054 | 0 | 0 | 1240 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 2.14% | 1.62% to 2.72% | 0.000 | 0.059 | 0 | 0 | 1241 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 3.22% | 2.65% to 3.79% | 0.000 | 0.117 | 0 | 0 | 1278 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 13.93% | 13.12% to 14.72% | 0.000 | 0.158 | 0 | 0 | 1168 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 2.89% | 2.37% to 3.42% | 0.073 | 0.070 | 0 | 0 | 1240 | 4.4 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 3.16% | 2.56% to 3.80% | 0.072 | 0.041 | 411 | 7 | 1227 | 4.3 | 0.039 | 1.94 |
| A8c | Shield + location cover (post-hoc) | 2.52% | 2.02% to 3.05% | 0.072 | 0.076 | 480 | 68 | 1244 | 4.3 | 0.039 | 1.94 |
| A10 | Shield, no fallback | 2.54% | 2.06% to 3.05% | 0.072 | 0.065 | 0 | 0 | 1236 | 4.3 | 0.034 | 1.69 |
| A12 | Oracle gate (diagnostic) | 2.58% | 2.08% to 3.10% | 0.099 | 0.066 | 0 | 0 | 1233 | 6.0 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 3.54% | 2.89% to 4.21% | 0.074 | 0.048 | 408 | 7 | 1231 | 4.5 | 0.039 | 1.94 |
| B2 | B2 = B1 + mass guard | 3.56% | 2.91% to 4.24% | 0.075 | 0.048 | 410 | 7 | 1231 | 4.5 | 0.039 | 1.94 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 3.07% | 2.50% to 3.65% | 0.075 | 0.052 | 415 | 12 | 1230 | 4.5 | 0.039 | 1.95 |
| B4 | B4 = B1 + cost-aware fallback | 3.03% | 2.47% to 3.60% | 0.074 | 0.052 | 413 | 12 | 1230 | 4.4 | 0.039 | 1.95 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 2.92% | 2.39% to 3.47% | 0.073 | 0.050 | 632 | 17 | 1234 | 4.4 | 0.016 | 0.78 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | +0.15 | -0.18 to +0.48 | 0.463 | 20 / 25 / 105 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | +0.65 | +0.24 to +1.08 | 0.003 | 23 / 44 / 83 |
| B3-A8 | P3: Shield-2 vs plan's Shield | -0.09 | -0.47 to +0.29 | 0.705 | 23 / 19 / 108 |
| B3-A6 | Shield-2 vs verification-only gate | +0.18 | -0.22 to +0.59 | 0.456 | 32 / 34 / 84 |
| G1-A1 | equal-footing gate vs always commit | +0.51 | +0.09 to +0.93 | 0.024 | 23 / 44 / 83 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.38 | +0.09 to +0.68 | 0.019 | 11 / 24 / 115 |
| B2-B1 | mass guard (full cover) | +0.02 | -0.04 to +0.09 | 1.000 | 1 / 2 / 147 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.49 | -0.75 to -0.27 | 0.000 | 17 / 0 / 133 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.51 | -0.77 to -0.29 | 0.000 | 18 / 0 / 132 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.04 | -0.04 to +0.13 | 0.751 | 1 / 2 / 147 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.36 | -0.66 to -0.07 | 0.020 | 29 / 13 / 108 |
| A6-A1 | verification-only gate vs always commit | +0.47 | +0.20 to +0.74 | 0.001 | 4 / 30 / 116 |
| A12-A1 | headroom: oracle gate vs always commit | +0.16 | -0.25 to +0.58 | 0.491 | 26 / 34 / 90 |
| A1-A0 | record-induced misses of the head vs gold | +1.07 | +0.66 to +1.51 | 0.000 | 5 / 44 / 101 |
| A1-A2 | Q4 vs FP16 | +0.60 | +0.20 to +1.01 | 0.005 | 13 / 36 / 101 |
| A3-A2 | Q8 vs FP16 | +0.33 | +0.04 to +0.62 | 0.040 | 12 / 25 / 113 |
| A4-A1 | recentred vs trained-on-Q4 | +0.80 | +0.33 to +1.29 | 0.001 | 21 / 54 / 75 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 67.4% | 2.10% | 6.57% | 32.6% | 18.0% | 2.10% | 48.8% |
| A10 | 67.8% | 2.20% | 6.83% | 32.2% | 17.7% | 2.20% | 48.0% |
| B1 | 67.4% | 2.07% | 6.63% | 32.6% | 17.8% | 2.07% | 48.4% |
| B2 | 52.5% | 0.40% | 0.73% | 47.5% | 17.8% | 0.40% | 36.7% |
| B3 | 52.5% | 0.40% | 0.73% | 47.5% | 17.9% | 0.40% | 36.8% |
| B4 | 67.6% | 2.10% | 6.67% | 32.4% | 17.9% | 2.10% | 48.6% |
| G1 | 0.0% | 0.00% | 0.00% | 46.0% | 17.9% | 0.87% | 37.1% |
| A6 | 0.0% | 0.00% | 0.00% | 7.3% | 17.7% | 13.70% | 55.3% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | COVER_DECLINED | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|---|
| A8 | 2010 | 12 | 0 | 0 | 216 | 743 | 0 | 19 | 0 |
| B1 | 2012 | 10 | 0 | 0 | 223 | 733 | 1 | 21 | 0 |
| B2 | 1569 | 6 | 0 | 0 | 226 | 734 | 1 | 22 | 442 |
| B3 | 1571 | 5 | 0 | 1 | 225 | 716 | 26 | 10 | 446 |
| B4 | 2018 | 9 | 0 | 1 | 222 | 713 | 27 | 10 | 0 |
| G1 | 0 | 0 | 1621 | 0 | 219 | 1122 | 23 | 15 | 0 |

### Level M: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 4.92% | 4.10% to 5.83% | 0.000 | 0.000 | 0 | 0 | 1076 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 7.41% | 6.42% to 8.46% | 0.000 | 0.076 | 0 | 0 | 1114 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 6.30% | 5.36% to 7.26% | 0.000 | 0.057 | 0 | 0 | 1106 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 6.50% | 5.53% to 7.49% | 0.000 | 0.063 | 0 | 0 | 1100 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 8.01% | 7.07% to 8.95% | 0.000 | 0.124 | 0 | 0 | 1141 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 16.49% | 15.56% to 17.42% | 0.000 | 0.164 | 0 | 0 | 1079 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 7.07% | 6.13% to 8.11% | 0.073 | 0.070 | 0 | 0 | 1107 | 4.4 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 8.23% | 7.22% to 9.28% | 0.076 | 0.043 | 436 | 7 | 1094 | 4.6 | 0.039 | 1.96 |
| A8c | Shield + location cover (post-hoc) | 7.05% | 6.13% to 8.02% | 0.077 | 0.079 | 493 | 63 | 1119 | 4.6 | 0.039 | 1.95 |
| A10 | Shield, no fallback | 7.01% | 6.09% to 7.98% | 0.077 | 0.069 | 0 | 0 | 1116 | 4.6 | 0.034 | 1.69 |
| A12 | Oracle gate (diagnostic) | 6.94% | 5.97% to 7.96% | 0.099 | 0.066 | 0 | 0 | 1106 | 6.0 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 8.56% | 7.51% to 9.61% | 0.075 | 0.048 | 434 | 9 | 1091 | 4.5 | 0.039 | 1.96 |
| B2 | B2 = B1 + mass guard | 8.57% | 7.53% to 9.62% | 0.076 | 0.048 | 436 | 9 | 1094 | 4.5 | 0.039 | 1.96 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 7.81% | 6.83% to 8.84% | 0.076 | 0.058 | 447 | 22 | 1104 | 4.6 | 0.040 | 1.98 |
| B4 | B4 = B1 + cost-aware fallback | 7.76% | 6.76% to 8.80% | 0.075 | 0.058 | 446 | 23 | 1102 | 4.5 | 0.040 | 1.98 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 7.74% | 6.78% to 8.77% | 0.073 | 0.055 | 656 | 30 | 1110 | 4.4 | 0.016 | 0.81 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | +0.07 | -0.44 to +0.61 | 0.842 | 31 / 30 / 89 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | +0.40 | -0.32 to +1.15 | 0.313 | 42 / 48 / 60 |
| B3-A8 | P3: Shield-2 vs plan's Shield | -0.42 | -0.88 to +0.05 | 0.101 | 33 / 23 / 94 |
| B3-A6 | Shield-2 vs verification-only gate | +0.74 | +0.02 to +1.48 | 0.054 | 38 / 55 / 57 |
| G1-A1 | equal-footing gate vs always commit | +0.33 | -0.38 to +1.03 | 0.389 | 43 / 55 / 52 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.33 | +0.00 to +0.67 | 0.073 | 15 / 25 / 110 |
| B2-B1 | mass guard (full cover) | +0.02 | -0.11 to +0.17 | 1.000 | 4 / 3 / 143 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.76 | -1.11 to -0.44 | 0.000 | 32 / 5 / 113 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.80 | -1.17 to -0.46 | 0.000 | 32 / 5 / 113 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.05 | -0.04 to +0.19 | 0.753 | 1 / 2 / 147 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.02 | -0.49 to +0.45 | 1.000 | 29 / 30 / 91 |
| A6-A1 | verification-only gate vs always commit | -0.35 | -0.84 to +0.13 | 0.185 | 34 / 28 / 88 |
| A12-A1 | headroom: oracle gate vs always commit | -0.47 | -1.07 to +0.13 | 0.141 | 44 / 33 / 73 |
| A1-A0 | record-induced misses of the head vs gold | +2.49 | +1.86 to +3.14 | 0.000 | 11 / 72 / 67 |
| A1-A2 | Q4 vs FP16 | +1.11 | +0.47 to +1.77 | 0.001 | 27 / 54 / 69 |
| A3-A2 | Q8 vs FP16 | +0.20 | -0.28 to +0.69 | 0.481 | 23 / 27 / 100 |
| A4-A1 | recentred vs trained-on-Q4 | +0.60 | -0.17 to +1.36 | 0.134 | 37 / 61 / 52 |

Per arrival seed (each seed re-partitions the same reports, so seeds are not independent):

| seed | B3 - G1 (pp) | CI | B3 - A1 (pp) | CI |
|---|---|---|---|---|
| 1 | +0.00 | -0.76 to +0.77 | -0.22 | -1.11 to +0.71 |
| 2 | +0.05 | -0.80 to +0.98 | +0.60 | -0.97 to +2.17 |
| 3 | +0.16 | -0.84 to +1.17 | +0.82 | -0.48 to +2.15 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 65.7% | 2.23% | 5.83% | 34.3% | 19.0% | 2.23% | 49.0% |
| A10 | 66.0% | 2.27% | 6.03% | 34.0% | 19.0% | 2.27% | 49.3% |
| B1 | 65.8% | 2.17% | 5.90% | 34.2% | 19.0% | 2.17% | 49.2% |
| B2 | 52.3% | 0.40% | 0.67% | 47.7% | 19.0% | 0.40% | 39.1% |
| B3 | 52.3% | 0.40% | 0.63% | 47.7% | 18.9% | 0.40% | 38.7% |
| B4 | 65.9% | 2.13% | 5.97% | 34.1% | 18.8% | 2.13% | 49.0% |
| G1 | 0.0% | 0.00% | 0.00% | 46.4% | 18.7% | 0.87% | 38.3% |
| A6 | 0.0% | 0.00% | 0.00% | 7.3% | 18.8% | 14.70% | 56.6% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | COVER_DECLINED | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|---|
| A8 | 1944 | 28 | 0 | 0 | 228 | 746 | 0 | 54 | 0 |
| B1 | 1935 | 38 | 0 | 0 | 224 | 739 | 1 | 63 | 0 |
| B2 | 1545 | 24 | 0 | 0 | 227 | 742 | 1 | 63 | 398 |
| B3 | 1550 | 20 | 0 | 3 | 229 | 684 | 79 | 34 | 401 |
| B4 | 1946 | 32 | 0 | 3 | 226 | 682 | 78 | 33 | 0 |
| G1 | 0 | 0 | 1607 | 2 | 219 | 1049 | 80 | 43 | 0 |

### Level H: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 13.42% | 12.11% to 14.67% | 0.000 | 0.000 | 0 | 0 | 772 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 16.39% | 15.05% to 17.63% | 0.000 | 0.073 | 0 | 0 | 795 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 15.33% | 13.96% to 16.64% | 0.000 | 0.056 | 0 | 0 | 792 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 16.11% | 14.65% to 17.46% | 0.000 | 0.061 | 0 | 0 | 791 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 16.48% | 15.20% to 17.65% | 0.000 | 0.119 | 0 | 0 | 812 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 22.56% | 21.29% to 23.79% | 0.000 | 0.156 | 0 | 0 | 769 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 16.09% | 14.76% to 17.35% | 0.073 | 0.056 | 0 | 0 | 786 | 4.4 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 17.87% | 16.49% to 19.11% | 0.076 | 0.036 | 474 | 10 | 787 | 4.6 | 0.040 | 1.98 |
| A8c | Shield + location cover (post-hoc) | 15.75% | 14.41% to 17.01% | 0.074 | 0.066 | 523 | 57 | 795 | 4.4 | 0.040 | 1.98 |
| A10 | Shield, no fallback | 15.64% | 14.26% to 16.95% | 0.073 | 0.056 | 0 | 0 | 793 | 4.4 | 0.034 | 1.69 |
| A12 | Oracle gate (diagnostic) | 15.69% | 14.39% to 16.91% | 0.099 | 0.055 | 0 | 0 | 788 | 6.0 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 18.37% | 16.99% to 19.61% | 0.078 | 0.037 | 462 | 10 | 790 | 4.7 | 0.040 | 1.99 |
| B2 | B2 = B1 + mass guard | 18.37% | 16.98% to 19.61% | 0.079 | 0.037 | 462 | 10 | 789 | 4.7 | 0.040 | 1.99 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 17.20% | 15.87% to 18.46% | 0.079 | 0.048 | 474 | 26 | 798 | 4.8 | 0.041 | 2.03 |
| B4 | B4 = B1 + cost-aware fallback | 17.17% | 15.84% to 18.45% | 0.078 | 0.047 | 474 | 26 | 799 | 4.7 | 0.041 | 2.03 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 17.33% | 15.97% to 18.61% | 0.073 | 0.051 | 671 | 35 | 789 | 4.4 | 0.017 | 0.85 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | -0.13 | -0.73 to +0.48 | 0.724 | 46 / 31 / 73 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | +0.82 | +0.00 to +1.63 | 0.054 | 37 / 62 / 51 |
| B3-A8 | P3: Shield-2 vs plan's Shield | -0.67 | -1.31 to -0.02 | 0.046 | 54 / 25 / 71 |
| B3-A6 | Shield-2 vs verification-only gate | +1.11 | +0.36 to +1.85 | 0.004 | 34 / 63 / 53 |
| G1-A1 | equal-footing gate vs always commit | +0.94 | +0.18 to +1.71 | 0.018 | 38 / 63 / 49 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.49 | -0.07 to +1.07 | 0.106 | 24 / 30 / 96 |
| B2-B1 | mass guard (full cover) | +0.00 | -0.05 to +0.05 | 1.000 | 1 / 1 / 148 |
| B3-B2 | cost-aware fallback (with mass guard) | -1.16 | -1.54 to -0.80 | 0.000 | 47 / 5 / 98 |
| B4-B1 | cost-aware fallback (no mass guard) | -1.20 | -1.60 to -0.82 | 0.000 | 47 / 5 / 98 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.04 | +0.00 to +0.11 | 1.000 | 0 / 1 / 149 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.35 | -0.86 to +0.15 | 0.205 | 39 / 25 / 86 |
| A6-A1 | verification-only gate vs always commit | -0.29 | -0.83 to +0.25 | 0.322 | 37 / 29 / 84 |
| A12-A1 | headroom: oracle gate vs always commit | -0.69 | -1.45 to +0.11 | 0.095 | 59 / 34 / 57 |
| A1-A0 | record-induced misses of the head vs gold | +2.96 | +2.21 to +3.72 | 0.000 | 18 / 90 / 42 |
| A1-A2 | Q4 vs FP16 | +1.05 | +0.31 to +1.80 | 0.009 | 38 / 63 / 49 |
| A3-A2 | Q8 vs FP16 | +0.78 | +0.22 to +1.37 | 0.010 | 23 / 38 / 89 |
| A4-A1 | recentred vs trained-on-Q4 | +0.09 | -0.76 to +0.93 | 0.869 | 50 / 58 / 42 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 63.0% | 2.07% | 4.17% | 37.0% | 20.9% | 2.07% | 51.0% |
| A10 | 63.4% | 2.17% | 4.53% | 36.6% | 20.5% | 2.17% | 50.1% |
| B1 | 62.6% | 2.00% | 4.07% | 37.4% | 20.9% | 2.00% | 50.6% |
| B2 | 52.0% | 0.40% | 0.53% | 48.0% | 20.9% | 0.40% | 42.7% |
| B3 | 52.0% | 0.40% | 0.53% | 48.0% | 20.8% | 0.40% | 42.5% |
| B4 | 62.7% | 2.00% | 4.17% | 37.3% | 20.8% | 2.00% | 50.4% |
| G1 | 0.0% | 0.00% | 0.00% | 47.6% | 20.7% | 0.80% | 41.9% |
| A6 | 0.0% | 0.00% | 0.00% | 7.3% | 20.4% | 16.23% | 57.1% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | COVER_DECLINED | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|---|
| A8 | 1749 | 141 | 0 | 0 | 228 | 704 | 0 | 178 | 0 |
| B1 | 1739 | 138 | 0 | 0 | 233 | 705 | 1 | 184 | 0 |
| B2 | 1454 | 107 | 0 | 0 | 237 | 704 | 1 | 185 | 312 |
| B3 | 1466 | 95 | 0 | 6 | 238 | 635 | 123 | 121 | 316 |
| B4 | 1757 | 124 | 0 | 6 | 234 | 636 | 122 | 121 | 0 |
| G1 | 0 | 0 | 1573 | 4 | 219 | 934 | 121 | 149 | 0 |

## Readout `f16`  (f16)

### Level L: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 1.34% | 0.91% to 1.86% | 0.000 | 0.000 | 0 | 0 | 1193 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 1.82% | 1.32% to 2.37% | 0.000 | 0.054 | 0 | 0 | 1240 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 1.82% | 1.32% to 2.37% | 0.000 | 0.054 | 0 | 0 | 1240 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 2.14% | 1.62% to 2.72% | 0.000 | 0.059 | 0 | 0 | 1241 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 3.22% | 2.65% to 3.79% | 0.000 | 0.117 | 0 | 0 | 1278 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 13.93% | 13.12% to 14.72% | 0.000 | 0.158 | 0 | 0 | 1168 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 2.76% | 2.25% to 3.30% | 0.072 | 0.078 | 0 | 0 | 1254 | 4.3 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 2.29% | 1.75% to 2.86% | 0.076 | 0.047 | 138 | 8 | 1225 | 4.5 | 0.029 | 1.44 |
| A8c | Shield + location cover (post-hoc) | 2.14% | 1.62% to 2.69% | 0.075 | 0.056 | 158 | 25 | 1236 | 4.5 | 0.029 | 1.44 |
| A10 | Shield, no fallback | 2.14% | 1.62% to 2.69% | 0.075 | 0.056 | 0 | 0 | 1237 | 4.5 | 0.027 | 1.35 |
| A12 | Oracle gate (diagnostic) | 2.34% | 1.85% to 2.87% | 0.098 | 0.051 | 0 | 0 | 1228 | 5.9 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 2.42% | 1.88% to 2.94% | 0.078 | 0.047 | 126 | 4 | 1228 | 4.7 | 0.029 | 1.44 |
| B2 | B2 = B1 + mass guard | 2.60% | 2.06% to 3.14% | 0.079 | 0.044 | 157 | 6 | 1232 | 4.7 | 0.029 | 1.46 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 2.49% | 1.97% to 3.03% | 0.079 | 0.044 | 157 | 6 | 1231 | 4.7 | 0.029 | 1.46 |
| B4 | B4 = B1 + cost-aware fallback | 2.34% | 1.83% to 2.85% | 0.078 | 0.047 | 126 | 4 | 1226 | 4.7 | 0.029 | 1.44 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 2.78% | 2.23% to 3.35% | 0.072 | 0.063 | 569 | 38 | 1239 | 4.3 | 0.013 | 0.64 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | -0.29 | -0.62 to +0.02 | 0.101 | 27 / 18 / 105 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | +0.67 | +0.32 to +1.03 | 0.001 | 14 / 42 / 94 |
| B3-A8 | P3: Shield-2 vs plan's Shield | +0.20 | -0.11 to +0.51 | 0.262 | 15 / 23 / 112 |
| B3-A6 | Shield-2 vs verification-only gate | -0.27 | -0.61 to +0.05 | 0.128 | 30 / 21 / 99 |
| G1-A1 | equal-footing gate vs always commit | +0.96 | +0.57 to +1.37 | 0.000 | 9 / 44 / 97 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.13 | -0.09 to +0.35 | 0.346 | 4 / 10 / 136 |
| B2-B1 | mass guard (full cover) | +0.18 | -0.02 to +0.40 | 0.127 | 10 / 17 / 123 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.11 | -0.24 to -0.02 | 0.122 | 4 / 0 / 146 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.07 | -0.17 to +0.00 | 0.248 | 3 / 0 / 147 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.15 | -0.07 to +0.37 | 0.267 | 11 / 17 / 122 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.62 | -0.96 to -0.29 | 0.000 | 34 / 10 / 106 |
| A6-A1 | verification-only gate vs always commit | +0.94 | +0.63 to +1.28 | 0.000 | 4 / 45 / 101 |
| A12-A1 | headroom: oracle gate vs always commit | +0.53 | +0.14 to +0.90 | 0.009 | 14 / 39 / 97 |
| A1-A0 | record-induced misses of the head vs gold | +0.47 | +0.18 to +0.78 | 0.005 | 9 / 28 / 113 |
| A1-A2 | Q4 vs FP16 | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| A3-A2 | Q8 vs FP16 | +0.33 | +0.04 to +0.62 | 0.040 | 12 / 25 / 113 |
| A4-A1 | recentred vs trained-on-Q4 | +1.40 | +0.96 to +1.85 | 0.000 | 13 / 64 / 73 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 84.2% | 4.97% | 12.17% | 15.8% | 12.1% | 4.97% | 45.1% |
| A10 | 84.2% | 4.97% | 12.03% | 15.8% | 12.2% | 4.97% | 45.9% |
| B1 | 84.0% | 5.00% | 12.00% | 16.0% | 12.2% | 5.00% | 44.8% |
| B2 | 60.8% | 0.33% | 2.90% | 39.2% | 12.1% | 0.33% | 30.1% |
| B3 | 60.8% | 0.33% | 2.90% | 39.2% | 12.1% | 0.33% | 30.1% |
| B4 | 84.0% | 5.00% | 12.00% | 16.0% | 12.2% | 5.00% | 44.9% |
| G1 | 0.0% | 0.00% | 0.00% | 39.0% | 12.2% | 0.93% | 28.8% |
| A6 | 0.0% | 0.00% | 0.00% | 7.2% | 12.2% | 9.83% | 32.7% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|
| A8 | 2507 | 18 | 0 | 227 | 242 | 4 | 2 | 0 |
| B1 | 2505 | 15 | 0 | 233 | 238 | 4 | 5 | 0 |
| B2 | 1816 | 8 | 0 | 237 | 285 | 4 | 7 | 643 |
| B3 | 1816 | 8 | 0 | 237 | 278 | 11 | 6 | 644 |
| B4 | 2506 | 15 | 0 | 233 | 232 | 9 | 5 | 0 |
| G1 | 0 | 0 | 1829 | 217 | 932 | 13 | 9 | 0 |

### Level M: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 4.92% | 4.10% to 5.83% | 0.000 | 0.000 | 0 | 0 | 1076 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 6.30% | 5.36% to 7.26% | 0.000 | 0.057 | 0 | 0 | 1106 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 6.30% | 5.36% to 7.26% | 0.000 | 0.057 | 0 | 0 | 1106 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 6.50% | 5.53% to 7.49% | 0.000 | 0.063 | 0 | 0 | 1100 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 8.01% | 7.07% to 8.95% | 0.000 | 0.124 | 0 | 0 | 1141 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 16.49% | 15.56% to 17.42% | 0.000 | 0.164 | 0 | 0 | 1079 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 6.74% | 5.84% to 7.66% | 0.072 | 0.077 | 0 | 0 | 1115 | 4.3 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 6.25% | 5.30% to 7.22% | 0.071 | 0.049 | 162 | 4 | 1100 | 4.3 | 0.029 | 1.46 |
| A8c | Shield + location cover (post-hoc) | 6.07% | 5.17% to 7.00% | 0.070 | 0.064 | 194 | 30 | 1101 | 4.2 | 0.029 | 1.46 |
| A10 | Shield, no fallback | 6.05% | 5.15% to 6.98% | 0.070 | 0.063 | 0 | 0 | 1101 | 4.2 | 0.027 | 1.35 |
| A12 | Oracle gate (diagnostic) | 6.23% | 5.38% to 7.09% | 0.098 | 0.048 | 0 | 0 | 1091 | 5.9 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 6.29% | 5.38% to 7.21% | 0.074 | 0.051 | 157 | 4 | 1106 | 4.4 | 0.029 | 1.46 |
| B2 | B2 = B1 + mass guard | 6.68% | 5.78% to 7.64% | 0.076 | 0.052 | 173 | 4 | 1105 | 4.5 | 0.029 | 1.47 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 6.47% | 5.59% to 7.40% | 0.076 | 0.053 | 177 | 8 | 1105 | 4.5 | 0.030 | 1.48 |
| B4 | B4 = B1 + cost-aware fallback | 6.09% | 5.23% to 7.01% | 0.074 | 0.053 | 161 | 8 | 1105 | 4.5 | 0.029 | 1.47 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 6.47% | 5.59% to 7.42% | 0.072 | 0.059 | 582 | 41 | 1103 | 4.3 | 0.013 | 0.66 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | +0.00 | -0.46 to +0.44 | 1.000 | 25 / 30 / 95 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | +0.16 | -0.46 to +0.77 | 0.648 | 37 / 47 / 66 |
| B3-A8 | P3: Shield-2 vs plan's Shield | +0.22 | -0.24 to +0.68 | 0.396 | 19 / 28 / 103 |
| B3-A6 | Shield-2 vs verification-only gate | -0.27 | -0.77 to +0.22 | 0.311 | 37 / 31 / 82 |
| G1-A1 | equal-footing gate vs always commit | +0.16 | -0.36 to +0.69 | 0.594 | 33 / 39 / 78 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.04 | -0.32 to +0.37 | 0.921 | 10 / 12 / 128 |
| B2-B1 | mass guard (full cover) | +0.40 | +0.13 to +0.68 | 0.006 | 7 / 22 / 121 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.22 | -0.46 to +0.00 | 0.096 | 11 / 3 / 136 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.20 | -0.38 to -0.04 | 0.040 | 9 / 1 / 140 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.38 | +0.14 to +0.64 | 0.004 | 6 / 18 / 126 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.67 | -1.10 to -0.26 | 0.004 | 39 / 14 / 97 |
| A6-A1 | verification-only gate vs always commit | +0.44 | +0.02 to +0.87 | 0.057 | 19 / 36 / 95 |
| A12-A1 | headroom: oracle gate vs always commit | -0.07 | -0.59 to +0.43 | 0.837 | 42 / 36 / 72 |
| A1-A0 | record-induced misses of the head vs gold | +1.38 | +0.88 to +1.90 | 0.000 | 13 / 56 / 81 |
| A1-A2 | Q4 vs FP16 | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| A3-A2 | Q8 vs FP16 | +0.20 | -0.28 to +0.69 | 0.481 | 23 / 27 / 100 |
| A4-A1 | recentred vs trained-on-Q4 | +1.71 | +1.04 to +2.41 | 0.000 | 25 / 69 / 56 |

Per arrival seed (each seed re-partitions the same reports, so seeds are not independent):

| seed | B3 - G1 (pp) | CI | B3 - A1 (pp) | CI |
|---|---|---|---|---|
| 1 | -0.82 | -1.65 to -0.05 | -0.60 | -1.70 to +0.44 |
| 2 | +0.27 | -0.59 to +1.09 | +0.22 | -1.04 to +1.48 |
| 3 | +0.54 | -0.05 to +1.18 | +0.87 | +0.11 to +1.66 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 82.7% | 5.07% | 11.20% | 17.3% | 13.2% | 5.07% | 47.3% |
| A10 | 82.5% | 4.97% | 11.13% | 17.5% | 13.1% | 4.97% | 46.6% |
| B1 | 82.4% | 5.00% | 11.00% | 17.6% | 13.4% | 5.00% | 47.4% |
| B2 | 60.3% | 0.33% | 2.50% | 39.7% | 13.2% | 0.33% | 32.5% |
| B3 | 60.4% | 0.33% | 2.53% | 39.6% | 13.2% | 0.33% | 32.5% |
| B4 | 82.3% | 4.97% | 11.00% | 17.7% | 13.3% | 4.97% | 47.3% |
| G1 | 0.0% | 0.00% | 0.00% | 39.8% | 13.0% | 0.97% | 30.3% |
| A6 | 0.0% | 0.00% | 0.00% | 7.2% | 13.1% | 10.43% | 36.4% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|
| A8 | 2439 | 43 | 0 | 213 | 290 | 4 | 11 | 0 |
| B1 | 2433 | 38 | 0 | 222 | 289 | 4 | 14 | 0 |
| B2 | 1796 | 14 | 0 | 227 | 327 | 4 | 17 | 615 |
| B3 | 1798 | 13 | 0 | 227 | 311 | 25 | 12 | 614 |
| B4 | 2433 | 36 | 0 | 223 | 276 | 20 | 12 | 0 |
| G1 | 0 | 0 | 1807 | 217 | 918 | 29 | 29 | 0 |

### Level H: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 13.42% | 12.11% to 14.67% | 0.000 | 0.000 | 0 | 0 | 772 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 15.33% | 13.96% to 16.64% | 0.000 | 0.056 | 0 | 0 | 792 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 15.33% | 13.96% to 16.64% | 0.000 | 0.056 | 0 | 0 | 792 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 16.11% | 14.65% to 17.46% | 0.000 | 0.061 | 0 | 0 | 791 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 16.48% | 15.20% to 17.65% | 0.000 | 0.119 | 0 | 0 | 812 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 22.56% | 21.29% to 23.79% | 0.000 | 0.156 | 0 | 0 | 769 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 15.55% | 14.19% to 16.88% | 0.072 | 0.063 | 0 | 0 | 791 | 4.3 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 15.48% | 14.13% to 16.73% | 0.076 | 0.038 | 225 | 6 | 789 | 4.5 | 0.030 | 1.49 |
| A8c | Shield + location cover (post-hoc) | 15.04% | 13.72% to 16.28% | 0.074 | 0.054 | 262 | 36 | 795 | 4.5 | 0.030 | 1.50 |
| A10 | Shield, no fallback | 15.08% | 13.75% to 16.31% | 0.074 | 0.053 | 0 | 0 | 795 | 4.5 | 0.027 | 1.35 |
| A12 | Oracle gate (diagnostic) | 14.86% | 13.50% to 16.15% | 0.098 | 0.039 | 0 | 0 | 781 | 5.9 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 15.68% | 14.26% to 16.92% | 0.075 | 0.038 | 233 | 6 | 785 | 4.5 | 0.030 | 1.50 |
| B2 | B2 = B1 + mass guard | 15.86% | 14.48% to 17.08% | 0.074 | 0.036 | 249 | 9 | 786 | 4.4 | 0.030 | 1.51 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 15.59% | 14.20% to 16.83% | 0.074 | 0.041 | 264 | 21 | 786 | 4.5 | 0.031 | 1.53 |
| B4 | B4 = B1 + cost-aware fallback | 15.39% | 14.01% to 16.60% | 0.075 | 0.041 | 245 | 15 | 785 | 4.5 | 0.030 | 1.51 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 16.00% | 14.61% to 17.34% | 0.072 | 0.052 | 609 | 54 | 790 | 4.3 | 0.014 | 0.69 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | -0.42 | -0.89 to +0.06 | 0.108 | 40 / 22 / 88 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | +0.25 | -0.38 to +0.86 | 0.455 | 38 / 47 / 65 |
| B3-A8 | P3: Shield-2 vs plan's Shield | +0.11 | -0.52 to +0.75 | 0.776 | 31 / 31 / 88 |
| B3-A6 | Shield-2 vs verification-only gate | +0.04 | -0.56 to +0.64 | 0.956 | 46 / 36 / 68 |
| G1-A1 | equal-footing gate vs always commit | +0.67 | +0.09 to +1.23 | 0.029 | 28 / 56 / 66 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.20 | -0.27 to +0.66 | 0.450 | 17 / 26 / 107 |
| B2-B1 | mass guard (full cover) | +0.18 | -0.15 to +0.54 | 0.380 | 13 / 14 / 123 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.27 | -0.60 to +0.05 | 0.124 | 17 / 6 / 127 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.29 | -0.60 to +0.02 | 0.080 | 18 / 4 / 128 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.20 | -0.11 to +0.55 | 0.311 | 9 / 13 / 128 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.51 | -0.91 to -0.11 | 0.016 | 35 / 14 / 101 |
| A6-A1 | verification-only gate vs always commit | +0.22 | -0.29 to +0.72 | 0.445 | 23 / 35 / 92 |
| A12-A1 | headroom: oracle gate vs always commit | -0.47 | -1.18 to +0.25 | 0.207 | 52 / 33 / 65 |
| A1-A0 | record-induced misses of the head vs gold | +1.91 | +1.24 to +2.60 | 0.000 | 19 / 70 / 61 |
| A1-A2 | Q4 vs FP16 | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| A3-A2 | Q8 vs FP16 | +0.78 | +0.22 to +1.37 | 0.010 | 23 / 38 / 89 |
| A4-A1 | recentred vs trained-on-Q4 | +1.14 | +0.31 to +1.96 | 0.006 | 35 / 74 / 41 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 78.7% | 4.63% | 9.17% | 21.3% | 15.0% | 4.63% | 48.5% |
| A10 | 78.6% | 4.57% | 9.13% | 21.4% | 14.9% | 4.57% | 48.1% |
| B1 | 78.3% | 4.53% | 9.00% | 21.7% | 14.8% | 4.53% | 47.4% |
| B2 | 58.9% | 0.37% | 2.00% | 41.1% | 14.8% | 0.37% | 35.2% |
| B3 | 58.9% | 0.37% | 1.97% | 41.1% | 14.8% | 0.37% | 35.2% |
| B4 | 78.2% | 4.53% | 8.97% | 21.8% | 14.8% | 4.53% | 47.0% |
| G1 | 0.0% | 0.00% | 0.00% | 40.9% | 15.3% | 0.80% | 35.5% |
| A6 | 0.0% | 0.00% | 0.00% | 7.2% | 15.2% | 12.03% | 44.2% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|
| A8 | 2192 | 169 | 0 | 227 | 353 | 3 | 56 | 0 |
| B1 | 2186 | 162 | 0 | 224 | 358 | 3 | 67 | 0 |
| B2 | 1676 | 91 | 0 | 222 | 385 | 2 | 77 | 547 |
| B3 | 1681 | 86 | 0 | 223 | 369 | 51 | 48 | 542 |
| B4 | 2188 | 157 | 0 | 224 | 345 | 41 | 45 | 0 |
| G1 | 0 | 0 | 1773 | 217 | 839 | 57 | 114 | 0 |

## Readout `q8`  (q8)

### Level L: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 1.34% | 0.91% to 1.86% | 0.000 | 0.000 | 0 | 0 | 1193 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 2.14% | 1.62% to 2.72% | 0.000 | 0.059 | 0 | 0 | 1241 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 1.82% | 1.32% to 2.37% | 0.000 | 0.054 | 0 | 0 | 1240 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 2.14% | 1.62% to 2.72% | 0.000 | 0.059 | 0 | 0 | 1241 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 3.22% | 2.65% to 3.79% | 0.000 | 0.117 | 0 | 0 | 1278 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 13.93% | 13.12% to 14.72% | 0.000 | 0.158 | 0 | 0 | 1168 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 2.43% | 1.89% to 3.01% | 0.074 | 0.071 | 0 | 0 | 1244 | 4.5 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 2.11% | 1.66% to 2.56% | 0.078 | 0.042 | 198 | 17 | 1212 | 4.7 | 0.030 | 1.51 |
| A8c | Shield + location cover (post-hoc) | 2.13% | 1.61% to 2.68% | 0.080 | 0.050 | 219 | 36 | 1223 | 4.8 | 0.030 | 1.51 |
| A10 | Shield, no fallback | 2.09% | 1.59% to 2.62% | 0.080 | 0.049 | 0 | 0 | 1222 | 4.8 | 0.028 | 1.41 |
| A12 | Oracle gate (diagnostic) | 2.36% | 1.89% to 2.88% | 0.098 | 0.051 | 0 | 0 | 1228 | 5.9 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 2.31% | 1.84% to 2.78% | 0.073 | 0.043 | 193 | 16 | 1221 | 4.4 | 0.030 | 1.52 |
| B2 | B2 = B1 + mass guard | 2.43% | 1.92% to 2.94% | 0.075 | 0.046 | 214 | 18 | 1225 | 4.5 | 0.031 | 1.53 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 2.29% | 1.82% to 2.75% | 0.075 | 0.046 | 214 | 18 | 1224 | 4.5 | 0.031 | 1.53 |
| B4 | B4 = B1 + cost-aware fallback | 2.27% | 1.82% to 2.74% | 0.073 | 0.044 | 193 | 16 | 1222 | 4.4 | 0.030 | 1.52 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 2.43% | 1.96% to 2.91% | 0.074 | 0.058 | 577 | 27 | 1233 | 4.5 | 0.013 | 0.66 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | -0.15 | -0.46 to +0.18 | 0.452 | 24 / 18 / 108 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | +0.15 | -0.29 to +0.56 | 0.557 | 20 / 28 / 102 |
| B3-A8 | P3: Shield-2 vs plan's Shield | +0.18 | -0.06 to +0.43 | 0.198 | 7 / 16 / 127 |
| B3-A6 | Shield-2 vs verification-only gate | -0.15 | -0.59 to +0.27 | 0.566 | 24 / 24 / 102 |
| G1-A1 | equal-footing gate vs always commit | +0.29 | -0.16 to +0.73 | 0.229 | 19 / 38 / 93 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.20 | +0.00 to +0.43 | 0.100 | 4 / 11 / 135 |
| B2-B1 | mass guard (full cover) | +0.13 | -0.07 to +0.36 | 0.361 | 5 / 10 / 135 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.15 | -0.36 to +0.00 | 0.252 | 4 / 1 / 145 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.04 | -0.11 to +0.04 | 0.626 | 3 / 1 / 146 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.02 | -0.15 to +0.18 | 1.000 | 6 / 9 / 135 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.31 | -0.69 to +0.06 | 0.132 | 27 / 15 / 108 |
| A6-A1 | verification-only gate vs always commit | +0.29 | -0.02 to +0.60 | 0.090 | 18 / 30 / 102 |
| A12-A1 | headroom: oracle gate vs always commit | +0.22 | -0.16 to +0.59 | 0.294 | 21 / 33 / 96 |
| A1-A0 | record-induced misses of the head vs gold | +0.80 | +0.45 to +1.16 | 0.000 | 9 / 39 / 102 |
| A1-A2 | Q4 vs FP16 | +0.33 | +0.04 to +0.62 | 0.040 | 12 / 25 / 113 |
| A3-A2 | Q8 vs FP16 | +0.33 | +0.04 to +0.62 | 0.040 | 12 / 25 / 113 |
| A4-A1 | recentred vs trained-on-Q4 | +1.07 | +0.59 to +1.53 | 0.000 | 17 / 64 / 69 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 81.6% | 4.20% | 12.03% | 18.4% | 13.1% | 4.20% | 48.6% |
| A10 | 81.4% | 4.23% | 11.93% | 18.6% | 13.1% | 4.23% | 47.8% |
| B1 | 81.5% | 4.30% | 12.03% | 18.5% | 13.2% | 4.30% | 48.0% |
| B2 | 58.9% | 0.53% | 2.60% | 41.1% | 13.2% | 0.53% | 30.9% |
| B3 | 58.9% | 0.50% | 2.57% | 41.1% | 13.3% | 0.50% | 31.0% |
| B4 | 81.4% | 4.30% | 12.00% | 18.6% | 13.2% | 4.30% | 48.1% |
| G1 | 0.0% | 0.00% | 0.00% | 40.0% | 13.4% | 1.07% | 30.8% |
| A6 | 0.0% | 0.00% | 0.00% | 7.4% | 13.0% | 9.90% | 41.3% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|
| A8 | 2438 | 11 | 0 | 233 | 311 | 2 | 5 | 0 |
| B1 | 2433 | 11 | 0 | 220 | 328 | 2 | 6 | 0 |
| B2 | 1763 | 4 | 0 | 224 | 351 | 2 | 9 | 647 |
| B3 | 1762 | 4 | 0 | 224 | 347 | 12 | 5 | 646 |
| B4 | 2432 | 11 | 0 | 220 | 321 | 12 | 4 | 0 |
| G1 | 0 | 0 | 1799 | 223 | 950 | 20 | 8 | 0 |

### Level M: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 4.92% | 4.10% to 5.83% | 0.000 | 0.000 | 0 | 0 | 1076 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 6.50% | 5.53% to 7.49% | 0.000 | 0.063 | 0 | 0 | 1100 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 6.30% | 5.36% to 7.26% | 0.000 | 0.057 | 0 | 0 | 1106 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 6.50% | 5.53% to 7.49% | 0.000 | 0.063 | 0 | 0 | 1100 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 8.01% | 7.07% to 8.95% | 0.000 | 0.124 | 0 | 0 | 1141 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 16.49% | 15.56% to 17.42% | 0.000 | 0.164 | 0 | 0 | 1079 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 6.30% | 5.41% to 7.21% | 0.074 | 0.070 | 0 | 0 | 1108 | 4.5 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 6.85% | 5.87% to 7.84% | 0.075 | 0.044 | 217 | 21 | 1106 | 4.5 | 0.031 | 1.53 |
| A8c | Shield + location cover (post-hoc) | 5.99% | 5.08% to 6.91% | 0.074 | 0.055 | 243 | 42 | 1101 | 4.4 | 0.031 | 1.53 |
| A10 | Shield, no fallback | 5.90% | 5.02% to 6.80% | 0.074 | 0.052 | 0 | 0 | 1100 | 4.4 | 0.028 | 1.41 |
| A12 | Oracle gate (diagnostic) | 6.03% | 5.21% to 6.90% | 0.098 | 0.046 | 0 | 0 | 1094 | 5.9 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 6.76% | 5.83% to 7.73% | 0.072 | 0.043 | 221 | 20 | 1098 | 4.3 | 0.031 | 1.54 |
| B2 | B2 = B1 + mass guard | 6.92% | 6.00% to 7.86% | 0.073 | 0.045 | 240 | 22 | 1100 | 4.4 | 0.031 | 1.55 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 6.49% | 5.62% to 7.39% | 0.074 | 0.048 | 253 | 30 | 1101 | 4.4 | 0.031 | 1.56 |
| B4 | B4 = B1 + cost-aware fallback | 6.38% | 5.50% to 7.31% | 0.072 | 0.046 | 229 | 24 | 1100 | 4.3 | 0.031 | 1.55 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 6.72% | 5.80% to 7.69% | 0.074 | 0.056 | 602 | 42 | 1105 | 4.5 | 0.014 | 0.68 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | -0.24 | -0.72 to +0.24 | 0.384 | 36 / 27 / 87 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | -0.02 | -0.60 to +0.54 | 1.000 | 36 / 41 / 73 |
| B3-A8 | P3: Shield-2 vs plan's Shield | -0.36 | -0.78 to +0.00 | 0.089 | 24 / 16 / 110 |
| B3-A6 | Shield-2 vs verification-only gate | +0.18 | -0.36 to +0.73 | 0.567 | 33 / 35 / 82 |
| G1-A1 | equal-footing gate vs always commit | +0.22 | -0.29 to +0.72 | 0.449 | 33 / 43 / 74 |
| B1-A8 | strict candidate check alone vs plan's Shield | -0.09 | -0.38 to +0.22 | 0.642 | 16 / 11 / 123 |
| B2-B1 | mass guard (full cover) | +0.16 | -0.05 to +0.36 | 0.185 | 2 / 12 / 136 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.44 | -0.71 to -0.20 | 0.001 | 19 / 3 / 128 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.38 | -0.68 to -0.13 | 0.008 | 14 / 3 / 133 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.11 | -0.04 to +0.26 | 0.245 | 3 / 9 / 138 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.31 | -0.67 to +0.05 | 0.117 | 28 / 19 / 103 |
| A6-A1 | verification-only gate vs always commit | -0.20 | -0.63 to +0.22 | 0.418 | 30 / 25 / 95 |
| A12-A1 | headroom: oracle gate vs always commit | -0.47 | -0.99 to +0.02 | 0.084 | 45 / 31 / 74 |
| A1-A0 | record-induced misses of the head vs gold | +1.58 | +1.15 to +2.03 | 0.000 | 8 / 61 / 81 |
| A1-A2 | Q4 vs FP16 | +0.20 | -0.28 to +0.69 | 0.481 | 23 / 27 / 100 |
| A3-A2 | Q8 vs FP16 | +0.20 | -0.28 to +0.69 | 0.481 | 23 / 27 / 100 |
| A4-A1 | recentred vs trained-on-Q4 | +1.51 | +0.79 to +2.21 | 0.000 | 24 / 72 / 54 |

Per arrival seed (each seed re-partitions the same reports, so seeds are not independent):

| seed | B3 - G1 (pp) | CI | B3 - A1 (pp) | CI |
|---|---|---|---|---|
| 1 | -0.71 | -1.42 to -0.05 | -0.54 | -1.54 to +0.44 |
| 2 | -0.11 | -0.85 to +0.65 | +0.38 | -0.22 to +0.99 |
| 3 | +0.11 | -0.91 to +1.15 | +0.11 | -1.13 to +1.32 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 79.7% | 4.37% | 11.13% | 20.3% | 14.1% | 4.37% | 47.9% |
| A10 | 79.7% | 4.27% | 11.13% | 20.3% | 14.0% | 4.27% | 48.0% |
| B1 | 79.4% | 4.37% | 10.97% | 20.6% | 14.1% | 4.37% | 47.2% |
| B2 | 58.3% | 0.47% | 2.20% | 41.7% | 14.1% | 0.47% | 32.7% |
| B3 | 58.3% | 0.47% | 2.13% | 41.7% | 14.3% | 0.47% | 33.2% |
| B4 | 79.3% | 4.40% | 10.87% | 20.7% | 14.3% | 4.40% | 47.9% |
| G1 | 0.0% | 0.00% | 0.00% | 40.8% | 14.3% | 0.97% | 32.6% |
| A6 | 0.0% | 0.00% | 0.00% | 7.4% | 14.0% | 10.60% | 45.7% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|
| A8 | 2359 | 31 | 0 | 224 | 362 | 2 | 22 | 0 |
| B1 | 2350 | 32 | 0 | 215 | 377 | 2 | 24 | 0 |
| B2 | 1734 | 15 | 0 | 220 | 398 | 2 | 26 | 605 |
| B3 | 1734 | 14 | 0 | 222 | 379 | 39 | 12 | 600 |
| B4 | 2349 | 29 | 0 | 217 | 357 | 34 | 14 | 0 |
| G1 | 0 | 0 | 1777 | 223 | 927 | 41 | 32 | 0 |

### Level H: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 13.42% | 12.11% to 14.67% | 0.000 | 0.000 | 0 | 0 | 772 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 16.11% | 14.65% to 17.46% | 0.000 | 0.061 | 0 | 0 | 791 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 15.33% | 13.96% to 16.64% | 0.000 | 0.056 | 0 | 0 | 792 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 16.11% | 14.65% to 17.46% | 0.000 | 0.061 | 0 | 0 | 791 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 16.48% | 15.20% to 17.65% | 0.000 | 0.119 | 0 | 0 | 812 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 22.56% | 21.29% to 23.79% | 0.000 | 0.156 | 0 | 0 | 769 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 15.60% | 14.16% to 16.99% | 0.074 | 0.055 | 0 | 0 | 785 | 4.5 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 15.91% | 14.53% to 17.23% | 0.073 | 0.033 | 280 | 20 | 789 | 4.4 | 0.032 | 1.58 |
| A8c | Shield + location cover (post-hoc) | 15.30% | 13.93% to 16.63% | 0.074 | 0.045 | 302 | 47 | 787 | 4.4 | 0.031 | 1.57 |
| A10 | Shield, no fallback | 15.28% | 13.91% to 16.61% | 0.074 | 0.045 | 0 | 0 | 787 | 4.4 | 0.028 | 1.41 |
| A12 | Oracle gate (diagnostic) | 15.11% | 13.70% to 16.40% | 0.098 | 0.042 | 0 | 0 | 783 | 5.9 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 16.39% | 15.01% to 17.66% | 0.071 | 0.035 | 295 | 23 | 789 | 4.3 | 0.032 | 1.58 |
| B2 | B2 = B1 + mass guard | 16.48% | 15.10% to 17.75% | 0.073 | 0.036 | 302 | 24 | 788 | 4.4 | 0.032 | 1.59 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 15.95% | 14.59% to 17.20% | 0.073 | 0.041 | 313 | 35 | 789 | 4.4 | 0.032 | 1.61 |
| B4 | B4 = B1 + cost-aware fallback | 15.69% | 14.37% to 16.93% | 0.071 | 0.038 | 306 | 34 | 788 | 4.3 | 0.032 | 1.60 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 15.84% | 14.51% to 17.06% | 0.074 | 0.046 | 628 | 39 | 797 | 4.5 | 0.015 | 0.73 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | +0.11 | -0.46 to +0.68 | 0.759 | 33 / 36 / 81 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | -0.16 | -0.89 to +0.57 | 0.699 | 45 / 44 / 61 |
| B3-A8 | P3: Shield-2 vs plan's Shield | +0.04 | -0.57 to +0.66 | 0.955 | 34 / 32 / 84 |
| B3-A6 | Shield-2 vs verification-only gate | +0.35 | -0.32 to +1.02 | 0.342 | 38 / 50 / 62 |
| G1-A1 | equal-footing gate vs always commit | -0.27 | -1.08 to +0.50 | 0.526 | 44 / 44 / 62 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.47 | +0.00 to +0.95 | 0.070 | 11 / 31 / 108 |
| B2-B1 | mass guard (full cover) | +0.09 | -0.26 to +0.50 | 0.716 | 6 / 6 / 138 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.53 | -0.92 to -0.16 | 0.009 | 24 / 8 / 118 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.69 | -1.10 to -0.33 | 0.001 | 28 / 7 / 115 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.25 | -0.09 to +0.64 | 0.214 | 2 / 8 / 140 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -0.31 | -0.81 to +0.20 | 0.265 | 36 / 23 / 91 |
| A6-A1 | verification-only gate vs always commit | -0.51 | -1.20 to +0.18 | 0.163 | 35 / 30 / 85 |
| A12-A1 | headroom: oracle gate vs always commit | -1.00 | -1.77 to -0.24 | 0.014 | 63 / 35 / 52 |
| A1-A0 | record-induced misses of the head vs gold | +2.69 | +2.00 to +3.40 | 0.000 | 16 / 88 / 46 |
| A1-A2 | Q4 vs FP16 | +0.78 | +0.22 to +1.37 | 0.010 | 23 / 38 / 89 |
| A3-A2 | Q8 vs FP16 | +0.78 | +0.22 to +1.37 | 0.010 | 23 / 38 / 89 |
| A4-A1 | recentred vs trained-on-Q4 | +0.36 | -0.57 to +1.27 | 0.463 | 41 / 73 / 36 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 75.6% | 3.87% | 8.53% | 24.4% | 16.3% | 3.87% | 50.9% |
| A10 | 75.8% | 3.83% | 8.60% | 24.2% | 16.1% | 3.83% | 50.9% |
| B1 | 75.5% | 3.77% | 8.33% | 24.5% | 16.2% | 3.77% | 50.6% |
| B2 | 56.9% | 0.50% | 1.63% | 43.1% | 16.1% | 0.50% | 36.3% |
| B3 | 56.9% | 0.50% | 1.63% | 43.1% | 16.2% | 0.50% | 36.5% |
| B4 | 75.5% | 3.77% | 8.40% | 24.5% | 16.1% | 3.77% | 50.5% |
| G1 | 0.0% | 0.00% | 0.00% | 42.6% | 16.4% | 0.83% | 36.5% |
| A6 | 0.0% | 0.00% | 0.00% | 7.4% | 16.5% | 12.50% | 53.4% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED | UNSUPPORTED_COMMIT |
|---|---|---|---|---|---|---|---|---|
| A8 | 2109 | 160 | 0 | 220 | 422 | 1 | 88 | 0 |
| B1 | 2101 | 164 | 0 | 213 | 421 | 2 | 99 | 0 |
| B2 | 1602 | 106 | 0 | 219 | 430 | 2 | 107 | 534 |
| B3 | 1608 | 99 | 0 | 219 | 406 | 65 | 66 | 537 |
| B4 | 2109 | 157 | 0 | 214 | 395 | 62 | 63 | 0 |
| G1 | 0 | 0 | 1722 | 223 | 872 | 65 | 118 | 0 |

## Readout `raw`  (raw)

### Level L: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 1.34% | 0.91% to 1.86% | 0.000 | 0.000 | 0 | 0 | 1193 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 13.93% | 13.12% to 14.72% | 0.000 | 0.158 | 0 | 0 | 1168 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 1.82% | 1.32% to 2.37% | 0.000 | 0.054 | 0 | 0 | 1240 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 2.14% | 1.62% to 2.72% | 0.000 | 0.059 | 0 | 0 | 1241 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 3.22% | 2.65% to 3.79% | 0.000 | 0.117 | 0 | 0 | 1278 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 13.93% | 13.12% to 14.72% | 0.000 | 0.158 | 0 | 0 | 1168 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 13.41% | 12.59% to 14.23% | 0.075 | 0.149 | 0 | 0 | 1176 | 4.5 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 4.31% | 3.59% to 5.01% | 0.069 | 0.242 | 955 | 296 | 1355 | 4.1 | 0.072 | 3.58 |
| A8c | Shield + location cover (post-hoc) | 3.91% | 3.28% to 4.54% | 0.069 | 0.333 | 1043 | 384 | 1411 | 4.1 | 0.072 | 3.58 |
| A10 | Shield, no fallback | 13.64% | 12.87% to 14.43% | 0.069 | 0.132 | 0 | 0 | 1153 | 4.1 | 0.059 | 2.95 |
| A12 | Oracle gate (diagnostic) | 11.61% | 10.89% to 12.36% | 0.100 | 0.143 | 0 | 0 | 1189 | 6.0 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 4.31% | 3.59% to 5.01% | 0.069 | 0.242 | 955 | 296 | 1355 | 4.1 | 0.074 | 3.72 |
| B2 | B2 = B1 + mass guard | 4.31% | 3.59% to 5.01% | 0.069 | 0.242 | 955 | 296 | 1355 | 4.1 | 0.074 | 3.72 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 3.78% | 3.09% to 4.46% | 0.069 | 0.249 | 942 | 309 | 1353 | 4.1 | 0.075 | 3.75 |
| B4 | B4 = B1 + cost-aware fallback | 3.78% | 3.09% to 4.46% | 0.069 | 0.249 | 942 | 309 | 1353 | 4.1 | 0.075 | 3.75 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 7.10% | 6.29% to 7.94% | 0.075 | 0.124 | 599 | 157 | 1261 | 4.5 | 0.026 | 1.28 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | -3.32 | -3.99 to -2.70 | 0.000 | 105 / 16 / 29 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | -10.15 | -11.00 to -9.33 | 0.000 | 145 / 2 / 3 |
| B3-A8 | P3: Shield-2 vs plan's Shield | -0.53 | -0.89 to -0.17 | 0.005 | 33 / 8 / 109 |
| B3-A6 | Shield-2 vs verification-only gate | -9.63 | -10.48 to -8.81 | 0.000 | 141 / 3 / 6 |
| G1-A1 | equal-footing gate vs always commit | -6.83 | -7.58 to -6.10 | 0.000 | 132 / 7 / 11 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| B2-B1 | mass guard (full cover) | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| B3-B2 | cost-aware fallback (with mass guard) | -0.53 | -0.89 to -0.17 | 0.005 | 33 / 8 / 109 |
| B4-B1 | cost-aware fallback (no mass guard) | -0.53 | -0.89 to -0.17 | 0.005 | 33 / 8 / 109 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -9.50 | -10.34 to -8.70 | 0.000 | 142 / 3 / 5 |
| A6-A1 | verification-only gate vs always commit | -0.53 | -0.77 to -0.29 | 0.000 | 33 / 4 / 113 |
| A12-A1 | headroom: oracle gate vs always commit | -2.33 | -2.72 to -1.94 | 0.000 | 98 / 9 / 43 |
| A1-A0 | record-induced misses of the head vs gold | +12.59 | +11.85 to +13.32 | 0.000 | 0 / 149 / 1 |
| A1-A2 | Q4 vs FP16 | +12.12 | +11.39 to +12.86 | 0.000 | 0 / 150 / 0 |
| A3-A2 | Q8 vs FP16 | +0.33 | +0.04 to +0.62 | 0.040 | 12 / 25 / 113 |
| A4-A1 | recentred vs trained-on-Q4 | -10.72 | -11.50 to -9.94 | 0.000 | 145 / 0 / 5 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 30.5% | 1.00% | 1.00% | 69.5% | 41.9% | 1.00% | 58.8% |
| A10 | 30.5% | 1.00% | 1.00% | 69.5% | 41.6% | 1.00% | 58.4% |
| B1 | 30.5% | 1.00% | 1.00% | 69.5% | 41.9% | 1.00% | 58.8% |
| B2 | 30.5% | 1.00% | 1.00% | 69.5% | 41.9% | 1.00% | 58.8% |
| B3 | 30.5% | 1.00% | 1.00% | 69.5% | 41.8% | 1.00% | 58.8% |
| B4 | 30.5% | 1.00% | 1.00% | 69.5% | 41.8% | 1.00% | 58.8% |
| G1 | 0.0% | 0.00% | 0.00% | 70.9% | 41.9% | 9.00% | 46.4% |
| A6 | 0.0% | 0.00% | 0.00% | 7.5% | 41.6% | 37.50% | 54.0% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | COVER_DECLINED | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED |
|---|---|---|---|---|---|---|---|---|
| A8 | 910 | 5 | 0 | 0 | 207 | 1411 | 433 | 34 |
| B1 | 910 | 5 | 0 | 0 | 207 | 1411 | 433 | 34 |
| B2 | 910 | 5 | 0 | 0 | 207 | 1411 | 433 | 34 |
| B3 | 911 | 4 | 0 | 43 | 207 | 1363 | 469 | 3 |
| B4 | 911 | 4 | 0 | 43 | 207 | 1363 | 469 | 3 |
| G1 | 0 | 0 | 873 | 23 | 226 | 1326 | 546 | 6 |

### Level M: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 4.92% | 4.10% to 5.83% | 0.000 | 0.000 | 0 | 0 | 1076 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 16.49% | 15.56% to 17.42% | 0.000 | 0.164 | 0 | 0 | 1079 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 6.30% | 5.36% to 7.26% | 0.000 | 0.057 | 0 | 0 | 1106 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 6.50% | 5.53% to 7.49% | 0.000 | 0.063 | 0 | 0 | 1100 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 8.01% | 7.07% to 8.95% | 0.000 | 0.124 | 0 | 0 | 1141 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 16.49% | 15.56% to 17.42% | 0.000 | 0.164 | 0 | 0 | 1079 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 15.82% | 14.84% to 16.82% | 0.075 | 0.145 | 0 | 0 | 1078 | 4.5 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 10.34% | 9.24% to 11.43% | 0.069 | 0.237 | 955 | 296 | 1165 | 4.1 | 0.072 | 3.58 |
| A8c | Shield + location cover (post-hoc) | 8.16% | 7.11% to 9.19% | 0.069 | 0.331 | 1051 | 392 | 1224 | 4.1 | 0.072 | 3.58 |
| A10 | Shield, no fallback | 16.31% | 15.36% to 17.26% | 0.069 | 0.134 | 0 | 0 | 1062 | 4.1 | 0.059 | 2.95 |
| A12 | Oracle gate (diagnostic) | 14.15% | 13.25% to 15.09% | 0.100 | 0.145 | 0 | 0 | 1094 | 6.0 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 10.34% | 9.24% to 11.43% | 0.069 | 0.237 | 955 | 296 | 1165 | 4.1 | 0.074 | 3.72 |
| B2 | B2 = B1 + mass guard | 10.34% | 9.24% to 11.43% | 0.069 | 0.237 | 955 | 296 | 1165 | 4.1 | 0.074 | 3.72 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 9.12% | 8.11% to 10.14% | 0.069 | 0.246 | 915 | 308 | 1173 | 4.1 | 0.075 | 3.77 |
| B4 | B4 = B1 + cost-aware fallback | 9.12% | 8.11% to 10.14% | 0.069 | 0.246 | 915 | 308 | 1173 | 4.1 | 0.075 | 3.77 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 11.15% | 10.12% to 12.23% | 0.075 | 0.145 | 609 | 180 | 1112 | 4.5 | 0.026 | 1.31 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | -2.03 | -2.72 to -1.38 | 0.000 | 79 / 29 / 42 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | -7.38 | -8.30 to -6.48 | 0.000 | 126 / 10 / 14 |
| B3-A8 | P3: Shield-2 vs plan's Shield | -1.22 | -1.81 to -0.66 | 0.000 | 55 / 21 / 74 |
| B3-A6 | Shield-2 vs verification-only gate | -6.70 | -7.60 to -5.84 | 0.000 | 122 / 11 / 17 |
| G1-A1 | equal-footing gate vs always commit | -5.34 | -6.21 to -4.48 | 0.000 | 114 / 14 / 22 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| B2-B1 | mass guard (full cover) | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| B3-B2 | cost-aware fallback (with mass guard) | -1.22 | -1.81 to -0.66 | 0.000 | 55 / 21 / 74 |
| B4-B1 | cost-aware fallback (no mass guard) | -1.22 | -1.81 to -0.66 | 0.000 | 55 / 21 / 74 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -7.67 | -8.59 to -6.74 | 0.000 | 129 / 9 / 12 |
| A6-A1 | verification-only gate vs always commit | -0.67 | -1.02 to -0.31 | 0.000 | 40 / 7 / 103 |
| A12-A1 | headroom: oracle gate vs always commit | -2.34 | -2.93 to -1.77 | 0.000 | 94 / 21 / 35 |
| A1-A0 | record-induced misses of the head vs gold | +11.57 | +10.68 to +12.44 | 0.000 | 3 / 144 / 3 |
| A1-A2 | Q4 vs FP16 | +10.19 | +9.25 to +11.13 | 0.000 | 6 / 143 / 1 |
| A3-A2 | Q8 vs FP16 | +0.20 | -0.28 to +0.69 | 0.481 | 23 / 27 / 100 |
| A4-A1 | recentred vs trained-on-Q4 | -8.48 | -9.33 to -7.63 | 0.000 | 135 / 5 / 10 |

Per arrival seed (each seed re-partitions the same reports, so seeds are not independent):

| seed | B3 - G1 (pp) | CI | B3 - A1 (pp) | CI |
|---|---|---|---|---|
| 1 | -2.13 | -3.19 to -1.09 | -7.68 | -9.32 to -6.07 |
| 2 | -1.96 | -3.18 to -0.66 | -7.41 | -9.17 to -5.67 |
| 3 | -2.02 | -3.20 to -0.89 | -7.03 | -8.52 to -5.55 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 30.5% | 1.00% | 1.00% | 69.5% | 42.4% | 1.00% | 59.5% |
| A10 | 30.5% | 1.00% | 1.00% | 69.5% | 42.0% | 1.00% | 58.9% |
| B1 | 30.5% | 1.00% | 1.00% | 69.5% | 42.4% | 1.00% | 59.5% |
| B2 | 30.5% | 1.00% | 1.00% | 69.5% | 42.4% | 1.00% | 59.5% |
| B3 | 30.5% | 1.00% | 1.00% | 69.5% | 42.3% | 1.00% | 59.5% |
| B4 | 30.5% | 1.00% | 1.00% | 69.5% | 42.3% | 1.00% | 59.5% |
| G1 | 0.0% | 0.00% | 0.00% | 70.9% | 42.2% | 9.00% | 46.9% |
| A6 | 0.0% | 0.00% | 0.00% | 7.5% | 41.9% | 37.80% | 54.0% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | COVER_DECLINED | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED |
|---|---|---|---|---|---|---|---|---|
| A8 | 894 | 21 | 0 | 0 | 207 | 1362 | 407 | 109 |
| B1 | 894 | 21 | 0 | 0 | 207 | 1362 | 407 | 109 |
| B2 | 894 | 21 | 0 | 0 | 207 | 1362 | 407 | 109 |
| B3 | 896 | 19 | 0 | 103 | 207 | 1275 | 478 | 22 |
| B4 | 896 | 19 | 0 | 103 | 207 | 1275 | 478 | 22 |
| G1 | 0 | 0 | 873 | 56 | 226 | 1263 | 562 | 20 |

### Level H: missed share (late + unverified), all outcomes and costs

| arm | what | missed | 95% CI (episodes) | requests / report | wasted trips / report | cover visits | cover wasted | distance m / report | hold s / report | decision s / report | allocator runs / report |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | Gold records (reference) | 13.42% | 12.11% to 14.67% | 0.000 | 0.000 | 0 | 0 | 772 | 0.0 | 0.000 | 0.00 |
| A1 | Q4 head, always commit | 22.56% | 21.29% to 23.79% | 0.000 | 0.156 | 0 | 0 | 769 | 0.0 | 0.000 | 0.00 |
| A2 | FP16 head, always commit | 15.33% | 13.96% to 16.64% | 0.000 | 0.056 | 0 | 0 | 792 | 0.0 | 0.000 | 0.00 |
| A3 | Q8 head, always commit | 16.11% | 14.65% to 17.46% | 0.000 | 0.061 | 0 | 0 | 791 | 0.0 | 0.000 | 0.00 |
| A4 | Recentred Q4 | 16.48% | 15.20% to 17.65% | 0.000 | 0.119 | 0 | 0 | 812 | 0.0 | 0.000 | 0.00 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 22.56% | 21.29% to 23.79% | 0.000 | 0.156 | 0 | 0 | 769 | 0.0 | 0.000 | 0.00 |
| A6 | Confidence gate, verification only | 21.96% | 20.71% to 23.18% | 0.075 | 0.133 | 0 | 0 | 763 | 4.5 | 0.000 | 0.00 |
| A8 | Shield (plan): full cover | 21.00% | 19.71% to 22.21% | 0.069 | 0.228 | 959 | 300 | 837 | 4.1 | 0.072 | 3.58 |
| A8c | Shield + location cover (post-hoc) | 17.91% | 16.67% to 19.18% | 0.069 | 0.309 | 1028 | 370 | 845 | 4.1 | 0.072 | 3.58 |
| A10 | Shield, no fallback | 22.42% | 21.19% to 23.65% | 0.069 | 0.119 | 0 | 0 | 760 | 4.1 | 0.059 | 2.95 |
| A12 | Oracle gate (diagnostic) | 21.18% | 19.94% to 22.41% | 0.100 | 0.137 | 0 | 0 | 766 | 6.0 | 0.000 | 0.00 |
| B1 | B1 strict candidate check | 21.09% | 19.78% to 22.29% | 0.069 | 0.229 | 960 | 301 | 836 | 4.1 | 0.074 | 3.72 |
| B2 | B2 = B1 + mass guard | 21.09% | 19.78% to 22.29% | 0.069 | 0.229 | 960 | 301 | 836 | 4.1 | 0.074 | 3.72 |
| B3 | B3 = Shield-2 (B2 + cost-aware fallback) | 18.69% | 17.35% to 19.97% | 0.069 | 0.231 | 862 | 301 | 823 | 4.1 | 0.076 | 3.80 |
| B4 | B4 = B1 + cost-aware fallback | 18.69% | 17.35% to 19.97% | 0.069 | 0.231 | 862 | 301 | 823 | 4.1 | 0.076 | 3.80 |
| G1 | G1 confidence gate with the same fallback (equal footing) | 20.15% | 18.80% to 21.41% | 0.075 | 0.138 | 574 | 177 | 792 | 4.5 | 0.027 | 1.35 |

Paired differences, percentage points of missed share (negative = first arm better), episode bootstrap 95% CI, sign-flip p:

| comparison | meaning | diff (pp) | 95% CI (pp) | p | episodes won first / second / tied |
|---|---|---|---|---|---|
| B3-G1 | P1 PRIMARY: Shield-2 vs equal-footing confidence gate | -1.45 | -2.28 to -0.61 | 0.001 | 81 / 40 / 29 |
| B3-A1 | P2: Shield-2 vs always commit (no gate) | -3.87 | -5.02 to -2.76 | 0.000 | 93 / 37 / 20 |
| B3-A8 | P3: Shield-2 vs plan's Shield | -2.31 | -3.26 to -1.41 | 0.000 | 79 / 32 / 39 |
| B3-A6 | Shield-2 vs verification-only gate | -3.27 | -4.38 to -2.18 | 0.000 | 88 / 36 / 26 |
| G1-A1 | equal-footing gate vs always commit | -2.42 | -3.43 to -1.39 | 0.000 | 89 / 37 / 24 |
| B1-A8 | strict candidate check alone vs plan's Shield | +0.09 | +0.00 to +0.28 | 1.000 | 0 / 1 / 149 |
| B2-B1 | mass guard (full cover) | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| B3-B2 | cost-aware fallback (with mass guard) | -2.40 | -3.38 to -1.48 | 0.000 | 79 / 32 / 39 |
| B4-B1 | cost-aware fallback (no mass guard) | -2.40 | -3.38 to -1.48 | 0.000 | 79 / 32 / 39 |
| B3-B4 | mass guard (with cost-aware fallback) | +0.00 | +0.00 to +0.00 | 1.000 | 0 / 0 / 150 |
| A8c-A6 | reference: location cover vs gate (post-hoc, iteration 0) | -4.05 | -5.16 to -2.94 | 0.000 | 102 / 26 / 22 |
| A6-A1 | verification-only gate vs always commit | -0.60 | -0.98 to -0.24 | 0.002 | 37 / 13 / 100 |
| A12-A1 | headroom: oracle gate vs always commit | -1.38 | -2.07 to -0.68 | 0.000 | 76 / 30 / 44 |
| A1-A0 | record-induced misses of the head vs gold | +9.14 | +8.09 to +10.21 | 0.000 | 10 / 134 / 6 |
| A1-A2 | Q4 vs FP16 | +7.23 | +6.13 to +8.35 | 0.000 | 13 / 125 / 12 |
| A3-A2 | Q8 vs FP16 | +0.78 | +0.22 to +1.37 | 0.010 | 23 / 38 / 89 |
| A4-A1 | recentred vs trained-on-Q4 | -6.09 | -7.19 to -4.99 | 0.000 | 115 / 21 / 14 |

Decisions of the Shield-type arms (share of reports):

| arm | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports | wrong-plan left unflagged | precision of flags |
|---|---|---|---|---|---|---|---|
| A8 | 30.5% | 1.00% | 1.00% | 69.5% | 43.3% | 1.00% | 60.9% |
| A10 | 30.5% | 1.00% | 1.00% | 69.5% | 43.3% | 1.00% | 60.9% |
| B1 | 30.5% | 1.00% | 1.00% | 69.5% | 43.3% | 1.00% | 60.9% |
| B2 | 30.5% | 1.00% | 1.00% | 69.5% | 43.3% | 1.00% | 60.9% |
| B3 | 30.5% | 1.00% | 1.00% | 69.5% | 43.4% | 1.00% | 61.0% |
| B4 | 30.5% | 1.00% | 1.00% | 69.5% | 43.4% | 1.00% | 61.0% |
| G1 | 0.0% | 0.00% | 0.00% | 70.9% | 43.3% | 9.00% | 48.4% |
| A6 | 0.0% | 0.00% | 0.00% | 7.5% | 43.1% | 39.00% | 54.9% |

Outcome classes (reports):

| arm | ACCEPT | ACCEPT_INFEASIBLE | COMMIT | COVER_DECLINED | ESCALATE | FALLBACK_COVERED | FALLBACK_PARTIAL | FALLBACK_UNRESOLVED |
|---|---|---|---|---|---|---|---|---|
| A8 | 830 | 85 | 0 | 0 | 207 | 1228 | 345 | 305 |
| B1 | 830 | 85 | 0 | 0 | 207 | 1228 | 345 | 305 |
| B2 | 830 | 85 | 0 | 0 | 207 | 1228 | 345 | 305 |
| B3 | 853 | 62 | 0 | 212 | 207 | 1088 | 493 | 85 |
| B4 | 853 | 62 | 0 | 212 | 207 | 1088 | 493 | 85 |
| G1 | 0 | 0 | 873 | 125 | 226 | 1113 | 566 | 97 |

