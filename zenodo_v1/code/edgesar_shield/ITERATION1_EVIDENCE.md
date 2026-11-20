# EdgeSAR iteration 1: evidence (development data only)

Written 2026-11-13 by the implementation chat. Protocol: `docs/ITERATION1_PROTOCOL.md`, SHA-256 `1ccce486d3935d6a7c5b49567648ee807973962ca55ccc99b15a00dcb43f7795` (hashed before the first run). Old results, old arms and the old cache are unchanged (`tests/test_iter1.py` checks that A1, A6, A8, A8c, A10 give exactly the old incident counts). **No fresh case was generated or read. This is not a confirmation.** Pooled intervals are optimistic: the three arrival seeds re-use the same 1,000 reports.

## 0. Short answer

1. **Label by the rule fixed in advance: NOT SHOWN** (competent Q4 head, level M). Shield-2 (B3) minus equal-footing confidence gate (G1) = +0.07 pp (95% CI -0.44 to +0.61); B3 minus always commit (A1) = +0.40 pp (95% CI -0.32 to +1.15). No second round of mechanisms follows from this (stopping rule, protocol section 4).
2. **What improved.** (a) The certificate is much safer: certified-and-wrong plan 2.23% -> 0.40%, certified-and-wrong table 5.83% -> 0.63% (A8 -> B3, level M), at the price of flagging 48% instead of 34% of the reports. (b) The cost-aware fallback removes harm done by the plan's full cover: B3 minus B2 = -0.76 pp (95% CI -1.11 to -0.44). (c) When the head is NOT adapted to Q4 (frozen FP16 head on Q4 vectors) Shield-2 cuts the missed share from 16.5% to 9.1%, and beats the equal-footing gate (11.2%): B3 minus G1 = -2.03 pp (95% CI -2.72 to -1.38).
3. **What did not improve.** With a competent Q4 head nothing beats always committing: the best any gate could do (oracle, A12) is -0.47 pp (95% CI -1.07 to +0.13), and every real arm is inside the noise or worse than A1. The pre-specified B3 (7.81%) is worse than the post-hoc A8c (7.05%) of iteration 0 at level M, and also on the unadapted head (9.12% vs 8.16%); the mass guard alone and the strict check alone change nothing in the missed share.
4. **Quantisation does cost something, even when the head is retrained for it.** Q4 minus FP16 = +1.11 pp (95% CI +0.47 to +1.77) at M (L: +0.60 pp (95% CI +0.20 to +1.01); H: +1.05 pp (95% CI +0.31 to +1.80)). Q8 minus FP16 = +0.20 pp (95% CI -0.28 to +0.69) at M.
5. **Most of the harm of a quantised model comes from using a head that was not adapted to it, and cheap adaptation removes most of it:** unadapted Q4 16.5%, recentred (no labels) 8.0%, retrained on Q4 vectors 7.4%, FP16 6.3%, gold records 4.9% (level M). Shield-2 on the unadapted head gives 9.1%.
6. **Not measured:** speed and memory of llama.cpp on Samadhi's computer (script ready, needs his machine); fresh data; chain-mode episodes; the Shield on the recentred head.

## 1. The five priorities: what was built, what came out

| # | priority | built (new files only) | result |
|---|---|---|---|
| 1 | fallback congestion and delay | `policy2.ShieldV2(cost_aware=True)`: the fallback is chosen by the predicted number of unmet requirements over ALL pending tasks of ALL reports (believed deadlines; runtime information only): full cover, else location cover, else commit r-hat (COVER_DECLINED) | B3 - B2 = -0.76 pp (95% CI -1.11 to -0.44) at M, -1.16 pp (95% CI -1.54 to -0.80) at H. Lowers the harm of the full cover; does not reach 'no worse than always commit' with a competent head |
| 2 | requirements under every candidate | `assess2`: each candidate's plan is checked against its own task (own priority -> own deadline, own camera); certified needs one signature AND one feasibility status | certified-and-wrong plan 2.23% -> 0.40% with the mass guard; the strict check alone moves it only 2.23% -> 2.17% (B1); missed share unchanged (B1 - A8 = +0.33 pp (95% CI +0.00 to +0.67)) |
| 3 | unsupported interpretations, missing candidates | mass guard (set mass >= 1 - alpha); class UNSUPPORTED_COMMIT (visible, unresolved, no cover because a cover cannot serve mass outside the set); EMPTY / OVERSIZE / R-hat-outside already uncertified | certified share 65.8% -> 52.3%; 398 reports at M ended as UNSUPPORTED_COMMIT; B2 - B1 = +0.02 pp (95% CI -0.11 to +0.17) (no change in misses) |
| 4 | equal-footing comparators | G1 (confidence gate, same cap, same cost-aware fallback, same flag rate as B3 on CAL); A1; A4 recentred; A2 FP16; A3 Q8; also all arms on FP16, Q8 and the unadapted head | sections 4 and 5 |
| 5 | latency and memory on his computer | `tools/bench_local.py` (llama.cpp per precision, heads, Shield, memory) | script tested here against a fake server; the Shield part measured in the cloud (section 6); his numbers are still to be made |

