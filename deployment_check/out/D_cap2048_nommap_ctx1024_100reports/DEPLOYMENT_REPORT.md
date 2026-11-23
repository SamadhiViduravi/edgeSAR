# Deployment benchmark of the Q4 system: D: as C, with a 2048 MB hard cap on committed memory of all processes

Status: **FINISHED**. 
This report gives MEASURED NUMBERS for this computer under this test. It does **not** say that a 2 GB device passes (see section 7).

## 1. What was run

* Command: `deploy_bench.py run --root D:\1 Samadhi UNI\aFYP\Claude --repair-dir D:\1 Samadhi UNI\aFYP\Claude\edgesar_repair_2026-11-14 --server D:\llama_cpu_edgesar_v1_1\llama-server.exe --model D:\llama\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf --out out\D_cap2048_nommap_ctx1024_100reports --label D: as C, with a 2048 MB hard cap on committed memory of all processes --no-mmap --ctx 1024 --episodes 5 --job-limit-mb 2048`
* llama-server command: `D:\llama_cpu_edgesar_v1_1\llama-server.exe -m D:\llama\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf --host 127.0.0.1 --port 8093 -ngl 0 -c 1024 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024 --load-mode none` (environment: CUDA_VISIBLE_DEVICES=-1)
* Context length requested 1024, batch 1024, ubatch 1024, threads 6, weights loaded into private memory (`--load-mode none`, chosen from this llama-server's own --help), classifier `map` (float32), mission level M, arrival seed 1, 5 episodes.
* Server says: {"build_info": "b11901-5320c87ff", "n_ctx": 1024, "total_slots": 1}
* Model file: D:\llama\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf, 807694176 bytes, SHA-256 26bac8efd811cb41 (audited file)
* Software: Python 3.12.6, numpy 2.5.3, psutil 7.2.2, Windows-11-10.0.26300-SP0. llama-server `--version`: version: 0.7.0-dev (build 11901, commit 5320c87ff) built with Clang 20.1.8 for Windows x86_64
* Computer: 11th Gen Intel(R) Core(TM) i5-11400H @ 2.70GHz; 12 logical / 6 physical CPUs; RAM 16107 MB total, 3997 MB free before; pagefile/swap 8326 MB total, 481 MB used before; on battery: False.
* Folded classifier: 10 x 2048 matrix + 10 bias = 20,490 numbers. FP16 files opened by this program: none (the 4 vector pins of the study code were skipped on purpose; the other 10 pinned files were verified).

## 2. Memory (MB). Definitions first

* **Working set** = memory resident in RAM (Windows task manager 'memory'); includes memory-mapped model pages. **Private/commit** = memory that must be backed by RAM or pagefile (does not include mapped model file pages).
* **Sampled combined** = largest sum of this program + llama-server seen at one instant (every 50 ms; can miss a very short spike). **Sum of OS peaks** = peak of each process added up (an upper bound: the peaks may not coincide). **Job peak** = peak committed memory of all processes together, measured by Windows.

| Measure | MB |
|---|---|
| Sum of OS peak working sets (upper bound, all processes) | 1119 |
| Combined working set, sampled, whole run (load + warm-up + mission) | 1139 |
| Combined working set, sampled, mission phase only | 1114 |
| Combined private bytes, sampled, whole run | 1205 |
| Job peak commit, all processes together (Windows only) | 1205 |
| llama-server OS peak working set | 978 |
| llama-server private bytes, sampled peak (compare Run A: weights in private memory should add about the model size) | 1061 |
| This program (orchestrator + study code + scikit-learn imports) OS peak working set | 142 |
| This program after imports, before the server started | 134 |
| Model file size on disk | 770 |

Memory cap used in this run: 2048 MB hard cap on committed memory of all processes (Job Object). Comparison line used in the project: 2048 MB. Largest measured value above: **1119 MB** (sum of OS peak working sets), job commit peak 1205 MB.
Job Object membership, asked after the server was ready (Windows only; the cap and the job peak cover only processes inside the job): {"this_program_in_job": true, "llama_server_in_job": true}.
This is a statement about this PC. A 2 GB device also has to hold its operating system and other programs, see section 7.

* **Evaluation data and the measurement.** Data files this program opened (name, when; the measured window closes at 219.6 s after the server started):
  * `cases.jsonl`: before the server started (-6.8 s)
  * `heads_config.json`: before the server started (-5.1 s)
  * `folded_manifest.json`: before the server started (-5.1 s)
  * `folded_q4.npz`: before the server started (-5.1 s)
  * `predictions.csv`: before the server started (-0.3 s)
  * `case_ids.json`: AFTER the measured window closed (222.7 s)
  * `Q4_K_M_prefix.npy`: AFTER the measured window closed (222.7 s)
  * Saved evaluation vectors (`Q4_K_M_prefix.npy`) and the saved predictions are used only to compare results; the peaks above were read BEFORE any of these comparison steps. FP16 files opened: none.
  * This program's own memory (resident) when the window closed: 137 MB; after the comparison step: 141 MB.

## 3. Latency (milliseconds per report; first request and load time are separate)

| Part | mean | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| Q4 forward pass on CPU (prompt -> vector), incl. HTTP | 2089.7 | 2039.4 | 2611.0 | 2748.2 | 2794.2 |
| Report to record (prompt build + vector + folded classifier + assembler) | 2089.9 | 2039.6 | 2611.2 | 2748.6 | 2794.5 |
| Table update and validation inside the decision (decision time minus the line above; NOT the allocator) | 0.0 | 0.0 | 0.1 | 0.1 | 0.1 |
| Whole decision, report arrives -> record committed | 2089.9 | 2039.7 | 2611.3 | 2748.6 | 2794.5 |
| Allocator planning, per allocator run (study CBBA, all runs of the mission; mean) | 0.4 | | | | |
| Allocator planning, per report (all allocator time of an episode / its reports; mean of episodes) | 1.0 | | | | |
| After the decision: table update + replan (MEASURED) | 0.2 | 0.0 | 0.6 | 0.8 | 1.2 |
|   of which allocator planning inside that window (MEASURED) | 0.1 | 0.0 | 0.5 | 0.7 | 1.0 |
| **Report arrives -> record committed -> new plan ready (END TO END, MEASURED)** | 2090.2 | 2040.1 | 2611.4 | 2748.8 | 2794.7 |
| Folded classifier alone (microseconds) | 76.6 | 77.0 | 103.8 | 111.4 | 117.8 |

* Server load time (process start to ready): 1.6 s. First request (includes touching the weights): 2213 ms. Same prompt twice: max |difference| of the two vectors = 0.00e+00.
* Prompt tokens: mean 622, max 659; context 1024. Mean prompt speed 301 tokens/s. 100 reports in 209 s.
* Latency includes a 50 ms memory-sampler thread and a Python HTTP client. Allocator: 251 runs in 100 reports (0 from policy requests, the rest replans after events); the study's bounded CBBA on 20-report episodes. Evaluation-only audit runs (never part of a deployment): OFF (0 runs, not counted above).

## 4. Agreement with the saved predictions

Live CPU decisions (Q4 server -> folded `map` classifier) against the saved style-B records of arm `C2p` (made earlier on the GPU, float64, unfolded):

| Check | Result |
|---|---|
| Whole record equal to the saved record | 87 of 100 |
| Action equal | 95 of 100 |
| Sensor equal (where both are record actions) | 32 of 35 |
| Priority equal (where both are record actions) | 30 of 35 |
| Live CPU vector vs saved GPU vector: cosine min / median | 0.997493 / 0.998421 (100 reports below 0.999) |
| Max |logit difference|, live vs the same classifier on the saved vector | 2.859e+00 (median 3.816e-01) |

Mission level (same episodes: level M, arrival seed 1, 5 episodes, 100 reports): missed incidents with live records 15 of 173 (8.67%), with the saved records replayed 13 of 173 (7.51%); 4 of 5 episodes have identical outcome counts.
Disagreements are listed in `disagreements.csv` with the margin of the live logits (a small margin means a near tie).

## 5. Paging conditions

* System free RAM: 3997 MB before the run, lowest 2391 MB during the mission phase (lowest 2391 MB during the whole run), 3393 MB after.
* Pagefile/swap in use: 481 MB before, 490 MB after.
* Windows pagefile detail before: `[{"Name": "C:\\pagefile.sys", "AllocatedBaseSize": 8325, "CurrentUsage": 481, "PeakUsage": 2451}]`; after: `[{"Name": "C:\\pagefile.sys", "AllocatedBaseSize": 8325, "CurrentUsage": 489, "PeakUsage": 2451}]`
* Hard page faults (pages read from disk per second, `Pages Input/sec`): mission phase {"available": true, "rows_in_window": 209, "time_alignment": "approximate (1 s rows, start time of typeperf)", "pages_input_per_s_max": 6075.37498092178, "pages_input_per_s_mean": 73.44099015124182, "page_faults_per_s_max": 227803.71043402437, "available_mbytes_min": 2397.0, "pages_input_total_estimate": 15349.166941609537}; whole run {"available": true, "rows_in_window": 216, "time_alignment": "approximate (1 s rows, start time of typeperf)", "pages_input_per_s_max": 6075.37498092178, "pages_input_per_s_mean": 71.07012003233545, "page_faults_per_s_max": 227803.71043402437, "available_mbytes_min": 2397.0, "pages_input_total_estimate": 15351.145926984458}.
* Page faults of the server process in total (soft and hard): 456445.
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
