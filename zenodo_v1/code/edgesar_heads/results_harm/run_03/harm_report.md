# EdgeSAR harm test: results (EXPLORATORY)

Made: 2026-11-12 18:34:49. Run folder: `run_03`. Plan: `HARM_TEST_PLAN.md` (frozen, fingerprint 2e791175a4fa). Main split: held-out style B = 400 reports, 40 families, 752 real incidents.

**What this is.** Every system's saved record for a report is given to the same allocator (simplified CBBA, 3 UAVs). A simulator then says which real incidents get verified by the 600 s horizon. The reference is a run with the **correct (gold) record** for the same report. The reference is not an optimal planner. **What this is not:** a closed-loop mission, full CBBA, a test of Shield or Cover (those are planned, not implemented), or a confirmation. Style B was already seen, so everything here is exploratory.

**Checks before the run:** plan fingerprint matches; allocator fingerprints match; predictions fingerprint matches; pilot files are the frozen ones; round-trip: all 21000 saved records agree with their record_ok flag; every one of the 15 systems has one record for each of the 1400 reports; reference compared with itself: no change at all; two identical runs (reference and Heads Q4) give identical results; bootstrap-head records round-trip OK (40000 rows); file not pinned in the plan.

## 1. Main result: real incidents not verified by 600 s (held-out B)

U = unverified real incidents / real incidents. dU = U(system) - U(gold-record reference), in percentage points. Intervals are 95% family-bootstrap intervals over **40 families** (paired with the reference). V->U = verified with the gold record but not with the system's record. U->V = the opposite.

| System | Unverified | U | dU vs reference (pp) | V->U | U->V | Unverified in both (resource-limited) |
|---|---|---|---|---|---|---|
| GOLD-RECORD (reference) | 0 of 752 | 0.0% (0.0% to 0.0%) | 0 | - | - | - |
| Heads FP16 | 15 of 752 | 2.0% (1.0% to 3.2%) | +2.0 (+1.0 to +3.2) | 15 | 0 | 0 |
| Heads Q8 | 16 of 752 | 2.1% (1.0% to 3.5%) | +2.1 (+1.0 to +3.5) | 16 | 0 | 0 |
| Heads Q4 | 13 of 752 | 1.7% (0.8% to 2.8%) | +1.7 (+0.8 to +2.8) | 13 | 0 | 0 |

'Unverified in both' are incidents the allocator could not verify even with the correct record (too few UAVs, camera limits, time). They are not caused by a record. Here the gold-record reference verified **all 752 real incidents** on B, so there are no resource-limited misses: every miss below comes from a record.

## 2. Does the precision change what happens? (system against system, held-out B)

| First -> second | dU (pp) | V->U | U->V | L0 record | L1 table | L2 assignment | L3 route | L4 verification | Absorbed / consequential |
|---|---|---|---|---|---|---|---|---|---|
| Heads FP16 -> Heads Q8 | +0.1 (-0.7 to +1.1) | 5 | 4 | 71 | 71 | 41 | 43 | 40 | 31 / 40 |
| Heads FP16 -> Heads Q4 | -0.3 (-1.1 to +0.5) | 5 | 7 | 110 | 110 | 65 | 67 | 49 | 61 / 49 |
| Heads Q8 -> Heads Q4 | -0.4 (-1.7 to +0.8) | 6 | 9 | 114 | 114 | 83 | 84 | 67 | 47 / 67 |
| Heads Q4 -> Shared head on Q4 vectors | -0.4 (-0.9 to +0.0) | 0 | 3 | 78 | 78 | 50 | 51 | 38 | 40 / 38 |
| Heads Q4 -> FP16-trained heads on Q4 vectors, offset removed | +0.7 (-0.5 to +2.0) | 11 | 6 | 152 | 151 | 101 | 102 | 76 | 75 / 76 |
| Heads FP16 -> FP16-trained heads on Q4 vectors | +16.8 (+14.8 to +18.8) | 126 | 0 | 190 | 189 | 171 | 171 | 165 | 24 / 165 |
| Generative FP16 -> Generative Q8 | +0.4 (-0.3 to +1.2) | 7 | 4 | 33 | 26 | 24 | 25 | 17 | 9 / 17 |
| Generative FP16 -> Generative Q4 | -1.9 (-3.4 to -0.5) | 5 | 19 | 139 | 108 | 63 | 68 | 47 | 61 / 47 |

