# EdgeSAR: Results and Limitations (EXPLORATORY)

Written Thu 12 Nov 2026. Everything here is exploratory: held-out style B was already seen before this plan was written.
Plan: `HARM_TEST_PLAN.md` (frozen by hash at 17:27 Colombo time, before any real system was run through the allocator).
Numbers: `results_harm\run_01\harm_report.md`. Every number below is in that file or in `harm_summary.json`.

## 1. Implemented (works now, one command each)

* **Chain:** report text -> hidden-state vector -> three small heads -> task record -> task table -> simplified CBBA allocator (3 UAVs) -> simulated mission -> which real incidents are verified by 600 s.
* **Reference:** the same allocator with the correct (gold) record. It is not an optimal planner. Here it verified all 752 real incidents on B, so every miss below comes from a record.
* **Paired runs:** every system and the reference use the same reports, the same start state and the same allocator. The simulator has no random part.
* **Evidence files:** `per_report_outcomes.csv` (one row per system and report), `per_incident_outcomes.csv` (one row per system and real incident), `harm_table.csv`, `harm_outcome.png`, `harm_summary.json`.
* **Demo:** `python 06_demo.py` shows one absorbed and one consequential case, with the counts of how common each kind is.
* **Tests:** 67 pass (`python -m pytest -q tests`).

Commands (PowerShell, in `edgesar_heads`): `python 05_harm_test.py` (makes a new `results_harm\run_NN`; the numbers must equal `run_01`), `python 06_demo.py`.

## 2. Observed (held-out B: 400 reports, 40 families, 752 real incidents)

Intervals are 95% family-bootstrap intervals. With 40 families they are wide. Nothing here is confirmatory.

| Question | What was seen |
|---|---|
| How many real incidents are left unverified because of a wrong record? | Heads FP16 15 (2.0%, 1.0 to 3.2 points above the reference), Heads Q8 16 (2.1%, 1.0 to 3.5), Heads Q4 13 (1.7%, 0.8 to 2.8). |
| Does the precision change that number? | FP16 -> Q8: +0.1 points (-0.7 to +1.1). FP16 -> Q4: -0.3 points (-1.1 to +0.5). The interval includes zero and also about one point in either direction. Individual incidents move both ways (FP16 -> Q4: 5 verified-to-unverified, 7 unverified-to-verified). |
| Is that the same on development style A (100 families, easier style)? | Not quite. FP16 -> Q4 on A: +0.5 points (+0.2 to +0.9), 10 verified-to-unverified and 0 the other way. On all 140 families: +0.3 (-0.04 to +0.7). So a small harm from Q4 heads is possible. B alone cannot rule it out or show it. |
| Do records change when the allocator absorbs them? | FP16 -> Q4 heads: the task table differs in 110 of 400 reports. 61 are absorbed (no verification changes) and 49 are consequential. This is in a setting with enough UAV capacity (the reference verifies everything). A more crowded mission may absorb less. |
| What is the cost of wrong records besides misses? | Delay of verified incidents: about +3.5 to +4.7 s against the reference (all three heads, similar). Wasted trips per report: 0.14 / 0.18 / 0.20 (FP16 / Q8 / Q4) against 0.00 for the reference. |
| What causes the misses? (post-run look, not in the plan) | Mostly a new real incident ignored (gold CREATE, system NO_ACTION) and a real incident wrongly closed (UPDATE or NO_ACTION read as CLOSE). |
| FP16-trained head on Q4 vectors (the vector moves, the head does not) | 18.8% of incidents unverified (16.4 to 21.1). Mostly missed alarms (92) and wrong closes (49). |
| The same, after removing the average vector shift (label-free) | 2.4% (1.2 to 3.9): back to about the level of the separate heads. This is one exploratory repair. It is not better than retraining the head. |
| One shared head for all precisions (Q4 vectors) | 1.3% (0.5 to 2.3). Against the separate Q4 head: -0.4 points (-0.9 to 0.0) on B and -0.3 (-0.5 to -0.1) on all 140 families. Small, and one direction in both styles. |
| For comparison: the pilot's text-writing model | Generative FP16 11.0%, Q8 11.4%, Q4 9.2% (B). The heads (about 2%) miss far fewer incidents. Generative FP16 -> Q4 is -1.9 points (-3.4 to -0.5): compression fixed more than it broke here. I did not expect this and I did not test why. |

## 3. Reading the controls (corrected)

* **The 27-number MATCH** only shows that the rerun gives the same numbers as attempt 1. It is a consistency check. It is not a validation.
* **19.6%** is the mean share of B reports whose task table changes between a head trained on a bootstrap sample of the dev families and the full-data FP16 head (same FP16 vectors). It is **bootstrap training-sample variability**, not a pure random-seed floor (head training has no random seed). The **22.8%** is the same measure between two bootstrap heads (pairs 1-2, 3-4, ...), so it is head against head.
* **Do not subtract** 19.6% from 27.5% and call the rest "quantization". The numbers compare different heads, samples and vectors. They are not additive.
* **Not concluded:** that Q8 has no effect, that two extra errors are "noise", or that Q4 having fewer danger errors "is not believable". Compression can fix some answers and break others. These are observations with uncertainty.
* **93% / 73%** (offset): the share of the average squared change of the vector that one constant shift accounts for. It is **not** the share of errors repaired.

