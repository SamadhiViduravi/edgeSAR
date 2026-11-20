# Deviations from STRENGTHENING_PLAN (13 Nov 2026)

Written by the implementation chat on 13 Nov 2026. The plan (sections 3 to 8) says that a change needs a written note: date, reason, what changed, and whether outcomes had been seen.
This file is that note. Each entry says what the plan said, what is built, why, whether outcomes had been seen, and what it does to the claims we may make.

**How to read the column "Outcomes seen?"**
* **No** = decided while the code of milestones M1 to M6 was written, before the first DEV outcome table existed.
* **Yes** = decided after DEV outcomes were seen. This is post-hoc and must be labelled in the paper.
* **Not recorded** = I did not keep a time stamp for the decision. The item is a diagnostic or a detail and it does not enter the primary comparison.

**Please accept or reject each entry** (decision D7 in `IMPLEMENTATION_EVIDENCE.md`). Entries marked "FRESH: carried" also apply to the fresh run (`docs/EVAL_PLAN_FRESH.md`).

---

## D-01 Episodes are "overlay" episodes, not chain episodes

* **Plan (section 5).** An episode has an initial belief table (0 to 3 open incidents) and a stream of 12 reports. Every report is generated from the episode's gold state, so reports depend on each other.
* **Built.** An episode is 20 independent reports. Each report keeps its own open table and its own incidents (the table it had in the pilot data). The reports arrive over time and **share one fleet of 3 UAVs**.
  A report does not change the belief table of another report. Competition is for UAVs only.
* **Why.** The saved vectors exist only for the pilot reports. A chain episode needs new prompts that are rendered from a shared state, which needs the GPU. Chain mode was moved to the extensions (plan section 10).
* **Outcomes seen?** No.
* **Effect.** Errors do not spread from one report to the next. The simulator cannot show "a wrong CLOSE hides an incident that a later UPDATE needs". Closed-loop prompts stay untested. Coverage per episode position (plan section 4.8) is not reported, because position carries no information when reports are independent.
* **FRESH: carried.**

## D-02 Data for FIT, CAL and DEV (plan section 8.1)

* **Plan.** FIT, CAL and DEV are 200 episodes each, from new seeds. "Existing pilot data is not reused for any of these sets."
* **Built.** DEV uses the 1,000 style-A pilot reports with their saved vectors (the instruction was: "Use saved vectors for development"), in 5 folds (see D-07).
  For FRESH, FIT is the 1,000 development reports (no new FIT episodes). CAL is new (40 episodes = 800 reports) and EVAL is new (1,100 episodes = 22,000 reports), from seed 20261201.
* **Why.** Fresh FIT and DEV data would need the GPU before the plan is frozen. Using the saved vectors lets development go on without the GPU.
* **Outcomes seen?** No.
* **Effect.** The heads of the fresh run are fitted on pilot reports. DEV results are not independent of the pilot (the pilot is where the idea came from). Only the FRESH EVAL numbers can be confirmatory.
* **FRESH: carried** (FIT from DEV reports; CAL and EVAL new).

## D-03 The committed record is the pilot's hierarchical record

* **Plan (section 4.5).** r-hat is the top-scoring candidate.
* **Built.** r-hat is the record that the pilot's hierarchical rule gives (argmax of each head, then the pilot's assembly). Every arm commits it, and the Shield's set is built around it. It differs from the top-scoring candidate in 4 of 1,000 reports. r-hat is inside the conformal set in 999 of 1,000 reports, and so is the top candidate.
* **Why.** All arms, including "always commit", must be comparable with the pilot results. The pilot committed the hierarchical record.
* **Outcomes seen?** No (decided in M4).
* **Effect.** Negligible (0.4% of reports). The certification rule is unchanged: r-hat must be in the set.
* **FRESH: carried.**

## D-04 At most 20 candidate records, not 22

* **Plan (section 4.1).** At most 4 + 9 + 9 = 22 combinations.
* **Built.** NO_ACTION (1) + CLOSE (1) + CREATE (3 sensors x 3 priorities = 9) + UPDATE (9) = 20. The plan's 22 counts CREATE and UPDATE twice.
* **Outcomes seen?** No. **Effect.** None. The cap K = 8 on the set size is unchanged. **FRESH: carried.**

## D-05 Two extra outcome classes

