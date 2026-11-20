# EdgeSAR pilot report

Made by analyze.py on 2026-10-28 18:18 from the files in `runs/`. Cases: 1400 (development style A: 1000, held-out style B: 400). Runs found: f16_P1 (1400), f16_P2 (300), f16_P3 (300), f16_P1_nogrammar (100), q4_P1 (1400), q4_P2 (300), q4_P3 (300), q4_P1_nogrammar (100), q8_P1 (1400), f16_P1_rerun (1400).

## Suggested call: GO

- Q4 changes enough decisions. Even a low harmful share (10%) should reach the 120 harmful flips needed. Build the CBBA harness.
- G2: on held-out wording FP16 did not clearly beat both Rule and TF-IDF/LR. The design says: drop the claim that a language model is necessary, report it, and continue.

This is my reading of the design's gates (G0 to G5), as a guide for your talk with your supervisors. It is not a rule from them. The yield levels (COMFORTABLE, ONLY IF HARM IS HIGH, BORDERLINE, SHORT) are my own cut-offs, not from the design.

### The gates one by one

| gate | what it checks | result | details | what the design says to do |
|---|---|---|---|---|
| G0 | FP16 gives the same answers after a restart | **PASS** | 0 of 1400 answers changed. (Tests T1 to T8 need your CBBA code and are not checked here.) | Fix it before piloting. |
| G1 | FP16 beats the better floor | **PASS** | FP16 59.1% against always NO_ACTION 40.0% (+19.1 pts, McNemar p < 0.0001, 1000 development cases) | If it fails: move to the 3B model once. If 3B also fails, stop the SLM study and apply the analysis to Rule and classifier flips. |
| G2 | FP16 clearly beats Rule and TF-IDF/LR on held-out wording | **FAIL** | Rule engine: baseline clearly better (-23.5 pts); TF-IDF + logistic regression: baseline clearly better (-26.2 pts) | If Rule or the classifier match or beat FP16: drop the necessity claim, report it, and continue. |
| G3 | Format flips are not the majority | **PASS** | Q4 vs FP16: 379 meaning flips, 0 format flips, 13 bad-incident flips | If format flips are the majority: fix the grammar or prompt on development families before freezing. |
| G4 | Enough flips to reach 120 harmful flips | **COMFORTABLE** | Q4 changed the task table in 28.0% of 1400 cases; lower 80% bound 26.9%; the design needs 3.3% (if 25% harmful), 8.3% (if 10%), 16.7% (if 5%) | If short: add Q3 as a separate arm in place of the Q8 subset and one robustness subset. If still short, the exploratory analyses become descriptive (C1 to C3 stay). |
| G5 | 132,200 calls fit in 75 hours | **PASS** | 0.62 s per call at the slowest precision gives 23 hours | Cut in the order given in the design (section G). |
| G6, G7 | Clustering of harm; absorption | **NOT TESTED** | these need the simulator |  |

## Your eight questions in one page

| Question | Answer |
|---|---|
| 1. Is FP16 competent? | On development cases FP16 chose the right action in 59.1% (56.0% to 62.1%). It got the whole record right in 30.3% (27.5% to 33.2%). |
| 2. Does it beat always-NO_ACTION and always-VERIFY? | Better floor: always NO_ACTION at 40.0%. FP16 minus floor: +19.1 points, McNemar p < 0.0001. **Yes, it beats it.** Other floor (always VERIFY): p < 0.0001. |
| 3. Do Rule and TF-IDF/LR match or beat FP16? | On held-out wording (the fair test), whole-record accuracy: FP16 27.3%, Rule 50.7%, TF-IDF/LR 53.5%. FP16 against Rule: baseline clearly better. FP16 against TF-IDF/LR: baseline clearly better. |
| 4. How often do Q8 and Q4 change the FP16 decision? | Q8_0 changes the task table in 6.5% (5.3% to 7.9%) of 1400 cases; Q4_K_M changes the task table in 28.0% (25.7% to 30.4%) of 1400 cases; FP16 against itself after a restart: 0 changed |
| 5. Which transition types happen? | Q4_K_M: UPDATE->NO_ACTION (60); NO_ACTION->CREATE (59); CLOSE->NO_ACTION (47); CREATE: sensor+priority (44) | Q8_0: UPDATE->NO_ACTION (26); CREATE->NO_ACTION (16); NO_ACTION->CLOSE (8); CREATE: sensor+priority (8) |
| 6. Are the outputs valid under the fixed schema? | f16_P1: valid JSON 100.0%, schema ok 100.0%; q4_P1: valid JSON 100.0%, schema ok 100.0%; f16_P1_nogrammar: valid JSON 100.0%, schema ok 95.0%; q4_P1_nogrammar: valid JSON 100.0%, schema ok 67.0% |
| 7. What is the real laptop speed? | FP16: 0.62 s per call (5791 per hour); Q8_0: 0.36 s per call (9969 per hour); Q4_K_M: 0.26 s per call (13824 per hour). The design needs about 132,200 calls: 23 hours at the slowest speed (limit 75 hours). **It fits.** |
| 8. Is the flip yield high enough for the CBBA experiment? | **COMFORTABLE.** Q4 changed the task table in 28.0% of cases. The design needs at least 3.3% if 25% of changes are harmful, 8.3% if 10%, 16.7% if 5%. Enough flips even if only 10% of them turn out harmful. |