## 2. Competent Q4 head (retrained on Q4 vectors), level M

| arm | what | missed share | 95% CI | verification requests / report | wasted trips / report | cover visits | cover visits wasted | distance m / report |
|---|---|---|---|---|---|---|---|---|
| A0 | gold records | 4.92% | 4.10 to 5.83 | 0.000 | 0.000 | 0 | 0 | 1076 |
| A2 | FP16, always commit | 6.30% | 5.36 to 7.26 | 0.000 | 0.057 | 0 | 0 | 1106 |
| A3 | Q8, always commit | 6.50% | 5.53 to 7.49 | 0.000 | 0.063 | 0 | 0 | 1100 |
| A1 | Q4, always commit | 7.41% | 6.42 to 8.46 | 0.000 | 0.076 | 0 | 0 | 1114 |
| A4 | recentred Q4 | 8.01% | 7.07 to 8.95 | 0.000 | 0.124 | 0 | 0 | 1141 |
| A6 | confidence gate (verification only) | 7.07% | 6.13 to 8.11 | 0.073 | 0.070 | 0 | 0 | 1107 |
| A8 | plan's Shield (full cover) | 8.23% | 7.22 to 9.28 | 0.076 | 0.043 | 436 | 7 | 1094 |
| A8c | Shield + location cover (post-hoc, iteration 0) | 7.05% | 6.13 to 8.02 | 0.077 | 0.079 | 493 | 63 | 1119 |
| A12 | oracle gate (diagnostic) | 6.94% | 5.97 to 7.96 | 0.099 | 0.066 | 0 | 0 | 1106 |
| B1 | strict check | 8.56% | 7.51 to 9.61 | 0.075 | 0.048 | 434 | 9 | 1091 |
| B2 | B1 + mass guard | 8.57% | 7.53 to 9.62 | 0.076 | 0.048 | 436 | 9 | 1094 |
| B3 | Shield-2 = B2 + cost-aware fallback | 7.81% | 6.83 to 8.84 | 0.076 | 0.058 | 447 | 22 | 1104 |
| B4 | B1 + cost-aware fallback | 7.76% | 6.76 to 8.80 | 0.075 | 0.058 | 446 | 23 | 1102 |
| G1 | equal-footing gate | 7.74% | 6.78 to 8.77 | 0.073 | 0.055 | 656 | 30 | 1110 |

Paired differences (negative = first arm better):

