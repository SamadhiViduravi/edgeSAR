# Audit 4: duplicates, families, folds and a duplicate-aware sensitivity analysis


## A. Duplicate groups

- **INFO** exact duplicates (same text AND same open-incident table): 9 groups, 19 reports: c0051(dev,A031)+c1372(dev,A040); c0192(held,B020)+c1129(held,B007); c0200(held,B003)+c1069(held,B006); c0343(dev,A020)+c0745(dev,A021)+c0963(dev,A035); c0432(dev,A070)+c0958(dev,A037); c0692(dev,A074)+c1114(dev,A067); c0830(dev,A049)+c0937(dev,A039); c1007(dev,A057)+c1397(dev,A071); c1085(dev,A098)+c1281(dev,A035)
- **INFO**   of these, 9 groups have identical gold records
- **INFO** same text, any open table: 125 groups, 293 reports (0 groups span dev and held)
- **INFO** template level (landmarks, ids, sources, numbers masked): 378 distinct templates in dev A, 198 in held B, 0 shared between A and B
- **INFO** the most frequent dev-A template covers 50 reports; median reports per template: dev A 1, held B 1

## B. What a family is

- **INFO** gen_cases.py: every report is drawn independently; family = 'A%03d' % (k // 10) over the generation order. A family is a block of 10 consecutive independent draws, not a shared scenario.
- **INFO** share of report pairs whose open tables share a landmark: within a family 0.233, between families 0.230 (no family structure)

## C. Do duplicates cross the folds used for the dev-A answers?

- **INFO** outer folds rebuilt with GroupKFold(5) on the dev families (the same call as heads_lib.make_plan and the pilot TF-IDF baseline; deterministic for a given scikit-learn version, 1.9.1 here and in the project run)
- **CHECK** exact duplicates: 6 of 7 dev groups have members in different outer folds (one member's out-of-fold answer came from a head trained on an identical report): [['c0051', 'c1372'], ['c0343', 'c0745', 'c0963'], ['c0432', 'c0958'], ['c0692', 'c1114'], ['c1007', 'c1397'], ['c1085', 'c1281']]
- **CHECK** same text (open table may differ): 87 of 125 dev groups cross outer folds. These are mostly short templated texts (status chatter, 'no change', 'searched X, nobody') that the generator repeats by design.
- **INFO** held-B duplicate groups: 2 (B is never used for training, so these cannot leak into a head; they only count twice in B metrics and fall in different families of the family bootstrap)

## D. Sensitivity: every report of a duplicate group (exact or same-text) removed

- **INFO** Heads FP16 whole-record accuracy: dev A 80.0% (n=1000) -> 74.2% (n=761); B 70.8% (n=400) -> 66.8% (n=346)
- **INFO** Heads Q4 whole-record accuracy: dev A 74.8% (n=1000) -> 67.7% (n=761); B 66.5% (n=400) -> 62.4% (n=346)
- **INFO** FP16-trained heads on Q4 vectors whole-record accuracy: dev A 50.5% (n=1000) -> 40.9% (n=761); B 47.5% (n=400) -> 41.6% (n=346)
- **INFO** FP16-trained heads on Q4 vectors, offset removed whole-record accuracy: dev A 70.9% (n=1000) -> 62.4% (n=761); B 57.8% (n=400) -> 53.8% (n=346)
- **INFO** Shared head on Q4 vectors whole-record accuracy: dev A 76.1% (n=1000) -> 69.4% (n=761); B 66.5% (n=400) -> 62.4% (n=346)
- **INFO** TF-IDF + LR whole-record accuracy: dev A 98.2% (n=1000) -> 97.8% (n=761); B 53.5% (n=400) -> 49.7% (n=346)
- **INFO** Generative FP16 whole-record accuracy: dev A 30.3% (n=1000) -> 23.7% (n=761); B 27.3% (n=400) -> 25.4% (n=346)
- **INFO** Generative Q4 whole-record accuracy: dev A 32.1% (n=1000) -> 23.1% (n=761); B 32.8% (n=400) -> 29.8% (n=346)
- **INFO** Heads FP16 unverified incidents: B 1.99% (752 incidents) -> 2.05% (684); dev A 0.05% -> 0.07%
- **INFO** Heads Q4 unverified incidents: B 1.73% (752 incidents) -> 1.75% (684); dev A 0.60% -> 0.68%
- **INFO** FP16-trained heads on Q4 vectors unverified incidents: B 18.75% (752 incidents) -> 19.44% (684); dev A 16.29% -> 17.70%
- **INFO** FP16-trained heads on Q4 vectors, offset removed unverified incidents: B 2.39% (752 incidents) -> 2.34% (684); dev A 0.93% -> 1.08%
- **INFO** Shared head on Q4 vectors unverified incidents: B 1.33% (752 incidents) -> 1.32% (684); dev A 0.33% -> 0.41%
- **INFO** TF-IDF + LR unverified incidents: B 3.99% (752 incidents) -> 4.09% (684); dev A 0.00% -> 0.00%
- **INFO** Generative FP16 unverified incidents: B 11.04% (752 incidents) -> 11.99% (684); dev A 10.03% -> 12.09%
- **INFO** Generative Q4 unverified incidents: B 9.18% (752 incidents) -> 9.94% (684); dev A 9.16% -> 11.08%
- **INFO** paired dU (Heads Q4 - Heads FP16) on B: all -0.27 pp (-1.10 to +0.54) -> duplicates removed -0.29 pp (-1.22 to +0.59)
- **INFO** audit04_duplicate_clusters.csv: 1232 clusters for 1400 reports. Any future split of these reports groups by duplicate_cluster (and keeps style A and B apart).

## F. Dev-A out-of-fold answers re-fitted with copies purged from training (same reports, same folds)

- **INFO** Section D changes the MIX of reports: the generative arms, which are never trained, lose accuracy too, so D mixes leakage with difficulty. Merging families through duplicate links is not usable either: the same-text links join 95 of the 100 dev families into one group of 950 reports. Here the project's family folds are kept, and for each fold every training report that shares its text with a test report is removed from training. Same test reports, almost the same training sets.
- **INFO** Heads FP16 dev-A whole-record accuracy: project folds 80.0% -> copies purged 79.8%; on the 239 reports with a same-text copy 98.3% -> 98.3%; on the other reports 74.2% -> 74.0% (323 training rows removed over the 5 folds)
- **INFO** Heads Q4 dev-A whole-record accuracy: project folds 74.8% -> copies purged 75.0%; on the 239 reports with a same-text copy 97.5% -> 97.5%; on the other reports 67.7% -> 67.9% (323 training rows removed over the 5 folds)
