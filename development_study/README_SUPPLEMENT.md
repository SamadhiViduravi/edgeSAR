# EdgeSAR supplement (version 3): files behind the label-budget, cost, gold-replacement, text-baseline and wording-shift results

This supplement adds files that are NOT in `EdgeSAR_dataset_release_v1.0.zip` (the Zenodo release, DOI 10.5281/zenodo.24218688). The release is unchanged. Everything here is development-data, exploratory evidence.

## What is inside
- `practical_advantage/` : the measurement plans, each written and hashed before its run (`PROTOCOL_PRACTICAL_ADVANTAGE.md` SHA-256 453c3059...b211; `PROTOCOL_TEXT_BASELINES.md` 33948c87...509a; `PROTOCOL_WORDING_SHIFT.md` efb54e7c...f4b3; each with a `.sha256` file), the scripts and their outputs:
  - `bench_cost.py`, `mission_gold_trace.py`, `power_design.py`, `load_levels_from_records.py`, `verify_from_records.py` and `out_cost/`, `out_trace/`, `out_levels/` (cost, label budget, gold-value replacement, load levels);
  - `text_baselines_mission.py`, `verify_text_baselines.py`, `out_text_baselines/` (TF-IDF and keyword rules in the style-A mission simulator);
  - `wording_shift_mission.py`, `verify_wording_shift.py`, `out_wording_shift/` (the saved style-B predictions in the mission simulator, with an audit of the inputs);
  - `release_only.py` (lets the study code run from the public release alone), `compare_records.py` (compares two runs record by record).
- `repair_package/` : the earlier label-free alignment package (`ppr_lib.py`, `mission_ladder.py`, protocols with hashes in `MANIFEST.sha256`) and its outputs, including the saved style-B predictions (`out/predictions.csv`, `out2/predictions.csv`) and the per-episode mission records of the all-label arms at load levels L, M and H (`out_mission/records_*_s*.json.gz`).
- `CHECKSUMS.sha256` : SHA-256 of every other file in this ZIP (`sha256sum -c CHECKSUMS.sha256` from this folder).

## Protocol file note
`practical_advantage/PROTOCOL_PRACTICAL_ADVANTAGE.md` is the ORIGINAL file, byte for byte: its SHA-256 (453c3059...b211) equals the hash recorded in `PROTOCOL_PRACTICAL_ADVANTAGE.sha256` and `out_trace/PROTOCOL.sha256`. Its line 3 names the earlier review score that triggered the check. The author's rule is to show that line to no gate-review chat; a variant of this ZIP with a reworded copy exists for that purpose.

`repair_package/REPAIR_FIRST_RESPONSE.md`, a long progress note written during the earlier repair work (not a protocol, script or result), is omitted, although `repair_package/MANIFEST.sha256` still lists it.

## Run from the public release alone (new in version 3; no hidden vectors, no private workspace)
Version 2 of this README said that `--no-cache` needs only the report texts. That was not true: the study code still looked for the saved hidden vectors, for `edgesar_pilot/data/cases.jsonl` in its Windows (CRLF) form, and for the author's duplicate-cluster file. `release_only.py` removes these three dependencies without changing any file of the release:
1. the published `data/cases.jsonl` (LF, SHA-256 833fafe2...) is checked, converted back to the CRLF form used in the experiments, and that form is checked against the pinned hash 3c51f0b4...;
2. the family and the duplicate cluster of each report (cluster = identical text; 1,232 clusters for 1,400 reports) are rebuilt from the texts;
3. the four pins of the hidden-vector files are skipped and the vector loader is replaced by an empty stand-in; the TF-IDF, rule and replay arms use no vectors. All other pinned study files (10) are still checked against their audited SHA-256.
Needs Python 3.12+, numpy, scipy, scikit-learn. Unzip the dataset release into a folder `release` (it must contain `code/` and `data/`), then, from this folder:

    python practical_advantage/text_baselines_mission.py --release release --ref repair_package/out_mission --out out_new
    python practical_advantage/compare_records.py out_new practical_advantage/out_text_baselines
    python practical_advantage/wording_shift_mission.py --release release --out out_ws
    python practical_advantage/compare_records.py out_ws practical_advantage/out_wording_shift
    python practical_advantage/verify_wording_shift.py practical_advantage/out_wording_shift

