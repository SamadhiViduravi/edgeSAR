# edgesar_shield

Code and results for the strengthening plan of 13 Nov 2026 (EdgeSAR: Q4-quantised Llama 3.2 1B writes task records for a multi-UAV flood search-and-rescue allocator).
It holds a bounded CBBA allocator, an episode simulator with a hidden-truth wall, the Shield (calibrated candidate sets, execution signatures, requirement check, feasible fallback),
15 comparison systems ("arms"), development results on the saved vectors, a demo, and the tools for one frozen fresh test.

**Read in this order:** `ITERATION1_EVIDENCE.md` (newest: the bounded development round of 13 Nov evening) -> `IMPLEMENTATION_EVIDENCE.md` (what was built, what improved, what failed, what is untested) -> `docs/DEVIATIONS.md` (where this differs from the plan) ->
`docs/EVAL_PLAN_FRESH.md` (the draft plan for the fresh test; `STATUS: DRAFT`).

## Status (13 Nov 2026)

* Done on **development data** (the saved vectors of the 1,000 style-A pilot reports): milestones M0 (partly) and M1 to M7, GPU extraction script, freeze tools, demo.
* **Not started:** M8, the fresh test. No fresh report exists. The plan is not frozen and not sent to the supervisors.
* Every development number is exploratory.

## Iteration 1 (13 Nov evening): one bounded development round

Protocol first (`docs/ITERATION1_PROTOCOL.md`, hashed in `results/iter1/PROTOCOL.sha256`), then every variant once on development data. Label by the fixed rule: **NOT SHOWN** for a head retrained on Q4; large protection for a head that was not adapted. Read `ITERATION1_EVIDENCE.md`.

```
python -m pytest -q tests/test_iter1.py                          # 17 checks, about 1 minute
python tools/run_iter1.py --tag q4 --readout q4 --processes 2    # also f16, q8, raw (each about 5 to 8 minutes); refuses if the protocol file changed
python tools/analyze_iter1.py                                    # results/iter1/ITER1_RESULTS.md and .json
python tools/power_iter1.py --tag q4                             # sample-size table (also --tag raw)
python tools/bench_local.py --llama-dir D:\llama --models-dir D:\llama\models --n 100    # speed and memory on YOUR computer (add --cpu; pip install psutil)
python tools/bench_local.py --shield-only                        # Shield and allocator timing only
python tools/build_iter1_evidence.py                             # rebuild ITERATION1_EVIDENCE.md
```
Old results are untouched. `tools/run_fresh.py` does not run the iteration-1 arms yet.

## Folder map