| comparison | L | M | H |
|---|---|---|---|
| B3-G1 P1 PRIMARY: Shield-2 vs equal-footing gate | +0.15 pp (95% CI -0.18 to +0.48) | +0.07 pp (95% CI -0.44 to +0.61) | -0.13 pp (95% CI -0.73 to +0.48) |
| B3-A1 P2: Shield-2 vs always commit | +0.65 pp (95% CI +0.24 to +1.08) | +0.40 pp (95% CI -0.32 to +1.15) | +0.82 pp (95% CI +0.00 to +1.63) |
| B3-A8 P3: Shield-2 vs plan's Shield | -0.09 pp (95% CI -0.47 to +0.29) | -0.42 pp (95% CI -0.88 to +0.05) | -0.67 pp (95% CI -1.31 to -0.02) |
| B3-A6 Shield-2 vs verification-only gate | +0.18 pp (95% CI -0.22 to +0.59) | +0.74 pp (95% CI +0.02 to +1.48) | +1.11 pp (95% CI +0.36 to +1.85) |
| G1-A1 equal-footing gate vs always commit | +0.51 pp (95% CI +0.09 to +0.93) | +0.33 pp (95% CI -0.38 to +1.03) | +0.94 pp (95% CI +0.18 to +1.71) |
| B3-B2 cost-aware fallback | -0.49 pp (95% CI -0.75 to -0.27) | -0.76 pp (95% CI -1.11 to -0.44) | -1.16 pp (95% CI -1.54 to -0.80) |
| B2-B1 mass guard | +0.02 pp (95% CI -0.04 to +0.09) | +0.02 pp (95% CI -0.11 to +0.17) | +0.00 pp (95% CI -0.05 to +0.05) |
| B1-A8 strict check | +0.38 pp (95% CI +0.09 to +0.68) | +0.33 pp (95% CI +0.00 to +0.67) | +0.49 pp (95% CI -0.07 to +1.07) |
| A12-A1 oracle gate vs always commit (headroom) | +0.16 pp (95% CI -0.25 to +0.58) | -0.47 pp (95% CI -1.07 to +0.13) | -0.69 pp (95% CI -1.45 to +0.11) |

Per arrival seed at M, B3 - G1: +0.00, +0.05, +0.16; B3 - A1: -0.22, +0.60, +0.82 (pp).

Reading. With a head trained on Q4 vectors, 52% of the reports are certified by Shield-2 and the certified ones are almost always right, but intervening on the other 48% (39% of them needed it) costs about as much as it saves: fallback trips delay other incidents. The oracle gate (told which reports are wrong, same delay, same cap) changes the missed share by only -0.47 pp (95% CI -1.07 to +0.13), so this setting has little headroom for any gate.

## 3. The certificate (priorities 2 and 3)

| arm (level M) | certified | certified and wrong plan | certified and wrong table | flagged | wrong-plan reports left unflagged | precision of flags |
|---|---|---|---|---|---|---|
| A8 | 65.7% | 2.23% | 5.83% | 34.3% | 2.23% | 49.0% |
| B1 | 65.8% | 2.17% | 5.90% | 34.2% | 2.17% | 49.2% |
| B2 | 52.3% | 0.40% | 0.67% | 47.7% | 0.40% | 39.1% |
| B3 | 52.3% | 0.40% | 0.63% | 47.7% | 0.40% | 38.7% |
| G1 | 0.0% | 0.00% | 0.00% | 46.4% | 0.87% | 38.3% |
| A6 | 0.0% | 0.00% | 0.00% | 7.3% | 14.70% | 56.6% |

The mass guard is what makes agreement inside the set mean something: A8 certified 65.7% of the reports and was wrong on 2.23% of all reports; with the guard 52.3% are certified and 0.40% are wrong. The conformal set misses the gold record on about 9% of the reports (coverage 90.8% in iteration 0); the heads and the parser can express the gold record in every report (gold_missing = 0), so the misses are set truncation, not an unsupported record type.

## 4. Equal footing (priority 4)

G1 gets everything B3 gets except the trigger: the same two-level use of the cap (verify first, fallback after), the same cost-aware fallback on the same conformal set, the same share of flagged reports on CAL. Competent head: B3 - G1 = +0.07 pp (95% CI -0.44 to +0.61): a tie. Unadapted head: B3 - G1 = -2.03 pp (95% CI -2.72 to -1.38). So the candidate set + signature + checks trigger is worth something only when the head is poor (wrong-plan reports left unflagged: B3 1.00% vs G1 9.00% on the unadapted head).

## 5. Precision, adaptation and the safety net (level M; all readouts, same episodes)

