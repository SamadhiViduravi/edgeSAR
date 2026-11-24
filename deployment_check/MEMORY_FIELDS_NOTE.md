# Note on the memory fields of the deployment summaries (added for manuscript draft v2.10)

The measurement files in `out/` are kept exactly as the runs wrote them on 15 November 2026. This note says what their memory fields measure and which raw fields give the values in Section V-I of the manuscript. `memory_for_paper.py` recomputes those values from the raw `results.json` files (Python standard library only):

    python deployment_check/memory_for_paper.py

## Units

`deploy_bench.py` defines `MB = 2**20`. Every "MB" in this folder (`DEPLOYMENT_REPORT.md`, `RESULTS_SUMMARY_2026-11-15.md`, `results.json`, the CSV files and the run commands) is therefore a **MiB** (1,048,576 bytes). The cap of run D is 2,048 MiB.

## Labels in the human-readable summaries that are wider than they say

| Where | Label | What it actually contains |
|---|---|---|
| `DEPLOYMENT_REPORT.md`, section 2; `results.json` field `memory.server_os_peak_ws_mb` | "llama-server OS peak working set" | the OS peak working sets of **all child processes alive at the end of the run**: llama-server **plus the `typeperf` memory logger** (about 11 MiB). Run A: 1,317 = 1,306 (llama-server) + 11 (typeperf). |
| same files; `memory.sum_of_os_peak_ws_mb` | "Sum of OS peak working sets (upper bound, all processes)" | orchestrator + llama-server + typeperf. It bounds the combined working set of those three processes. |
| same files; `memory.combined_ws_peak_sampled_mb_whole_run` | "largest sum of this program + llama-server seen at one instant" | the orchestrator plus **all** of its child processes at each 50 ms sample: llama-server, typeperf and, while they ran, short-lived `nvidia-smi` calls. This is why it can be higher than the sum of the two pipeline processes (runs B to D). |

## Raw fields used in the manuscript (Section V-I)

| Value in the manuscript | Raw field in `out/<run>/results.json` |
|---|---|
| llama-server peak working set, 967 to 1,306 MiB | `os_peaks.children[name == "llama-server.exe"].peak_ws_mb` |
| Python orchestrator peak working set, 139 to 142 MiB | `os_peaks.orchestrator.peak_ws_mb` |
| sum of the two, 1,106 to 1,447 MiB (bounds their combined working set) | the two fields above, added |
| sampled combined working set of the orchestrator and all child processes, 1,137 to 1,452 MiB | `memory.combined_ws_peak_sampled_mb_whole_run` |
| peak committed memory of all processes in the job, 996 to 1,307 MiB (1,205 MiB in run D) | `memory.job_peak_commit_mb` |
| time per report, 1.97 to 2.09 s (mean) | `latency_ms.embed_ms.mean` |

## Per run (MiB)

| Run | llama-server peak WS | orchestrator peak WS | sum of the two | sampled combined WS (all processes) | job peak commit | cap |
|---|---:|---:|---:|---:|---:|---|
| A_cpu_mmap_ctx4096_400reports | 1305.9 | 141.4 | 1447.3 | 1452.1 | 996.4 | none |
| B_cpu_nommap_ctx4096_100reports | 1063.3 | 140.3 | 1203.5 | 1234.4 | 1306.7 | none |
| C_cpu_nommap_ctx1024_100reports | 966.8 | 138.7 | 1105.5 | 1137.1 | 1203.4 | none |
| D_cap2048_nommap_ctx1024_100reports | 966.8 | 141.6 | 1108.4 | 1139.2 | 1205.3 | 2048 |