* **Plan (section 4.6).** ACCEPT, ACCEPT_INFEASIBLE, ESCALATE, FALLBACK_COVERED, FALLBACK_UNRESOLVED, UNCERTIFIED_COMMIT.
* **Built.** Also **TIMEOUT** (the decision needed more simulated time than the 5 s limit; it is committed without assessment, and counted) and **FALLBACK_PARTIAL** (the cover does not serve every plausible candidate: either the set was empty or larger than K, so only the top K candidates are covered, which the plan calls "partial cover"; or the location cover of A8c does not serve candidates that differ in camera or priority from r-hat). The plan's full cover (A8) never had this class on DEV data, because no set was larger than K.
* **Why.** TIMEOUT is the user's boundary "computation consumes time". FALLBACK_PARTIAL keeps the limits of the revised cover visible (the user's boundary: no fallback may assume every possibility is covered).
* **Outcomes seen?** TIMEOUT: No. FALLBACK_PARTIAL: the class was coded for the empty and oversized sets (No); almost all its DEV cases come from A8c (Yes, see D-06).
* **Effect.** More visible classes, no hidden ones. **FRESH: carried.**

## D-06 Extra arms: A6b, A8c, A12, OBS

* **Plan (section 7).** Arms A1 to A11.
* **Built.** A1 to A11 as in the plan, and
  * **A6b** record-score gate (a second confidence baseline) and **A12** oracle gate (diagnostic upper bound: it asks exactly when the best-guess plan is wrong; not deployable): outcomes seen? Not recorded. Diagnostic only.
  * **OBS** observer (commits like A1 and logs every risk score; used to set thresholds on CAL and for the ranking analysis): No.
  * **A8c** Shield with the **location cover**: it keeps r-hat's camera and priority where r-hat has a task, and adds the other candidates' locations. It was designed **after** the DEV outcomes showed that the plan's cover (A8) costs more than it saves. **Outcomes seen? Yes. Post-hoc.**
* **Effect.** A8 vs A6 stays the registered primary comparison. A8c vs A6 is reported as secondary S1 and must be called post-hoc. A8c shows what a better cover could do; it is not evidence that the plan worked.
* **FRESH: carried** (A8c as S1 only; changing the primary to A8c is open decision D1).

## D-07 Development splits by family; exact duplicates removed from FIT

* **Plan (W13).** The episode is the unit of splits. Old reports are grouped by `audit04_duplicate_clusters.csv`.
* **Built.** The pilot's family (100 families of 10) is the grouping unit for 5 folds of 200 reports. For fold k: EVAL = fold k, CAL = fold (k+1) mod 5, FIT = the other three folds. Exact duplicates link families into one giant component (950 of 1,000 reports), so duplicates cannot be the grouping unit.
  Instead, every FIT report that has an exact duplicate in CAL or EVAL is removed from FIT for that fold (the count is logged; FIT keeps about 515 to 523 reports instead of 600). The code stops if a family or duplicate appears in two roles.
* **Outcomes seen?** No. **Effect.** FIT is smaller on DEV. Family members are still related (same generator), so DEV coverage is not a proof for fresh data. **FRESH: DEV only.**

## D-08 Requirement R3 is "no active task without a UAV"

* **Plan (section 4.4).** R3: no incident is dropped except by a CLOSE record.
* **Built.** R3: after planning, no active task of the report's table is left without a UAV. A record can only remove an incident by a CLOSE (this is how the records are applied), and any other change of the set of active tasks shows in the execution signature (D-09).
* **Why.** R3 as written is a property of record application, not of a plan. "A task nobody can take" is the failure the allocator can actually show.
* **Outcomes seen?** No. **Effect.** ACCEPT_INFEASIBLE also fires when a task cannot be assigned. **FRESH: carried.**

## D-09 The execution signature also holds the list of unassigned tasks

* **Plan (section 4.3).** Signature = the set of active tasks (landmark, required cameras, dwell) and each UAV's ordered path.
* **Built.** The same, plus the list of tasks that nobody could take.
* **Why.** Two plans that drop different tasks must not be called equal.
* **Outcomes seen?** No. **Effect.** The certificate is stricter (fewer certified sets), never looser. **FRESH: carried.**

## D-10 How the gate thresholds are set (budget matching)

* **Plan (section 7).** Each threshold is set on calibration episodes so that its request rate equals b; the threshold on rho for A8 to A11.
* **Built.** Thresholds come from observer (OBS) runs on CAL reports. Risk scores are tuples that are compared in order (the Shield: rho first, then 1 - score of r-hat). A threshold is (theta, xi): ask when the risk is above theta, or equal to theta with a fixed pseudo-random number below xi. The random number is a hash of the seed and the report id, so nothing depends on the order of data. The hard cap is floor(b x 20 + 0.5) = 2 requests per 20-report episode.
* **Why.** rho takes few distinct values (zero for most certified sets), so ties need a fixed rule.
* **Outcomes seen?** No. **Effect.** None on validity. **FRESH: carried.**

## D-11 The realised request rate is 7.2% to 7.7%, not 10%

