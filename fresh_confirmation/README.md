# EdgeSAR fresh confirmation package (version 1.2, 19 Nov 2026)

Pre-registered confirmation of the EdgeSAR development results on 7,000 freshly generated reports.

## Rebuild the primary table with one command
    python rebuild_primary.py episode_outcomes.csv
(Python 3 + numpy.) It recomputes H1, H2a, H2b and H3 (paired episode bootstrap, sign-flip test, Holm) from the per-episode outcomes and checks
every value against `results.json`.

## Files
| File | What it is |
|---|---|
| `PROTOCOL_FRESH_CONFIRM.md` | The frozen protocol (written before any fresh data) |
| `FROZEN.sha256`, `FROZEN_INFO.txt` | Hashes of the protocol, the three scripts and the pre-freeze check; freeze time |
| `TIMESTAMP_EVIDENCE.md` | Dated record: freeze, upload to the shared supervisor folder, extraction, analysis |
| `CHECK_results.json`, `CHECK_RESULTS.md` | Pre-freeze check: the analysis code reproduced the saved development style-B results exactly |
| `gen_fresh.py` | Makes the fresh reports from the published generator (seeds 20261118 and 20261119) |
| `cases_fresh.jsonl`, `generation_manifest.json` | The 7,000 fresh reports and how they were made |
| `episode_manifest.csv` | Which report is in which episode and position |
| `fresh_extract.py`, `extraction_report.json`, `case_ids.json` | GPU extraction script, anchor check (cosine 1.0) and SHA-256 of the four vector files |
| `fresh_confirm.py` | The frozen analysis script (one run) |
| `results.json`, `RESULTS.md` | All registered results |
| `episode_outcomes.csv` | Missed, late and unverified incidents per set, load, arrival seed, episode and arm (78,750 rows) |
| `rebuild_primary.py` | One-command rebuild of the primary table |
| `records/records_<set>_<load>_s<seed>.json.gz` | Registered per-episode records of every arm (the source of `episode_outcomes.csv`) |
| `RUN_NOTES_AND_DEVIATIONS.md` | Everything that happened around the run |
| `review_analyses.py`, `review_r2b.py`, `review_r2c.py`, `review_r7.py` | Exploratory analyses added after the registered run, in answer to review (not pre-registered); `review_r7.py` (22 Nov 2026) is the label accounting of Table 10; `review_overlap.py` (23 Nov 2026) is the overlap of Table 6 by development population |
| `REVIEW_RESULTS.md`, `review_results.json`, `review_results_r2b.json`, `review_results_r2c.json`, `review_results_r7.json`, `review_overlap_by_population.json` | Their outputs (Tables 6 to 10 of the paper) |

The hidden-state vectors (4 x 57 MB) and model files are not in this package. The vectors can be re-made with `fresh_extract.py` and the
audited GGUF files (llama.cpp b11901); their SHA-256 values are in `extraction_report.json`.
Data CC BY 4.0, code MIT, as in EdgeSAR-Reports-1400 (doi:10.5281/zenodo.24218688).

## Exploratory analyses (added after review, not pre-registered)
    python review_analyses.py --root <EdgeSAR code root> --cases cases_fresh.jsonl --vectors <vector folder> --fresh-out <folder with results.json and the records_*.json.gz files> --out out_review
    python review_r2b.py  (same arguments)   # episodes from unseen templates only
    python review_r2c.py  (same arguments)   # control: all reports regrouped the same way, and the action mix of each subset
    python review_r7.py   (same arguments)   # label accounting: map from 100/300 pairs, FP16 heads on 100/300 labels, equal supervision (Table 10)
    python review_overlap.py --root ROOT --cases fresh/cases_fresh.jsonl --out out_review   # overlap by development population (Table 6)
These need the hidden-state vectors and the EdgeSAR code (Zenodo record). Each first checks that the refitted arms reproduce the registered
missed counts exactly (R0) and stops if not. They were run after the registered results were known and do not change them.
