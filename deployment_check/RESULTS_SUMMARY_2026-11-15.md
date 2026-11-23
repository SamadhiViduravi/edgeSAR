# Deployment check: real results (Windows PC, CPU only). Written Sun 15 Nov 2026

**Read this first.** All numbers are for ONE Windows PC (i5-11400H, 6 cores, 16 GB RAM, Windows 11, llama.cpp b11901, Q4_K_M model, 6 threads, no GPU used).
This is **not** a test of a 2 GB device. Nothing here says "passes 2 GB". The gate was not run and no model was changed.

## 1. The runs

| Run | Setting | Reports | Status |
|---|---|---|---|
| A | CPU only, weights memory-mapped (llama.cpp default), context 4096 | 400 (all style-B) | FINISHED |
| B | weights in private memory (`--load-mode none`), context 4096 | 100 | FINISHED |
| C | as B, context 1024 | 100 | FINISHED |
| D | as C, Windows Job Object cap 2048 MB of committed memory for all processes | 100 | FINISHED (cap was not reached) |
| Smoke | 20 reports, CPU only | 20 | FINISHED (PC was short of free RAM at that time; not used for numbers) |
| GPU check (2 tries) | -ngl 99 on the CUDA llama.cpp folder | 20 | **INVALID**: that llama-server lists "Available devices: (none)", so it ran on the CPU. The report says "GPU NOT USED". No GPU result exists. |

Why B, C, D were re-run: the first attempt failed in 15 s because llama.cpp b11901 no longer accepts `--no-mmap`. The program now reads the server's own `--help` and uses `--load-mode none` (two public sources say `none` replaces `--no-mmap`; the program checks that `none` is in the server's own help). The failed first attempt is in the decision log.

## 2. Memory (MB = MiB). Whole pipeline: python program + llama-server together

| Run | Sum of OS peak working sets (upper bound) | Sampled combined working set | Job peak commit (Windows) | llama-server private bytes (sampled peak) |
|---|---|---|---|---|
| A (mmap, ctx 4096) | 1458 | 1452 | 996 | not recorded (field added later) |
| B (private, ctx 4096) | 1214 | 1234 | 1307 | 1163 |
| C (private, ctx 1024) | 1117 | 1137 | 1203 | 1061 |
| D (C + 2048 MB cap) | 1119 | 1139 | 1205 | 1061 |