## 1. Accuracy against the construction labels

Action accuracy = the right one of the four actions. Record accuracy = the whole decision is right (action, incident, landmark, sensor, priority). Intervals are 95% Wilson. 'dev' = development style A. 'held' = held-out style B, written with words the Rule engine and the classifier never saw.

| System | dev: action acc | dev: record acc | dev: macro-F1 | held: action acc | held: record acc | held: macro-F1 |
|---|---|---|---|---|---|---|
| always NO_ACTION | 40.0% (37.0% to 43.1%) | n/a | 0.14 | 40.0% (35.3% to 44.9%) | n/a | 0.14 |
| always VERIFY | 25.0% (22.4% to 27.8%) | n/a | 0.10 | 25.0% (21.0% to 29.5%) | n/a | 0.10 |
| Rule engine | 97.0% (95.7% to 97.9%) | 97.0% (95.7% to 97.9%) | 0.96 | 55.0% (50.1% to 59.8%) | 50.7% (45.9% to 55.6%) | 0.45 |
| TF-IDF + logistic regression | 100.0% (99.6% to 100.0%) | 98.2% (97.2% to 98.9%) | 1.00 | 76.2% (71.8% to 80.2%) | 53.5% (48.6% to 58.3%) | 0.74 |
| Llama 3.2 1B FP16 | 59.1% (56.0% to 62.1%) | 30.3% (27.5% to 33.2%) | 0.54 | 58.8% (53.9% to 63.5%) | 27.3% (23.1% to 31.8%) | 0.53 |
| Llama 3.2 1B Q8_0 | 60.5% (57.4% to 63.5%) | 31.7% (28.9% to 34.6%) | 0.55 | 60.0% (55.1% to 64.7%) | 28.2% (24.1% to 32.9%) | 0.55 |
| Llama 3.2 1B Q4_K_M | 60.1% (57.0% to 63.1%) | 32.1% (29.3% to 35.1%) | 0.48 | 62.5% (57.7% to 67.1%) | 32.8% (28.3% to 37.5%) | 0.51 |

The 'always VERIFY' floor has no meaningful full record, so its record accuracy is not shown.

**G1 (FP16 against the floors, 1000 development cases):** FP16 action accuracy 59.1% (56.0% to 62.1%). Better floor = always NO_ACTION at 40.0%. FP16 minus floor = +19.1 points (95% family-bootstrap interval +14.9 to +23.4). McNemar exact p < 0.0001 (FP16 only right in 357 cases, floor only right in 166). **PASS**

### FP16: what it answered for each true action (all cases)

| true action | cases | said CREATE | said UPDATE | said CLOSE | said NO_ACTION | recall |
|---|---|---|---|---|---|---|
| CREATE | 350 | 196 | 144 | 0 | 10 | 56.0% |
| UPDATE | 280 | 6 | 272 | 0 | 2 | 97.1% |
| CLOSE | 210 | 1 | 89 | 37 | 83 | 17.6% |
| NO_ACTION | 560 | 81 | 146 | 12 | 321 | 57.3% |

### G2: FP16 against the Rule engine and TF-IDF/LR (same cases, paired)

