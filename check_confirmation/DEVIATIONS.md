# Deviations from the frozen protocol and notes on the run

**No frozen file was changed.** `check_confirm.py`, `cases_C.jsonl` and the other frozen files have the SHA-256 values in
`FROZEN.sha256`. The analysis was run once with the command of Section 8 of the protocol (paths shortened there):

    python3 check_confirm.py --root ROOT --cases cases_C.jsonl --vectors vectors_C --dev-vectors vectors_C --out out_checkC --workers 2

The notes below are not changes to the analysis; they record facts a reader may want to check.

1. **The 3-bit model file already existed.** The protocol (Section 3) makes Q3_K_M with `llama-quantize` "if the file does not exist yet".
   The file was already on the laptop: it was made in the pilot study by `make_quants.py` (`zenodo_v1/code/edgesar_pilot/`), from the same
   FP16 file, with the same tool and recipe as the Q4_K_M file and without an importance matrix. Its size in the extraction report
   (690,843,488 bytes) equals the size recorded in the pilot (`zenodo_v1/code/edgesar_pilot/results/model_hashes.json`).
   SHA-256 check on the laptop: PENDING.

2. **Code root.** The analysis machine used its working copy of the code root (with the saved development vectors, which are not in the
   repository). Its 139 code and data files (`.py`, `.json`, `.jsonl`) were compared with a root built by `make_root.py` from this
   repository: all are byte-identical (three result files of the pilot that the analysis does not read were absent from the working copy).

3. **Candidates fitted.** The run log reports "37 candidates fitted" per target; with TF-IDF and the rule engine, which are the same for
   both targets and need no fitting on the quantized vectors, this gives the 39 candidates per target of Section 4.

4. **Earlier exploratory run (R11).** As stated in Section 8 of the protocol, the same script was run on the first confirmation's sets A
   and B (Q4_K_M only) before the freeze; its outputs are in `exploratory_R11_setsAB/` and were read only after the protocol was frozen
   and pushed. They do not enter any hypothesis.
