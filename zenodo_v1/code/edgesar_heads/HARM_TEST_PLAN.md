# EdgeSAR harm test: analysis plan (EXPLORATORY)

Written: Thu 12 Nov 2026 (Colombo time), BEFORE any system's records were run through the allocator in this study.
Frozen: the SHA-256 of this file is stored in `harm_config.json`. `05_harm_test.py` refuses to run if this file has changed since (use `--allow-changed-plan` only to record a documented deviation).
Supervisor review of the evaluation priorities (section 5): ______ (name, date, comment). Until then the priorities are Samadhi's proposal, not a decision.

## 1. Status

* **Exploratory.** Held-out style B was already used in attempt 1 and in the controls (run 1). Writing this plan now does not make B confirmatory.
* Dev A answers are out-of-fold (a head never sees the family it predicts). They are secondary and descriptive.
* Nothing in `edgesar_pilot\`, `results_heads\`, or `results_controls\` run 1 is changed. All earlier registrations stay as they are.
* Nothing is tuned here. No threshold or weight is chosen after seeing results.
* Before this plan was frozen, the code was tested only on made-up answers and on the gold-record reference against itself. No real system's answers (Heads, Generative, TF-IDF, Rule) were run through the allocator for this study.

## 2. Question

When a system (a head on FP16, Q8 or Q4 hidden states) writes a different task record, **does it change what happens to the real incidents once the same allocator uses that record?** This is measured by a simulator, not by counting wrong fields.

## 3. Setting (the existing V1 allocation code, used unchanged and pinned by hash)

Pinned files (`harm_config.json`, `allocator_sha256`): `packages/allocation/cbba.py`, `bids.py`, `mission.py`, `world.py`, `funnel.py`. The run stops if any of them is different.

* **Unit of one test = one report ("single-record fork-and-replay").** Start state = the case's open-incident table and 3 UAVs at fixed start points. One record arrives. The table after the record is given to the allocator. **This is not a closed-loop mission:** there is no stream of reports over time, no later corrections, all tasks are known at t = 0. A closed-loop mission is planned, not implemented.
* **Allocator = a SIMPLIFIED CBBA**, not full CBBA: each UAV holds one task at a time (bundle size 1), perfect messages, tasks that nobody can take wait for the next free UAV. Bid = priority value x exp(-0.01 x arrival time), priority value {1: 1, 2: 2, 3: 3}. Ties go to the lower UAV id.
* **UAVs (world.py):** UAV-01 18 m/s RGB; UAV-02 16 m/s RGB + THERMAL; UAV-03 20 m/s RGB. Straight-line flight, no obstacles, no battery, no message loss.
* **Real incidents ("simulator truth")** = the landmarks of the gold task table, with the camera really needed (RGB, THERMAL or ANY). Truth is used only (a) to decide what a UAV finds when it arrives and (b) to score the run. The allocator never receives it.
* **Verification:** a visit takes DWELL = 12 s (`mission.py`). A real incident is verified when a UAV that can see it (needed ANY: every UAV; needed RGB or THERMAL: a UAV carrying that camera) finishes the visit. A wrong-camera visit finds nothing; the task returns to the waiting list and that UAV cannot try it again. A task where nobody is really there, or that is already verified, is an empty visit.
* **Fixed mission horizon:** HORIZON = 600 s (`mission.py`: "A victim not verified by then is MISSED"). **In this plan an incident counts as verified only if its verification time is <= 600 s.** (`mission.py` also records a visit that starts before 600 s and ends after it; those are counted as unverified here, and their number is reported.)
* **No random part.** The simulator is deterministic, so "identical environmental randomness" holds by construction (`test_funnel.py` in V1 checks determinism and task-order independence). All arms use the same cases, start states, report (one per case), and allocator settings.
* **Implemented:** report -> predicted record -> task table -> simplified CBBA -> simulated verification. **Planned, NOT implemented, not shown as results:** candidate-set construction, the Shield gate, Cover, closed-loop missions, full (multi-task bundle) CBBA, message loss.

## 4. Systems (arms) and the reference

* **GOLD-RECORD (reference):** for each report, the correct record for that report, in the same allocator with the same UAVs. It is **not** an optimal planner and it is not all-knowing: incidents that cannot be verified even with correct records (too few UAVs, wrong cameras, time) stay unverified in the reference. Those are "resource-limited" and are reported separately from errors caused by a record. FP16 is not truth either.
* **Primary:** `Heads FP16`, `Heads Q8`, `Heads Q4` (one head per precision, trained on dev A; answers from `results_controls/predictions_end.csv`, run 1, SHA-256 in `harm_config.json`).
* **Secondary:** `FP16-trained heads on Q8 / Q4 vectors` (fixed head), the same with `offset removed`, and `Shared head on FP16 / Q8 / Q4 vectors`. And, when the file exists, the **20 bootstrap-sample heads** (`bootstrap_predictions_end.csv` from the first controls rerun that reproduces run 1) on 5 vector sets (FP16, Q8, Q4, Q8-offset, Q4-offset).
* **Paired contrasts between two systems** (listed in `harm_config.json`, `arm_pairs`): Heads FP16 -> Heads Q8; Heads FP16 -> Heads Q4; Heads Q8 -> Heads Q4; Heads Q4 -> Shared head on Q4 vectors; Heads Q4 -> FP16-trained heads on Q4 vectors, offset removed; Heads FP16 -> FP16-trained heads on Q4 vectors; Generative FP16 -> Generative Q8; Generative FP16 -> Generative Q4. No other contrast is looked at as a result.
* **Context only:** `Generative FP16 / Q8 / Q4` (the pilot's text writer), `TF-IDF + LR`, `Rule engine`. They are shown for comparison, not for claims about heads.
* **Offset:** one constant vector per precision, the mean of (Q vector - FP16 vector) over the 1,000 dev A reports. No labels and no style-B report is used to fit it. (Dev A out-of-fold answers use an offset fitted on all dev A vectors: label-free, but the test fold's own vectors take part.) The 93% / 73% figures in the controls report mean "share of the average squared change of the vector that one constant offset accounts for". They are **not** a share of errors repaired.

## 5. Outcomes (reported separately; no weighted "harm score", no penalty number)

The priorities below are an **evaluation choice proposed by Samadhi on 12 Nov 2026, pending supervisor review.** They are not an established operational SAR policy. A wasted trip can delay another incident, so effects are judged over the whole run.

**Primary:** the proportion of real incidents **not verified by the 600 s horizon**:
U = (number of real incidents unverified) / (number of real incidents), summed over the reports of a split.
Reported (a) absolute, against simulator truth, for every arm, and (b) as the paired difference from the GOLD-RECORD reference, dU = U(arm) - U(reference).
Every unverified incident is also placed in one group: **resource-limited** (unverified in the reference too), **system-induced** (verified in the reference, unverified with the arm's record: V->U), or **recovered** (unverified in the reference, verified with the arm: U->V). V->V and U->U complete the transition table.

**Secondary (each separately):**
1. Verified-to-unverified and unverified-to-verified transitions between paired runs (counts, and per 100 reports).
2. Verification delay: arm minus reference, in seconds, over incidents verified in **both** runs (count given). Unverified incidents are **never dropped silently**: they stay in the counts of item 1 and in item 3.
3. Verification time with misses counted at the horizon (the existing `rmivt` convention in `mission.py`: "mean verification time, missed = horizon"). It is a convention to allow a mean; it always sits next to the miss counts. (A visit that finishes after 600 s keeps its real finishing time in this mean, as in `mission.py`; those incidents are counted unverified in item 1 of the primary outcome and their number is printed.)
4. Delay to confirmed incidents: the median and 90th percentile of the verification time of incidents that were verified, per arm (absolute).
5. Unnecessary trips: empty visits and wrong-camera visits per report, separately.
6. Distance flown: metres per report (straight-line legs from each UAV's start through its visits).
7. Computation time: wall-clock milliseconds of `run_mission` per report (descriptive; depends on the machine; not compared statistically).
8. Funnel levels (`funnel.py`, unchanged): L0 record differs, L1 task table differs, L2 assignment differs, L3 route differs, L4 verification differs. A table change with no verification change = **absorbed**; with a verification change = **consequential**.

**Delay threshold:** the only existing protocol that has one is `packages/allocation/funnel.py` (`HARM_SECONDS = 30.0`, `EPS = 0.5`: "POC values: EPS and HARM_SECONDS were chosen by me after seeing the pilot cases"; harmful = a new miss, or an incident at least 30 s later). Any analysis that uses it is **exploratory** and labelled so. The primary analysis uses no threshold.

## 6. Pairing and uncertainty

* Pairing is by report: every arm and the reference run on the same case.
* **Splits:** held-out style B (400 reports, 40 families) is the main split. Dev A (1,000 reports, 100 families; answers are out-of-fold) and all 1,400 reports are reported as secondary and descriptive.
* **Independent unit = the family** (10 reports from one scenario family). Held-out B has **40 families**; dev A has **100**. Intervals are 95% percentile intervals from a **family bootstrap** (2,000 resamples, seed 20261112): whole families are redrawn, and the same draw is used for the arm and the reference, so differences are paired.
* 40 families is small. Wide intervals are expected and are the honest result.
* The 20 bootstrap-sample heads were tested on the **same** B reports. They are **not 20 independent datasets**. Only their spread (mean, lowest, highest) is shown, with no pooled interval.
* No p-values and no pass/fail rule are declared. Results are descriptive.

## 7. Required checks (the run stops or flags if one fails)

* Plan file hash = the hash in `harm_config.json`. Allocator files = the pinned hashes. `predictions_end.csv` hash = the pinned hash.
* Every saved record, rebuilt from the file, equals the gold record exactly when the file says `record_ok = 1` (round-trip check).
* The reference compared with itself shows no change at all.
* Two identical runs give identical results (determinism).
* Every system in the plan has exactly one saved record for every one of the 1,400 reports.
* The pilot files are the frozen ones (`heads_common.check_pilot_frozen`).

## 8. Disclosures

* **Earlier exploratory runs exist.** Before this plan, the same allocator was run on the pilot's generative FP16 and Q4 outputs (`funnel_all.py`, `funnel2.py`, marked "Exploratory only"). Those numbers were seen. EPS and HARM_SECONDS were chosen after seeing them. They are not repeated here as findings.
* Style B was seen in attempt 1 and in controls run 1.
* The first controls report used the words "noise floor". The 19.6% is the mean disagreement of **bootstrap-sample heads** with the reference FP16 head on B. It is bootstrap-sample variability of the head, not a pure random-seed floor. It must not be subtracted from 27.5% to get a quantization effect.
* Pre-registration: the conflict between bullets 1 and 3 of section 6 of `HEADS_TEST_PLAN.md` is documented as a deviation in `CONTROLS_PLAN.md` section 9. Further heads work is exploratory.
* The old "danger error" counts of the controls report are rough proxies (definitions in `provenance.json` of the rerun). They are **not** used here. Simulator outcomes replace them.

## 9. Files and commands (Windows PowerShell, in `edgesar_heads`)

* `python 05_harm_test.py` -> `results_harm\run_NN\`: `harm_report.md`, `harm_summary.json`, `harm_table.csv`, `per_report_outcomes.csv`, `per_incident_outcomes.csv`, `harm_outcome.png`. One line per run is added to `results_harm\harm_runs.log` (hashes of plan, config, allocator files and inputs, check results). Earlier run folders are never overwritten.
* `python 05_harm_test.py --bootstrap-file results_controls\run_02\bootstrap_predictions_end.csv` adds the 20 bootstrap-sample heads (without the option, the newest `results_controls\run_*\bootstrap_predictions_end.csv` is used if it exists). That file did not exist when this plan was frozen, so its hash is logged but not pinned.
* `python 06_demo.py` -> prints, for illustrative reports, the report, the predicted record, the task table, the allocation and the verification outcome; writes `demo_cases.md`.
* `python -m pytest -q tests` -> all tests.

## 10. After this run

The smallest confirmatory evaluation is specified from the observed between-family spread: fresh families from a **new generator seed** (never `gen_cases.py` inside the pilot folder), fresh hidden-state extraction for FP16, Q8, Q4, settings and arms frozen first, Shield recalibrated on separate data if any repair is used. The report prints the approximate number of families needed for a 95% interval no wider than +/- 2 points of U on the main paired contrasts (F_needed = F_observed x (observed half-width / 0.02)^2; approximate, assumes similar spread per family).