| baseline | cases | metric | n | FP16 | baseline | FP16 minus baseline | 95% interval (family bootstrap) | McNemar p | verdict |
|---|---|---|---|---|---|---|---|---|---|
| Rule engine | held-out | action | 400 | 58.8% | 55.0% | +3.8 pts | -2.2 to +10.0 | 0.2926 | no clear difference |
| Rule engine | held-out | record | 400 | 27.3% | 50.7% | -23.5 pts | -27.8 to -19.2 | < 0.0001 | baseline clearly better |
| Rule engine | development | action | 1000 | 59.1% | 97.0% | -37.9 pts | -41.2 to -34.8 | < 0.0001 | baseline clearly better |
| Rule engine | development | record | 1000 | 30.3% | 97.0% | -66.7 pts | -69.5 to -63.7 | < 0.0001 | baseline clearly better |
| TF-IDF + logistic regression | held-out | action | 400 | 58.8% | 76.2% | -17.5 pts | -23.5 to -11.2 | < 0.0001 | baseline clearly better |
| TF-IDF + logistic regression | held-out | record | 400 | 27.3% | 53.5% | -26.2 pts | -32.8 to -19.5 | < 0.0001 | baseline clearly better |
| TF-IDF + logistic regression | development | action | 1000 | 59.1% | 100.0% | -40.9 pts | -44.2 to -37.7 | < 0.0001 | baseline clearly better |
| TF-IDF + logistic regression | development | record | 1000 | 30.3% | 98.2% | -67.9 pts | -70.7 to -64.9 | < 0.0001 | baseline clearly better |

A difference is claimed only when the family-bootstrap interval and McNemar both agree. Read the held-out rows first: on development wording the baselines were built from the same words, so they have an unfair advantage.

## 2. How often do the smaller models change the FP16 decision?

'Changed' = the validated answer is not identical. 'Table-changing' = the answer would change what the allocator sees (NO_ACTION and an UPDATE that changes nothing count as the same). The design calls these operational flips.

| comparison | cases | changed | changed % | table-changing | table-changing % | meaning flips | format flips | bad-incident flips | right -> wrong | wrong -> right | wrong -> other wrong |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q8_0 vs FP16 | 1400 | 108 | 7.7% (6.4% to 9.2%) | 91 | 6.5% (5.3% to 7.9%) | 90 | 0 | 1 | 8 | 26 | 74 |
| Q4_K_M vs FP16 | 1400 | 494 | 35.3% (32.8% to 37.8%) | 392 | 28.0% (25.7% to 30.4%) | 379 | 0 | 13 | 63 | 103 | 328 |
| FP16 restarted vs FP16 (must be 0) | 1400 | 0 | 0.0% (0.0% to 0.3%) | 0 | 0.0% (0.0% to 0.3%) | 0 | 0 | 0 | 0 | 0 | 0 |

Meaning flips = both answers were valid and still differ. Format flips = one answer could not be read or broke the schema, so the validator replaced it with NO_ACTION. Bad-incident flips = one answer named an incident that is not open. The design (gate G3) asks for these to be reported separately, because only meaning flips say something about the quantized model's decision.

'right -> wrong' = FP16 had the whole record right and the smaller model did not. This is only a rough pointer to harm. Harm itself needs the simulator.

### Does the flip rate depend on the wording style? (table-changing flips)

| model vs FP16 | development style A | held-out style B |
|---|---|---|
| Q8_0 | 6.5% (5.1% to 8.2%) (65 of 1000) | 6.5% (4.5% to 9.4%) (26 of 400) |
| Q4_K_M | 28.4% (25.7% to 31.3%) (284 of 1000) | 27.0% (22.9% to 31.6%) (108 of 400) |

If the two columns are very different, the flip rate depends on how the reports are written. Mission logs will be a third style, so treat the rate as a rough range, not a fixed number.

### Transition types: Q4_K_M vs FP16

| transition (FP16 -> Q4_K_M) | count | share of table-changing flips |
|---|---|---|
| UPDATE->NO_ACTION | 60 | 15.3% |
| NO_ACTION->CREATE | 59 | 15.1% |
| CLOSE->NO_ACTION | 47 | 12.0% |
| CREATE: sensor+priority | 44 | 11.2% |
| NO_ACTION->UPDATE | 38 | 9.7% |
| CREATE->NO_ACTION | 38 | 9.7% |
| CREATE: sensor | 29 | 7.4% |
| CREATE: priority | 23 | 5.9% |
| UPDATE: priority | 14 | 3.6% |
| UPDATE->CREATE | 14 | 3.6% |
| CREATE: location | 8 | 2.0% |
| UPDATE: sensor | 7 | 1.8% |
| UPDATE: sensor+priority | 5 | 1.3% |
| CREATE->UPDATE | 2 | 0.5% |
| UPDATE: location+sensor+priority | 1 | 0.3% |
| CREATE: location+sensor+priority | 1 | 0.3% |
| UPDATE->CLOSE | 1 | 0.3% |
| UPDATE: link+location | 1 | 0.3% |

