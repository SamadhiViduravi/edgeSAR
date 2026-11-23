# Deployment benchmark of the Q4 system: A: CPU only, as extracted (mmap, ctx 4096), 400 reports

Status: **FINISHED**. 
This report gives MEASURED NUMBERS for this computer under this test. It does **not** say that a 2 GB device passes (see section 7).

## 1. What was run

* Command: `deploy_bench.py run --root D:\1 Samadhi UNI\aFYP\Claude --repair-dir D:\1 Samadhi UNI\aFYP\Claude\edgesar_repair_2026-11-14 --server D:\llama_cpu_edgesar_v1_1\llama-server.exe --model D:\llama\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf --out out\A_cpu_mmap_ctx4096_400reports --label A: CPU only, as extracted (mmap, ctx 4096), 400 reports --episodes 20`
* llama-server command: `D:\llama_cpu_edgesar_v1_1\llama-server.exe -m D:\llama\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf --host 127.0.0.1 --port 8093 -ngl 0 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024` (environment: CUDA_VISIBLE_DEVICES=-1)
* Context length requested 4096, batch 1024, ubatch 1024, threads 6, weights memory-mapped from the file (llama.cpp default), classifier `map` (float32), mission level M, arrival seed 1, 20 episodes.
* Server says: {"build_info": "b11901-5320c87ff", "n_ctx": 4096, "total_slots": 1}
* Model file: D:\llama\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf, 807694176 bytes, SHA-256 26bac8efd811cb41 (audited file)
* Software: Python 3.12.6, numpy 2.5.3, psutil 7.2.2, Windows-11-10.0.26300-SP0. llama-server `--version`: version: 0.7.0-dev (build 11901, commit 5320c87ff) built with Clang 20.1.8 for Windows x86_64
* Computer: 11th Gen Intel(R) Core(TM) i5-11400H @ 2.70GHz; 12 logical / 6 physical CPUs; RAM 16107 MB total, 5098 MB free before; pagefile/swap 8326 MB total, 460 MB used before; on battery: False.
* Folded classifier: 10 x 2048 matrix + 10 bias = 20,490 numbers. FP16 files opened by this program: none (the 4 vector pins of the study code were skipped on purpose; the other 10 pinned files were verified).

## 2. Memory (MB). Definitions first

* **Working set** = memory resident in RAM (Windows task manager 'memory'); includes memory-mapped model pages. **Private/commit** = memory that must be backed by RAM or pagefile (does not include mapped model file pages).
* **Sampled combined** = largest sum of this program + llama-server seen at one instant (every 50 ms; can miss a very short spike). **Sum of OS peaks** = peak of each process added up (an upper bound: the peaks may not coincide). **Job peak** = peak committed memory of all processes together, measured by Windows.

| Measure | MB |
|---|---|
| Sum of OS peak working sets (upper bound, all processes) | 1458 |
| Combined working set, sampled, whole run (load + warm-up + mission) | 1452 |
| Combined working set, sampled, mission phase only | 1452 |
| Combined private bytes, sampled, whole run | 996 |
| Job peak commit, all processes together (Windows only) | 996 |
| llama-server OS peak working set | 1317 |
| This program (orchestrator + study code + scikit-learn imports) OS peak working set | 141 |
| This program after imports, before the server started | 131 |
| Model file size on disk | 770 |

Memory cap used in this run: none. Comparison line used in the project: 2048 MB. Largest measured value above: **1458 MB** (sum of OS peak working sets), job commit peak 996 MB.
Job Object membership, asked after the server was ready (Windows only; the cap and the job peak cover only processes inside the job): {"this_program_in_job": true, "llama_server_in_job": true}.
This is a statement about this PC. A 2 GB device also has to hold its operating system and other programs, see section 7.

* **Evaluation data and the measurement.** Data files this program opened (name, when; the measured window closes at 803.1 s after the server started):
  * `cases.jsonl`: before the server started (-6.7 s)
  * `heads_config.json`: before the server started (-5.1 s)
  * `folded_manifest.json`: before the server started (-5.1 s)
  * `folded_q4.npz`: before the server started (-5.1 s)
  * `predictions.csv`: before the server started (-0.3 s)
  * `case_ids.json`: AFTER the measured window closed (805.9 s)
  * `Q4_K_M_prefix.npy`: AFTER the measured window closed (805.9 s)
  * Saved evaluation vectors (`Q4_K_M_prefix.npy`) and the saved predictions are used only to compare results; the peaks above were read BEFORE any of these comparison steps. FP16 files opened: none.
  * This program's own memory (resident) when the window closed: 141 MB; after the comparison step: 153 MB.

## 3. Latency (milliseconds per report; first request and load time are separate)

| Part | mean | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| Q4 forward pass on CPU (prompt -> vector), incl. HTTP | 1979.5 | 1964.8 | 2157.4 | 2381.9 | 3011.9 |
| Report to record (prompt build + vector + folded classifier + assembler) | 1979.8 | 1965.0 | 2157.7 | 2382.3 | 3012.2 |
| Table update and validation inside the decision (decision time minus the line above; NOT the allocator) | 0.0 | 0.0 | 0.1 | 0.1 | 0.1 |
| Whole decision, report arrives -> record committed | 1979.8 | 1965.0 | 2157.7 | 2382.3 | 3012.2 |
| Allocator planning, per allocator run (study CBBA, all runs of the mission; mean) | 0.4 | | | | |
| Allocator planning, per report (all allocator time of an episode / its reports; mean of episodes) | 1.0 | | | | |
| After the decision: table update + replan (MEASURED) | 0.2 | 0.0 | 0.7 | 1.0 | 1.4 |
|   of which allocator planning inside that window (MEASURED) | 0.1 | 0.0 | 0.6 | 0.9 | 1.2 |
| **Report arrives -> record committed -> new plan ready (END TO END, MEASURED)** | 1980.1 | 1965.1 | 2158.2 | 2382.5 | 3012.4 |
| Folded classifier alone (microseconds) | 99.8 | 75.0 | 106.8 | 128.2 | 9318.6 |

