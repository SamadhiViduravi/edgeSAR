# Timestamp evidence for the fresh confirmation (all times UTC unless marked)

| Event | Time | Evidence |
|---|---|---|
| Protocol and scripts hashed (`FROZEN.sha256`) | 2026-11-18 14:16:03 | `FROZEN_INFO.txt` |
| Final 7,000 fresh reports generated (inputs only, deterministic from the frozen `gen_fresh.py` and its seeds; no model run) | 2026-11-18 14:16:04 | `generation_manifest.json` "made" |
| Protocol uploaded to the shared supervisor Google Drive folder "2026-11-18 update" | 2026-11-18 14:17:03 | Drive file `PROTOCOL_FRESH_CONFIRM.md`, id 1Hft7ts8k2CypUamYN5mws7QpjDC2N6oQ, createdTime 2026-11-18T14:17:03.053Z (visible to both supervisors) |
| Hash file uploaded to the same folder | 2026-11-18 14:17:05 | Drive file `FROZEN.sha256`, id 1OYO9aze4yf5sRUN4IStck6anEdXq5hSK, createdTime 2026-11-18T14:17:05.215Z |
| First GPU attempt (failed to load the model; no vector produced) | about 2026-11-18 14:44 | `RUN_NOTES_AND_DEVIATIONS.md` item 2 |
| Fresh-vector extraction started | 2026-11-18 14:49:19 (20:19:19 Colombo) | `extraction_report.json` "started" |
| Fresh-vector extraction finished | 2026-11-18 15:47:14 (21:17:14 Colombo) | `extraction_report.json` "finished" |
| Fresh analysis (one run) | 2026-11-18 18:18:57 to 18:47:13 | `results.json` (script hash inside equals `FROZEN.sha256`) |
| Exploratory analyses after review (not pre-registered; do not change `results.json`) | 2026-11-19 03:32 to 03:48 | `review_results_r2b.json`, `review_results_r2c.json`, `review_results.json` (run times inside) |

The Drive creation times are recorded by Google and cannot be set by the uploader. The SHA-256 values in `FROZEN.sha256` can be checked
against the files in this package with `sha256sum -c FROZEN.sha256` (Linux) or `certutil -hashfile <file> SHA256` (Windows).

Before the freeze, a smaller code-test generation with the same generator (150 set-A episodes) was made to test the scripts; no model was run on it and only
its input counts were looked at (protocol section 3). The externally dated claim is therefore: the protocol and hash file were deposited before any model
output on the fresh reports existed.
