# Iteration 2, Amendment 1 (written 2026-11-14, BEFORE any iteration-2 result was looked at)

Parent: `docs/ITERATION2_PROTOCOL.md` (hash `ac3cd73a...`, unchanged). Approved by Samadhi on 2026-11-14 (answer "Yes, add the control file").

## Why

The in-domain calibration text was used in full: 181 chunks of 1024 tokens (about 185,000 tokens, see `logs/iter2/imatrix_domain_gguf.log`). The generic text (bartowski `calibration_datav3.txt`, 279,515 bytes) is shorter. A difference between "in-domain" and "generic" could then come from the amount of text and not from the kind of text. A reviewer would ask for this control, and it is cheap.

## What is added (one file, nothing else)

* `Q4_IMX_DOMAIN_M`: Q4_K_M made with an importance matrix from the SAME in-domain text file, cut to exactly the number of chunks that `llama-imatrix` really used for the generic file (read from `logs/iter2/imatrix_generic_gguf.log`, line "computing over N chunks"), with `--chunks N`, `-c 1024`, the same `--parse-special` as the in-domain file, the same quantize command, the same FP16 source.
* Vectors, readouts and missions for it exactly as for the other files (protocol sections 3 and 4).

## What does NOT change

* The primary test (protocol section 4: Q4_IMX_DOMAIN minus Q4, MATCHED at `prefix`, level M) and the decision rule for "SUPPORTED on DEV / NOT SHOWN" (section 5, first bullet).
* No setting of the three original files.

## Use of the control (fixed now)

* The statement "in-domain text matters" needs CI(Q4_IMX_DOMAIN_M minus Q4_IMX_GENERIC) upper bound < 0 at M (MATCHED, `prefix`). The unmatched comparison Q4_IMX_DOMAIN minus Q4_IMX_GENERIC is still printed, labelled "budgets differ".
* Q4_IMX_DOMAIN minus Q4_IMX_DOMAIN_M is printed as the "more text" effect.
* If the control file does not win against generic but the full file does, the only allowed statement is "more calibration text helps", not "in-domain".
* If the generic file cannot be made, the in-domain-versus-generic comparison is reported as incomplete.
* Both further files are reported whatever they show. No further file is added after this.
