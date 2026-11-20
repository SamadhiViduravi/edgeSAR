# Update package, 13 Nov 2026 evening (iteration 1)

Extract this zip INSIDE `D:\1 Samadhi UNI\aFYP\Claude\edgesar_shield` (so that `tools\bench_local.py` sits next to your `tools\check_inputs.py`). Answer "yes" if Windows asks to replace files.

It adds new files and replaces only these existing ones: `README.md`, `docs\DEVIATIONS.md`, `docs\EVAL_PLAN_FRESH.md` (a note at the top; still a draft), `tests\test_fresh.py`.
It does NOT touch `shield\devrun.py` (keep the version from the Windows repair), the cache, or any old result.

Then, in CMD:

    cd /d "D:\1 Samadhi UNI\aFYP\Claude\edgesar_shield"
    python -m pytest -q tests\test_iter1.py
    python -m pytest -q tests\test_fresh.py
    python -m pip install psutil
    python tools\bench_local.py --llama-dir D:\llama --models-dir D:\llama\models --n 100
    python tools\bench_local.py --llama-dir D:\llama --models-dir D:\llama\models --n 100 --cpu

Expected: test_iter1 17 passed; test_fresh: all pass, with 1 skipped (the bit-for-bit comparison with the cloud cache is skipped on a different machine, by design).
Close other GPU programs before the benchmark. Send back `results\bench_<time>\BENCH.md` and `bench.json`.
Read `ITERATION1_EVIDENCE.md` first.