* Working set = RAM actually resident (includes mapped model pages). Commit = memory that needs RAM or pagefile (does not include mapped model file pages, so Run A's commit is low because the weights are mapped; B/C/D count the weights).
* Largest value of any measure in any run: 1458 MB (Run A, sum of OS peak working sets). Largest commit: 1307 MB (Run B).
* Context 1024 instead of 4096 saved about 100 MB in the server (1163 to 1061 private). The longest prompt has 659 to 670 tokens, so 1024 is enough for these reports.
* Run D ran under a 2048 MB commit cap and finished with a 1205 MB peak, so the cap did not bind. The cap itself was checked in STEP1 (program and child were both blocked at 2x a 400 MB cap).
* The python program holds the study code (simulator, scikit-learn). Its own peak is about 140 MB. A stripped build was not made.
* Paging: free RAM stayed at or above 2391 MB in B, C, D (lowest during the mission) and 3472 MB in A; the pagefile did not grow by more than about 25 MB. So the PC was not short of memory in these runs. This says nothing about a computer that really has only 2 GB.

## 3. Speed (per report, report arrives to record committed to new plan ready; measured with a stopwatch)

| Run | mean | p50 | p95 | max |
|---|---|---|---|---|
| A (400 reports) | 1980 ms | 1965 | 2158 | 3012 |
| B | 1973 ms | 1976 | 2123 | 2166 |
| C | 1997 ms | 2000 | 2231 | 2615 |
| D | 2090 ms | 2040 | 2611 | 2795 |

* The Q4 forward pass (prompt of about 620 tokens) is almost all of it: about 300 prompt tokens per second on this CPU. The folded classifier takes about 0.1 ms. The allocator (study CBBA) takes about 0.3 to 0.4 ms per run and about 1 ms per report.
* For comparison, the original extraction on the RTX 2050 GPU took about 106 ms per report. So the CPU-only path is about 19 times slower on this PC.
* Same prompt twice gives the same vector (difference 0.0), and B, C, D give exactly the same records as Run A on the same 100 reports. So `--load-mode none` and context 1024 do not change decisions in this test.

## 4. Do the CPU decisions equal the saved ones? (this is the important caution)

| | Run A, 400 reports | first 100 reports (B, C, D identical) |
|---|---|---|
| Record equal to the saved record (made from GPU vectors) | 358 of 400 | 87 of 100 |
| Action equal | 390 of 400 | 95 of 100 |
| Live vector vs saved vector, cosine min / median | 0.9969 / 0.9984 | 0.9975 / 0.9984 |
| Whole record equals GOLD: live CPU / saved | 273 (68.2%) / 285 (71.2%) | 69 / 74 |
| Only live right / only saved right | 5 / 17 (sign test p = 0.017, exploratory) | 0 / 5 (p = 0.062) |
| Mission replay, missed incidents live / saved | 66 of 752 (8.78%) / 65 of 752 (8.64%) | 15 of 173 (8.67%) / 13 of 173 (7.51%) |

* Every live vector differs a little from the saved one (cosine about 0.998 for all reports). The classifier and the map were fitted on the saved (GPU) vectors. A small systematic CPU-versus-GPU difference is the most likely reason, but it is **not confirmed**: the GPU check could not run (see section 1).
* So the CPU path loses about 3 points of exact-record accuracy against gold in Run A (68.2% vs 71.2%). The action itself is almost unchanged (375 vs 377 of 400). The mission miss rate is almost the same in the 400-report replay. These are exploratory numbers on a dataset that has been inspected many times.
* Not done and not decided: re-fitting the map and heads on CPU vectors would be a new experiment. It was not run.
* Mission replay is an agreement check only. The 2 s CPU inference time is NOT injected as a mission delay, so this does not validate real-time mission performance.

## 5. What can be said, and what cannot

Can be said (measured):
* On this Windows PC, CPU only, the whole pipeline (python program plus llama-server) used between about 1.1 and 1.5 GB of RAM (working set) and at most 1.3 GB of committed memory in these runs, and about 2 s per report.
* A run under a 2048 MB Windows commit cap finished.
* Decisions follow the saved ones in 358 of 400 reports; the loss in exact-record accuracy against gold is about 3 points (exploratory).

Not demonstrated:
* Operation on a real 2 GB device (the operating system, file cache and other programs also need memory there; CPU speed and cooling differ).
* Real-time mission performance with a 2 s decision delay.
* Energy per report.
* That the CPU-versus-GPU difference is only numeric drift (GPU check invalid).

Next evidence that would matter: a real 2 GB board, or a Linux/WSL2 virtual machine with a hard 2 GB limit; energy per report; (if wanted) a re-fit on CPU vectors.

## 6. Where the files are

Folder: `D:\1 Samadhi UNI\aFYP\Claude\edgesar_shield\submission\DEPLOYMENT_CHECK\out\`
* `A_cpu_mmap_ctx4096_400reports`, `B_cpu_nommap_ctx4096_100reports`, `C_cpu_nommap_ctx1024_100reports`, `D_cap2048_nommap_ctx1024_100reports`: each has `DEPLOYMENT_REPORT.md`, `QUALITY_vs_GOLD.md`, `results.json`, `per_report.csv`, `memory_series.csv`, `server.log`.
* `SMOKE_20_reports`, `DIAG_GPU_20_reports`, `DIAG2_GPU_20_reports`: kept for the record; the two GPU folders are INVALID as GPU results.