dU here = U(second) - U(first). Levels are counts of reports (out of 400) where that level differs between the two systems. Absorbed = the task table differs but no verification changes; consequential = the table differs and a verification changes (a verification time moves by more than 0.5 s, or a miss appears or disappears).

## 3. Secondary outcomes (held-out B, each separately)

Delay = system minus reference, in seconds, over incidents verified in **both** runs (the count is shown; unverified incidents are in section 1, not hidden). Brackets = 95% family-bootstrap interval of that system's own value (not of a difference). RMIVT = mean verification time with a miss counted as 600 s (the `mission.py` convention). Trips = empty + wrong-camera visits per report. Distance = metres flown per report.

| System | Paired delay (s) | RMIVT (s) | Trips / report | Distance (m) / report | Verification time of verified: median / p90 (s) | Compute ms (median) |
|---|---|---|---|---|---|---|
| GOLD-RECORD (reference) | - | 84.5 (81.9 to 86.9) | 0.00 (0.00 to 0.00) | 2101 (1940 to 2261) | 75.9 / 130.1 | 0.02 |
| Heads FP16 | 3.5 s (1.8 to 5.3) (n=737) | 98.6 (92.9 to 104.9) | 0.14 (0.10 to 0.18) | 2230 (2061 to 2398) | 82.0 / 142.0 | 0.02 |
| Heads Q8 | 4.7 s (2.8 to 6.6) (n=736) | 100.3 (94.2 to 107.4) | 0.18 (0.14 to 0.22) | 2272 (2111 to 2434) | 82.0 / 148.0 | 0.02 |
| Heads Q4 | 3.5 s (1.9 to 5.2) (n=739) | 96.9 (91.4 to 103.3) | 0.20 (0.16 to 0.24) | 2288 (2116 to 2449) | 82.0 / 142.0 | 0.02 |
| FP16-trained heads on Q8 vectors | 3.2 s (1.8 to 4.6) (n=742) | 94.7 (90.9 to 98.8) | 0.17 (0.12 to 0.21) | 2256 (2095 to 2414) | 82.0 / 142.0 | 0.02 |
| FP16-trained heads on Q4 vectors | 0.4 s (-1.8 to 2.6) (n=611) | 182.0 (170.3 to 194.2) | 0.14 (0.10 to 0.18) | 1874 (1711 to 2030) | 75.9 / 130.1 | 0.01 |
| FP16-trained heads on Q8 vectors, offset removed | 3.8 s (2.2 to 5.5) (n=736) | 99.5 (94.3 to 105.6) | 0.16 (0.12 to 0.20) | 2255 (2092 to 2418) | 81.7 / 142.6 | 0.02 |
| FP16-trained heads on Q4 vectors, offset removed | 3.8 s (2.2 to 5.7) (n=734) | 100.7 (93.8 to 108.7) | 0.26 (0.21 to 0.31) | 2353 (2176 to 2527) | 85.5 / 142.0 | 0.02 |
| Shared head on FP16 vectors | 3.9 s (2.1 to 5.6) (n=737) | 98.8 (92.8 to 105.5) | 0.14 (0.10 to 0.17) | 2229 (2059 to 2397) | 82.0 / 142.0 | 0.02 |
| Shared head on Q8 vectors | 3.5 s (1.9 to 5.3) (n=736) | 99.2 (93.1 to 106.5) | 0.14 (0.10 to 0.18) | 2228 (2070 to 2386) | 81.7 / 142.0 | 0.02 |
| Shared head on Q4 vectors | 3.6 s (1.7 to 5.7) (n=742) | 94.9 (90.0 to 100.2) | 0.18 (0.14 to 0.23) | 2285 (2116 to 2455) | 82.0 / 142.0 | 0.02 |

Compute time depends on this computer and is only descriptive. Incidents whose verification ended after 600 s (counted as unverified): Heads FP16 0, Heads Q8 0, Heads Q4 0; reference 0.

## 4. Absorbed and consequential record changes (held-out B, against the gold-record reference)

