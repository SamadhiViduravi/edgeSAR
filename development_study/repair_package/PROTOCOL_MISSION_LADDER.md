# Mission-level check of the readout arms: protocol (written BEFORE the run)

Status: FIXED. Written 14 Nov 2026 (morning, Colombo) by the research-design chat, after experiment 1 was analysed and before the results of experiment 2 were seen. Hashed before the run (`out_mission/PROTOCOL_MISSION.sha256`).

**Exploratory, development data only.** It uses the implementation chat's simulator (`edgesar_shield`, original package of 13 Nov, code fingerprint in its manifest) **without changing any of its files**. The episodes are the same overlay episodes as its development runs: 1,000 style-A reports, 5 family folds, episodes of 20 independent reports that share 3 UAVs, bounded CBBA, levels L / M / H, arrival seeds 1, 2, 3. Pooled intervals are optimistic because the three seeds reuse the same reports.

## 1. Question

Experiments 1 and 2 measure decisions. This check asks what the same readout arms do to the mission outcome: the share of real incidents late or unverified at their deadline ("missed share"), when every record is committed without any gate.

## 2. Arms (always commit; no gate, no Shield, no verification)

Heads are fitted exactly as in `shield/readout.py` (`Heads`: standardise, logistic regression, C by grouped cross-validation inside FIT, tolerance 1e-6), on the FIT reports of each outer fold only. Label-free maps use the FIT pairs only.

| Arm | Position | What it is |
|---|---|---|
| gold | | gold records (reference; the simulator's A0) |
| f16, q8, q4, rec, raw | end | read from the package's saved cache (its A2, A3, A1, A4, A5). **Integrity check**: missed counts must equal the package's own results. |
| aln | end | FP16 heads on affine-mapped Q4 vectors (the map of experiment 1, fitted on FIT pairs, λ chosen on held-out pairs) |
| f16p, q8p, q4p | prefix | heads fitted on each precision's own `prefix` vectors |
| rawp | prefix | f16p heads on raw Q4 `prefix` vectors |
| recp | prefix | f16p heads on recentred Q4 `prefix` vectors |
| alnp | prefix | f16p heads on affine-mapped Q4 `prefix` vectors |

A second integrity check: f16 and q4 heads refitted here (`end`) must give the cache's probabilities (same machine type as the cache builder) or, failing that, identical committed records.

## 3. Outcome and comparisons (all descriptive; no test label is attached)

* Missed share per arm and level, with a 95% episode-bootstrap interval (2,000 resamples), using the package's own `arm_table`, `episode_bootstrap_ci` and `paired` functions.
* Paired differences on the same episodes at each level: aln − q4, aln − rec, aln − f16, q4p − q4, f16p − f16, alnp − q4p, alnp − f16p, q4p − f16p, q4p − f16, alnp − f16, rec − raw, aln − raw.
* Costs reported beside the outcome: wasted trips per report and distance per report.

## 4. Rules

* One run. Nothing is tuned. No arm is added or dropped after results are seen.
* If an integrity check fails, the run is void until the cause is found; the failed output is kept.
* The simulator's limits apply unchanged (independent reports that share a fleet; wrong records do not change later prompts; decision time is charged at 0.02 s per allocator run).
