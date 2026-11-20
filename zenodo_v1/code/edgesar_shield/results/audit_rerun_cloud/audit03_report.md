# Audit 3: allocator behaviour and harm-number reproduction


## A. Harm numbers on held-out B, recomputed

- **PASS** gold-record reference: 0 of 752 real incidents on B unverified by 600 s
- **PASS** Heads FP16: 15 of 752 unverified (2.0%) from saved records; harm run_03 says 15; independent re-fit records give 15
- **PASS** Heads Q8: 16 of 752 unverified (2.1%) from saved records; harm run_03 says 16
- **PASS** Heads Q4: 13 of 752 unverified (1.7%) from saved records; harm run_03 says 13; independent re-fit records give 13
- **PASS** FP16-trained heads on Q4 vectors: 141 of 752 unverified (18.8%) from saved records; harm run_03 says 141; independent re-fit records give 141
- **PASS** FP16-trained heads on Q4 vectors, offset removed: 18 of 752 unverified (2.4%) from saved records; harm run_03 says 18; independent re-fit records give 18
- **PASS** Shared head on Q4 vectors: 10 of 752 unverified (1.3%) from saved records; harm run_03 says 10
- **PASS** Generative FP16: 83 of 752 unverified (11.0%) from saved records; harm run_03 says 83
- **PASS** Generative Q4: 69 of 752 unverified (9.2%) from saved records; harm run_03 says 69
- **PASS** TF-IDF + LR: 30 of 752 unverified (4.0%) from saved records; harm run_03 says 30

## B. Frozen FP16 head on Q4: which misses the correction removes or adds (incident level, B)

- **INFO** raw frozen head: 141 incidents unverified; after the correction 123 of them are verified, 18 stay unverified, and 0 incidents that were verified become unverified. Of the 18 corrected-arm misses, 7 are also missed by the precision-matched Q4 head.
- **INFO** raw frozen-head misses by (gold action -> system action): {'CREATE_VERIFICATION -> NO_ACTION': 92, 'NO_ACTION -> CLOSE_INCIDENT': 31, 'UPDATE_INCIDENT -> CLOSE_INCIDENT': 18}

## C. Load and slack in the current single-record replay (all 1400 reports, gold records)

- **INFO** task-table size after the gold record (tasks per report: count): {0: 178, 1: 418, 2: 423, 3: 241, 4: 100, 5: 40}; 140 of 1400 reports have more tasks than the 3 UAVs
- **INFO** with gold records the last visit ends at median 91 s, 99th percentile 234 s, max 327 s, against a 600 s horizon; 0 of all real incidents are unverified
- **INFO** every possible single-field error (priority or sensor) of every CREATE/UPDATE gold record, flown: {'priority: no miss': 1260, 'sensor: no miss': 1260}

## D. The V1 'CBBA' against a centralised greedy auction

- **INFO** first assignment identical to a centralised greedy auction in 1400 of 1400 gold tables; whole mission identical in 1400 of 1400; 'consensus' rounds used: {0: 178, 1: 630, 2: 438, 3: 154}

## Reading

- **INFO** Measured, not assumed: none of the single-field priority or sensor errors probed in C produced an unverified incident, and the frozen-head misses in B are all action errors (CREATE->NO_ACTION, ->CLOSE). At this load, with a 600 s horizon, the primary outcome can only see errors that remove or never create a task; it is blind to sensor and priority errors.
- **INFO** The V1 'CBBA' made exactly the same decisions as a centralised greedy auction in every mission tested: it has no bundles, no per-agent consensus state and no message passing.