| System | Record differs from gold | Task table differs | Absorbed | Consequential | Absorbed share of table changes | Harmful by the 30 s rule (exploratory) |
|---|---|---|---|---|---|---|
| Heads FP16 | 117 | 117 | 48 | 69 | 41% | 46 of 400 |
| Heads Q8 | 127 | 127 | 51 | 76 | 40% | 57 of 400 |
| Heads Q4 | 134 | 134 | 64 | 70 | 48% | 45 of 400 |
| FP16-trained heads on Q8 vectors | 137 | 137 | 72 | 65 | 53% | 43 of 400 |
| FP16-trained heads on Q4 vectors | 210 | 210 | 32 | 178 | 15% | 169 of 400 |
| FP16-trained heads on Q8 vectors, offset removed | 122 | 122 | 53 | 69 | 43% | 51 of 400 |
| FP16-trained heads on Q4 vectors, offset removed | 169 | 168 | 79 | 89 | 47% | 56 of 400 |
| Shared head on FP16 vectors | 108 | 108 | 46 | 62 | 43% | 45 of 400 |
| Shared head on Q8 vectors | 105 | 105 | 41 | 64 | 39% | 48 of 400 |
| Shared head on Q4 vectors | 134 | 134 | 64 | 70 | 48% | 43 of 400 |

The 30 s rule is from `funnel.py` (`HARM_SECONDS = 30.0`, chosen by me after seeing the pilot cases). It is **exploratory**. 'Harmful' = a new miss, or an incident verified at least 30 s later than in the reference.

## 5. Secondary systems: fixed head, offset removed, shared head (held-out B)

| System | U | dU vs reference (pp) | V->U | U->V | Task table differs | Consequential |
|---|---|---|---|---|---|---|
| FP16-trained heads on Q8 vectors | 1.3% (0.7% to 2.1%) | +1.3 (+0.7 to +2.1) | 10 | 0 | 137 | 65 |
| FP16-trained heads on Q4 vectors | 18.8% (16.4% to 21.1%) | +18.8 (+16.4 to +21.1) | 141 | 0 | 210 | 178 |
| FP16-trained heads on Q8 vectors, offset removed | 2.1% (1.1% to 3.4%) | +2.1 (+1.1 to +3.4) | 16 | 0 | 122 | 69 |
| FP16-trained heads on Q4 vectors, offset removed | 2.4% (1.2% to 3.9%) | +2.4 (+1.2 to +3.9) | 18 | 0 | 168 | 89 |
| Shared head on FP16 vectors | 2.0% (0.9% to 3.3%) | +2.0 (+0.9 to +3.3) | 15 | 0 | 108 | 62 |
| Shared head on Q8 vectors | 2.1% (1.0% to 3.5%) | +2.1 (+1.0 to +3.5) | 16 | 0 | 105 | 64 |
| Shared head on Q4 vectors | 1.3% (0.5% to 2.3%) | +1.3 (+0.5 to +2.3) | 10 | 0 | 134 | 70 |

## 6. The 20 bootstrap-sample heads (held-out B)

Each head was trained on a bootstrap sample of the dev families and tested on the **same** B reports. They are not 20 independent datasets, so only the spread is shown (mean, lowest, highest over heads). 'Offset' = the constant offset removed from the Q vectors first.

| Vectors | Heads | U mean (lowest to highest) | dU pp | V->U | U->V |
|---|---|---|---|---|---|
| FP16 | 20 | 2.4% (1.5% to 3.2%) | +2.4 (+1.5 to +3.2) | 18.1 (11 to 24) | 0.0 (0 to 0) |
| Q8 | 20 | 1.8% (1.3% to 2.4%) | +1.8 (+1.3 to +2.4) | 13.5 (10 to 18) | 0.0 (0 to 0) |
| Q4 | 20 | 17.3% (10.5% to 24.6%) | +17.3 (+10.5 to +24.6) | 130.4 (79 to 185) | 0.0 (0 to 0) |
| Q8-offset | 20 | 2.4% (1.6% to 3.7%) | +2.4 (+1.6 to +3.7) | 18.3 (12 to 28) | 0.0 (0 to 0) |
| Q4-offset | 20 | 2.6% (2.0% to 3.2%) | +2.6 (+2.0 to +3.2) | 19.8 (15 to 24) | 0.0 (0 to 0) |

## 7. Context systems (held-out B)

| System | U | dU vs reference (pp) | V->U | U->V | Task table differs | Consequential |
|---|---|---|---|---|---|---|
| Generative FP16 | 11.0% (8.8% to 13.6%) | +11.0 (+8.8 to +13.6) | 83 | 0 | 248 | 146 |
| Generative Q8 | 11.4% (9.0% to 13.9%) | +11.4 (+9.0 to +13.9) | 86 | 0 | 246 | 149 |
| Generative Q4 | 9.2% (7.5% to 11.2%) | +9.2 (+7.5 to +11.2) | 69 | 0 | 246 | 136 |
| TF-IDF + LR | 4.0% (2.5% to 5.6%) | +4.0 (+2.5 to +5.6) | 30 | 0 | 157 | 88 |
| Rule engine | 10.2% (8.1% to 12.5%) | +10.2 (+8.1 to +12.5) | 77 | 0 | 197 | 115 |

