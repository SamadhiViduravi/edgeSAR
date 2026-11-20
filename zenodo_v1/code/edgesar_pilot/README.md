# EdgeSAR pilot kit (Tue 27 - Thu 29 Oct 2026)

This kit runs a small, honest test before you build the big simulator. Call it the **mini pilot**. The pilot in your design (100 mission-sets, 60 forks) needs the simulator and comes later.
It answers your eight questions with numbers from your own laptop:

1. Is the FP16 model competent at the task?
2. Does it beat "always NO_ACTION" and "always VERIFY"?
3. Do the Rule engine and TF-IDF/LR match or beat it?
4. How often do Q8_0 and Q4_K_M change the FP16 decision?
5. Which kinds of change happen (for example CREATE -> NO_ACTION)?
6. Are the outputs valid under the fixed schema?
7. How fast is your laptop?
8. Are there enough changes ("flips") to justify the CBBA / closed-loop experiment?

It does NOT need the simulator or CBBA. It uses 1,400 made-up field reports (1,000 in style A for development, 400 in style B for held-out).
The reports are made-up text. They contain no personal data. The pilot does not measure harm (that needs the simulator); it measures flips.

**Your computer:** Windows 11, ASUS TUF A17, i5-11400H, RTX 2050 (4 GB), 16 GB RAM. This should be enough. The smoke test in Step 7 will show it.
**Disk space:** about 8 GB free (the four model files are about 2.5 + 1.3 + 0.8 + 0.7 GB).
**Time:** set-up about 1 hour. The full run is about 2 to 4 hours if the GPU is used. It can stop and continue.

---

## Step by step

All commands are typed in **PowerShell**. Replace the folder names if yours are different.

### Step 0. Get the laptop ready
- Plug in the power. Windows: Settings > System > Power & battery > Power mode = **Best performance**. Set "Screen and sleep" to **Never** while plugged in.
- ASUS Armoury Crate (if you have it): choose **Turbo** or **Performance**.
- Close games, video, and anything heavy on the GPU. Speed numbers are wrong if the GPU is busy.
- Unzip this kit to `C:\edgesar_pilot`. Then: `cd C:\edgesar_pilot`

### Step 1. Python packages
```
python --version
python -m pip install numpy scikit-learn
```
Python 3.10 or newer is needed. (If `python` is not found, try `py` instead of `python` everywhere.)

### Step 2. Download llama.cpp (the program that runs the model)
1. Open https://github.com/ggml-org/llama.cpp/releases and open the **latest** release.
2. Under "Assets" download **two** files:
   - `llama-bNNNN-bin-win-cuda-12.4-x64.zip`
   - `cudart-llama-bin-win-cuda-12.4-x64.zip`
   (If you only see newer CUDA versions, like 13.x, take those two instead.)
3. Make the folder `C:\llama`. Unzip **both** files into that same folder.
   `llama-server.exe`, `llama-quantize.exe` and `cudart64_12.dll` must be directly inside `C:\llama` (not in a sub-folder).
4. In PowerShell run `nvidia-smi`. The driver version must be **551 or higher** for the 12.4 files. If it is lower, update the NVIDIA driver first.
5. Test it: run `C:\llama\llama-server.exe --version`. It should print a version line. If Windows says a DLL is missing, see the table at the end.
6. Keep the zip files. **Do not update llama.cpp** until the study is finished. Write the build number in your log (the kit saves it too, in `results\env.json`).

### Step 3. Download the FP16 model (one file, about 2.5 GB)
1. Open https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF
2. Click **Files and versions**. Download **`Llama-3.2-1B-Instruct-f16.gguf`**.
3. Save it in `C:\llama\models` (make the folder).

Do NOT download Q8 or Q4 files from the internet. Step 5 makes them from your FP16 file, so the only difference between models is the precision.

### Step 4. Check `config.json`
Open `config.json` in Notepad. If you used other folders, change `paths.llama_bin_dir` and `paths.models_dir`. Use `/` or `\\` in the paths (for example `C:/llama`).

### Step 5. Make the Q8, Q4 and Q3 files (about 1 minute)
```
python make_quants.py
```
It prints the sizes and writes `results\model_hashes.json` (the file fingerprints).

### Step 6. Check the labels yourself (30 to 45 minutes)
Open `data\audit_sample.csv` in Excel. It has 60 reports with the "correct" answer I built. For each row read the report and the gold answer, then type **y** or **n** in the column "gold looks right?". Write a short note when you say n.
- If you say **n** to 4 or more rows, send me the rows before you run the full test.
- This check is yours. It is evidence that the test labels are fair. Keep the file.

### Step 7. Smoke test (about 1 to 2 minutes)
```
python run_model.py --smoke
```
It should print:
- `special tokens ok: True, start token added once: True`
- `valid under the schema: 20 (100%)`
- `median time per call` about 0.5 to 2 seconds (my estimate), and `VRAM used` about 2,800 to 3,500 MB (my estimate).

If the time per call is above 5 seconds, the GPU is not used. Go to "If something goes wrong".
The smoke test also shows 5 answers next to the gold answers. This is only to check that the machinery works. Do not judge the model from it.

### Step 8. The full run (2 to 4 hours)
```
python run_model.py --all
```
- It runs four sessions one after another: FP16, Q4_K_M, Q8_0, and FP16 again. The second FP16 run is the **repeat test**: it must give the same answers as the first.
- You can stop with `Ctrl+C` and start again with the same command. It continues where it stopped.
- To see progress at any time: `python run_model.py --list`
- Keep the lid open and the power plugged in. Do not run heavy programs.

