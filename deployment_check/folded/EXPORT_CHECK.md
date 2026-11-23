# Export check: folded Q4 classifiers against the saved style-B predictions

Offline preparation (this step sees FP16 vectors; the deployment benchmark does not). Nothing new was fitted: same functions, same seed as `run_ppr2.py` protocol B.

| Classifier | Saved arm | Reports compared | Whole record equal to saved (float64) | Whole record equal to saved (float32) | Max logit difference vs unfolded (float64 / float32) |
|---|---|---|---|---|---|
| map | C2p | 400 | 400 of 400 | 400 of 400 | 1.55e-13 / 1.44e-05 |
| retrained | MATCHEDp | 400 | 400 of 400 | 400 of 400 | 5.00e-14 / 1.52e-05 |

Size of one folded classifier: 20490 numbers = 81960 bytes in float32.
Overall: **all checks pass (the folded matrices reproduce the saved style-B records)**
arrays SHA-256 `f372b13aaef25ce890a49bbc8f4f99ebc01088c714dab6fe520816acfd466e26`