| head | always commit | confidence gate (verification only) | equal-footing gate G1 | plan's Shield A8 | Shield-2 B3 | B3 minus always commit |
|---|---|---|---|---|---|---|
| FP16 (reference) | 6.30% | 6.74% | 6.47% | 6.25% | 6.47% | +0.16 pp (95% CI -0.46 to +0.77) |
| Q8_0, retrained | 6.50% | 6.30% | 6.72% | 6.85% | 6.49% | -0.02 pp (95% CI -0.60 to +0.54) |
| Q4_K_M, retrained on Q4 vectors | 7.41% | 7.07% | 7.74% | 8.23% | 7.81% | +0.40 pp (95% CI -0.32 to +1.15) |
| Q4_K_M, head NOT adapted (frozen FP16 head) | 16.49% | 15.82% | 11.15% | 10.34% | 9.12% | -7.38 pp (95% CI -8.30 to -6.48) |

Other references at M: gold records 4.92%; Q4 head recentred (label-free shift removed from the Q4 vectors, FP16 head) 8.01%. Quantisation effect with a retrained head: Q8 - FP16 +0.20 pp (95% CI -0.28 to +0.69); Q4 - FP16 +1.11 pp (95% CI +0.47 to +1.77). Unadapted Q4 - FP16 +10.19 pp (95% CI +9.25 to +11.13). At levels L / H the same ordering holds (see `results/iter1/ITER1_RESULTS.md`).

What this says about quantisation: (i) the large damage appears when the readout head was fitted on full-precision vectors and is applied to quantised ones; (ii) removing the average shift or retraining on quantised vectors removes most of it; (iii) a small cost remains for Q4 (about 1.1 pp of missed share here); (iv) a runtime safety net helps in case (i) and not in case (iii). The conclusions are for this model, this head, this simulated mission and these reports.

## 6. Speed and memory (priority 5)

