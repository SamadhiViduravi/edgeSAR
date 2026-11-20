# EdgeSAR Iteration 1: one bounded development round (written BEFORE any run)

Status: FIXED. Date written: 2026-11-13. This file is hashed before the first iteration-1 run (`results/iter1/PROTOCOL.sha256`).
Data: DEVELOPMENT only (1,000 style-A reports, saved vectors, 5 family folds, overlay episodes). No fresh case is generated or read.
Old results, old arms (A0-A12) and the old cache are NOT changed. Everything new goes to `results/iter1/`.

## 1. Why this round

The evidence so far: the competent Q4 head gives 7.4% missed incidents (level M); the confidence gate 7.1%; the plan's Shield (A8) 8.2%;
the location-cover variant (A8c) 7.0% (post-hoc). The Shield finds risky reports better than the gate (AUROC 0.904 vs 0.874) but its
fallback (cover) costs other incidents time. Main chat priorities 1-5 for this round:

1. fallback congestion and delay (cost to OTHER pending incidents, runtime information only)
2. requirements (deadline, camera) under EVERY candidate, not only under the committed record
3. unsupported interpretations and missing-candidate failures made explicit (agreement inside an incomplete set is not safety)
4. equal-footing comparators: gate with the same fallback and the same verification cap; Q4 no gate; recentred; FP16; Q8
5. real latency and memory on the user's PC (script prepared; numbers need his hardware)

## 2. The variants (all defined now; nothing is added after results are seen)

Common to all: same heads, same conformal set (alpha 0.10, K = 8), same verification cap b = 10% (2 per 20-report episode), d_v = 60 s,
0.02 s simulated cost per allocator run, 5 s timeout, same episodes, same budget-matching rule for the escalation threshold (theta, xi) on CAL.

| Arm | What it is |
|---|---|
| B1 | A8 + **strict candidate check**: certified only if all candidates give the same execution signature AND every candidate has the same feasibility status when its plan is checked against ITS OWN task (its priority gives its own deadline, its camera its own R1). A mix of feasible and infeasible candidates is NOT certified (reason FEASIBILITY_DIFFERS). Cover is the plan's full cover. |
| B2 | B1 + **mass guard**: certified also needs the conformal set's score mass M(C) >= 1 - alpha (= 0.90). Otherwise reason LOW_MASS. If the plans and feasibility agree and only the mass is low, covering cannot help (all candidates already give the same plan), so: escalate if the risk gate allows, else commit r-hat as **UNSUPPORTED_COMMIT** (counted and shown as unresolved). |
| B3 (= "Shield-2", the candidate method) | B2 + **cost-aware fallback**: for a report that needs a fallback, evaluate (a) committing r-hat, (b) the full cover, (c) the location cover (A8c style). Fleet-wide count of predicted unmet requirements n_bad = |R1 U R2 U R3| over ALL pending tasks of ALL reports (believed deadlines, runtime information only). Take the full cover if n_bad(full) <= n_bad(r-hat); else the location cover if n_bad(loc) <= n_bad(r-hat); else commit r-hat as **COVER_DECLINED**. ("do no predicted harm") |
| B4 | B1 + the same cost-aware fallback, without the mass guard (isolates the mass guard) |
| G1 | **Equal-footing gate**: same trigger score as A6 (low pilot confidence), two thresholds. (i) ESCALATE when the confidence risk is above the A6 threshold (rate b on CAL) and the cap allows. (ii) Otherwise FALLBACK when the confidence risk is above a second threshold set on CAL so that G1 flags the same share of reports as B3 flags (not certified); the fallback is the SAME cost-aware fallback as B3 (r-hat vs full cover vs location cover, same n_bad rule) on the same conformal set. (iii) Otherwise commit r-hat. Same allocator-run accounting and the same cap of 2 verifications per episode. The only difference to B3 is the trigger: confidence score instead of candidate set + execution signatures + checks. |
Existing arms in the same run: A0 gold, A1 Q4 no gate, A2 FP16, A3 Q8, A4 recentred Q4, A6 gate (verification only), A8, A8c, A10, A12 (oracle, diagnostic), OBS.
B-arms and G1 also run on three more readouts, as separate tags: FP16 (`f16`), Q8 (`q8`), and the mismatched frozen head (`raw`, diagnostic).

Escalation risk for B1-B4: (rho_total, 1 - top score), rho_total = 1 - sum of scores of the candidates in C that have the same signature as r-hat and the same
feasibility as r-hat (0 for certified reports). The (theta, xi) rule is the old one (CAL, hash tie-break, cap 2 per episode).

## 3. Primary comparison and decision rule (fixed now)

Metric: missed share = (late + unverified) / incidents, level M, readout Q4, 3 arrival seeds pooled, paired by episode, 95% episode-bootstrap CI
(pooled CIs are optimistic because seeds reuse the same reports; per-seed numbers are shown too).

* P1 (primary): B3 minus G1.
* P2: B3 minus A1 (no gate). P3: B3 minus A8 (old Shield). Levels L and H, and costs, are secondary.

Outcome labels, decided by the numbers only:

* **SUPPORTED on DEV**: CI(B3 - G1) upper bound < 0 AND CI(B3 - A1) upper bound < 0 at level M, and point estimates <= 0 at L and H.
* **NOT SHOWN**: anything else with CI(B3 - A1) containing 0, or B3 within +-0.3 pp of G1 (a tie). Report honestly as a risk monitor / measurement.
* **HARMFUL on a competent head**: CI(B3 - A1) lower bound > 0. Report as a failure; do not freeze B3 as a safety method.

Separately and descriptively: the same arms on the mismatched head (`raw`) show what the method does when quantisation really breaks the readout.

## 4. Stopping rule

* This round runs each variant ONCE. No parameter (alpha, K, the 0.90 mass limit, the n_bad rule, b) is changed after seeing results.
* If the label is NOT SHOWN or HARMFUL: no second round of mechanisms. The paper uses the honest story (risk monitor / measurement); the frozen method for the fresh test is chosen by the main chat and the supervisors from the table, not by more tuning.
* A bug is different from tuning: if the code is found to differ from the text of section 2, the code is fixed, the fix is listed in docs/DEVIATIONS.md, and ALL arms are rerun; results of the buggy run stay on disk, labelled.
* A second round needs written approval and gets its own protocol file.
* No fresh data are generated or looked at in this round.

## 5. Sample size (after the arms are fixed)

Computed from DEV paired standard deviations of the per-episode difference (B3-G1, B3-A1), for effects 0.5 / 0.75 / 1.0 / 1.5 percentage points of missed share, 80% and 90% power,
and an episode-count correction for the correlation caused by seeds. Delivered as a table; the final number is decided by the main chat before freezing.

## 6. What is NOT done here

Fresh GPU run; CPU timing on the user's PC (script only); verification queue; OSF; slides; paper.