Table-changing flips by true action: CLOSE 58 of 210 (27.6%); CREATE 154 of 350 (44.0%); NO_ACTION 101 of 560 (18.0%); UPDATE 79 of 280 (28.2%)

### Transition types: Q8_0 vs FP16

| transition (FP16 -> Q8_0) | count | share of table-changing flips |
|---|---|---|
| UPDATE->NO_ACTION | 26 | 28.6% |
| CREATE->NO_ACTION | 16 | 17.6% |
| NO_ACTION->CLOSE | 8 | 8.8% |
| CREATE: sensor+priority | 8 | 8.8% |
| NO_ACTION->UPDATE | 7 | 7.7% |
| NO_ACTION->CREATE | 6 | 6.6% |
| CREATE: sensor | 5 | 5.5% |
| UPDATE: location | 2 | 2.2% |
| CREATE->UPDATE | 2 | 2.2% |
| UPDATE->CLOSE | 2 | 2.2% |
| CLOSE->NO_ACTION | 2 | 2.2% |
| CREATE: priority | 2 | 2.2% |
| CREATE: location+sensor+priority | 1 | 1.1% |
| UPDATE: location+sensor | 1 | 1.1% |
| UPDATE: sensor+priority | 1 | 1.1% |
| UPDATE: sensor | 1 | 1.1% |
| CREATE->CLOSE | 1 | 1.1% |

Table-changing flips by true action: CLOSE 12 of 210 (5.7%); CREATE 29 of 350 (8.3%); NO_ACTION 30 of 560 (5.4%); UPDATE 20 of 280 (7.1%)

### Is quantization bigger than prompt noise? (the 300-case prompt subset, development cases only)

| comparison | cases | changed | table-changing |
|---|---|---|---|
| FP16 vs FP16 restarted (same prompt) | 300 | 0.0% (0.0% to 1.3%) | 0.0% (0.0% to 1.3%) |
| Q8_0 vs FP16 (same prompt P1) | 300 | 6.3% (4.1% to 9.7%) | 6.3% (4.1% to 9.7%) |
| Q4_K_M vs FP16 (same prompt P1) | 300 | 38.3% (33.0% to 43.9%) | 31.3% (26.3% to 36.8%) |
| FP16: prompt P1 vs prompt P2 | 300 | 46.0% (40.4% to 51.7%) | 41.7% (36.2% to 47.3%) |
| FP16: prompt P1 vs prompt P3 | 300 | 58.0% (52.3% to 63.4%) | 48.7% (43.1% to 54.3%) |
| Q4_K_M: prompt P1 vs prompt P2 | 300 | 37.0% (31.7% to 42.6%) | 33.0% (27.9% to 38.5%) |
| Q4_K_M: prompt P1 vs prompt P3 | 300 | 48.0% (42.4% to 53.6%) | 39.3% (34.0% to 45.0%) |

If a different wording of the prompt changes as many decisions as quantization does, a quantization result can really be a prompt result. The design asks you to freeze the prompt before any held-out run.

### Does the sign of the Q4 effect depend on the prompt? (Q4 accuracy minus FP16 accuracy)

| prompt | cases | FP16 action acc | Q4 action acc | Q4 minus FP16 | FP16 record acc | Q4 record acc | Q4 minus FP16 |
|---|---|---|---|---|---|---|---|
| P1 | 300 | 58.7% | 61.0% | +2.3 pts | 30.0% | 31.3% | +1.3 pts |
| P2 | 300 | 61.7% | 68.0% | +6.3 pts | 29.7% | 38.7% | +9.0 pts |
| P3 | 300 | 66.7% | 59.7% | -7.0 pts | 38.3% | 39.0% | +0.7 pts |

## 3. Are the outputs valid under the fixed schema?

With the grammar on, llama.cpp can only write the allowed JSON, so format errors should be 0. 'Bad incident' = the model named an incident that is not open; the validator replaces it with NO_ACTION (as in the design). 'Truncated' = it hit the 100-token limit.

| run | grammar | cases | valid JSON | schema ok | bad incident | format fallback | truncated |
|---|---|---|---|---|---|---|---|
| f16_P1 | yes | 1400 | 100.0% | 100.0% | 19 | 0 | 0 |
| f16_P2 | yes | 300 | 100.0% | 100.0% | 0 | 0 | 0 |
| f16_P3 | yes | 300 | 100.0% | 100.0% | 0 | 0 | 0 |
| f16_P1_nogrammar | NO | 100 | 100.0% | 95.0% | 3 | 5 | 0 |
| q4_P1 | yes | 1400 | 100.0% | 100.0% | 1 | 0 | 0 |
| q4_P2 | yes | 300 | 100.0% | 100.0% | 0 | 0 | 0 |
| q4_P3 | yes | 300 | 100.0% | 100.0% | 0 | 0 | 0 |
| q4_P1_nogrammar | NO | 100 | 100.0% | 67.0% | 0 | 33 | 0 |
| q8_P1 | yes | 1400 | 100.0% | 100.0% | 18 | 0 | 0 |
| f16_P1_rerun | yes | 1400 | 100.0% | 100.0% | 19 | 0 | 0 |

