# EdgeSAR Shield: implementation evidence for the main chat

Friday 13 November 2026 (Colombo). From the implementation chat to the research-design chat ("main chat"), to Samadhi, and later to the supervisors.
Package: `edgesar_shield` (the folder that holds this file). Every number below is read from files in `results/` by `tools/build_evidence.py`. The headline numbers were also recomputed from the raw records by independent code (`tools/verify_dev_numbers.py`: all counts and differences equal, intervals and p-values within bootstrap noise).

**State.** Milestones M0 to M7 are done on **development (DEV) data**: the saved vectors of the 1,000 style-A reports. The GPU extraction script, the freeze tools and the demo are built and tested. **M8 (the FRESH run) has not started.** No fresh report exists. No fresh outcome has been generated or looked at. `docs/EVAL_PLAN_FRESH.md` says `STATUS: DRAFT`: it is not frozen, not hashed and not sent to the supervisors.

**Asked of the main chat:** review this file, answer the open decisions in section 9, and only then freeze the plan and rerun the supervisor gates.

---

## 0. Short version

*Plain English, for Samadhi.*

1. **Built and tested.** A real bounded CBBA allocator. A simulator where 20 reports share 3 UAVs. The Shield. 15 test systems ("arms") and an observer. A demo with a failure case. The tools for the fresh run. 91 automatic checks pass.
2. **What got better.** The Shield finds wrong-plan reports much more completely: wrong-plan reports that nobody checks are **2.2%** of all reports with the Shield, 14.7% with the confidence gate and 18.6% with no gate. This is not an equal-cost comparison: the Shield acts on 34% of reports (verification or cover) and the gate on 7%. At an equal flag rate its ranking is better by a modest margin (AUROC 0.904 against 0.874). The promise "certified and wrong is at most 10%" holds (2.2%). When the readout is poor (stress test), missed incidents fall from 16.5% to **10.3%** (plan cover) or **8.2%** (location cover); the confidence gate only to 15.8%.
3. **What did not get better.** With the good Q4 readout, the plan's Shield (A8) is **worse** than the simple confidence gate: 8.2% vs 7.1% missed at level M (+1.16 pp (+0.37 to +1.96), p 0.006). The revised location cover (A8c) is equal to the gate (-0.02 pp (-0.49 to +0.45), p 1.000). There is little left to fix: wrong records cost +2.5 pp over gold records, and a perfect gate would win back only 0.5 pp (not significant). Q4 is also worse than FP16 always-on at mission level (+1.11 pp (+0.47 to +1.77) at M).
4. **Not tested.** Anything on fresh data. The GPU step on real hardware. Timing on a laptop or an edge board. Other models. Real report text. Closed-loop prompts. Message loss between UAVs. The full list is in section 8.
5. **Next.** The main chat answers the questions in section 9. Then: set `STATUS: FROZEN-READY`, run `tools/freeze_plan.py`, email the hash to the supervisors, make the fresh reports, run the GPU extraction (about 2 hours), run the fresh test **once**.

---

## 1. Existing findings and new experiments are kept apart

| Kind | What | Status |
|---|---|---|
| Existing, unchanged | Pilot and harm test on the 1,400 pilot reports (style A 1,000, style B 400). On held-out B, incidents unverified out of 752: gold records 0, FP16 heads 15, Q8 heads 16, Q4 heads 13, FP16 head on raw Q4 vectors 141, same head with the offset removed 18, shared head 10, generative FP16 83, generative Q4 69, TF-IDF 30. | Exploratory. Reproduced again in this session from the saved records (audit script 03: 10 of 10 PASS). Not changed. |
| Existing, unchanged | The audit of 13 Nov (79 inspected files, provenance, duplicates). | Re-run in this session on the staged copy, in the cloud (`results/audit_rerun_cloud/`): manifest 79 listed, 0 missing, 0 changed; audit 01: 37 PASS, 0 FAIL; audit 03: 10 PASS, 0 FAIL; audit 02: 2 PASS and 3 CHECK (a few near-tie records, head margins 0.002 to 0.102; AUDIT_REPORT section 5 expects this on another platform). All 13 comparable output files are identical to the saved ones in `edgesar_audit_2026-11-13/out`. Both runs were made in cloud sessions, so this is a reproducibility check, **not** the laptop run. |
| **New, DEV (exploratory)** | Everything in section 5: saved vectors, 1,000 style-A reports, overlay episodes, 3 arrival seeds, three contention levels, stress test, sensitivity runs. | Used to build and set the design. **Not confirmatory.** The pooled intervals are optimistic because the seeds re-use the same reports. |
| **New, FRESH (confirmatory)** | Nothing. | Not started. Waits for the frozen plan. |

Rules kept: `edgesar_pilot`, `edgesar_heads`, `V1` and the audit folder are read-only (14 pinned files are exactly the audited versions: `python tools/check_inputs.py`). Style B was not used for any choice. Each rerun keeps the first run (`results/dev/main_first` and `raw_first` have identical records; `tools/compare_runs.py`).

## 2. What was built

| Part | Files | What it does | Checked by |
|---|---|---|---|
| Bounded CBBA + legacy wrapper | `shield/alloc.py` | Bundles of up to 3 tasks, bid warping (Johnson et al. 2012), release of later bundle tasks, consensus rounds on a connected graph, round cap logged; `legacy_greedy_s1` wraps V1 unchanged | `tests/test_cbba.py` (18), `results/M1_cbba_report.md` |
| Simulator | `shield/sim.py`, `shield/core.py` | Event loop, deadlines, verification requests (delay and budget cap), scorer with every incident in the denominator, hidden-truth wall, simulated compute time (0.02 s per allocator run, time-out 5 s) | `tests/test_sim.py` (23) |
| Heads, candidates, conformal sets | `shield/data.py`, `readout.py`, `candidates.py`, `calibrate.py`, `service.py`, `devset.py`, `episodes.py` | Heads on saved vectors (tol 1e-6), up to 20 candidate records, split conformal sets | `results/M4_readout_report.md` |
| Shield and all arms | `shield/policy.py`, `cover.py`, `oracle.py`, `devrun.py` | Certification by execution signature, requirement check R1 to R3, escalation, cover fallback, ablations, gates with budget matching | `tests/test_policy.py` (26) |
| FRESH tools | `shield/freshset.py`, `shield/frozen.py`, `tools/gen_episodes_fresh.py`, `tools/freeze_plan.py`, `tools/run_fresh.py` | Regenerate the cases from the seed, freeze the plan and the code, refuse to run if anything changed | `tests/test_fresh.py` (13) |
| GPU extraction (kept apart) | `tools/extract_fresh_vectors.py` | One vector per report and precision with explicit llama.cpp settings, report-id hash, model hashes, log-order check, anchor and CPU checks, manifest | `tests/test_extraction.py` (11) |
| Analysis | `tools/run_dev.py`, `analyze_dev.py`, `power.py`, `sens_summary.py`, `compare_runs.py`, `verify_dev_numbers.py`, `check_inputs.py`, `build_evidence.py` | Tables, power, sensitivity, reproducibility, independent number check, input pins | run in section 10 |
| Demo | `demo.py` | One case for each outcome class and one failure case, with candidates, signatures, decision, outcome and cost | `results/demo_output.txt` |

## 3. Acceptance checks of STRENGTHENING_PLAN section 9, one by one