### Step 9. Register your plan on OSF first (Wed 28 Oct)
Your own design says the pre-registration comes before you look at pilot results.
**Do not run `analyze.py` and do not open the report until the OSF registration is done.**

### Step 10. Score the results (Thu 29 Oct)
```
python analyze.py
```
Open `results\pilot_report.md`. It starts with a **suggested call** (GO, CONDITIONAL, STOP, or FIX FIRST) and a table of the gates G0 to G5 from your design. Then it answers your eight questions in one table.

Then open `results\flips_Q4_K_M_vs_FP16.csv`. It lists every case where Q4 changed the task table. Read at least 20 of them and write in your own words what kind of change you see. This is your own analysis, not mine.

### Step 11. Send back
- `results\pilot_report.md`
- `results\summary.json`
- `results\env.json`
- `results\model_hashes.json`
- `data\audit_sample.csv` (with your y/n)

Do not send the model files.

---

## Optional: the Q3 arm (only if the report says SHORT or BORDERLINE)
Your design says: if Q4 gives too few flips, add Q3 as a **separate** arm. Step 5 already made the Q3 file.
```
python run_model.py --only s5_q3_optional
python analyze.py
```
This takes about 15 to 30 minutes. The report then shows Q3 next to Q4. Q3 is never mixed into the Q4 numbers.

## If the FP16 model is not competent (gate G1 fails)
Do not panic and do not edit the test cases. Send me the report first. Your design allows fixing the prompt or the grammar on **development** cases (write each change in a change log with the accuracy before and after). If it still fails, the design says to try the 3B model once. That model does not fit fully in 4 GB of GPU memory, so tell me before you try it.

---

## If something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `llama-server not found in C:/llama` | wrong folder | Put the `.exe` files directly in `C:\llama`, or fix `paths.llama_bin_dir` in `config.json` |
| Windows says a DLL is missing (`cudart64_12.dll`, `ggml-cuda.dll`) | the cudart zip is not in the same folder | Unzip the cudart zip into the same folder as `llama-server.exe` |
| `Port 8089 is already in use` | an old `llama-server.exe` is still running | Task Manager > end `llama-server.exe`, or change `server.port` in `config.json` |
| Time per call above 5 s in the smoke test | running on the CPU | Open `logs\server_s1_f16.log`. Look for a line like `offloaded 17/17 layers to GPU` (both numbers equal). If it says 0 layers, you have the wrong zip or an old driver. Update the driver and download the CUDA zip again |
| `out of memory` or `failed to allocate` in the log | GPU memory is full | Close other programs (Chrome, games), then try `python run_model.py --smoke --ngl 12` and tell me, because speed changes |
| `special tokens ok: False` | wrong kind of model file | Download the file named in Step 3 again |
| Warning: `start token is not added exactly once` | the prompt format is not as expected | Stop and tell me before you continue |
| `ModuleNotFoundError` (sklearn, numpy) | package missing | `python -m pip install numpy scikit-learn` |
| Windows asks about the firewall | the server only listens on 127.0.0.1 | Click Cancel (no access is needed) |
| The run stopped (sleep, lid closed, power cut) | normal | Run the same command again. It resumes |
| `5 failed requests in this run` | the server crashed | Send me the last 30 lines of `logs\server_*.log` |

---

## Rules for a clean pilot
1. After you have seen any model result, do not change `data\cases.jsonl`, the prompts in `common.py`, or the baselines in `baselines.py`. The one exception is the fix allowed by gate G1 or G3 on development cases, and then you write a change log.
2. Keep every raw file: `runs\*.jsonl`, `logs\*.log`, `results\*`. Copy the whole folder to a second place (USB or cloud). These files are your evidence.
3. Keep a short log in your own words: date, time, command, and anything strange (a sleep, a crash, a fan noise problem).
4. Never use this pilot's cases in the final study. They are for the pilot only.
5. In your own report, write what the numbers say **and what they cannot say**. The report has a section for this. Use your own words.

## For your PP tables
**AI-use table.** This kit was written with Claude (AI). Write: the tool; what it produced (the case generator, the runner, the analysis script, this README); what you checked (you read every file, ran the tests, checked 60 labels); and what you changed. You must be able to explain each file in the viva:
- `common.py`: the prompt, the schema, the grammar, and the validator.
- `gen_cases.py`: how the 1,400 made-up reports were produced.
- `baselines.py`: the floors, the Rule engine, and TF-IDF/LR.
- `run_model.py`: starts the model, sends the cases, saves the raw answers.
- `analyze.py`: scores the answers and applies the gates.

**Licence table.** Add: Llama 3.2 (Llama 3.2 Community License; the file and its checksum are in `results\model_hashes.json`); llama.cpp (MIT; the build number is in `results\env.json`); scikit-learn and numpy (BSD). Check the Llama licence text yourself before you publish.

## Files in this kit
| File | What it is |
|---|---|
| `config.json` | folders, server settings, and the list of runs |
| `data\cases.jsonl` | the 1,400 made-up reports with the gold answers |
| `data\subsets.json` | which cases go in which run |
| `data\audit_sample.csv` | 60 rows for your label check |
| `gen_cases.py` | the program that made the cases (fixed seed). You do not need to run it; running it again rewrites the files in `data\` |
| `requirements.txt` | the two Python packages |
| `make_quants.py` | makes Q8_0, Q4_K_M and Q3_K_M from the FP16 file |
| `run_model.py` | smoke test and full run |
| `analyze.py` | scoring and the report |
| `runs\` | the raw model answers (made by the run) |
| `logs\` | the server logs |
| `results\` | the report and the numbers |
