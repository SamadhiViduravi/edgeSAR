# EdgeSAR heads test: how to run it

Put this folder (`edgesar_heads`) **next to** `edgesar_pilot`, for example `D:\1 Samadhi UNI\aFYP\Claude\edgesar_heads`.
The pilot folder is only **read**. Nothing is written into it. Before every step the kit checks the pilot files against your freeze (28 Oct 2026) and stops if one has changed.

## Before you start (5 minutes)

1. Read `HEADS_TEST_PLAN.md`. Write **your own three guesses** in section 5, date it, save it. Do this **before step 2**. (The reason: you cannot change a guess after you see a result.)
2. Plug in the power. Close games, Chrome video and anything heavy on the GPU. Close any old `llama-server.exe` (Task Manager).
3. Open PowerShell:
   ```
   cd "D:\1 Samadhi UNI\aFYP\Claude\edgesar_heads"
   ```
   The kit uses the same Python packages as the pilot (`numpy`, `scikit-learn`). Same llama.cpp build, same model files. Do not update anything.

## Step 1. Smoke test (about 2 to 4 minutes)

```
python 01_smoke_embed.py
```
**Why:** before we spend an hour, we check that the server really returns a vector for each prompt, that the same prompt gives the same vector, that the token count matches, and that different reports give different vectors.
**You should see:** lines starting with `PASS`, and at the end `RESULT: no FAIL`. A `CHECK` line is a note, not an error.
**Send me:** `results_heads\smoke_report.txt` (before you go on, if there is any `CHECK` or `FAIL`).

## Step 2. Get the vectors (about 30 to 60 minutes, my estimate)

```
python 02_extract.py
```
**Why:** this is the only step that uses the model. It sends all 1,400 prompts to FP16, Q8_0 and Q4_K_M (one server at a time) and saves one vector per report and per variant in `features\`. After this, the model is not needed any more.
**Safe to stop:** press `Ctrl+C`; run the same command again and it continues. It saves every 100 reports.
**For a quick look first (optional):** `python 02_extract.py --limit 50` writes 50 reports to a separate folder and does not touch the real one.

## Step 3. Train the heads and write the report (a few minutes, up to about 20)

```
python 03_heads.py
```
**Why:** trains the three heads on style A, tests them on A (out-of-fold) and once on B, and compares with your pilot numbers (Rule, TF-IDF/LR, the generated answers of FP16/Q8/Q4). No model needed.
**You get:** `results_heads\heads_report.md` (read the table "1. The three outcomes" first), `heads_summary.json`, and a new line in `attempts.log`.
**Send me:** `heads_report.md`, `heads_summary.json`, `smoke_report.txt`, and `features\*.meta.json`.

**Important:** run step 3 for the main result **once**. If you change `heads_config.json` or anything else after you see style B, write what and why in your log. It counts as attempt 2.

## What is in the folder

| File | What it is |
|---|---|
| `HEADS_TEST_PLAN.md` | the plan, fixed before the run, with your guesses |
| `heads_config.json` | all settings (port 8091, variants, regularisation grid, folds) |
| `heads_common.py` | paths, pilot freeze check, prompts, the small client for the server |
| `heads_extract.py` | the loop that collects vectors (and the smoke checks) |
| `heads_lib.py` | the heads, the folds, the measures |
| `heads_report.py` | the numbers and the report text, and the three outcome rules |
| `01_smoke_embed.py`, `02_extract.py`, `03_heads.py` | the three steps |
| `tests\` | 24 tests with a fake server and made-up vectors (`python -m pytest -q`) |

## If something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `Cannot find the pilot folder` | the two folders are not side by side | put them side by side, or fix `pilot_dir` in `heads_config.json` |
| `STOP. The pilot folder is not the frozen one` | a pilot file changed | restore it from your backup; do not go on |
| `Port 8091 is already in use` | an old server is running | end `llama-server.exe` in Task Manager, or change `port` in `heads_config.json` |
| Server stops while loading, or log shows `embeddings` / `pooling` not known | this llama.cpp build does not accept the flags | send me the last 30 lines of `logs\server_*.log`. Do not update llama.cpp |
| `input is too large to process` / token error | batch smaller than the prompt | send me the log. (The longest prompt is 667 tokens; the batch is 1024) |
| `out of memory` / `failed to allocate` | GPU memory is full | close other programs, then `python 02_extract.py --ngl 12` and tell me |
| `FAIL ... SAME vector` in the smoke test | the report text is not reaching the model | stop and send me the smoke report |
| `FAIL ... token count differs` | the prompt is read in a different way than in the pilot | stop and send me the smoke report |
| `The server failed on report c0xxx` | a request failed twice | progress is saved; send me the last 30 lines of `logs\server_*.log`, then run the same command again |