| M | Plan wants | Result | Met? |
|---|---|---|---|
| M0 | Folder, `git init`, audit scripts on the laptop, gguf re-hash | Done in the cloud session on the staged copy: 14 pinned files and 79 manifest files MATCH; audits as in section 1. **Not done:** the laptop run, the gguf re-hash, `git init` (my shell on the laptop cannot start: too little free disk space). | Partly |
| M1 | (a) conflict-free (b) 10,000 random instances converge, zero non-converged on the full graph (c) deterministic (d) order invariant (e) L_t = 1 equals legacy on 1,400 gold tables (f) brute-force ratio (g) warping frequency | (a),(c),(d) tests pass. (b) 10000 instances: 0 not converged on the full graph (worst 10 rounds) and 0 on a line graph (worst 21); with warping OFF 18 do not converge (worst 114 rounds). (e) 1400 of 1400 first assignments identical. (f) mean ratio to the best 0.986 (worst 0.836) for L_t = 3; 0.961 for L_t = 1; 0.958 for legacy. (g) warping lowered 281 of 114998 bids (0.24%). | Yes |
| M2 | Truth wall test; deterministic gold runs; counts add up; hand-made scenario episodes | Source scan and runtime tests of the wall; deterministic reruns; random episodes add up (on time + late + unverified + resolved externally = incidents); one hand-made episode for each scenario type of plan section 5 | Yes |
| M3 | Generator reproducible; extraction script with provenance; CPU vs GPU cosine | Generator is deterministic and unique (tests; `run_fresh.py` regenerates it from the seed). Extraction script tested against a mock llama server and a failure matrix. **Not run on a GPU. CPU vs GPU cosine not measured.** | Built, not run |
| M4 | <= 22 combinations, missing candidates counted; coverage inside the binomial band | At most 20 combinations (deviation D-04). Missing candidates: 0 of 2000 CAL + EVAL rows. Coverage at alpha 0.10: 90.8%, inside the 95% band 88.1% to 91.9% (inside). At alpha 0.05: 94.9% (inside); at alpha 0.20: 80.7% (inside). | Yes |
| M5 | One unit test per outcome class and scenario type; zero truth access; ms per decision | 26 policy tests (one per class: ACCEPT, ACCEPT_INFEASIBLE, ESCALATE, FALLBACK_COVERED, FALLBACK_UNRESOLVED, UNCERTIFIED_COMMIT, TIMEOUT, empty set, oversized set, missing candidate, competing deadlines); source scan shows no policy module names the truth; decision times in section 4.7 | Yes |
| M6 | Realised request rates within +-1 pp of b for A6 to A11 | The deployable arms are within **0.4 pp of each other** (7.2% to 7.7%), as plan section 7 requires. But they are **2.3 to 2.8 pp below b = 10%**, because the hard cap (2 requests per 20 reports) cuts bursts. The plan's M6 wording is **not** met; see decision D6. | Partly |
| M7 | DEV runs; settings; N_e; `EVAL_PLAN_FRESH.md`; hash recorded before FRESH exists | DEV runs, sensitivity and power done; draft plan written. **Hash not recorded: the plan is a DRAFT.** | Partly (waits for approval) |
| Kill criteria | Fewer than 3% certified non-singleton sets **and** A8 does not beat A6 on DEV | Certified non-singleton sets: 10.6% of reports at L, 8.9% at M, 6.2% at H, so the first part is **false** and the rule is not triggered by its letter. A8 does not beat A6 (section 5). See decision D4. | Not triggered by its letter |
| Kill criterion 2 and plan section 5 | Gold-record miss rate 3 to 8% at level M and 10 to 20% at level H | Gold records miss 1.3% at L, **4.9% at M, 13.4% at H**: inside both bands. Only the report gaps were tuned (60, 30, 8 s); the share of CREATE reports and of THERMAL needs were not. | Yes |

### Plan items that are not built, or only partly built

| Plan item | State | Effect on what the numbers can say |
|---|---|---|
| Section 5: scenario types **tagged**, with a guaranteed minimum count of each in development episodes, and subgroup reporting | **Not built.** I report two data-derived shares instead (section 4.11) and I test each type by a hand-made unit test | Subgroup results (for example only the competing-deadline reports) cannot be given. |
| Section 5: contention tuned by report gaps, **share of CREATE reports and share of THERMAL needs** | Only the gaps were tuned | The contention is one-dimensional. |
| Section 3.1: verification **queue time** | The simulated verifier has no queue: every request is answered d_v seconds later; requests are limited only by the budget cap | Waiting costs are the hold seconds only. |
| W11 / section 3.1: memory and **CPU latency** of Q4 + Shield, Q8 always-on, FP16 always-on | Only file sizes are known (0.75, 1.23 and 2.31 GiB for Q4_K_M, Q8_0 and FP16). Forward-pass latency was **not measured** | The cost table has no model-latency column. The 2 GB assumption excludes FP16 on file size alone. |
| W14 / M3: 100-report **CPU-backend** check, CPU vs GPU cosine | Built into the extraction script, **not run** | Unknown platform effect. |
| W8 / M9: versioned **evidence package**, hosting | The folder is a candidate package. **No upload.** Hosting needs Samadhi's approval | Reviewers cannot yet rerun the tables. |
| Section 8.1: FIT / CAL / DEV of **200 episodes each**, new seeds | DEV uses the 1,000 saved style-A reports in 5 family folds (D-02, D-07); FRESH uses new episodes | DEV is not independent of the pilot data. |
| Section 8.6: demo cases **from FRESH** after the analysis | The demo reads DEV records only; the FRESH version is not written | The demo shown now is a development demo. |

## 4. Results (DEV, saved vectors)

### 4.1 Setup

1,000 style-A reports, 5 outer folds by family. In each fold the EVAL reports are tested, the next fold calibrates, the other three (minus exact duplicates) fit the heads. An episode is 20 independent reports that arrive over time and **share one fleet** of 3 UAVs (deviation D-01). Levels L, M, H have mean gaps of 60, 30 and 8 s between reports. 3 arrival seeds give 150 episodes per level (the seeds re-partition the same reports, so pooled intervals are optimistic). Verification budget b = 10% of reports (hard cap 2 per episode), delay d_v = 60 s, alpha = 0.10, K = 8, deadlines 240/360/480 s for priority 3/2/1, bounded CBBA with L_t = 3, 0.02 s of simulated time per allocator run, time-out 5 s. **U** is the share of real incidents verified late or not verified (late + unverified) / incidents; every incident is in the denominator. Lower is better. Level M has 5505 incidents per arm; gold records miss 4.9% of them.

### 4.2 Outcomes and costs, level M (all arms)

Rows: A0 gold records (reference); A1 Q4 commit; A2 FP16 and A3 Q8 (off-board references); A4 recentred Q4; A5 frozen FP16 head on raw Q4 (**diagnostic, deliberately mismatched**); A6 confidence gate, A6b record-score gate, A7 random gate (budget-matched baselines); A8 Shield with the plan's full cover; A8c Shield with the revised location cover (**designed after the DEV outcomes were seen**); A9 singleton sets only; A10 Shield without fallback; A11 top-2 what-if; A12 oracle gate (diagnostic upper bound, not deployable; uses more requests).