* Server load time (process start to ready): 1.6 s. First request (includes touching the weights): 2028 ms. Same prompt twice: max |difference| of the two vectors = 0.00e+00.
* Prompt tokens: mean 624, max 670; context 4096. Mean prompt speed 316 tokens/s. 400 reports in 792 s.
* Latency includes a 50 ms memory-sampler thread and a Python HTTP client. Allocator: 1107 runs in 400 reports (0 from policy requests, the rest replans after events); the study's bounded CBBA on 20-report episodes. Evaluation-only audit runs (never part of a deployment): OFF (0 runs, not counted above).

## 4. Agreement with the saved predictions

Live CPU decisions (Q4 server -> folded `map` classifier) against the saved style-B records of arm `C2p` (made earlier on the GPU, float64, unfolded):

| Check | Result |
|---|---|
| Whole record equal to the saved record | 358 of 400 |
| Action equal | 390 of 400 |
| Sensor equal (where both are record actions) | 159 of 174 |
| Priority equal (where both are record actions) | 156 of 174 |
| Live CPU vector vs saved GPU vector: cosine min / median | 0.996909 / 0.998433 (400 reports below 0.999) |
| Max |logit difference|, live vs the same classifier on the saved vector | 3.175e+00 (median 3.725e-01) |

Mission level (same episodes: level M, arrival seed 1, 20 episodes, 400 reports): missed incidents with live records 66 of 752 (8.78%), with the saved records replayed 65 of 752 (8.64%); 16 of 20 episodes have identical outcome counts.
Disagreements are listed in `disagreements.csv` with the margin of the live logits (a small margin means a near tie).

## 5. Paging conditions

* System free RAM: 5098 MB before the run, lowest 3472 MB during the mission phase (lowest 3456 MB during the whole run), 4679 MB after.
* Pagefile/swap in use: 460 MB before, 483 MB after.
* Windows pagefile detail before: `[{"Name": "C:\\pagefile.sys", "AllocatedBaseSize": 8325, "CurrentUsage": 459, "PeakUsage": 2451}]`; after: `[{"Name": "C:\\pagefile.sys", "AllocatedBaseSize": 8325, "CurrentUsage": 483, "PeakUsage": 2451}]`
* Hard page faults (pages read from disk per second, `Pages Input/sec`): mission phase {"available": true, "rows_in_window": 785, "time_alignment": "approximate (1 s rows, start time of typeperf)", "pages_input_per_s_max": 10413.762752851415, "pages_input_per_s_mean": 42.10435282384528, "page_faults_per_s_max": 110034.45549167263, "available_mbytes_min": 3462.0, "pages_input_total_estimate": 33051.91696671855}; whole run {"available": true, "rows_in_window": 792, "time_alignment": "approximate (1 s rows, start time of typeperf)", "pages_input_per_s_max": 10413.762752851415, "pages_input_per_s_mean": 41.786190940103324, "page_faults_per_s_max": 110034.45549167263, "available_mbytes_min": 3462.0, "pages_input_total_estimate": 33094.66322456183}.
* Page faults of the server process in total (soft and hard): 448614.
* Reading: if free RAM stayed high and `Pages Input/sec` is near zero in the mission phase, the PC was not short of memory, so these peaks are not distorted by paging. This says nothing about a computer that has only 2 GB.

## 6. CPU-only evidence

* Flags: `-ngl 0`, `CUDA_VISIBLE_DEVICES=-1`. Server log: layers offloaded to GPU = []; backends loaded = []; GPU words in log = [].
* GPU memory in use (nvidia-smi): before start 0 MB, after the server was ready 0 MB, after the mission 0 MB.
* The server log has no 'load_backend' lines, so the backends could not be checked from the log; read server.log yourself.

## 7. What this report cannot show

1. **A 2 GB device is not tested.** The numbers are for this PC. On a 2 GB device the operating system, the file cache and other programs use part of the RAM; the pipeline must fit in what is left, and a Windows PC with 2 GB is a different case from a small Linux board.
2. A Job Object cap limits **committed** memory. With memory-mapped weights the model file pages are not counted by the cap but are counted in the working set; run both `--no-mmap` and the default and read both numbers.
3. CPU speed, thread count and cooling differ on a target device; latency here is for this CPU only.
4. Energy was not measured. Quantisation of the model itself, the offline FP16 alignment preparation and training are not part of this deployment measurement.
5. The orchestrator process also holds the study code (simulator, scikit-learn imports). A stripped-down build would use less; that build was not made or measured.
6. The decisions are for 400 style-B reports of one synthetic dataset; agreement says the pipeline reproduces the saved records, not that the records are good.

## Warnings

* Replay checks decision consistency. Measured CPU inference wall time is NOT injected as simulated mission delay; these counts do not validate real-time mission performance.