The generative rows are the pilot's text writer (the EdgeSAR design). They are shown for comparison only.

## 8. Development style A (descriptive)

Who was fitted on style A matters. Heads and shared heads: out-of-fold by family (fair). Generative models: nothing is trained on A (fair). TF-IDF + LR: cross-validated by the pilot code. **Rule engine: written while style A was visible, so its result on A is not a fair test.** Style A is the easier style. Do not compare A with B as if they were the same test.

Reference U on A: 0.0% (0.0% to 0.0%) (100 families).

| System | U | dU vs reference (pp) | V->U | U->V |
|---|---|---|---|---|
| Heads FP16 | 0.1% (0.0% to 0.2%) | +0.1 (+0.0 to +0.2) | 1 | 0 |
| Heads Q8 | 0.1% (0.0% to 0.3%) | +0.1 (+0.0 to +0.3) | 2 | 0 |
| Heads Q4 | 0.6% (0.3% to 1.0%) | +0.6 (+0.3 to +1.0) | 11 | 0 |
| FP16-trained heads on Q8 vectors | 0.2% (0.0% to 0.4%) | +0.2 (+0.0 to +0.4) | 3 | 0 |
| FP16-trained heads on Q4 vectors | 16.3% (14.9% to 17.5%) | +16.3 (+14.9 to +17.5) | 299 | 0 |
| FP16-trained heads on Q8 vectors, offset removed | 0.1% (0.0% to 0.3%) | +0.1 (+0.0 to +0.3) | 2 | 0 |
| FP16-trained heads on Q4 vectors, offset removed | 0.9% (0.5% to 1.4%) | +0.9 (+0.5 to +1.4) | 17 | 0 |
| Shared head on FP16 vectors | 0.1% (0.0% to 0.2%) | +0.1 (+0.0 to +0.2) | 1 | 0 |
| Shared head on Q8 vectors | 0.0% (0.0% to 0.0%) | +0.0 (+0.0 to +0.0) | 0 | 0 |
| Shared head on Q4 vectors | 0.3% (0.1% to 0.6%) | +0.3 (+0.1 to +0.6) | 6 | 0 |
| Generative FP16 | 10.0% (8.7% to 11.4%) | +10.0 (+8.7 to +11.4) | 184 | 0 |
| Generative Q8 | 10.2% (8.9% to 11.4%) | +10.2 (+8.9 to +11.4) | 187 | 0 |
| Generative Q4 | 9.2% (8.0% to 10.3%) | +9.2 (+8.0 to +10.3) | 168 | 0 |
| TF-IDF + LR | 0.0% (0.0% to 0.0%) | +0.0 (+0.0 to +0.0) | 0 | 0 |
| Rule engine | 0.0% (0.0% to 0.0%) | +0.0 (+0.0 to +0.0) | 0 | 0 |

## 9. Smallest fresh-family evaluation (approximate, from the spread seen here)

| Contrast | dU now (pp) | Half-width now (pp) | Families needed for +/- 2 pp |
|---|---|---|---|
| Heads FP16 vs reference | +2.0 | +/- 1.1 | 12 |
| Heads Q8 vs reference | +2.1 | +/- 1.3 | 17 |
| Heads Q4 vs reference | +1.7 | +/- 1.0 | 11 |
| Heads FP16 -> Heads Q4 | -0.3 | +/- 0.8 | 7 |
| Heads FP16 -> Heads Q8 | +0.1 | +/- 0.9 | 8 |

Approximate: F_needed = F_now x (half-width now / 2 pp)^2, assuming similar spread per family. A number below 40 means the interval is already narrower than +/- 2 points; '-' means the interval has no width (nothing to scale). The confirmation uses fresh families from a new generator seed, fresh hidden-state extraction, and arms and settings frozen first. If Shield is used, it is recalibrated on separate data.

## 10. Post-run look (NOT in the frozen plan; added after the first run; descriptive only)

Which kind of record change caused the incidents that were verified with the gold record but not with the system's record (V->U), held-out B. The numbers in each row add up to the V->U column of section 1.

