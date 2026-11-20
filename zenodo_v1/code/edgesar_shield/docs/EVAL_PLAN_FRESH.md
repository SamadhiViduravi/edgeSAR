# EdgeSAR: evaluation plan for the fresh confirmation run (EVAL_PLAN_FRESH)

> **ITERATION 1 NOTE (13 Nov 2026, evening).** The plan below is unchanged and is still marked as a draft. A bounded development round was run after it was written (`docs/ITERATION1_PROTOCOL.md`, `ITERATION1_EVIDENCE.md`). Its results are meant to decide the primary condition, the frozen method, the margin and the sample size; the PARAMS block has NOT been edited. Deviations D-16 to D-19 are new.

STATUS: DRAFT

Version 0, written 13 Nov 2026 by the implementation chat for review by the research-design chat (main chat), the user and the supervisors.
It follows `STRENGTHENING_PLAN` section 8. **Nothing in this file is frozen.** To freeze it, the person who approves it changes the line above to
`STATUS: FROZEN-READY` and runs `python tools/freeze_plan.py`. The freeze script refuses a plan that says DRAFT. After the freeze, `tools/run_fresh.py`
refuses to run if this file or any code file changed. No fresh report exists yet and no fresh outcome has been seen.

---

## 1. What this run is for

The development experiments (saved vectors, 1,000 style-A reports) gave a mixed picture. They are **exploratory**; the FRESH run is the confirmation.

| Finding on development data (level M unless said, b = 10%, alpha = 0.10, K = 8) | Number |
|---|---|
| Gold-record policy misses by deadline (A0), levels L / M / H | 1.3% / 4.9% / 13.4% |
| Q4 heads, always commit (A1), M | 7.4% (record-induced misses +2.5 pp over A0) |
| Perfect gate (A12, not deployable) recovers | only about 0.5 pp of those 2.5 pp at M |
| Plan arm A8 (Shield + full cover) minus A6 (confidence gate), M | **+1.2 pp (A8 worse)**, CI +0.4 to +2.0, 3 of 3 seeds the same sign |
| Post-hoc variant A8c (Shield + location cover) minus A6, M | 0.0 pp, CI -0.5 to +0.5 (no difference) |
| Wrong-plan reports left unflagged, share of all reports: A1 / A6 / Shield | 18.6% / 14.7% / 2.2% |
| Certified and wrong plan (guarantee: at most alpha = 10%) | 2.2% |
| Mismatched-head stress test (raw readout), M: A1 / A6 / A8 / A8c | 16.5% / 15.8% / 10.3% / 8.2% |

So the Shield **finds** most wrong-plan reports (it acts on 34% of reports, the confidence gate on 7%), but with a competent Q4 head there is little to gain, and the plan's full cover costs more than it saves (A8 is worse than A6 by about 1.2 pp at M).
The FRESH run tests this on reports nobody has looked at. It can show the effect is real, or that it was a development artefact.
These DEV values are the pre-registered predictions: A8 - A6 > 0 at M (about +1 pp); A8c - A6 within +-0.5 pp; Shield unflagged wrong-plan about 2%;
certified-and-wrong about 2%; stress test: A8c clearly below A6.

## 2. Data (all inputs are fixed by the seed below, before any model sees them)

| Role | Reports | Source | Used for |
|---|---|---|---|
| FIT | 1,000 style-A reports (development) | saved vectors, audited | the three heads of each precision are fitted **once** on all of them (tol 1e-6; C by grouped CV inside FIT) |
| CAL | 40 fresh episodes x 20 = 800 reports | `fresh_cal` | conformal threshold; gate thresholds (from observer runs that commit like A1) |
| EVAL | 1,100 fresh episodes x 20 = 22,000 reports | `fresh_eval` | **every reported number** |

* Generator: `tools/gen_episodes_fresh.py`, seed **20261201** (the pilot used 20261026). It imports the pilot's own generator functions (SHA-256 pinned),
  style A, class mix CREATE 25 / UPDATE 20 / CLOSE 15 / NO_ACTION 40 percent (chatter, duplicate, non-human and negation 10 each).
  Every report is unique: a report whose (text, open table, gold record) is already in the development set or earlier in the file is redrawn (count logged).
