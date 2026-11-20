# Reproduction and verification of the label-free linear map (written BEFORE the run)

Status: FIXED. 2026-11-14. Development data only. This is a reproduction, not a new variant. Nothing is tuned. Every number is reported.

Why: the map (called ALN) comes from the research-design chat's repair experiment (folder edgesar_repair_2026-11-14). The implementation chat had not reproduced it. A supervisor gate needs the claim checked by independent code.

Checks (all on the 1,000 style-A reports, the package's 5 folds, FIT/CAL/EVAL roles unchanged; exact-duplicate FIT reports already removed by the package):
1. Direction and training-only fitting: the map sends Q4 vectors to the FP16 space; map and heads use FIT reports only.
2. Independent code: ALN-mine is written from the mathematical description (ridge on the standardised difference F-Q, dual form, strength chosen by 3-fold CV on held-out pairs, folds grouped by FAMILY, not by template). Compare with the other chat's ALN (its own code, re-run unchanged here).
3. Control: pairs shuffled (Q4 vector of report i paired with the FP16 vector of another report). If the gain comes from real pairing, the shuffled map must not match ALN.
4. Specificity control: the same map applied to Q8 vectors (Q8 -> FP16).
5. Folding: ALN followed by the FP16 head is one linear layer. Fold it, and compare logits and records with the unfolded pipeline (extra run-time cost must be zero).
6. Mission outcome (always commit, no gate, levels L/M/H, seeds 1-3) for gold, f16, q4, rec, raw, ALN-mine, shuffled-pair map; paired differences ALN-mine minus q4, rec, f16, raw, other-chat ALN.

Decision rule: ALN-mine is "REPRODUCED" if its missed share at level M is within 0.3 pp of the other chat's ALN (6.81%) and its paired difference to raw has the same sign and CI excludes 0; the folded model gives identical records and logits to 1e-8. The shuffled map must be worse than ALN-mine at level M by a CI excluding 0, otherwise the claim "gain comes from the pairing" is NOT shown.
Not done: fresh data, new variants, tuning.