## 4. What was matched and what was fitted

* Same 1400 reports, same dev/held split, same training reports (dev A only), same family folds, same labels, same C grid, same pipeline (StandardScaler + logistic regression, lbfgs, C chosen inside the training rows), same prompt, same vector type.
* Not matched on purpose: the vectors, and the C each head picks.
* Head training has **no random seed**, so the same data gives the same head. `heads_config.json` has a seed, but head training does not use it. Only the bootstrap sampling uses `bootstrap_seed` (head b has seed `bootstrap_seed + 1000 + b`).
* The offset is the mean of (Q vector - FP16 vector) over the 1000 dev A reports. No labels. No style B vector. Dev A out-of-fold answers use an offset computed from all dev A vectors, so test-fold vectors take part in it (label-free). B answers use dev A only.
* **Danger error** (rough proxy, not used in the harm test): *missed alarm* = gold CREATE or UPDATE and the system does NO_ACTION; *wrong close* = the system closes an incident that gold does not close; *priority too low* = same action, numerically lower priority (3 = most urgent). `danger_total` is the sum of the three. *False alarm* (gold NO_ACTION or CLOSE, system CREATE or UPDATE) is counted separately.
* Full, machine-readable version: `provenance.json` and `bootstrap_predictions_end.csv`. They are written by the extended `python 04_controls.py` (run 2 goes to `results_controls\run_02`; run 1 is not touched; the run checks that it reproduces the run-1 records). **Not run yet.** Run it, then run `python 05_harm_test.py` again to add the 20 bootstrap heads.

## 5. Not implemented or not tested

* Candidate-set construction, the Shield gate and Cover: **planned, not implemented.** Nothing here tests them.
* Closed-loop missions (reports over time), full CBBA with bundles, message loss, battery, obstacles. The allocator is a simplified CBBA proxy. Each report is a single-record fork-and-replay.
* The 20 bootstrap heads in the harm test (waiting for the rerun of step 4).
* Fresh families, other bit widths, other models, other prompts.
* Supervisor review of the evaluation priorities (unverified incidents first, then delay, then trips). They are my proposal. A wasted trip can delay another incident.
* Style B and A come from the same generator. They are not independently written language.

## 6. Deviations and disclosures

* All heads work after attempt 1 is exploratory (decided after B was seen). Bullets 1 and 3 of section 6 of `HEADS_TEST_PLAN.md` conflict for this outcome; the note is in `CONTROLS_PLAN.md` section 9.
* The first controls report used the words "noise floor". That wording was wrong (section 3 above). The step-4 code and report text are corrected; the numbers did not change.
* Earlier exploratory runs of the same allocator on the pilot's generative FP16 and Q4 outputs (`funnel_all.py`, `funnel2.py`) were seen before the plan. `EPS = 0.5` and `HARM_SECONDS = 30` in `funnel.py` were chosen after seeing the pilot cases, so any 30 s analysis is exploratory. The primary result uses no threshold.
* After the first harm-test run I added section 10 of the report (reasons for the misses), a note on who was fitted on style A, and intervals for trips and distance. These are not in the frozen plan. They are labelled. No number of the plan's analysis changed.
* The first run folder was recreated after those wording changes. The numbers are identical (checked).
* Fingerprints: plan `2e791175a4fa3ae0b4fc832000e4e89f427f531bb97e384b3d79cca3a740acfb`, `harm_config.json` in `results_harm\harm_runs.log`, saved answers `6b3e7b64e484337d75525b1f9abb19d555ba8b347c65099bfe7ef20fa7298e6f`, allocator files in `harm_config.json`.

## 7. Smallest fresh-family confirmation (to be registered before it is run)

* **New families:** a new generator seed (never run `gen_cases.py` inside `edgesar_pilot`), 60 families x 10 reports = 600 reports, style B wording. Fresh hidden states from FP16, Q8, Q4.
* **Frozen first (OSF):** systems (Heads FP16, Q8, Q4 trained on dev A; at most two repair arms: shared head and offset-removed fixed head), the gold-record reference, the allocator hashes, 600 s horizon, 12 s dwell, the family bootstrap, and one primary contrast (Heads Q4 minus Heads FP16, unverified real incidents).
* **Margin:** a number of points that supervisors accept (for example 1 or 2). Decide it before the run.
* **Size:** on B the paired contrast has a half-width of about 0.8 points with 40 families. By the rule F_needed = F_now x (half-width now / target)^2, a half-width of 1 point needs about 27 families and 0.5 points needs about 108. 60 families should give about +/- 0.7 points, if the spread is like B. This is approximate and assumes the same spread per family.
* **Recalibrate** Shield on separate data if any repair is used.