| System | V->U | Largest groups |
|---|---|---|
| Heads FP16 | 15 | 7 x gold CREATE, system NO_ACTION (missed alarm); 7 x gold UPDATE, system CLOSE (wrong close); 1 x gold NO_ACTION, system CLOSE (wrong close) |
| Heads Q8 | 16 | 9 x gold CREATE, system NO_ACTION (missed alarm); 5 x gold UPDATE, system CLOSE (wrong close); 2 x gold NO_ACTION, system CLOSE (wrong close) |
| Heads Q4 | 13 | 10 x gold CREATE, system NO_ACTION (missed alarm); 1 x gold NO_ACTION, system CLOSE (wrong close); 1 x gold UPDATE, system CLOSE (wrong close); 1 x gold UPDATE, system NO_ACTION |
| FP16-trained heads on Q8 vectors | 10 | 9 x gold CREATE, system NO_ACTION (missed alarm); 1 x gold NO_ACTION, system CLOSE (wrong close) |
| FP16-trained heads on Q4 vectors | 141 | 92 x gold CREATE, system NO_ACTION (missed alarm); 31 x gold NO_ACTION, system CLOSE (wrong close); 18 x gold UPDATE, system CLOSE (wrong close) |
| FP16-trained heads on Q8 vectors, offset removed | 16 | 9 x gold CREATE, system NO_ACTION (missed alarm); 6 x gold UPDATE, system CLOSE (wrong close); 1 x gold NO_ACTION, system CLOSE (wrong close) |
| FP16-trained heads on Q4 vectors, offset removed | 18 | 8 x gold CREATE, system NO_ACTION (missed alarm); 7 x gold UPDATE, system CLOSE (wrong close); 3 x gold NO_ACTION, system CLOSE (wrong close) |
| Shared head on FP16 vectors | 15 | 8 x gold CREATE, system NO_ACTION (missed alarm); 5 x gold UPDATE, system CLOSE (wrong close); 2 x gold NO_ACTION, system CLOSE (wrong close) |
| Shared head on Q8 vectors | 16 | 9 x gold CREATE, system NO_ACTION (missed alarm); 6 x gold UPDATE, system CLOSE (wrong close); 1 x gold NO_ACTION, system CLOSE (wrong close) |
| Shared head on Q4 vectors | 10 | 7 x gold CREATE, system NO_ACTION (missed alarm); 1 x gold NO_ACTION, system CLOSE (wrong close); 1 x gold UPDATE, system CLOSE (wrong close); 1 x gold UPDATE, system NO_ACTION |
| Generative FP16 | 83 | 39 x gold CREATE, system UPDATE; 26 x gold UPDATE, system UPDATE; 7 x gold NO_ACTION, system UPDATE; 5 x gold CREATE, system CREATE |
| Generative Q8 | 86 | 39 x gold CREATE, system UPDATE; 26 x gold UPDATE, system UPDATE; 5 x gold CREATE, system CREATE; 5 x gold NO_ACTION, system CLOSE (wrong close) |
| Generative Q4 | 69 | 34 x gold CREATE, system UPDATE; 24 x gold UPDATE, system UPDATE; 5 x gold CREATE, system CREATE; 3 x gold NO_ACTION, system UPDATE |
| TF-IDF + LR | 30 | 26 x gold CREATE, system NO_ACTION (missed alarm); 4 x gold UPDATE, system CLOSE (wrong close) |
| Rule engine | 77 | 77 x gold CREATE, system NO_ACTION (missed alarm) |

'Missed alarm' = a new real incident ignored. 'Wrong close' = a real incident removed from the table. These match the rough 'danger error' proxies of the controls report, but here they are counted by what happens in the simulator.

## 11. Limits

* Single-record fork-and-replay with a simplified CBBA (bundle size 1, perfect messages, no random parts). Not a closed-loop mission, and the result may not carry over to full CBBA, many reports over time, or message loss.
* Truth is the gold table. All tasks are known at t = 0. UAVs fly straight lines. Only 3 UAVs and 12 landmarks.
* Held-out B has 40 families. Intervals are wide, and B was already seen, so nothing here is confirmatory.
* Records come from one set of trained heads per precision. Head-to-head differences include head-training variability (see section 6 and `CONTROLS_PLAN.md`); a difference between Heads FP16 and Heads Q4 is not a pure quantization effect.
* The offset is fitted on dev A vectors, label-free. Its 'share explained' is about the vector, not about errors repaired.
* Candidate sets, the Shield gate and Cover are NOT implemented. Nothing here tests them.
* The priorities used (unverified incidents first, then delay, then trips) are an evaluation choice pending supervisor review.