* **Plan (section 7 and M6).** Realised rates within +-1 pp of each other (section 7), and within +-1 pp of b (M6).
* **Built.** The thresholds give an expected rate of 10% when uncapped. The hard cap (2 per episode) cuts bursts and does not make up for quiet episodes, so the realised rate is 2.3 to 2.8 pp below b. The deployable arms are within 0.5 pp of each other.
* **Why.** Found when the first DEV runs were analysed; it is a property of the cap.
* **Outcomes seen?** Yes (the rate is a DEV outcome). **Effect.** The arms are matched to each other, but not to b. Recalibrating on the capped rate is open decision D6. **FRESH: carried unless D6 changes it before the freeze.**

## D-12 Computation is charged in simulated time

* **Plan (section 3.4).** Decision latency is measured on the laptop CPU (target under 200 ms per report).
* **Built.** Each allocator run costs 0.02 s of simulated time: the new table takes effect only after that time, and the UAVs go on with the old plan meanwhile. A decision that needs more than 5 s is a TIMEOUT. The real wall time of the Shield's own work is measured on the cloud CPU and reported (median and 99th percentile).
  Sensitivity runs use 0.2 s and 1.0 s per run.
* **Why.** The user's boundary: verification and computation consume time and resources. A clock cost makes that visible in the outcomes.
* **Outcomes seen?** No. **Effect.** The 0.02 s is an assumption. No laptop or edge-board timing exists (see the not-built list). The language-model forward pass is not charged. **FRESH: carried.**

## D-13 Contention tuned by the report gaps only; scenario types not tagged

* **Plan (section 5).** Tune the report gaps, the share of CREATE reports and the share of THERMAL needs. Tag five scenario types (harmless changes, consequential errors, missing candidates, competing deadlines, impossible coverage) and guarantee a minimum count of each in development episodes.
* **Built.** Only the gaps (L, M, H = 60, 30, 8 s) were tuned. The class mix is the pilot generator's. No tags and no minimum counts. Each type has a hand-made unit test; two data shares (harmless record changes; wrong-plan reports) are computed afterwards (`IMPLEMENTATION_EVIDENCE.md`, section 4.11).
* **Outcomes seen?** No. **Effect.** No subgroup results. Impossible coverage and competing deadlines are shown by tests and in the demo, not counted in the data. **FRESH: carried.**

## D-14 Statistics on DEV

* **Plan (section 8.4).** Episode unit; 10,000 bootstrap resamples; paired sign-flip test; N_e from DEV.
* **Built.** Paired differences use 10,000 episode-bootstrap resamples and a two-sided paired sign-flip test, as in the plan. The per-arm intervals in the outcome tables use 2,000 resamples. DEV has 3 arrival seeds that re-partition the **same** 1,000 reports into 150 episodes per level, so pooled intervals are optimistic; N_e is given for each seed separately (805, 1,099, 1,423 for A8 vs A6 at M).
* **Outcomes seen?** No. **Effect.** DEV intervals are narrower than a true repeat. FRESH has independent episodes. **FRESH: the same analysis code is used (paired differences 10,000 resamples, per-arm intervals 2,000).**

## D-15 Milestone M0 is not complete

* **Plan (M0).** Set up the folder on the laptop, `git init`, run the audit scripts on the laptop, re-hash the gguf files.
* **Built.** The 14 pinned files and the audit scripts were checked in the cloud session on the staged copy (`results/audit_rerun_cloud/`). The laptop run, the gguf re-hash and `git init` were **not** done: the shell on the laptop could not start (too little free space on its Windows partition), and at the end of the session the link to the laptop was no longer available.
* **Update, 13 Nov evening.** Samadhi ran `tools/check_inputs.py` on his computer: all 14 pinned files and the three gguf files (SHA-256 and size) PASS; Python 3.12.6, numpy 2.5.3, scikit-learn 1.9.1. `git init` and the audit scripts on the laptop are still open.
* **Effect.** The reproducibility check was made on another platform (3 near-tie records move; audit 02 shows 3 CHECK lines, as AUDIT_REPORT section 5 predicts). `tools/check_inputs.py` does the pin check and the gguf hashing on the laptop. **FRESH: must be done before the freeze.**

