# EdgeSAR heads test: plan written BEFORE any heads result is seen

Written: 10 November 2026 (with Claude, from the pilot results and the "Main chat" design).
Status: **side test**. It does not replace the submitted proposal or the registered pilot. Nothing here changes the pilot files.

## 1. The question

The pilot showed that Q4_K_M changes the task table in **28.0%** of reports (Q8_0: **6.5%**) when the model writes the answer as text.
The new idea ("prevent" line): do not let the model write text. Read its **hidden state** with three small trained classifiers ("heads":
action, sensor, priority). The place and the incident id come from string matching, as in the TF-IDF/LR baseline.

> If we read the shrunk model with heads, do its decisions change less than when it writes text, without reading the reports worse?

## 2. What we do (three steps, no new model, no simulator)

1. `01_smoke_embed.py` - check that the server gives repeatable vectors (2 minutes).
2. `02_extract.py` - get one vector per report for FP16, Q8_0 and Q4_K_M, two prompt variants (30 to 60 minutes, my estimate).
3. `03_heads.py` - train the heads on style A, test on style A (out-of-fold, folds grouped by family) and **once** on style B. Compare with the pilot numbers.

## 3. What is fixed now (do not change after you see style B)

* Cases: the 1,400 pilot cases, unchanged (SHA256 starts `3c51f0b4`). Pilot files are checked against your freeze file before every step.
* Vector: last layer, last token (all llama.cpp gives). Variant **end** = the exact pilot prompt P1 (this is the main variant). Variant **prefix** = the same prompt plus `{"action":"` (second look only).
* Heads: standardise, then logistic regression. The strength C is chosen **inside the training rows only** from {0.0003, 0.003, 0.03, 0.3, 3} by grouped 3-fold log-loss.
* Dev A: out-of-fold, 5 folds grouped by family. Held-out B: heads trained on all of A, tested once.
* Heads for each model are trained on that model's own vectors. A second test applies FP16-trained heads to Q8/Q4 vectors without retraining.
* Settings fingerprint: `heads_config.json` (its hash is printed in the report). Every run of step 3 is written in `results_heads\attempts.log`.

## 4. The three outcomes (these rules are coded in `heads_report.py`)

| | Rule | Why this rule |
|---|---|---|
| **O1** reads well | Held-out B, action right, Heads FP16 against TF-IDF/LR, exact McNemar test, p < 0.05 decides BETTER / WORSE, else SAME | Same test as the pilot's gate G2. TF-IDF/LR is the fair rival: it is also trained on A. |
| **O2** calmer when shrunk | Held-out B, table-changing disagreement with FP16. LOWER if the heads' 95% upper bound is below the generative point value (Q4: 27.0%, Q8: 6.5%) | Compares like with like on the same 400 reports. |
| **O3** risky cases can be found | Held-out B, Q4 head's own confidence. USEFUL if AUROC >= 0.70 **and** the least-confident 20% of reports holds at least 2 times its share of the flips | 0.70 and 2x are my suggestion, not a law. **Change them now if you disagree, not later.** |

## 5. My guesses (write yours here BEFORE you run step 2, then do not edit)

Write your own numbers. Do not copy mine. Date and sign this section.

* Heads FP16, held-out B, action accuracy:1 % (range 1% to 2%)
* Heads Q4 vs Heads FP16, held-out B, table-changing disagreement: 15 % (generative Q4 was 27.0%)
* Will low confidence point at the cases that flip (O3)? yes
* Your one-line reason: ______________________________________________ no idea

due to lack of knowledge about AI side I struggled so much to answer these. 
Date: ____________6.50PM,11-Nov-2026   Signed: ____________Samadhi

## 6. What each result would mean (a guide, not a verdict)

* **O1 WORSE** or **O2 NOT SHOWN LOWER**: reading the hidden state does not help on this data. Stop the heads line. Keep the benchmark path and the Shield-only idea. This is a valid result.
* **O1 SAME or BETTER, O2 LOWER, O3 USEFUL**: the "prevent" and "sharpen" lines are worth a proper design, with your supervisors' agreement.
* **O1 SAME or BETTER, O2 NOT SHOWN LOWER**: heads read well, but shrinking still moves them. Then "absorb" and "cover" matter more.
* **O3 TOO FEW FLIPS TO JUDGE** (fewer than 10 flips on B): say so. Do not stretch it.

## 7. Risks I already know (so they are not a surprise later)

1. **Heads need labels.** The story changes from "a model as it is, only shrunk" to "a model plus a small trained part". Your supervisors must agree before this becomes part of the project.
2. **Easy data.** TF-IDF/LR gets 100% on style A. On A, any two good classifiers agree, so low disagreement on A means little. Style B (400 reports) is the real test, and its intervals are wide.
3. **Two classifiers trained on the same labels agree when both are right.** The report shows how many flips happen where FP16 was already wrong, to separate "stable" from "easy".
4. **Last layer only.** Middle layers may carry more. A weak result here is not proof that hidden states fail.
5. **Same author for A and B.** Both styles come from the same program. Real reports are not tested.
6. **Pilot cases are for the pilot.** If this line goes forward, the confirmatory study needs new cases, generated after the full-study registration.

## 8. Stop rules and time box

* Time box: 2 days. If it is not done by then, stop and tell me why.
* If the smoke test shows FAIL twice, stop and send me `results_heads\smoke_report.txt`.
* Step 3 is run once for the main result. If you change anything after you see B, write what and why in your log. It becomes attempt 2 and is reported as such.

## 9. AI-use note

The kit (`heads_*.py`, `01_`, `02_`, `03_`, tests) and this plan were written with Claude. You read and run them and take responsibility. You must be able to explain each file in the viva.
