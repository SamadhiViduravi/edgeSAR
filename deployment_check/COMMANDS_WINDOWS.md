> Updated by v1.1: start with START_HERE_v1_1.md. Use the shipped batch files. Windows runs A to D are done (see RESULTS_SUMMARY_2026-11-15.md).

# COMMANDS_WINDOWS: how to run the deployment check on your Windows PC

Folder: `D:\1 Samadhi UNI\aFYP\Claude\edgesar_shield\submission\DEPLOYMENT_CHECK`

**Status (15 Nov 2026): Runs A, B, C, D were run on the PC and finished. Results are in `RESULTS_SUMMARY_2026-11-15.md`.** Nobody may say "runs in 2 GB": the numbers are for this PC, not for a 2 GB device. STEP2C (GPU check) is INVALID on this PC because the CUDA llama.cpp folder sees no GPU. In new llama.cpp builds (b11901) `--no-mmap` does not exist any more; the program picks `--load-mode none` by itself.

## What this check does (short)

It runs the whole Q4 pipeline on the **CPU only** (no GPU file is loaded): report text, then the Q4 model (llama-server), then the folded classifier, then the record, then the mission planner (CBBA). While it runs it measures:

1. **Peak memory of all processes together** (the Python program + llama-server).
2. **Time per report**, from "report arrives" to "record ready", and the planner time.
3. **Agreement with the saved predictions** (the same 400 style-B reports).
4. **Settings** (context length, batch size, versions) and **paging** (does Windows use the disk as memory?).

## Before you start (2 minutes)

* Plug in the charger. Set Windows power mode to "Best performance".
* Close the browser and other big programs. Close any other `llama-server` window.
* Do not use the computer while a run is going. A run uses all CPU cores.
* Python must work. Test: open Command Prompt and type `python --version`.

## How to start

Easiest way: double-click the `.bat` files in order. Each one asks you to press a key at the end.

If you prefer typing, open the folder in File Explorer, click the address bar, type `cmd`, press Enter. Then type:

```
cd /d "D:\1 Samadhi UNI\aFYP\Claude\edgesar_shield\submission\DEPLOYMENT_CHECK"
call paths_windows.bat
```

`paths_windows.bat` finds your folders by itself. If a step says "Cannot find ...", open `paths_windows.bat` in Notepad and fix the one line it names.

## The steps

| Step | File | What it does | Time |
|---|---|---|---|
| 1 | `STEP1_install_and_probe.bat` | installs `psutil numpy scipy scikit-learn`; about 40 second test of the measuring tools, including a test that the memory cap really blocks the program and its child | 1 to 3 min |
| 2 | `STEP2_make_cpu_only_llama.bat` | copies only CPU runtime files from your llama.cpp to `D:\llama_cpu_edgesar_v1_1` **without** `ggml-cuda.dll` | 1 min |
| 3 | `STEP3_optional_recreate_folded_classifier.bat` | optional; makes the folded classifier again and compares it with the shipped one | 1 min |
| 4 | `STEP4_run_A_main_400_reports.bat` | **Run A**: main run, 400 reports, same settings as the saved vectors | unknown, longest |
| 5 | `STEP5_run_B_no_mmap_100_reports.bat` | **Run B**: weights in private memory, 100 reports | unknown |
| 6 | `STEP6_run_C_lean_context_100_reports.bat` | **Run C**: like B with context 1024 | unknown |
| 7 | `STEP7_run_D_cap_2048MB_100_reports.bat` | **Run D**: like C, Windows may commit at most 2048 MB for all processes | unknown |
| 8 | `STEP8_optional_run_E_cap_1536MB.bat` | optional **Run E**: stricter cap 1536 MB | unknown |
| 9 | `STEP9_zip_results.bat` | makes `DEPLOYMENT_RESULTS.zip` | seconds |

I do not know how long a run takes. It depends on your CPU. After each episode the screen prints "about N s left".

**Stop rule:** if STEP1 says "SOME PARTS FAILED", do not run the other steps. Copy all the text and give it to Claude.

## The exact commands (same as inside the .bat files)

Run `call paths_windows.bat` once first (see above). Then:

```
:: STEP 1
python -m pip install psutil numpy scipy scikit-learn
python deploy_bench.py probe --tmp "%TEMP%"

:: STEP 2 (CPU-only copy of llama.cpp: everything except ggml-cuda.dll)
python prepare_cpu_runtime.py --source "%LLAMA_SRC%" --destination "%LLAMA_CPU%"
"%LLAMA_CPU%\llama-server.exe" --version

:: STEP 3 (optional; this is the OFFLINE step that sees FP16 vectors; the benchmark does not)
python export_folded_classifier.py --root "%WORKSPACE%" --repair-dir "%REPAIR%" --out "out\folded_recreated" --compare-with "folded"

:: STEP 4  Run A
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\A_cpu_mmap_ctx4096_400reports" --label "A: CPU only, as extracted (mmap, ctx 4096), 400 reports" --episodes 20

:: STEP 5  Run B
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\B_cpu_nommap_ctx4096_100reports" --label "B: CPU only, weights in private memory (no-mmap), ctx 4096, 100 reports" --no-mmap --episodes 5

:: STEP 6  Run C
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\C_cpu_nommap_ctx1024_100reports" --label "C: CPU only, no-mmap, context 1024, 100 reports" --no-mmap --ctx 1024 --episodes 5

:: STEP 7  Run D
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\D_cap2048_nommap_ctx1024_100reports" --label "D: as C, with a 2048 MB hard cap on committed memory of all processes" --no-mmap --ctx 1024 --episodes 5 --job-limit-mb 2048

:: STEP 8  Run E (optional)
python deploy_bench.py run --root "%WORKSPACE%" --repair-dir "%REPAIR%" --server "%SERVER%" --model "%MODEL%" --out "out\E_cap1536_nommap_ctx1024_100reports" --label "E: as C, with a 1536 MB hard cap (stricter, optional)" --no-mmap --ctx 1024 --episodes 5 --job-limit-mb 1536

:: STEP 9
powershell -NoProfile -Command "Compress-Archive -Path 'out' -DestinationPath 'DEPLOYMENT_RESULTS.zip' -Force"
```

What the settings mean:

* `--episodes 20` = all 400 style-B reports (20 reports per episode). `--episodes 5` = the first 100.
* `--no-mmap` = the model weights are copied into the program's own memory. Then Windows "commit" memory includes the weights, so the 2048 MB cap in Run D can see them.
* `--ctx 1024` = context length 1024 tokens. The longest prompt of these reports has 670 tokens, so 1024 is enough. The saved vectors used 4096 (Runs A and B use 4096).
* `--job-limit-mb 2048` = Windows Job Object: all processes of the run together may commit at most 2048 MB. If the server cannot start, that is also a result.
* Always on: `-ngl 0` (no layers on the GPU), `CUDA_VISIBLE_DEVICES=-1`, `-np 1`, `-b 1024 -ub 1024`, `--embeddings --pooling last`, 6 threads.

## When the runs are finished

1. Open each `out\<run name>\DEPLOYMENT_REPORT.md` in Notepad. Do not edit anything.
2. Run `STEP9_zip_results.bat`. It makes **`DEPLOYMENT_RESULTS.zip`** in this folder.
3. Give ChatGPT: `DEPLOYMENT_RESULTS.zip` and `README_FOR_CHATGPT.md`. Tell it which steps you ran and copy any red or error text.
4. If you want ChatGPT to check the program first, give it `EdgeSAR_DEPLOYMENT_CHECK_code_v1.zip` (all scripts and the test; it is in this folder).

Do not run the gate and do not change any proposal text until ChatGPT has read the results.

## If something goes wrong

| What you see | What to do |
|---|---|
| `Cannot find llama-server.exe` / `Cannot find the Q4 model file` | open `paths_windows.bat` in Notepad, fix the line `LLAMA_SRC` or `MODEL` |
| `Cannot find the saved predictions` | give the folder that has `out2\predictions.csv` as `REPAIR` in `paths_windows.bat` |
| Port 8093 is in use | close other llama-server windows; or add `--port 8094` to the command |
| The run stops with `SERVER_FAILED_TO_START` | normal result in Run D/E if the cap is too small. The report says why. Keep it. |
| Windows says "python is not recognized" | install Python from python.org and tick "Add to PATH" |
| The last lines say GPU / CUDA was loaded | `ggml-cuda.dll` is still in `D:\llama_cpu_edgesar_v1_1`. Delete it by hand and run the step again |