The two 'nogrammar' runs show what happens when the model is free to write anything. If they are much worse, the grammar is doing real work.

## 4. Laptop throughput

| model | calls | median per call | mean per call | 90th percentile | calls per hour | prompt tok/s (median) | generation tok/s (median) | mean tokens in / out |
|---|---|---|---|---|---|---|---|---|
| FP16 | 1400 | 0.71 s | 0.62 s | 0.84 s | 5791 | 4784 | 41 | 619 / 21 |
| Q8_0 | 1400 | 0.41 s | 0.36 s | 0.49 s | 9969 | 6727 | 75 | 619 / 20 |
| Q4_K_M | 1400 | 0.29 s | 0.26 s | 0.35 s | 13824 | 6492 | 115 | 619 / 18 |

Design check (G5): 132,200 calls x 0.62 s (slowest model) = **23 hours**; with the average of the models = 15 hours. Limit: 75 hours and 135,000 calls. **FITS**

Total model time used by this pilot: 0.9 hours. Mission prompts will be longer than these test prompts, and a hot laptop or battery mode is slower. Measure again in the simulator.

Model loading: s1_f16 5 s, 2.48 GB, VRAM used 2635 MB; s2_q4 3 s, 0.81 GB, VRAM used 1045 MB; s3_q8 3 s, 1.32 GB, VRAM used 1535 MB; s4_f16_rerun 3 s, 2.48 GB, VRAM used 2635 MB

## 5. Is the flip yield high enough to build the CBBA / closed-loop experiment?

The design needs at least 120 harmful flips in development (and 60 in held-out) from 14400 decisions per stage. Harmful flips = flip rate x 14400 x (share of flips that are harmful). The harmful share is unknown until the simulator exists, so three cases are shown. The 'lower 80% bound' is the smaller of a one-sided Wilson bound and a family-bootstrap bound.

**Q4_K_M vs FP16:** table-changing rate 28.0% of 1400 cases (95% interval 25.7% to 30.4%; lower 80% bound 26.9%). Level: **COMFORTABLE.** Enough flips even if only 10% of them turn out harmful.

| if this share of flips is harmful | flip rate needed | expected harmful flips (best guess) | expected (lower 80% bound) | enough? |
|---|---|---|---|---|
| 5% | 16.7% | 202 | 194 | yes |
| 10% | 8.3% | 403 | 388 | yes |
| 25% | 3.3% | 1008 | 969 | yes |

Levels: COMFORTABLE = the lower bound reaches the need even at a 10% harmful share. ONLY IF HARM IS HIGH = it reaches the need only at 25%. BORDERLINE = only the best guess reaches the need at 25%. SHORT = even the best guess is below the need at 25%. The held-out stage needs only 60 harmful flips, so the development need (120) is the harder one.

## What this pilot cannot tell you (read before you quote any number)

- The reports are templated. I wrote the templates and the Rule engine, so Rule and TF-IDF/LR can look better here than on real messages. Trust the held-out (style B) rows more than the development rows.
- Harm is not measured. Only flips are. The harmful share needs the simulator and the forks (design stage B).
- Q8_0 is not a safe 'no change' control. Quantizing to 8 bits can still change some decisions.
- One model family (Llama 3.2 1B), one quantization tool (llama-quantize, no importance matrix), one prompt family, one laptop.
- Greedy decoding with a fixed seed. The FP16 restart run is the test of whether the engine is repeatable on your machine.
- The class mix (25% create, 20% update, 15% close, 40% no action) is my guess. Mission logs will have a different mix, so the real flip rate will differ.
- Cases in one family share a template, so they tend to flip together. The family-bootstrap intervals allow for this; the Wilson intervals do not.
- This is the mini pilot on made-up reports. The pilot in your design (100 mission-sets, 60 forks) needs the simulator and comes later.
- Do not reuse these cases in the confirmatory study.

## Files to send back

`results/pilot_report.md`, `results/summary.json`, `results/env.json`, `results/model_hashes.json`. Do not send the model files.