## D-16 Windows: fork is not available, and cached probabilities differ in the 3rd decimal
* **Found by.** Samadhi's run on Windows (Python 3.12.6): 88 of 91 tests passed. Three failed: `multiprocessing.get_context("fork")` does not exist on Windows; two comparisons of cached against refitted probabilities (max difference 0.0022 for q4 action; 0.0094 for the diagnostic raw head).
* **Cause.** First: platform. Second: the heads are fitted with lbfgs at tol 1e-6; another Python/BLAS build stops at a slightly different point. This is consistent with the diagnostic (`results/repro_diagnostic_*/diagnosis.json`: on the same machine the fresh path and the development path agree exactly; no pilot-style record, top record or conformal set changed for q4, f16, q8, recentred; one set changed for the raw head; outcomes of A1, A6, A8 on 10 episodes identical) but it is **not proven**.
* **Done.** (a) `shield/devrun.py` was repaired by the main chat's patch (spawn + worker initializer); my files do not overwrite it. `shield/devrun2.py` has its own pool that works with fork and spawn; `tests/test_iter1.py` checks serial = spawn. (b) `tests/test_fresh.py`: the old exact comparison is split into three: same-machine equality of the fresh path and an independent refit of the development path (1e-12, runs everywhere); agreement with the cached probabilities at decision level (probabilities < 2e-2, identical pilot-style and top records and conformal sets, q within 1e-4, at most one changed set for the raw head); bit-for-bit comparison with the cache, which runs only where the cache was built (reported as skipped elsewhere). (c) The cache and all earlier results were not changed (cache SHA-256 e5b0716111434a8f6b6848201eabd40103ea8832f4fc744cfb588bdc5cbd8269).
* **Outcomes seen?** Not relevant (no outcome changed). **Effect.** Results on another machine can differ in small probabilities; the fresh run uses fresh heads fitted on that machine, so the cache is not used there. **FRESH: carried.**

## D-17 Iteration 1: new arms B1-B4, G1 (docs/ITERATION1_PROTOCOL.md)
* **Plan.** Section 4.3-4.7 (certify / verify / cover) and section 7 (arms).
* **Built.** B1 strict candidate check (each candidate's plan checked against its own task); B2 + mass guard (set mass >= 1 - alpha; new class UNSUPPORTED_COMMIT); B3 = B2 + cost-aware fallback (full cover, else location cover, else commit r-hat as COVER_DECLINED, by fleet-wide predicted unmet requirements n_bad); B4 = B1 + cost-aware fallback; G1 = confidence gate with two thresholds and the same fallback and cap. Definitions, primary comparison, decision rule and stopping rule were written and hashed (SHA-256 1ccce486...) before the first run; every variant ran once on DEV; nothing was tuned afterwards.
* **Choices made inside the definition (not tuned).** n_bad counts distinct tasks breaking R1, R2 or R3 in any report under the believed deadlines; the mass limit is 1 - alpha = 0.90; the escalation risk is (1 - mass of candidates that agree with r-hat in plan and feasibility, 1 - top score); the order of preference is full cover, location cover, r-hat; G1's second threshold gives the share of flagged reports that B3 has on CAL.
* **Outcomes seen?** Yes, DEV only, after the protocol was fixed. **Effect.** Label NOT SHOWN for the competent head (`ITERATION1_EVIDENCE.md`). **FRESH: B1-B4 and G1 are not wired into tools/run_fresh.py.**

## D-18 The unadapted head (raw) is a condition, not a diagnostic, in iteration 1
* **Plan.** A5 (frozen FP16 head on raw Q4 vectors) is a diagnostic arm.
* **Built.** All B arms and G1 were also run with the unadapted head as the readout (tag `raw`), next to f16 and q8. On it Shield-2 reduces the missed share from 16.5% to 9.1% at level M and beats G1 (11.2%).
* **Effect.** If the fresh test makes this condition primary, that choice was made after seeing DEV and must be disclosed. **FRESH: main-chat decision.**

## D-19 Simulated computation cost versus measured
* **Plan / earlier build (D-12).** 0.02 s of simulated decision time per allocator run.
* **Measured now (cloud container, not the laptop).** 0.15 ms per run; one Shield-2 decision 0.28 ms median, 1.6 ms at the 99th percentile. The charge is about 130 times larger than measured here, i.e. conservative. The llama.cpp part (embedding time, memory per precision) is not measured: `tools/bench_local.py` must be run on Samadhi's computer. **FRESH: needed before any latency or memory claim.**

---

## Not deviations, but not built (see `IMPLEMENTATION_EVIDENCE.md`, section 3)

Verification queue time (the simulated verifier has no queue); llama.cpp latency and memory on the laptop (script ready: tools/bench_local.py); the 100-report CPU-backend check (built into the extraction script, not run); the FRESH version of the demo; the evidence package and its hosting (needs Samadhi's approval); the extensions of plan section 10.

## What these entries do to the claims

* Allowed: "On development data, the Shield ranks wrong-plan reports better than the confidence gate, and its certificate holds at the stated level" (exploratory).
* Allowed after the fresh run, if the numbers say so: a confirmatory test of the registered primary comparison (A8 vs A6, level M).
* Allowed after iteration 1 (DEV, exploratory): "with a head retrained for Q4, no tested gate or Shield variant reduced missed deadlines against always committing; with a head not adapted to Q4, Shield-2 reduced them from 16.5% to 9.1% and beat a confidence gate given the same fallback".
* Not allowed: any statement that A8c beats the gate (post-hoc, and DEV shows no difference); any statement about chain-mode errors, other models, other hardware, or real report text.
