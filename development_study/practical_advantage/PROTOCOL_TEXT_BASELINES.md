# Conventional text baselines in the mission simulator: protocol (written BEFORE any run), 14 Nov 2026

Question: do the existing conventional text baselines (a TF-IDF + logistic-regression classifier and a keyword rule engine, both from the earlier pilot) reach the same mission outcome as the hidden-vector readouts when they are run through the SAME simulator, evaluation reports, load levels and arrival seeds? Nothing here is tuned, and no model is run.

Status: EXPLORATORY, development data (style A wording, 1,000 reports, the same 5 outer folds). Pooled intervals are optimistic because the three arrival seeds reuse the same reports.

## Arms (added to the existing ones)
- `tfidf`: the pilot's `baselines.LRBaseline`, unchanged (TfidfVectorizer ngram (1,2), sublinear_tf, min_df=2; LogisticRegression C=10, max_iter 5000; text = `lr_text(case)` with its structural flags). Fitted per outer fold on exactly the FIT reports used by the heads (`DevData.split`: 3 of the 5 folds, exact duplicates of CAL/EVAL reports purged, no family in two roles). Action head on all FIT reports; sensor and priority heads on FIT reports whose gold action is CREATE or UPDATE (as in `LRBaseline.fit` and as for the hidden-vector heads). Its class probabilities enter the same assembler, candidate list, service and simulator as the hidden-vector heads.
- `rule`: the pilot's `baselines.rule_decision`, unchanged, no fitting. Its action, sensor and priority are turned into one-hot probabilities (uniform where the rule gives no sensor or priority). Its own landmark and incident choices are NOT used: the common assembler supplies landmark and incident for every arm.
- Reference arms are NOT re-run: gold, f16p, q4p, alnp, recp, rawp are read from the saved per-episode records of the repair package (`out_mission/records_{L,M,H}_s{1,2,3}.json.gz`). Integrity: the gold arm is re-run here, and for every episode its late / unverified / incident counts must equal the saved ones, otherwise the run stops and nothing is reported as paired.

## Setting (identical to the saved records)
Development reports, 5 outer folds, EVAL reports of each fold, overlay episodes `make_episodes(eval, level, seed*1000+k, 20)`, levels L, M, H, arrival seeds 1, 2, 3 (150 episodes and 5,505 incidents per level), bounded CBBA allocator, always-commit policy, simulator configuration unchanged. Reading position `prefix` for the hidden-vector arms (as saved).

## Outputs
1. Missed share, `(late + unverified) / incidents`, ordinary (every incident counts once) and priority-weighted (weights 3/2/1 by incident priority; incidents resolved externally are excluded from numerator and denominator in the weighted version, as in `power_design.py`), with episode-bootstrap 95% intervals, per level.
2. Paired differences (episode-paired bootstrap, 10,000 resamples, seed 7): tfidf and rule against f16p, q4p, alnp, recp and gold, ordinary and priority-weighted.
3. Decision accuracy on the EVAL reports (whole record, action) for tfidf and rule, next to the saved values of the hidden-vector arms.
4. Which fields are wrong, for tfidf and rule (action / sensor / priority), counted once per report decision.

## Decision rule
None. Every result is reported, including results that favour the simpler baselines. The text may say "a baseline is lower, equal or higher" only with the interval beside it. No margin is used. If a baseline is lower than or not distinguishable from the hidden-vector arms on this development wording, that is reported as "no advantage of the hidden-vector readout shown on development wording".

## Out of scope
New wording (style B) is not in the simulator; no new extraction; no tuning of the baselines (C, n-grams, word lists are as in the pilot); no change to the simulator; no confirmation data.