The first run takes about 45 s, the second about 75 s. `compare_records.py` ignores only the wall-clock timing fields. The older command with `--root <folder holding edgesar_shield, edgesar_pilot, edgesar_heads, V1>` still works for the author's workspace layout.

## Conventional text baselines in the mission simulator (style A, development wording)
`PROTOCOL_TEXT_BASELINES.md`, `text_baselines_mission.py`: the pilot's TF-IDF + logistic-regression classifier and keyword rule engine, unchanged, through the same simulator, evaluation reports, load levels (L, M, H), arrival seeds and training folds as the hidden-vector arms. Results: `out_text_baselines/TEXT_BASELINES_RESULTS.md`, `results.json`, per-episode records. Integrity: the re-run gold arm reproduced the saved counts in 450 of 450 episodes. Every result is reported. Numpy-only check: `python practical_advantage/verify_text_baselines.py repair_package/out_mission practical_advantage/out_text_baselines`.

## Wording-shift check (style B, new wording, 400 reports)
`PROTOCOL_WORDING_SHIFT.md`, `wording_shift_mission.py`: the style-B predictions saved in `repair_package/out/` (reading position `end`) and `repair_package/out2/` (`prefix`) are replayed, as saved, through the same mission episodes (same builder, 20 reports per episode, gaps 60 / 30 / 8 s, arrival seeds 1 to 3) at the three load levels. Nothing is refitted, extracted or tuned. Before any mission is run the script checks file integrity, coverage, the training protocol (1,000 style-A reports and labels, 400 style-B test reports), duplicate handling (no style-B text occurs in style A), record parity and assembler parity, and prints what each arm sees; the audit is `out_wording_shift/WORDING_SHIFT_AUDIT.md`, the results are `out_wording_shift/WORDING_SHIFT_RESULTS.md`. Style B has been inspected many times, so this is exploratory; there are no 100- or 300-label arms for style B.

## Path fix
`bench_cost.py` and `mission_gold_trace.py` looked for the repair package at `repair_pkg/edgesar_repair_2026-11-14`; in this supplement it is `repair_package/`. The patched scripts try `repair_package/` first and then the old path; nothing else changed. The scripts exactly as they were run are in `practical_advantage/as_run/` with their SHA-256 (`SHA256_as_run.txt`), which also holds `text_baselines_mission.py` as run for `out_text_baselines/` (the file in `practical_advantage/` adds the `--release` option).

## Check the headline numbers without any model (numpy only, seconds)
    python practical_advantage/verify_from_records.py practical_advantage/out_trace/records_M.json.gz
    python practical_advantage/verify_from_records.py repair_package/out_mission/records_L_s*.json.gz
    python practical_advantage/verify_from_records.py repair_package/out_mission/records_M_s*.json.gz
    python practical_advantage/verify_from_records.py repair_package/out_mission/records_H_s*.json.gz
The first command prints the missed share of the gold, F16, retrained (100 / 300 / all labels), map, recentred and unchanged-transfer arms at medium load and the paired differences. Expected values are in `practical_advantage/out_trace/TRACE_RESULTS.md`.

## What is NOT included, and why
- The saved hidden vectors and the model files (GGUF) are not included (size; the release also has none). The cost benchmark, the label-budget re-run and any refit of the heads need them; the per-episode records and saved predictions above are the saved outputs of those runs.
- Cost timings were measured on a 2-vCPU cloud CPU, not on the laptop or on the target device.
- The simulator, the allocator and the head-fitting code (`shield/`) are in the release code folder.

## Limits that apply to every number
Synthetic reports (125 texts repeat in style A; 26 text groups repeat in style B). The arrival seeds reuse the same reports, so pooled intervals are optimistic. The 100- and 300-label arms use one random label subset per fold and exist at medium load on style A only. The F16 classifier used by the map was trained on about 520 labels per fold in the style-A mission analysis and on 1,000 labels in the style-B check. The reading position `prefix` and the 100-label focus were chosen or highlighted after development results were seen. Style B was examined many times before this check.