Measured now, **in the cloud container (x86_64; 2 CPUs; not Samadhi's computer)**, on saved vectors: heads p50 0.58 ms; one Shield-2 decision p50 0.28 ms, p95 1.17 ms, p99 1.59 ms (2.31 allocator runs per decision); the allocator takes 0.15 ms per run. The simulation charges **20 ms per run**, about 132 times more than measured here, so the simulated delay is a conservative stand-in for a slow edge CPU, and decision time is not what limits Shield-2. Python process peak memory 251 MB (includes the whole development set).

**Not measured:** the llama.cpp part (time to embed one report, server memory, GPU memory) for f16, Q8_0 and Q4_K_M. Model files: 2.31, 1.23 and 0.75 GiB. Run on his computer: `python tools\bench_local.py --llama-dir D:\llama --models-dir D:\llama\models --n 100` (add `--cpu` for CPU only; `pip install psutil` for memory). The script writes `results/bench_<time>/BENCH.md`; paste it back and the evidence is complete.

## 7. Sample size for the fresh test (estimate from development; the final number is a main-chat decision)

From the DEV paired standard deviation of the per-episode difference (episodes of 20 reports, ~36.7 incidents). Details: `results/iter1/POWER_ITER1.md` and `POWER_ITER1_raw.md`.

| comparison | sd (missed incidents / episode) | effect | episodes for 80% / 90% power |
|---|---|---|---|
| q4, B3-G1 | 1.19 | 0.50 pp | 332 / 444 |
| q4, B3-G1 | 1.19 | 0.75 pp | 147 / 197 |
| q4, B3-G1 | 1.19 | 1.00 pp | 83 / 111 |
| q4, B3-A1 | 1.67 | 0.50 pp | 651 / 872 |
| q4, B3-A1 | 1.67 | 0.75 pp | 289 / 387 |
| q4, B3-A1 | 1.67 | 1.00 pp | 163 / 218 |
| raw, B3-G1 | 1.56 | 1.00 pp | 142 / 190 |
| raw, B3-G1 | 1.56 | 2.00 pp | 35 / 47 |
| raw, B3-A1 | 2.17 | 1.00 pp | 274 / 367 |
| raw, B3-A1 | 2.17 | 2.00 pp | 69 / 92 |

With a competent head the expected effect is about zero, so the fresh test there would be a 'no harm' (non-inferiority) test against a margin that Samadhi and the supervisors must choose; with the unadapted head the expected effect of B3 over G1 is about 2 pp. 600 episodes (12,000 reports, roughly 65 min of GPU time) gives >= 98% power for a 0.75 pp margin against A1 and ~100% for the unadapted comparison; 1,100 episodes is needed only for a 0.5 pp margin against A1 (95%). The 0.75 pp margin (about 10% of the Q4 missed share) is a choice, not a result.

## 8. Reproducibility repair (Windows)

Samadhi's run (Python 3.12.6, Windows) failed 3 tests: `fork` does not exist on Windows (repaired by the patch the main chat prepared and Samadhi applied (`shield/devrun.py`, `tests/test_windows_spawn.py`; I have not seen those files and my update does not overwrite them); the iteration-1 runner `shield/devrun2.py` has its own portable pool and a test that serial = spawn), and two comparisons of cached against refitted probabilities. The diagnostic (`diagnosis.json`) shows: the fresh path and the development path give **identical** probabilities on the same machine (difference 0.0); cached (built elsewhere, Python 3.13.17) against local differ by at most 0.0094 in one probability (q4 action 0.0022), with **0 changed pilot-style records, 0 changed top records, 0 changed conformal sets** for q4, f16, q8 and recentred, and 1 changed set for the diagnostic raw head; outcomes of A1, A6, A8 on 10 episodes identical. The cause (lbfgs stops at a slightly different point under another BLAS, tol 1e-6) is consistent with this but not proven. Nothing was loosened silently: the same-machine equality test runs everywhere (1e-12); the decision-level test (probabilities < 2e-2, records and sets identical) runs everywhere; the bit-for-bit comparison with the cache runs only in the environment that built the cache and is reported as skipped elsewhere. The cache was not changed (SHA-256 `e5b07161...`).

## 9. Improved / failed / untested

**Improved (DEV, exploratory):** safer certificate; cost-aware fallback; large protection when the head is not adapted; Windows portability; a cleaner statement of what quantisation costs.

**Failed or not shown:** a gain over always-commit or over the equal-footing gate with a competent head (label NOT SHOWN); the pre-specified B3 is worse than the post-hoc A8c on both the competent and the unadapted head; the mass guard and the strict check do not lower missed share by themselves.

**Untested:** fresh data; llama.cpp speed and memory on Samadhi's computer; CPU backend; the Shield on the recentred head; location cover combined with the new certificate (the most promising untried variant, needs a second, approved round); chain-mode episodes; a verification queue; another model or real text. **Not built:** `tools/run_fresh.py` still runs the old arms only (devrun, not devrun2); B1-B4 and G1 are not wired into the fresh runner, and there is no fresh demo.

## 10. Decisions needed from the main chat (and supervisors)

1. **Which condition is primary in the fresh test?** (a) competent Q4 only, (b) unadapted Q4 only, (c) both. Recommended (c): competent Q4 as a 'no harm and no gain claimed' test, unadapted Q4 as the superiority test of B3 against G1 and A1. Disclose that (b) became primary after seeing DEV.
2. **Which method is frozen?** B3 as registered, with A8c carried as a named secondary arm (it already exists; no new tuning). Or a second round for 'location cover + new certificate' under its own protocol.
3. **Fresh size and margin** (section 7). Suggested 600 episodes with a 0.75 pp no-harm margin; the main chat decides.
4. The plan's section 12 questions to the supervisors are still open.

## 11. Files (new in iteration 1)

`docs/ITERATION1_PROTOCOL.md`, `shield/policy2.py`, `shield/devrun2.py`, `tools/run_iter1.py`, `tools/analyze_iter1.py`, `tools/power_iter1.py`, `tools/bench_local.py`, `tools/build_iter1_evidence.py`, `tests/test_iter1.py`, changed `tests/test_fresh.py` (two-tier numerical tests), `results/iter1/*` (records for q4, f16, q8, raw; ITER1_RESULTS.md/json; POWER files; PROTOCOL.sha256), `results/bench_cloud_shield_only_20261113/`.

Tests: 110 passed, 0 failed, 0 skipped in 313 s in the cloud container (Python 3.13.17, Linux): 93 tests in the earlier files (one numerical test was split into three: same-machine equality, decision-level agreement, bit-for-bit with the cache) + 17 in tests/test_iter1.py. On Samadhi's Windows PC the bit-for-bit comparison with the cache is expected to be reported as skipped (different environment); this was not run there.
