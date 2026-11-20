# Audit 5: Shield design probe on dev A only (not a result)

- **INFO** dev-A reports whose gold record the heads can express at all: 100.0%
- **INFO** alpha 0.05: coverage 94.8% (target >= 95%), set sizes {'1': 263, '2': 52, '3': 104, '4': 38, '5': 26, '6': 11, '7': 5, '9': 1}, empty 0, over K=8 1; accept 60.8% of 500; accepted with a wrong plan: Shield 1 vs confidence gate at the same count 9 (wrong plans in total 82); non-singleton sets that are plan-equivalent 41
- **INFO**    ablation without the downstream check (accept singletons only): accept 52.6%, wrong plans accepted 1 (confidence gate at that count 1)
- **INFO** alpha 0.10: coverage 91.0% (target >= 90%), set sizes {'1': 280, '2': 109, '3': 90, '4': 18, '5': 3}, empty 0, over K=8 0; accept 67.2% of 500; accepted with a wrong plan: Shield 8 vs confidence gate at the same count 21 (wrong plans in total 82); non-singleton sets that are plan-equivalent 56
- **INFO**    ablation without the downstream check (accept singletons only): accept 56.0%, wrong plans accepted 3 (confidence gate at that count 2)
- **INFO** alpha 0.20: coverage 82.6% (target >= 80%), set sizes {'0': 7, '1': 370, '2': 114, '3': 9}, empty 7, over K=8 0; accept 83.6% of 500; accepted with a wrong plan: Shield 42 vs confidence gate at the same count 45 (wrong plans in total 82); non-singleton sets that are plan-equivalent 48
- **INFO**    ablation without the downstream check (accept singletons only): accept 74.0%, wrong plans accepted 40 (confidence gate at that count 29)
- **INFO** This probe uses style A only, one allocator (the V1 greedy auction) and no resource competition. It decides nothing; it shows whether the mechanism has room to work before anything is built.
