# Audit 2: independent head re-fit, offset definitions, head-space decomposition


## Offset numbers: exact definitions (vectors are the L2-normalised last-token states, float64)

- **INFO** Q4: delta = mean over the 1000 dev-A reports of d_i = x_i(Q4) - x_i(FP16). ||delta|| = 0.2730.
- **INFO** Q4: RMS change sqrt(mean_i ||d_i||^2) = 0.2831 on dev A, 0.2847 on B.
- **INFO** Q4: spread of reports = sqrt(mean_i ||x_i(FP16) - mean_dev x(FP16)||^2) over dev A = 0.0997. ||delta|| / spread = 2.74.
- **INFO** Q4: energy share of the constant shift = 1 - mean||d_i - delta||^2 / mean||d_i||^2 = 0.930 on dev A, 0.929 on B (delta from dev A only).
- **INFO** Q4: per-report on B: cosine(d_i, delta) from 0.918 (min) to 0.982 (max), median 0.966; the part left after removing delta is median 26% (max 40%) of a report's own change. Residual RMS 0.0757 = 76% of the report spread.
- **INFO** Q4: share of ||delta||^2 in the largest 1 / 10 / 50 coordinates: 0.01 / 0.05 / 0.17
- **INFO** Q8: delta = mean over the 1000 dev-A reports of d_i = x_i(Q8) - x_i(FP16). ||delta|| = 0.0433.
- **INFO** Q8: RMS change sqrt(mean_i ||d_i||^2) = 0.0505 on dev A, 0.0503 on B.
- **INFO** Q8: spread of reports = sqrt(mean_i ||x_i(FP16) - mean_dev x(FP16)||^2) over dev A = 0.0997. ||delta|| / spread = 0.43.
- **INFO** Q8: energy share of the constant shift = 1 - mean||d_i - delta||^2 / mean||d_i||^2 = 0.734 on dev A, 0.729 on B (delta from dev A only).
- **INFO** Q8: per-report on B: cosine(d_i, delta) from 0.643 (min) to 0.907 (max), median 0.866; the part left after removing delta is median 50% (max 87%) of a report's own change. Residual RMS 0.0262 = 26% of the report spread.
- **INFO** Q8: share of ||delta||^2 in the largest 1 / 10 / 50 coordinates: 0.01 / 0.06 / 0.19

## Independent re-fit (heads trained on all 1000 dev-A reports, applied to held-out B)

- **INFO** FP16 heads: C chosen action 3, sensor 0.03, priority 0.03
- **INFO** Q4 heads: C chosen action 0.03, sensor 0.003, priority 0.003
- **CHECK** Heads FP16: independent re-fit gives the saved record for 396 of 400 B reports; the differing reports have smallest head margin (top-1 minus top-2 probability) 0.009, 0.013, 0.007, 0.002
- **PASS** Heads Q4: independent re-fit gives the saved record for 400 of 400 B reports
- **CHECK** FP16-trained heads on Q4 vectors: independent re-fit gives the saved record for 398 of 400 B reports; the differing reports have smallest head margin (top-1 minus top-2 probability) 0.102, 0.034
- **CHECK** FP16-trained heads on Q4 vectors, offset removed: independent re-fit gives the saved record for 396 of 400 B reports; the differing reports have smallest head margin (top-1 minus top-2 probability) 0.004, 0.003, 0.034, 0.041

## What the action head sees: standardised input and logits (FP16 head)

- **INFO** Action-head logit change FP16 -> raw Q4 (centred across classes): RMS 12.16; logit spread across B reports at FP16: RMS 9.68.
- **INFO** The constant part W(delta/sigma) carries 81.3% of that logit change energy; after the correction the RMS logit change is 5.25.
- **INFO** Constant logit shift by class: CLOSE_INCIDENT +7.08, CREATE_VERIFICATION -6.39, NO_ACTION -3.93, UPDATE_INCIDENT +3.23
- **PASS** Removing delta from the input equals changing only the intercepts b' = b - W(delta/sigma) (max |logit difference| 1.4e-14): the correction is an intercept (bias) adjustment of the frozen head.

## Decision-level accounting on B (whole record and action), FP16 head

- **INFO** Whole record differs from the FP16 head's own record: raw Q4 191 of 400; corrected 140 (90 raw changes undone, 39 new ones).
- **INFO** Action differs from the FP16 head's own action: raw 142, corrected 56. Raw action changes: {'CREATE_VERIFICATION -> NO_ACTION': 86, 'NO_ACTION -> CLOSE_INCIDENT': 32, 'UPDATE_INCIDENT -> CLOSE_INCIDENT': 13, 'NO_ACTION -> UPDATE_INCIDENT': 5, 'CREATE_VERIFICATION -> UPDATE_INCIDENT': 4, 'CLOSE_INCIDENT -> UPDATE_INCIDENT': 2}
- **INFO** Correct whole records (of 400): {'FP16 head on FP16': 285, 'FP16 head on raw Q4': 190, 'FP16 head on corrected Q4': 231, 'Q4 head': 266}
- **INFO** Correct actions (of 400): {'FP16 head on FP16': 369, 'FP16 head on raw Q4': 250, 'FP16 head on corrected Q4': 334, 'Q4 head': 356}

## Reading

- **INFO** 93% is a share of squared vector CHANGE (an energy share), not a share of errors explained. The shift is common in direction but not identical: every report keeps a residual change (see the per-report numbers above).
