# Allocator-time sensitivity: 20 ms (original) vs 0.22 ms (measured)

Protocol: `docs/ITERATION1_ALLOC_SENSITIVITY.md` (fixed before the run). Development data. Original results are unchanged.

## competent Q4 head, level M

| arm | missed 20 ms | missed 0.22 ms |
|---|---|---|
| A0 | 4.92% | 4.92% |
| A1 | 7.41% | 7.41% |
| A2 | 6.30% | 6.30% |
| A6 | 7.07% | 7.07% |
| A8 | 8.23% | 8.21% |
| A8c | 7.05% | 6.99% |
| B1 | 8.56% | 8.56% |
| B2 | 8.57% | 8.56% |
| B3 | 7.81% | 7.83% |
| B4 | 7.76% | 7.77% |
| G1 | 7.74% | 7.76% |
| A12 | 6.94% | 6.94% |

| paired (first minus second) | 20 ms: pp (95% CI) | 0.22 ms: pp (95% CI) | change (pp) | CI status changed |
|---|---|---|---|---|
| B3 - G1 | +0.07 (-0.44 to +0.61) | +0.07 (-0.44 to +0.61) | +0.00 | no |
| B3 - A1 | +0.40 (-0.32 to +1.15) | +0.42 (-0.30 to +1.16) | +0.02 | no |
| B3 - A8 | -0.42 (-0.88 to +0.05) | -0.38 (-0.84 to +0.09) | +0.04 | no |
| A8 - A1 | +0.82 (+0.04 to +1.58) | +0.80 (+0.02 to +1.56) | -0.02 | no |

## unadapted head (raw), level M

| arm | missed 20 ms | missed 0.22 ms |
|---|---|---|
| A0 | 4.92% | 4.92% |
| A1 | 16.49% | 16.49% |
| A2 | 6.30% | 6.30% |
| A6 | 15.82% | 15.82% |
| A8 | 10.34% | 10.34% |
| A8c | 8.16% | 8.10% |
| B1 | 10.34% | 10.34% |
| B2 | 10.34% | 10.34% |
| B3 | 9.12% | 9.05% |
| B4 | 9.12% | 9.05% |
| G1 | 11.15% | 11.15% |
| A12 | 14.15% | 14.15% |

| paired (first minus second) | 20 ms: pp (95% CI) | 0.22 ms: pp (95% CI) | change (pp) | CI status changed |
|---|---|---|---|---|
| B3 - G1 | -2.03 (-2.72 to -1.38) | -2.11 (-2.79 to -1.45) | -0.07 | no |
| B3 - A1 | -7.38 (-8.30 to -6.48) | -7.45 (-8.38 to -6.54) | -0.07 | no |
| B3 - A8 | -1.22 (-1.81 to -0.66) | -1.29 (-1.88 to -0.74) | -0.07 | no |
| A8 - A1 | -6.16 (-7.23 to -5.07) | -6.16 (-7.23 to -5.07) | +0.00 | no |

## Finding (rule fixed in advance)

**ASSUMPTION DOES NOT MATTER**