| Path | What |
|---|---|
| `shield/` | The library: `alloc.py` (bounded CBBA + legacy wrapper), `sim.py`, `core.py` (simulator, truth wall), `policy.py`, `cover.py`, `oracle.py` (arms), `candidates.py`, `calibrate.py`, `readout.py`, `service.py` (heads, candidates, conformal sets), `data.py`, `devset.py`, `episodes.py`, `devrun.py` (development), `freshset.py`, `frozen.py` (fresh test and freeze), `paths.py` (input pins) |
| `tools/` | Command-line tools (see below) |
| `tests/` | 110 automatic checks: `test_cbba.py` (18), `test_sim.py` (23), `test_policy.py` (26), `test_extraction.py` (11), `test_fresh.py` (15), `test_iter1.py` (17); on Windows also `test_windows_spawn.py` (3, from the main chat's patch) |
| `docs/` | `EVAL_PLAN_FRESH.md` (draft plan), `DEVIATIONS.md` |
| `results/` | `dev/<tag>/` development runs, `M1_cbba_report.md`, `M4_readout_report.md`, `demo_output.txt`, `audit_rerun_cloud/`, test logs. After the fresh run: `results/fresh/` |
| `demo.py` | Nine cases chosen by a fixed rule: eight outcome classes and one failure case |
| `IMPLEMENTATION_EVIDENCE.md` | The evidence document. Built by `tools/build_evidence.py` from the result files (no number is typed by hand) |

## Quick start

Needs Python 3.12 or newer, `numpy`, `scipy`, `scikit-learn`, `pytest`. The older folders `edgesar_pilot`, `edgesar_heads`, `V1` and `edgesar_audit_2026-11-13` must sit **next to** this folder (or set `EDGESAR_ROOT`). They are read-only.

```
python tools/check_inputs.py                  # the 14 pinned files are exactly the audited versions
python -m pytest -q tests                     # 91 checks; test_fresh.py takes about 4 minutes
python demo.py                                # the demo, including the failure case
python tools/analyze_dev.py --tag main        # tables from results/dev/main
python tools/verify_dev_numbers.py --tag main # recompute the headline numbers from the raw records with independent code
python tools/build_evidence.py                # rebuild IMPLEMENTATION_EVIDENCE.md
```

To rerun the development experiments (about 10 minutes on 2 cores for `main`):

```
python tools/build_readout_cache.py                                    # heads on the saved vectors (deterministic)
python tools/run_dev.py --tag main --levels L M H --seeds 1 2 3
python tools/run_dev.py --tag raw  --levels M H --seeds 1 2 3 --readout raw     # the deliberately mismatched head
bash tools/run_sensitivity.sh                                           # one setting changed at a time
python tools/compare_runs.py main main_first                            # are two runs identical? (wall times ignored)
```

## The fresh test (M8): who does what, and what stops a run

Do **not** start before the plan is approved. Order:

1. Main chat / Samadhi approve `docs/EVAL_PLAN_FRESH.md` and set `STATUS: FROZEN-READY` in it.
2. `python tools/freeze_plan.py` writes `docs/EVAL_PLAN_FRESH.sha256` (hash of the plan and a fingerprint of all `shield/*.py` and the five tools `run_fresh.py`, `analyze_dev.py`, `gen_episodes_fresh.py`, `extract_fresh_vectors.py`, `freeze_plan.py`). Email the printed hash and time to the supervisors. Commit it.
3. `python tools/gen_episodes_fresh.py --seed 20261201 --cal-episodes 40 --eval-episodes 1100 --out fresh/` (CPU, no model).
4. Copy `fresh/cases_fresh.jsonl` to the GPU computer. Run `tools/extract_fresh_vectors.py` (exact command in its header; llama.cpp b11901, prompt P1, three audited gguf files; about 2 hours; it stops at the first failed check).
5. Bring `fresh/vectors/` back. `python tools/run_fresh.py --cases fresh/cases_fresh.jsonl --vectors fresh/vectors --check-only`, then `--tag all`.
6. `python tools/analyze_dev.py --base fresh --tag main` (and the other tags). One run only.

`tools/run_fresh.py` **refuses to run** if: there is no freeze file; the plan or any fingerprinted code file changed; the cases file differs from what the frozen seed generates; the extraction manifest is missing, not OK, or its vector hashes differ; or the run was already done (a repeat needs `--rerun-reason`, is logged as a deviation, and keeps the old files).

## Rules of this folder

* The older folders are never written to. Their key files are pinned by SHA-256 in `shield/paths.py`.
* After the freeze, do not edit `shield/*.py` or the five fingerprinted tools. A change needs a new freeze and a written note in `docs/DEVIATIONS.md`.
* Style B was not used to choose anything. It is touched once, as an exploratory check (tag `sb`), after the main report is written.
* Runtime decisions never read hidden truth (tests in `tests/test_sim.py` and `tests/test_policy.py`).
* Missing candidates, time-outs, unavailable fallbacks and unresolved incidents are separate classes in every table. Every real incident is in every denominator.

## Environment of the saved results

Python 3.13 (cloud session), numpy 2.5.3, scikit-learn 1.9.1, scipy 1.18. The project environment is Python 3.12.6, numpy 2.5.3, scikit-learn 1.9.1: `tools/check_inputs.py` prints both. A different platform can move a few near-tie records (AUDIT_REPORT section 5).
`git init` must be run **inside** this folder only.
