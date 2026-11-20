# Iteration 2: what to run on your PC (about 45 to 60 minutes, mostly waiting)

Protocol: `docs\ITERATION2_PROTOCOL.md` (fixed and hashed). Nothing in `edgesar_pilot` or `edgesar_heads` is changed: the scripts only read them and copy `edgesar_heads` to new folders.

## Before you start (5 minutes)

1. Plug in the power. Close games, Chrome video and anything on the GPU. Close any old `llama-server.exe` (Task Manager).
2. **Generic calibration text** (needed for the Q4_IMX_GENERIC file). Search for "bartowski calibration_datav3.txt" (a public file used for llama.cpp importance matrices) and save it as `D:\llama\calib\calib_generic.txt` (make the folder). Any general English text of at least 100 KB also works (for example wikitext-2 raw), but tell me which one you used. If you cannot get it, skip it: the script then makes only the other two files and tells you.
3. About 3 GB of free disk space on D:.

## Step 1: make the model files (10 to 25 minutes)

```
cd "D:\1 Samadhi UNI\aFYP\Claude\edgesar_shield"
python tools\iter2_prepare_models.py make --llama-dir D:\llama --models-dir D:\llama\models --generic-calib D:\llama\calib\calib_generic.txt
```
**Why:** `llama-imatrix` measures which weights matter on the calibration text; `llama-quantize` then keeps those more precise. It also makes a plain Q5_K_M. The first thing it does is check that your FP16 file has the pinned hash.
**You should see:** for each of Q4_IMX_DOMAIN, Q4_IMX_GENERIC and Q5 a line `done: ... GB`.
**If it prints an error:** copy the last lines it shows and send them to me. Do not change any option.

## Step 2: check that the extraction is the same as before (3 minutes)

```
python tools\iter2_prepare_models.py check --models-dir D:\llama\models
```
**Why:** the same pipeline on your existing plain Q4 file must give the same vectors as the ones saved on 11 Nov. If not, a difference later could come from the pipeline and not from the new file.
**You should see:** `IDENTITY CHECK: PASS`. If it says CHECK, send me `results\iter2\identity_check.json` and stop.

## Step 3: get the vectors (about 15 to 25 minutes)

```
python tools\iter2_prepare_models.py extract --models-dir D:\llama\models
```
Safe to stop with Ctrl+C and run again: it continues.
**You should see:** `All collected in ...results\iter2\features`.

## Step 1b (only if Step 1 was run before the generic file had the right name): run Step 1 and Step 3 again

The generic file must be named exactly `calib_generic.txt` (Windows may add a hidden `.txt`: check with `dir D:\llama\calib`). Then run the SAME `make` command and the SAME `extract` command again. They skip every file that is already finished, so only the missing ones are made: `Q4_IMX_GENERIC` and the control `Q4_IMX_DOMAIN_M` (Amendment 1, `docs\ITERATION2_AMENDMENT1.md`). Do not run `03_heads.py`: the line "Next: python 03_heads.py" printed by the extraction is only a hint from the old project and is not part of this round.

## Step 4: tell me

Step 4 is NOT a command. Open this Claude chat and type the message: iter2 vectors ready. (That is all.) I read `results\iter2\features`, `MANIFEST.json` and `identity_check.json` and run the analysis here (about 15 minutes). The decision rule is already fixed in the protocol, so the label comes from the numbers only.