* `tools/run_fresh.py` regenerates the file from the seed and stops if the cases file differs by one character. Nobody can pick, drop or edit reports.
* An episode is a fixed group of 20 reports that **share one fleet**. Each report carries its own open table (see deviation D-01, section 9).
* Prompts are rendered with each report's own gold open list, so the vectors are computed once and are the same for every policy (paired comparisons).
* GPU step (kept apart): `tools/extract_fresh_vectors.py`. llama.cpp b11901-5320c87ff, `-ngl 99 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024`,
  prompt P1, last-token state, three audited gguf files (SHA-256 checked), log-order check, 20 development reports re-embedded to check they reproduce the saved
  vectors (cosine >= 0.9999), 100 fresh reports re-embedded on the CPU (cosine >= 0.999). Cost: 22,800 reports x 3 models x about 0.107 s = **about 2 h**.
  Vectors: about 190 MB per model (float32).

## 3. Fixed settings

alpha = 0.10 (conformal), K = 8 (largest set the Shield will certify), b = 10% of reports (hard cap floor(b R + 0.5) = 2 requests per 20-report episode),
verification delay d_v = 60 s, deadlines D(3) / D(2) / D(1) = 240 / 360 / 480 s, dwell 12 s, bounded CBBA (L_t = 3, bid warping), simulated cost 0.02 s per
allocator run, decision time-out 5 s, mean gaps between reports L / M / H = 60 / 30 / 8 s (tuned on development data only), arrival seed 1.
These are the development defaults. The supervisors' answers to STRENGTHENING_PLAN section 12 are still open; if they change, the plan changes **before** the freeze.

## 4. Arms (all use the same Q4 heads unless stated)