| Arm | System | Missed by deadline U (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 | Gold records (reference) | 4.9% (4.1% to 5.8%) | 269 | 2 | 0.000 | 0.000 | 0 (0) | 1076 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 7.4% (6.4% to 8.5%) | 392 | 16 | 0.000 | 0.076 | 0 (0) | 1114 | 0.0 | 0.00 | 0.01 / 0.01 |
| A2 | FP16 heads, always commit (off-board reference) | 6.3% (5.4% to 7.3%) | 342 | 5 | 0.000 | 0.057 | 0 (0) | 1106 | 0.0 | 0.00 | 0.01 / 0.01 |
| A3 | Q8 heads, always commit | 6.5% (5.5% to 7.5%) | 353 | 5 | 0.000 | 0.063 | 0 (0) | 1100 | 0.0 | 0.00 | 0.01 / 0.01 |
| A4 | Recentred Q4 (FP16 head, label-free shift removed) | 8.0% (7.1% to 9.0%) | 385 | 56 | 0.000 | 0.124 | 0 (0) | 1141 | 0.0 | 0.00 | 0.01 / 0.01 |
| A5 | Frozen FP16 head on raw Q4 (diagnostic) | 16.5% (15.6% to 17.4%) | 218 | 690 | 0.000 | 0.164 | 0 (0) | 1079 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 7.1% (6.1% to 8.1%) | 354 | 35 | 0.073 | 0.070 | 0 (0) | 1107 | 4.4 | 0.00 | 0.01 / 0.03 |
| A6b | Top-record-score gate | 7.6% (6.6% to 8.7%) | 372 | 47 | 0.077 | 0.074 | 0 (0) | 1115 | 4.6 | 0.00 | 0.01 / 0.03 |
| A7 | Random gate | 7.4% (6.4% to 8.4%) | 388 | 19 | 0.072 | 0.086 | 0 (0) | 1121 | 4.3 | 0.00 | 0.01 / 0.03 |
| A8 | Shield + full cover fallback (plan) | 8.2% (7.2% to 9.3%) | 428 | 25 | 0.076 | 0.043 | 436 (7) | 1094 | 4.6 | 1.96 | 0.30 / 2.26 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 7.0% (6.1% to 8.0%) | 361 | 27 | 0.077 | 0.079 | 493 (63) | 1119 | 4.6 | 1.95 | 0.29 / 2.39 |
| A9 | Shield, singleton sets only | 8.7% (7.7% to 9.8%) | 437 | 43 | 0.076 | 0.050 | 545 (8) | 1105 | 4.5 | 1.36 | 0.24 / 1.26 |
| A10 | Shield, no fallback | 7.0% (6.1% to 8.0%) | 356 | 30 | 0.077 | 0.069 | 0 (0) | 1116 | 4.6 | 1.69 | 0.26 / 1.65 |
| A11 | Top-2 what-if, no conformal | 9.6% (8.5% to 10.6%) | 499 | 27 | 0.076 | 0.385 | 1036 (607) | 1208 | 4.6 | 2.59 | 0.58 / 2.86 |
| A12 | Oracle gate (diagnostic upper bound) | 6.9% (6.0% to 8.0%) | 350 | 32 | 0.099 | 0.066 | 0 (0) | 1106 | 6.0 | 0.00 | 0.00 / 0.01 |

Decision time is measured on the cloud session's CPU (not the laptop, not an edge board) and covers the Shield's own work: candidates, what-if allocator runs and the cover plan. It does not include the language-model forward pass.

### 4.3 Levels L and H (key arms)

**Level L** (gold records miss 1.3%)

| Arm | System | Missed by deadline U (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 | Gold records (reference) | 1.3% (0.9% to 1.9%) | 73 | 1 | 0.000 | 0.000 | 0 (0) | 1193 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 2.4% (1.9% to 3.0%) | 121 | 12 | 0.000 | 0.075 | 0 (0) | 1250 | 0.0 | 0.00 | 0.01 / 0.02 |
| A2 | FP16 heads, always commit (off-board reference) | 1.8% (1.3% to 2.4%) | 96 | 4 | 0.000 | 0.054 | 0 (0) | 1240 | 0.0 | 0.00 | 0.01 / 0.01 |
| A3 | Q8 heads, always commit | 2.1% (1.6% to 2.7%) | 114 | 4 | 0.000 | 0.059 | 0 (0) | 1241 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 2.9% (2.4% to 3.4%) | 128 | 31 | 0.073 | 0.070 | 0 (0) | 1240 | 4.4 | 0.00 | 0.01 / 0.04 |
| A7 | Random gate | 2.6% (2.0% to 3.2%) | 125 | 18 | 0.072 | 0.082 | 0 (0) | 1251 | 4.3 | 0.00 | 0.01 / 0.02 |
| A8 | Shield + full cover fallback (plan) | 3.2% (2.6% to 3.8%) | 153 | 21 | 0.072 | 0.041 | 411 (7) | 1227 | 4.3 | 1.94 | 0.20 / 1.53 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 2.5% (2.0% to 3.0%) | 119 | 20 | 0.072 | 0.076 | 480 (68) | 1244 | 4.3 | 1.94 | 0.19 / 1.59 |
| A10 | Shield, no fallback | 2.5% (2.1% to 3.0%) | 118 | 22 | 0.072 | 0.065 | 0 (0) | 1236 | 4.3 | 1.69 | 0.18 / 1.09 |
| A12 | Oracle gate (diagnostic upper bound) | 2.6% (2.1% to 3.1%) | 105 | 37 | 0.099 | 0.066 | 0 (0) | 1233 | 6.0 | 0.00 | 0.00 / 0.02 |

**Level H** (gold records miss 13.4%)

| Arm | System | Missed by deadline U (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 | Gold records (reference) | 13.4% (12.1% to 14.7%) | 700 | 39 | 0.000 | 0.000 | 0 (0) | 772 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 16.4% (15.1% to 17.6%) | 832 | 70 | 0.000 | 0.073 | 0 (0) | 795 | 0.0 | 0.00 | 0.01 / 0.02 |
| A2 | FP16 heads, always commit (off-board reference) | 15.3% (14.0% to 16.6%) | 783 | 61 | 0.000 | 0.056 | 0 (0) | 792 | 0.0 | 0.00 | 0.01 / 0.01 |
| A3 | Q8 heads, always commit | 16.1% (14.6% to 17.5%) | 817 | 70 | 0.000 | 0.061 | 0 (0) | 791 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 16.1% (14.8% to 17.4%) | 816 | 70 | 0.073 | 0.056 | 0 (0) | 786 | 4.4 | 0.00 | 0.01 / 0.04 |
| A7 | Random gate | 16.2% (14.8% to 17.5%) | 813 | 78 | 0.072 | 0.073 | 0 (0) | 787 | 4.3 | 0.00 | 0.01 / 0.03 |
| A8 | Shield + full cover fallback (plan) | 17.9% (16.5% to 19.1%) | 898 | 86 | 0.076 | 0.036 | 474 (10) | 787 | 4.6 | 1.98 | 0.68 / 5.48 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 15.7% (14.4% to 17.0%) | 795 | 72 | 0.074 | 0.066 | 523 (57) | 795 | 4.4 | 1.98 | 0.69 / 5.48 |
| A10 | Shield, no fallback | 15.6% (14.3% to 16.9%) | 785 | 76 | 0.073 | 0.056 | 0 (0) | 793 | 4.4 | 1.69 | 0.65 / 4.37 |
| A12 | Oracle gate (diagnostic upper bound) | 15.7% (14.4% to 16.9%) | 790 | 74 | 0.099 | 0.055 | 0 (0) | 788 | 6.0 | 0.00 | 0.00 / 0.01 |

### 4.4 Paired comparisons (same episodes; difference in U; negative = the first arm is better)

| Comparison | Arms | Level L | Level M | Level H |
| --- | --- | --- | --- | --- |
| **Plan primary:** Shield + full cover vs confidence gate | A8 - A6 | +0.27 pp (-0.25 to +0.80), p 0.355 | +1.16 pp (+0.37 to +1.96), p 0.006 | +1.78 pp (+0.95 to +2.61), p <0.001 |
| Revised (post-hoc): Shield + location cover vs confidence gate | A8c - A6 | -0.36 pp (-0.66 to -0.07), p 0.020 | -0.02 pp (-0.49 to +0.45), p 1.000 | -0.35 pp (-0.86 to +0.15), p 0.205 |
| Fallback effect: full cover vs no fallback | A8 - A10 | +0.62 pp (+0.16 to +1.08), p 0.012 | +1.22 pp (+0.50 to +1.93), p 0.001 | +2.23 pp (+1.45 to +3.05), p <0.001 |
| Location cover vs no fallback | A8c - A10 | -0.02 pp (-0.13 to +0.13), p 1.000 | +0.04 pp (-0.13 to +0.20), p 0.843 | +0.11 pp (-0.11 to +0.33), p 0.429 |
| Location cover vs full cover | A8c - A8 | -0.64 pp (-1.09 to -0.20), p 0.008 | -1.18 pp (-1.90 to -0.47), p 0.001 | -2.13 pp (-2.95 to -1.36), p <0.001 |
| Shield without fallback vs confidence gate | A10 - A6 | -0.35 pp (-0.64 to -0.07), p 0.025 | -0.05 pp (-0.53 to +0.42), p 0.882 | -0.45 pp (-0.96 to +0.04), p 0.082 |
| Conformal sets vs singleton sets only | A8 - A9 | -0.09 pp (-0.45 to +0.27), p 0.696 | -0.49 pp (-1.06 to +0.07), p 0.119 | -0.71 pp (-1.43 to -0.02), p 0.057 |
| Conformal sets vs top-2 what-if | A8 - A11 | -0.96 pp (-1.55 to -0.40), p 0.002 | -1.33 pp (-2.12 to -0.55), p 0.001 | -1.98 pp (-2.97 to -1.01), p <0.001 |
| Confidence gate vs always commit | A6 - A1 | +0.47 pp (+0.20 to +0.74), p <0.001 | -0.35 pp (-0.84 to +0.13), p 0.185 | -0.29 pp (-0.83 to +0.25), p 0.322 |
| **Headroom:** perfect gate vs always commit | A12 - A1 | +0.16 pp (-0.25 to +0.58), p 0.491 | -0.47 pp (-1.07 to +0.13), p 0.141 | -0.69 pp (-1.45 to +0.11), p 0.095 |
| Record-induced misses of the Q4 head (vs gold records) | A1 - A0 | +1.07 pp (+0.66 to +1.51), p <0.001 | +2.49 pp (+1.86 to +3.14), p <0.001 | +2.96 pp (+2.21 to +3.72), p <0.001 |
| Quantisation effect: Q4 vs FP16 always commit | A1 - A2 | +0.60 pp (+0.20 to +1.01), p 0.005 | +1.11 pp (+0.47 to +1.77), p 0.001 | +1.05 pp (+0.31 to +1.80), p 0.009 |
| Recentred Q4 vs matched Q4 head | A4 - A1 | +0.80 pp (+0.33 to +1.29), p <0.001 | +0.60 pp (-0.17 to +1.36), p 0.134 | +0.09 pp (-0.76 to +0.93), p 0.869 |

Per-seed differences for A8 - A6 at level M: +1.3, +0.8, +1.4 pp (same sign in all three seeds). Episodes won / lost / tied by A8 against A6 at M: 37 / 64 / 49.

### 4.5 Does the Shield find the risky reports? (level M)

A report is *wrong-plan* if the plan of the best-guess record differs from the plan of the gold record (evaluation-side audit only; never seen by a policy). A method *flags* a report if it asks for verification or flies a cover.

| Arm | System | reports flagged (verify or cover) | recall: wrong-plan reports flagged | precision: flagged that were wrong-plan | wrong-plan reports left unflagged, share of ALL reports |
| --- | --- | --- | --- | --- | --- |
| A1 | Q4 heads, always commit | 0 (0.0%) | 0.0% | - | 18.6% |
| A6 | Confidence gate (min head confidence) | 219 (7.3%) | 21.9% | 56.6% | 14.7% |
| A6b | Top-record-score gate | 230 (7.7%) | 25.0% | 61.7% | 14.2% |
| A7 | Random gate | 217 (7.2%) | 6.6% | 17.1% | 17.5% |
| A8 | Shield + full cover fallback (plan) | 1028 (34.3%) | 88.3% | 49.0% | 2.2% |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 1023 (34.1%) | 88.6% | 49.5% | 2.2% |
| A9 | Shield, singleton sets only | 1296 (43.2%) | 94.0% | 41.4% | 1.1% |
| A10 | Shield, no fallback | 230 (7.7%) | 28.2% | 70.0% | 13.7% |
| A11 | Top-2 what-if, no conformal | 2289 (76.3%) | 87.7% | 22.1% | 2.4% |
| A12 | Oracle gate (diagnostic upper bound) | 298 (9.9%) | 38.2% | 72.8% | 11.7% |

Equal-budget ranking: the share of wrong-plan reports caught when each method flags the top f of every episode (OBS arm, which commits like A1 and logs every risk score). 3000 reports, 558 of them wrong-plan.

| Ranking by | f = 5% | f = 10% | f = 20% | f = 30% | AUROC |
| --- | --- | --- | --- | --- | --- |
| A8 Shield (rho, 1-score) | 18.8% | 35.1% | 61.1% | 79.9% | 0.904 |
| A9 singleton-only | 16.3% | 31.5% | 56.6% | 72.8% | 0.876 |
| A11 top-2 what-if | 18.3% | 34.6% | 59.1% | 76.5% | 0.830 |
| A6 confidence | 16.8% | 30.1% | 55.4% | 74.4% | 0.874 |
| A6b record score | 15.9% | 31.5% | 55.7% | 72.2% | 0.875 |
| random | 5.9% | 9.1% | 17.7% | 29.2% | 0.500 |

Paired episode bootstrap of the AUROC difference, Shield minus confidence: **+0.030** (95% CI +0.023 to +0.038); AUROC 0.904 vs 0.874.

### 4.6 Certificate, conformal sets and what the Shield decided (level M)

* Conformal sets on 1000 EVAL reports (target 90%): gold record in the set **908 (90.8%)**; empty sets 1; singleton sets 568; sets of 2 to K 431; oversized sets (> K) 0; gold record not expressible by the heads + parser (missing candidate) **0**.
* Certified (ACCEPT + ACCEPT_INFEASIBLE): **65.7%** of reports. Certified **and** the committed plan differs from the gold plan: 67 reports = **2.23%** of all reports (the marginal bound is alpha = 10% under exchangeability). Among certified reports alone the wrong-plan rate is 3.4%.
* Certified set sizes: 1: 1704, 2: 217, 3: 51. Certified sets with more than one record (the case that motivates the Shield, where the allocator absorbs the difference): 10.6% of reports at L, 8.9% at M, 6.2% at H.

| Outcome class | A8 reports | A8 share | A8c reports | A8c share |
| --- | --- | --- | --- | --- |
| ACCEPT | 1944 | 64.8% | 1946 | 64.9% |
| FALLBACK_COVERED | 746 | 24.9% | 204 | 6.8% |
| FALLBACK_PARTIAL | 0 | 0.0% | 569 | 19.0% |
| ESCALATE | 228 | 7.6% | 230 | 7.7% |
| FALLBACK_UNRESOLVED | 54 | 1.8% | 20 | 0.7% |
| ACCEPT_INFEASIBLE | 28 | 0.9% | 31 | 1.0% |

ACCEPT_INFEASIBLE means the allocator gave one plan for all candidates but the fleet cannot meet the requirement; it is counted as unresolved, never as safe. FALLBACK_PARTIAL (A8c only) means the cover does not serve every plausible candidate. FALLBACK_UNRESOLVED means the fleet could not meet the cover. All of them stay in the denominators.

### 4.7 Compute and waiting costs (A8, Shield with full cover)

| Level | allocator runs / report | decision ms median / p99 | hold s / report | requests / report | cover trips | distance m / report |
| --- | --- | --- | --- | --- | --- | --- |
| L | 1.94 | 0.20 / 1.53 | 4.3 | 0.072 | 411 (7 wasted) | 1227 |
| M | 1.96 | 0.30 / 2.26 | 4.6 | 0.076 | 436 (7 wasted) | 1094 |
| H | 1.98 | 0.68 / 5.48 | 4.6 | 0.076 | 474 (10 wasted) | 787 |

The plan's target of under 200 ms per report is met by a wide margin on this CPU. This says nothing about an edge board. In the sensitivity run where one allocator run costs 1.0 s of simulated time, **9** Shield decisions hit the 5 s time-out and are committed without assessment (class TIMEOUT, counted).

### 4.8 Stress test: the deliberately mismatched head (FP16-fitted head on raw Q4 vectors)

*Diagnostic only (plan W3). The Shield, the gates and the conformal sets all sit on the mismatched head here.* Gold records miss 4.9% at M and 13.4% at H.

**Level M**

| Arm | System | Missed by deadline U (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 | Gold records (reference) | 4.9% (4.1% to 5.8%) | 269 | 2 | 0.000 | 0.000 | 0 (0) | 1076 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 16.5% (15.6% to 17.4%) | 218 | 690 | 0.000 | 0.164 | 0 (0) | 1079 | 0.0 | 0.00 | 0.00 / 0.02 |
| A6 | Confidence gate (min head confidence) | 15.8% (14.8% to 16.8%) | 211 | 660 | 0.075 | 0.145 | 0 (0) | 1078 | 4.5 | 0.00 | 0.01 / 0.02 |
| A7 | Random gate | 15.8% (14.9% to 16.7%) | 225 | 644 | 0.072 | 0.163 | 0 (0) | 1082 | 4.3 | 0.00 | 0.01 / 0.02 |
| A8 | Shield + full cover fallback (plan) | 10.3% (9.2% to 11.4%) | 528 | 41 | 0.069 | 0.237 | 955 (296) | 1165 | 4.1 | 3.58 | 0.43 / 5.71 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 8.2% (7.1% to 9.2%) | 408 | 41 | 0.069 | 0.331 | 1051 (392) | 1224 | 4.1 | 3.58 | 0.40 / 5.15 |
| A10 | Shield, no fallback | 16.3% (15.4% to 17.3%) | 213 | 685 | 0.069 | 0.134 | 0 (0) | 1062 | 4.1 | 2.95 | 0.25 / 3.57 |
| A12 | Oracle gate (diagnostic upper bound) | 14.2% (13.3% to 15.1%) | 213 | 566 | 0.100 | 0.145 | 0 (0) | 1094 | 6.0 | 0.00 | 0.00 / 0.01 |

A8 - A6: -5.49 pp (-6.53 to -4.43), p <0.001. A8c - A6: -7.67 pp (-8.59 to -6.74), p <0.001. A8 - A10 (fallback effect): -5.98 pp (-7.01 to -4.92), p <0.001. Share of the always-commit arm's excess misses removed: A6 6%, A8 53%, A8c 72%.

**Level H**

| Arm | System | Missed by deadline U (95% CI) | late | unverified | requests / report | wasted trips / report | cover trips (wasted) | distance m / report | hold s / report | allocator runs / report | decision ms median / p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 | Gold records (reference) | 13.4% (12.1% to 14.7%) | 700 | 39 | 0.000 | 0.000 | 0 (0) | 772 | 0.0 | 0.00 | 0.00 / 0.00 |
| A1 | Q4 heads, always commit | 22.6% (21.3% to 23.8%) | 539 | 703 | 0.000 | 0.156 | 0 (0) | 769 | 0.0 | 0.00 | 0.01 / 0.01 |
| A6 | Confidence gate (min head confidence) | 22.0% (20.7% to 23.2%) | 536 | 673 | 0.075 | 0.133 | 0 (0) | 763 | 4.5 | 0.00 | 0.01 / 0.03 |
| A7 | Random gate | 22.4% (21.0% to 23.7%) | 574 | 658 | 0.072 | 0.155 | 0 (0) | 766 | 4.3 | 0.00 | 0.01 / 0.02 |
| A8 | Shield + full cover fallback (plan) | 21.0% (19.7% to 22.2%) | 1031 | 125 | 0.069 | 0.228 | 959 (300) | 837 | 4.1 | 3.58 | 0.90 / 12.34 |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 17.9% (16.7% to 19.2%) | 890 | 96 | 0.069 | 0.309 | 1028 (370) | 845 | 4.1 | 3.58 | 0.93 / 12.52 |
| A10 | Shield, no fallback | 22.4% (21.2% to 23.7%) | 540 | 694 | 0.069 | 0.119 | 0 (0) | 760 | 4.1 | 2.95 | 0.59 / 8.64 |
| A12 | Oracle gate (diagnostic upper bound) | 21.2% (19.9% to 22.4%) | 590 | 576 | 0.100 | 0.137 | 0 (0) | 766 | 6.0 | 0.00 | 0.00 / 0.01 |

A8 - A6: -0.96 pp (-2.19 to +0.27), p 0.139. A8c - A6: -4.05 pp (-5.16 to -2.94), p <0.001. A8 - A10 (fallback effect): -1.42 pp (-2.67 to -0.16), p 0.034. Share of the always-commit arm's excess misses removed: A6 7%, A8 17%, A8c 51%.

Costs of the Shield in the stress test: wasted trips per report rise to 0.237 (A8) and 0.331 (A8c) from 0.164 (A1); 3.58 allocator runs per report; certified share only 30.5% of reports; late incidents rise (A8 528, A8c 408, A1 218 at M) while unverified incidents fall (A8 41, A8c 41, A1 690). Against always commit, the Shield (A8) leaves 649 fewer incidents unverified and has 310 more late ones: much of what it saves is saved late.

### 4.9 Sensitivity (level M, 3 seeds, one setting changed at a time)

| Setting | A1 commit | A6 confidence gate | A8 Shield + full cover | A8c location cover | A8 - A6 (95% CI) | A8c - A6 (95% CI) |
| --- | --- | --- | --- | --- | --- | --- |
| default (b 10%, alpha 0.10, K 8, d_v 60 s, CBBA, 0.02 s per run) | 7.4% | 7.1% | 8.2% | 7.0% | +1.16 pp (+0.37 to +1.96) | -0.02 pp (-0.49 to +0.45) |
| budget b = 5% | 7.4% | 7.0% | 8.7% | 7.0% | +1.73 pp (+0.99 to +2.46) | +0.04 pp (-0.29 to +0.36) |
| budget b = 20% | 7.4% | 6.9% | 7.5% | 6.8% | +0.60 pp (+0.02 to +1.19) | -0.09 pp (-0.58 to +0.41) |
| budget b = 30% | 7.4% | 7.1% | 7.1% | 6.7% | -0.02 pp (-0.55 to +0.52) | -0.38 pp (-0.89 to +0.13) |
| alpha = 0.05 | 7.4% | 7.1% | 9.4% | 7.0% | +2.29 pp (+1.41 to +3.15) | -0.09 pp (-0.54 to +0.35) |
| alpha = 0.20 | 7.4% | 7.1% | 7.2% | 7.2% | +0.18 pp (-0.28 to +0.63) | +0.13 pp (-0.31 to +0.57) |
| K = 4 | 7.4% | 7.1% | 8.3% | 7.1% | +1.27 pp (+0.47 to +2.08) | +0.00 pp (-0.47 to +0.47) |
| verifier answers after 30 s | 7.4% | 7.0% | 8.2% | 6.7% | +1.16 pp (+0.41 to +1.93) | -0.33 pp (-0.80 to +0.14) |
| verifier answers after 120 s | 7.4% | 7.4% | 8.5% | 7.0% | +1.13 pp (+0.30 to +1.95) | -0.38 pp (-0.88 to +0.11) |
| legacy greedy allocator instead of bounded CBBA | 10.8% | 10.7% | 12.4% | 10.8% | +1.63 pp (+0.86 to +2.38) | +0.11 pp (-0.42 to +0.62) |
| an allocator run costs 0.2 s | 7.4% | 7.1% | 8.2% | 7.2% | +1.18 pp (+0.44 to +1.93) | +0.16 pp (-0.31 to +0.63) |
| an allocator run costs 1.0 s | 7.4% | 7.1% | 8.4% | 7.2% | +1.34 pp (+0.56 to +2.13) | +0.18 pp (-0.39 to +0.77) |

A8 - A6 is positive (A8 worse) in 11 of 12 settings and its interval excludes zero in 10 of them; it is smallest when the budget is large (b = 30%: -0.02 pp (-0.55 to +0.52)) or alpha is large (alpha = 0.20: +0.18 pp (-0.28 to +0.63)). A8c - A6 stays within 0.38 pp and its interval excludes zero in 0 of 12 settings. The result does not depend on the allocator (legacy: A8 - A6 +1.63 pp (+0.86 to +2.38)).

### 4.10 Sample size (plan section 8.4, from DEV)

N_e = ((1.96 + 0.84) sd_D / delta)^2 with delta = 20% of A6's record-induced misses per episode. For A8 vs A6 at level M the three seeds give N_e = 805, 1,099, 1,423 episodes (`results/dev/main/POWER.md`). The draft plan uses **1,100 episodes** (22,000 evaluation reports plus 800 calibration reports; about 122 minutes of GPU time), which gives a power of 91%, 80%, 69% for those three values of delta. For an effect as large as the DEV difference (A8 - A6 = +1.16 pp (+0.37 to +1.96)) far fewer episodes would do (93, 396, 97 for the three seeds).

### 4.11 The other outcomes of plan section 3.1 (level M, DEV)

**Harmless and harmful record changes.** Of 3000 report decisions (1,000 reports, each seen under 3 arrival seeds), the best-guess record is wrong in 771 (25.7%). In 213 of those (27.6% of the wrong records) the allocator still gives the gold plan: the change is *harmless*. In 558 reports (18.6% of all reports) the plan is wrong. At level L the harmless count is 238 and at H 161: the more contention, the fewer wrong records the allocator absorbs. Per-type tags (missed CREATE, wrong CLOSE, wrong location) are not built (section 3).

**Incident by incident against the gold-record run** (the same 5505 real incidents, the same episodes). *On time -> missed* means the incident was on time with gold records and is late or unverified with this arm. *Delay* is the mean extra time to verification, over the incidents verified in both runs, with a 95% episode-bootstrap interval; positive means later than with gold records. Part of the delay is shared by every arm, because wrong records and extra trips take fleet time.

| Arm | System | on time -> missed | missed -> on time | extra missed vs gold | verified -> never verified | never verified -> verified | delay vs gold, s (95% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Q4 heads, always commit | 221 | 84 | +137 | 16 | 2 | 10.1 (7.8 to 12.5) |
| A2 | FP16 heads, always commit (off-board reference) | 150 | 74 | +76 | 3 | 0 | 7.1 (5.1 to 9.2) |
| A6 | Confidence gate (min head confidence) | 208 | 90 | +118 | 35 | 2 | 9.0 (6.9 to 11.2) |
| A8 | Shield + full cover fallback (plan) | 272 | 90 | +182 | 25 | 2 | 14.4 (11.7 to 17.1) |
| A8c | Shield + location cover (revised, post-hoc on DEV) | 199 | 82 | +117 | 27 | 2 | 9.9 (7.8 to 12.3) |
| A10 | Shield, no fallback | 198 | 83 | +115 | 30 | 2 | 9.4 (7.3 to 11.9) |
| A12 | Oracle gate (diagnostic upper bound) | 193 | 82 | +111 | 30 | 0 | 8.1 (6.0 to 10.2) |

Other costs are in the tables above: verification requests, hold seconds, wasted trips, cover trips, distance and allocator runs per report. The verifier has no queue (section 3). Model memory: the Q4_K_M file is 0.75 GiB, Q8_0 1.23 GiB and FP16 2.31 GiB; against the 2 GB working assumption (unconfirmed) FP16 does not fit. Model latency was not measured.

### 4.12 Demo

`python demo.py` prints 9 cases chosen by a rule fixed in advance (the first evaluation episode, by id, that contains each outcome class): ACCEPT, ACCEPT_INFEASIBLE, ESCALATE, FALLBACK_COVERED, FALLBACK_UNRESOLVED, FALLBACK_PARTIAL (A8c), UNCERTIFIED_COMMIT (A10), TIMEOUT (allocator run set to 1.0 s), and a **failure case**: incident N1 of report c0128 is verified on time under the confidence gate (7 s before its deadline) and late under the Shield (5 s after), where the Shield's decision on that report was a cover (1 cover trip, 4 allocator runs). For each case it prints the report, the open table, the candidates with scores, the execution signature of each candidate, the decision, the cost, and (marked evaluation-only) the gold record and what happened to the real incidents. The failure case does not prove that one decision caused the lateness: both arms share the fleet with 19 other reports. Full output: `results/demo_output.txt`.

## 5. What improved, what failed, and why

### Improved (measured on DEV)

1. **The Shield finds wrong-plan reports much more completely, at a price.** Wrong-plan reports left unflagged: 2.2% of all reports (Shield) against 14.7% (confidence gate), 14.2% (record-score gate), 17.5% (random gate) and 18.6% (no gate). Recall of wrong-plan reports 88.3% against 21.9% for the confidence gate; precision 49.0% against 56.6%. This is **not an equal-cost comparison**: the Shield acts on 34.3% of reports (7.6% verifications and 26.7% covers), the gates on 7.3%. At an equal flag rate the ranking is better by a smaller margin: at f = 10% it catches 35.1% of the wrong-plan reports against 30.1%; AUROC 0.904 against 0.874 (difference +0.030, CI +0.023 to +0.038).
2. **The conformal certificate behaves as promised.** Coverage 90.8% at a target of 90%; certified-and-wrong 2.23% of all reports (bound 10%). The observed conditional rate among certified reports (3.4%) is far below the worst case alpha / P(certified) = 15.2%.
3. **Conformal sets are better than the top-2 what-if, and not worse than singleton-only sets.** A8 - A11 (top-2 what-if without conformal): -1.33 pp (-2.12 to -0.55), p 0.001 at M, -1.98 pp (-2.97 to -1.01), p <0.001 at H. A8 - A9 (singleton sets only): -0.49 pp (-1.06 to +0.07), p 0.119 at M, -0.71 pp (-1.43 to -0.02), p 0.057 at H, -0.09 pp (-0.45 to +0.27), p 0.696 at L; the sign-flip p-values are all at least 0.057, so I do not claim an advantage over singleton-only sets.
4. **When the readout is poor, the Shield protects the mission.** Stress test at M: U falls from 16.5% (always commit) to 10.3% (A8) and 8.2% (A8c); the confidence gate reaches 15.8%. The Shield removes 53% (A8) and 72% (A8c) of the excess misses over gold records; the confidence gate 6%. *Cost:* 528 late incidents (A8) against 218 for always commit, wasted trips per report 0.237 against 0.164.
5. **The allocator is now a real bounded CBBA** with measured convergence, determinism and a measured ratio to the best assignment; the old V1 allocator is kept as `legacy_greedy_s1` and the result does not depend on the choice.

### Failed or not achieved

1. **With the competent Q4 head, the plan's Shield does not lower deadline misses.** A8 - A6 is +1.16 pp (+0.37 to +1.96), p 0.006 at M, +1.78 pp (+0.95 to +2.61), p <0.001 at H and +0.27 pp (-0.25 to +0.80), p 0.355 at L. The plan's primary comparison therefore points the wrong way on DEV.
2. **The revised location cover (A8c) is about equal to the gate, not clearly better** (A8c - A6: -0.02 pp (-0.49 to +0.45), p 1.000 at M, -0.35 pp (-0.86 to +0.15), p 0.205 at H, -0.36 pp (-0.66 to -0.07), p 0.020 at L). The interval excludes zero at: level L (A8c lower). A8c was designed after the DEV outcomes were seen and no multiplicity correction is applied, so none of this is confirmatory.
3. **There is little headroom.** Record errors cost +2.49 pp at M (A1 - A0); a perfect gate with the same budget wins back only 0.47 pp (A12 - A1: -0.47 pp (-1.07 to +0.13), p 0.141, not significant). Even the perfect gate (6.9%) does not reach FP16 always-on (6.3%).
4. **Q4 is measurably worse than FP16 at mission level** on DEV: A1 - A2 is +0.60 pp (+0.20 to +1.01), p 0.005 at L, +1.11 pp (+0.47 to +1.77), p 0.001 at M, +1.05 pp (+0.31 to +1.80), p 0.009 at H. This is not the same outcome definition as the pilot's held-out result (B: -0.3 pp, -1.1 to +0.5; "unverified by 600 s"), so the two are not in conflict, but the supporting finding "Q4 is close to FP16" of plan section 1 should be re-read with this in mind. The recentred baseline (A4) is not better than the matched Q4 head: A4 - A1 +0.60 pp (-0.17 to +1.36), p 0.134 at M.
5. **Budget matching in the plan's M6 sense is not met** (realised rates 7.2% to 7.7% instead of 10%; section 3). The arms are matched to each other.

### Why the full cover costs more than it saves (evidence, not proof)

* Same certification, same escalation, only the fallback differs: A8 - A10 = +1.22 pp (+0.50 to +1.93), p 0.001 at M and +2.23 pp (+1.45 to +3.05), p <0.001 at H. So the cover is what costs.
* A8 flies 436 cover trips at M (A10 flies none). Against A10, A8 has 72 more late and 5 fewer unverified incidents; incident by incident against gold records (section 4.11) 74 more incidents go from on time to missed. So the cover mostly delays incidents that would have been on time. It rescues few.
* The plan's cover takes the union of cameras and the maximum priority of all candidates. In this fleet a task that needs RGB and THERMAL can only go to UAV-02, the only thermal UAV (unit test `test_cover_task_with_two_cameras_goes_to_the_only_uav_that_has_both`). The location cover (A8c) keeps the committed camera and priority and removes the loss: A8c - A8 = -1.18 pp (-1.90 to -0.47), p 0.001 at M. I did **not** measure how many cover tasks needed both cameras, so this is the best-supported explanation, not a measured fact.
* Verification is not free either: the oracle gate A12 asks for 0.099 requests per report and still recovers only 0.47 pp.

## 6. The boundaries you set, and how each is enforced and checked

| Boundary | How it is enforced | How it is checked |
|---|---|---|
| Runtime decisions cannot read hidden incident truth | Hidden truth lives in one object only the engine and scorer hold; policies get a view with no route to it | `test_truth_and_gold_are_closed_outside_the_engine`, `test_policy_view_has_no_route_to_the_gold_record`, `test_source_scan_policy_modules_never_name_the_truth`, `test_policy_modules_do_not_import_the_truth`; the evaluation-side fields (`rpg`, `tg`, gold sets) are written to the records only after the decision |
| Identical candidate allocations are not sufficient evidence of safety | Certification is separate from the requirement check R1 to R3; a certified plan that fails R1 to R3 is ACCEPT_INFEASIBLE (alarm, counted unresolved); outcomes are always judged by the scorer, never by plan equality | `test_accept_infeasible_when_certified_but_the_fleet_cannot_meet_the_deadline`; ACCEPT_INFEASIBLE counts: 12 / 28 / 141 reports at L / M / H |
| Missing candidates, time-outs, unavailable fallbacks and unresolved incidents stay visible | Separate outcome classes and counters in every table; every incident is in every denominator | Missing candidates: 0 on saved data (reported in every table, exercised by `test_missing_candidate_the_shield_accepts_a_wrong_record_and_the_incident_is_missed`); TIMEOUT: `test_timeout_when_the_what_if_runs_do_not_fit_into_the_time_limit`; FALLBACK_UNRESOLVED: 19 / 54 / 178 reports at L / M / H for A8 |
| Verification and computation consume time and resources | Verification waits (delay d_v, hold), budget cap per episode, simulated cost per allocator run that advances the clock, time-out, cover trips and distance counted | `test_decision_time_is_charged_per_allocator_run_and_timeout_is_labelled`, `test_budget_cap_is_enforced_and_rounded_per_episode`, `test_escalation_holds_the_old_rows_but_still_dispatches_them`; costs in sections 4.2 to 4.7 |
| No fallback may assume that every possibility can always be covered | The cover is planned with the same allocator and checked against R1 and R2; empty or oversized sets are never truncated silently; the cover can end FALLBACK_UNRESOLVED or FALLBACK_PARTIAL | `test_fallback_unresolved_when_the_cover_cannot_meet_the_requirements`, `test_impossible_coverage_only_one_uav_has_thermal_so_not_everything_can_be_covered`, `test_empty_set_is_uncertified_and_not_truncated`, `test_oversized_set_is_uncertified_and_counted` |
| Evaluation protocol frozen before fresh outcomes exist | `tools/freeze_plan.py` hashes the plan and the code; `tools/run_fresh.py` stops if either changed, if the cases differ from the frozen seed, or if the vectors do not match their manifest; one run per tag | `tests/test_fresh.py` (13); the real folder has no freeze file yet |

## 7. Reproducibility

* Rerunning the main run and the stress run after the last code change gave **identical** records: 7,200 records in 9 files and 3,300 records in 6 files (`results/compare_runs.txt`; `python tools/compare_runs.py main main_first`, `raw raw_first`; wall-clock times are ignored).
* Heads are deterministic (no random seed; tol 1e-6; no fit hit the iteration limit). Everything random (arrival gaps, random gate, tie-breaking) is seeded by hashes of the seed and the report id.
* Tests: full test suite, final run (tests_final.log): 91 passed in 280 s. Total 91.

## 8. Not tested, and limits of what the numbers can say

1. **Anything on fresh data.** No fresh report exists. Every claim above is exploratory. The 1,000 reports were re-used across 5 folds and 3 seeds, so the intervals are narrower than a true repeat would give.
2. **The GPU extraction run.** The script is tested against a mock llama server and a failure matrix only. Not exercised on hardware: the real llama.cpp run, the 20-report anchor check against the saved vectors, the 100-report CPU check (CPU vs GPU cosine).
3. **Hardware timing.** Decision times are from a cloud CPU. The 0.02 s per allocator run is an assumption (sensitivity at 0.2 s and 1.0 s is included). The language-model forward pass is outside the Shield's cost. No laptop or edge-board timing.
4. **Chain-mode episodes and closed-loop prompts.** In the built episodes reports do not influence each other's belief tables (deviation D-01), and a wrong record never changes a later prompt. Competition is for UAVs only.
5. **Parser faults.** The pilot's parser produced zero missing candidates on 2,000 CAL and EVAL rows. The "gold record not expressible" path is covered by unit tests, not by data; the real fault rate on realistic text is unknown.
6. **Requirement-level or regret-based certificates.** The certificate is plan equality plus R1 to R3. No guarantee is claimed about incident outcomes.
7. **Cost-aware fallback ordering** (verify before cover, or cover only when cheap) and **provisional-commit semantics** for held reports.
8. **Style shift.** The style-B check (tag `sb`, the 400 saved style-B reports in 20 fixed episodes) is part of the draft plan and of `tools/run_fresh.py`, tested with fake vectors only. It has not been run on real data.
9. **Other models, real report text, message loss or delay between UAVs, a line-graph network as the main setting.**
10. **The supervisors' answers** to plan section 12 (outcome priorities, who verifies and how fast, public evidence package, the 2 GB memory assumption). Defaults are used.
11. **M0 on the laptop:** the audit scripts on the real files, the gguf re-hash and `git init` (section 11).
12. **The conformal guarantee** assumes exchangeable calibration and test reports. Reports of one family are not independent, and the wording shifts for style B. Measured coverage on DEV is inside the band, which is not a proof for fresh data.
13. **Multiplicity.** 13 paired comparisons are shown per level (section 4.4). Only the plan's primary comparison is a registered test; all others are descriptive.
14. **A8c is post-hoc.** It was designed after the DEV outcomes were seen.

## 9. Decisions needed from the main chat (I will not decide these)

**D1. Primary comparison.** DEV points the wrong way for the registered primary (A8 - A6 = +1.16 pp (+0.37 to +1.96) at M). Options: (a) *keep A8 vs A6 as primary* and report A8c vs A6 as secondary S1 (my default in the draft plan; honest, and the only fully pre-registered test); (b) make A8c vs A6 primary, with a deviation note that A8c was designed after DEV outcomes (DEV predicts about zero, so the most that can be shown is "no detectable difference"; a non-inferiority claim needs its own margin); (c) run one more DEV round on a redesigned, cost-aware fallback and freeze that (risk: more tuning on the same 1,000 reports).

**D2. Sample size.** 1,100 fresh episodes (power 91%, 80%, 69% for delta = 20% of A6's record-induced misses, for the three DEV seeds; about 122 minutes of GPU time) or fewer (400 episodes: power 51%, 39%, 32% and about 47 minutes, but enough for an effect as large as the DEV difference).

**D3. Stress test (S7) and style-B check (S9).** I recommend including both, labelled diagnostic / exploratory.

**D4. Kill criterion and the story of the paper.** By its letter the rule is not triggered (certified non-singleton sets 8.9% at M against the 3% limit). By its intent ("A8 does not beat A6") it is. Please decide how the paper describes the Shield: (i) a monitor that ranks wrong-plan reports better than confidence (AUROC 0.904 against 0.874), finds most of them when it may also fly covers, and protects the mission when the readout degrades, with an honest finding that it does not lower misses for a competent Q4 head; or (ii) a measurement-and-diagnostic study. The data in sections 4.5 and 4.8 support (i); sections 4.2 and 4.4 limit it.

**D5. Settings and the supervisors.** alpha, K, b, d_v and the deadlines are the DEV defaults. The supervisors' four questions (plan section 12) are still open; any change must come **before** the freeze.

**D6. Request-rate matching.** Keep the thresholds as they are (arms matched to each other within 0.4 pp, realised rate 7.2% to 7.7% instead of 10%), or recalibrate them on the capped rate so that the realised rate is closer to b (the gates would then spend their budget on the first reports that cross a lower threshold; one more DEV round).

**D7. Deviations D-01 to D-15** (`docs/DEVIATIONS.md`): please accept or reject each, especially D-01 (overlay episodes instead of chain episodes) and D-03 (the committed record is the pilot's hierarchical record, which differs from the top-scoring candidate in 0.4% of reports).

**D8. Who sets `STATUS: FROZEN-READY`**, and whether to freeze before the supervisors reply. After the freeze, any change to the plan or to `shield/*.py` or the five listed tools needs a new freeze and a written deviation note.

## 10. How to reproduce and check

```
python -m pytest -q tests                                  # 91 checks (test_fresh.py takes about 4 minutes)
python tools/check_inputs.py                                # the 14 pinned files; add --gguf-dir D:\llama\models for the model hashes
python tools/run_dev.py --tag main --levels L M H --seeds 1 2 3     # about 10 minutes on 2 cores
python tools/run_dev.py --tag raw  --levels M H --seeds 1 2 3 --readout raw
bash tools/run_sensitivity.sh                              # the sensitivity runs, about 1 minute each
python tools/analyze_dev.py --tag main                     # results/dev/main/DEV_main.md and .json
python tools/verify_dev_numbers.py --tag main              # independent recomputation from the raw records
python tools/sens_summary.py ; python tools/power.py --tag main
python tools/build_evidence.py                             # this file
python demo.py                                             # eight outcome classes and the failure case
```

Set `EDGESAR_ROOT` if the older folders are not next to `edgesar_shield`. The FRESH procedure is in `README.md` and `docs/EVAL_PLAN_FRESH.md` section 8.

## 11. What Samadhi still has to do on the laptop

0. **Put the folder on the laptop.** This session could not write to the laptop at the end (the link to the computer was no longer available), so the package comes as downloads. Unpack it as `D:\1 Samadhi UNI\aFYP\Claude\edgesar_shield` (next to `edgesar_pilot`, `edgesar_heads`, `V1`). Do not change the older folders.
1. `cd "D:\1 Samadhi UNI\aFYP\Claude\edgesar_shield"` then `python tools/check_inputs.py --gguf-dir D:\llama\models` (hashes the three model files, about 4.6 GB; compares with the audited values).
2. The audit scripts of `edgesar_audit_2026-11-13\scripts` as written in its `HANDOFF.md` section 3 (PowerShell).
3. `git init` **inside** `edgesar_shield` only (the `.gitignore` is already there). Do not run it in the parent folder.
4. Ask Dr. Achala and Mr. Maninda the four questions of plan section 12 (outcome priorities and deadlines; who verifies and how fast; public evidence package; 2 GB memory assumption).

Nothing else is needed from the laptop until the plan is frozen. The GPU step comes after the freeze.