A0 gold records (reference only) - A1 Q4 commit - A2 FP16 (off-board reference) - A3 Q8 - A4 recentred Q4 - A5 frozen FP16 head on raw Q4 (diagnostic, deliberately
mismatched) - A6 confidence gate - A6b top-record-score gate - A7 random gate - **A8 Shield + full cover (plan)** - **A8c Shield + location cover (revised, post-hoc on DEV)** -
A9 singleton sets only - A10 Shield, no fallback - A11 top-2 what-if - A12 oracle list gate (diagnostic upper bound, not deployable) - OBS (observer: behaves as A1 and logs
every gate's risk score).
Budget matching: every gate's threshold is set on the calibration episodes so its expected request rate equals b, then the per-episode cap applies.
Realised request rates are reported; deployable gates must lie within 1 percentage point of each other, or the comparison is labelled unmatched. A12 uses more
requests by construction and is labelled as such.

## 5. Primary comparison (fixed now)

**A8 (Shield + full cover) minus A6 (confidence gate)**, difference in pooled U_deadline = (late + unverified) / incidents, level M, style A, bounded CBBA,
run `main`, arrival seed 1, all 1,100 evaluation episodes. Paired by episode. Two-sided test at 0.05.
* Estimator: ratio of sums over episodes. Interval: episode bootstrap, 10,000 resamples. Test: paired sign-flip permutation test on the per-episode difference
  in missed incidents (late + unverified), 10,000 draws.
* **How the result will be read (written before the run):**
  * interval entirely below 0 and p < 0.05: the Shield with full cover lowers deadline misses compared with the confidence gate at the same budget;
  * interval entirely above 0: it raises them; the paper reports that the plan's end-to-end claim failed in this setting;
  * otherwise: no detectable difference; the paper states the largest benefit the interval does not exclude.
* Sample size by the plan's rule (section 8.4): N_e = ((1.96 + 0.84) sd_D / delta)^2 with sd_D and delta from development (level M, three seeds):
  sd_D = 1.58 / 2.13 / 1.83 misses per episode, delta = 20% of A6's record-induced misses = 0.156 / 0.180 / 0.136 per episode, so N_e = 805 / 1,099 / 1,423.
  **N_e = 1,100** gives power 91% / 80% / 69% for those three (about 80%). Smaller choices give less (400 episodes: 51% / 39% / 32%).
  The extraction time grows linearly (400 episodes: about 45 min). This choice is open (decision D2).
* No non-inferiority margin is used. Any non-inferiority claim (for example Q4 + Shield against FP16) would need its own margin, justified before the freeze.

## 6. Secondary comparisons (labelled secondary; no multiplicity correction; descriptive)

* S1 **A8c minus A6** at M (the revised variant was designed after the development outcomes were seen, so it is labelled "revised", not "confirmatory"). DEV prediction: 0.
* S2 A8 and A8c against A1, A7, A6b, A9, A10, A11 at M; then the same at H and L.
* S3 A8 and A8c against A2 and A3 with costs (Q4 + Shield against Q8 or FP16 always on); A1 minus A0 (record-induced misses); A1 minus A2 (quantisation effect).
* S4 **Gate quality** (descriptive): wrong-plan reports left unflagged (share of all reports), recall and precision of flagged reports, equal-budget ranking recall
  at 5 / 10 / 20 / 30% and AUROC for Shield, confidence, record score, random (OBS arm). Paired episode bootstrap of the AUROC difference Shield minus confidence.
* S5 **Certificate check**: P(certified and committed plan differs from the gold plan) against alpha, and the share of reports certified.
* S6 **Conformal coverage** of the gold record on the evaluation reports, empty sets, oversized sets, missing candidates (gold record not expressible), per level.
* S7 **Stress test** (`raw`): the same arms on a deliberately mismatched head (FP16-fitted head on raw Q4 vectors), levels M and H. Diagnostic: it shows the Shield's
  value when the readout is poor. Not a claim about the deployed system (STRENGTHENING_PLAN W3).
* S8 **Sensitivity runs** (level M, arms A0 A1 A6 A8 A8c A10 A12 OBS): legacy allocator, arrival seeds 2 and 3, alpha 0.05 / 0.20, b 5 / 20 / 30%, K = 4,
  d_v 30 / 120 s, allocator cost 0.2 / 1.0 s per run. Extra arrival seeds re-use the same reports (not new data), so they are never pooled with the primary run.
* S9 **Exploratory style-shift check** (`sb`, run by name, once, after the main report is written): the 400 style-B development reports in 20 fixed episodes; heads and
  conformal threshold as for style A. Style B was used before, so this is descriptive only (coverage and outcome change), with no test and no claim.

## 7. Everything that must stay visible (reported in every table, never filtered)

Missing candidates (gold record not expressible), empty sets, oversized sets, TIMEOUT decisions, ACCEPT_INFEASIBLE, FALLBACK_PARTIAL (the cover does not serve every
plausible candidate), FALLBACK_UNRESOLVED (the fleet cannot meet the cover), UNCERTIFIED_COMMIT, unverified and late incidents (every incident is in every denominator),
incidents resolved externally, and the costs: verification requests per report, wasted trips per report, cover trips and how many were wasted, distance per report,
hold seconds per report, allocator runs per report, decision time (median and 99th percentile, with the machine named). Identical candidate allocations are not treated
as evidence that the allocation meets the safety objective: acceptance also needs the requirement check R1 to R3, and outcomes are always judged by the scorer.

## 8. Order of work and checks

1. Approve this plan (main chat, user). Set `STATUS: FROZEN-READY`. Run `python tools/freeze_plan.py`. Send the printed hash and time to the supervisors by email.
2. `python tools/gen_episodes_fresh.py --seed 20261201 --cal-episodes 40 --eval-episodes 1100 --out fresh` (CPU, no model).
3. Copy `fresh/cases_fresh.jsonl` to the GPU computer. Run `tools/extract_fresh_vectors.py` (exact command in the script header). It stops at the first FAIL.
4. Bring `fresh/vectors/` back. `python tools/run_fresh.py --cases fresh/cases_fresh.jsonl --vectors fresh/vectors --check-only`, then `--tag all`.
5. `python tools/analyze_dev.py --base fresh --tag main` (and the other tags). Demo cases by the rule in section 10.
6. Data checks allowed before arms are compared: extraction manifest OK; the cosine checks; the gold-record miss rate per level (reported, not re-tuned); realised request rates.
7. **One run.** A repeat needs `--rerun-reason`, keeps the old files and is written to `results/fresh/RUN_LOG.json` as a deviation. No interim looks, no early stopping.
8. Exclusions: none planned. A missing or non-finite vector stops the run; it is not dropped.

## 9. Deviations from STRENGTHENING_PLAN carried into this run (details in `docs/DEVIATIONS.md`)

* **D-01 Episodes.** Plan section 5: an episode has an initial belief table and a stream of 12 reports conditioned on its gold state. Built here: 20 independent reports,
  each with its own open table and incidents, arriving over time and **sharing one fleet** (overlay episodes). Reports do not influence each other's belief tables.
  Chain-mode episodes and closed-loop prompts are not built and stay untested.
* D-02 FIT is the 1,000 development style-A reports (saved vectors), not 200 new episodes; CAL is fresh.
* D-03 The record that is committed or explored is r-hat = the pilot's hierarchical record (argmax of each head) for all arms, not the joint-score top (they differ in 0.4% of reports).
* D-04 At most 20 combinations per report (the plan's 22 counts CREATE and UPDATE twice).
* D-05 Extra outcome class FALLBACK_PARTIAL and extra decision TIMEOUT (a decision needing more simulated time than 5 s).
* D-06 Arms A6b, A8c, A12 and OBS are additions. A8c was designed after development outcomes were seen.
* D-07 Dev-only: families are folded and exact duplicates are purged from FIT (a giant duplicate component links 950 of 1,000 reports).
* D-08 Requirement R3 means "no active task is left without a UAV" (the plan's wording is about how records are applied).
* D-09 The execution signature also lists the tasks that nobody could take (a stricter certificate).
* D-10 Gate thresholds come from observer runs on CAL; risk scores are compared as tuples; ties are broken by a fixed hash; the hard cap is 2 requests per 20-report episode.
* D-11 The realised request rate is 7.2% to 7.7%, not 10%, because of the cap. The arms are matched to each other, not to b (open decision D6 of the evidence file).
* D-12 Computation is charged in simulated time (0.02 s per allocator run, 5 s time-out). Wall time is measured on the machine that runs the analysis.
* D-13 Contention is tuned by the report gaps only. Scenario types are not tagged.
* D-14 Paired differences use 10,000 bootstrap resamples; per-arm intervals use 2,000.
* D-15 Milestone M0 is not complete: the laptop run of the audit scripts, the gguf re-hash and `git init` must be done before the freeze.

## 10. Demonstration cases (rule fixed before selection; plan section 8.6)

For each outcome class, the first evaluation episode by id that contains it; plus the first episode where A8 misses an incident that A6 verifies (a failure case).
`demo.py` prints the report, the open table, the candidates with scores, each candidate's execution signature, the decision, the outcome and the cost.

## 11. Open decisions (the implementation chat will not decide these)

* **D1 Primary comparison.** Recommended: keep A8 vs A6 (the pre-registered one) and report A8c vs A6 as S1. Alternative: make A8c vs A6 primary; that needs a deviation note,
  because A8c was designed after the development outcomes.
* **D2 Sample size.** N_e = 1,100 (plan rule, about 80% power, about 2 h GPU) or fewer (less power). Decide before the freeze.
* **D3 Include the stress test (S7) and the style-B check (S9)?** Recommended yes, both labelled diagnostic / exploratory.
* **D4 Kill criterion** (plan section 9). Development: certified non-singleton sets are 8.9% of reports at M (10.6% at L, 6.2% at H; limit: 3%), so the rule is **not triggered by its letter**, but A8 does not
  beat A6. If you read the rule by its intent, the paper becomes the measurement-and-diagnostic study. Please decide how the paper will describe the Shield result.
* **D5 Settings.** alpha, K, b, d_v, deadlines (section 3) and the supervisors' answers to plan section 12.

<!-- PARAMS-BEGIN -->
```json
{
  "fresh_seed": 20261201,
  "cal_episodes": 40,
  "eval_episodes": 1100,
  "R": 20,
  "alpha": 0.10,
  "K": 8,
  "b": 0.10,
  "d_v": 60.0,
  "alloc_cost_s": 0.02,
  "decision_timeout_s": 5.0,
  "dwell_s": 12.0,
  "deadlines_s": {"1": 480, "2": 360, "3": 240},
  "level_gap_s": {"L": 60.0, "M": 30.0, "H": 8.0},
  "allocator_default": "cbba_bounded",
  "primary": {"run": "main", "level": "M", "x": "A8", "y": "A6", "metric": "U_deadline", "bootstrap": 10000, "test": "paired sign-flip, two-sided, 0.05"},
  "runs": {
    "main": {"readout": "q4", "levels": ["M", "H", "L"], "arrival_seeds": [1]},
    "raw": {"readout": "raw", "levels": ["M", "H"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A6b", "A7", "A8", "A8c", "A9", "A10", "A12", "OBS"]},
    "legacy": {"allocator": "legacy_greedy_s1", "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "seed2": {"levels": ["M"], "arrival_seeds": [2], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "seed3": {"levels": ["M"], "arrival_seeds": [3], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "a05": {"alpha": 0.05, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "a20": {"alpha": 0.20, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "b05": {"b": 0.05, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "b20": {"b": 0.20, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "b30": {"b": 0.30, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "K4": {"K": 4, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "dv30": {"d_v": 30.0, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "dv120": {"d_v": 120.0, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "ac02": {"alloc_cost_s": 0.2, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "ac10": {"alloc_cost_s": 1.0, "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]},
    "sb": {"eval_set": "style_b", "hold": true, "readout": "q4", "levels": ["M"], "arrival_seeds": [1], "arms": ["A0", "A1", "A6", "A8", "A8c", "A10", "A12", "OBS"]}
  }
}
```
<!-- PARAMS-END -->
