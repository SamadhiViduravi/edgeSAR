# CPU deployment check (Section V-I of the paper)

Run on 15 Nov 2026 on one Windows 11 laptop (Intel i5-11400H, 6 cores, 16 GB RAM), CPU only, llama.cpp build b11901 (`llama-server`), Llama 3.2 1B Instruct Q4_K_M, six threads. These files back the memory and latency figures of Section V-I. No accuracy or mission result of the paper depends on them.

## What was run

| Folder in `out/` | Setting | Reports |
|---|---|---|
| `A_cpu_mmap_ctx4096_400reports` | weights memory-mapped (llama.cpp default), context 4,096 tokens | 400 style-B development reports |
| `B_cpu_nommap_ctx4096_100reports` | weights in private memory (`--load-mode none`), context 4,096 | first 100 of the same reports |
| `C_cpu_nommap_ctx1024_100reports` | as B, context 1,024 | 100 |
| `D_cap2048_nommap_ctx1024_100reports` | as C, under a 2,048 MB Windows Job Object cap on committed memory | 100 |

Each folder holds `DEPLOYMENT_REPORT.md`, `QUALITY_vs_GOLD.md`, `results.json`, `per_report.csv` (per-report latency and records), `memory_series.csv` and `typeperf_memory.csv` (memory samples), `disagreements.csv`, `report_to_plan.csv` and the `server.log` of llama-server. The live Q4 hidden vectors (`live_vectors_q4_prefix.npy`) are not included, as for all hidden vectors of the study.

## Classifier and comparator

The device runs one folded linear layer (`folded/folded_q4.npz`, 10 x 2,048 weights plus biases, 81,960 bytes in float32): the label-free map followed by the FP16 heads, prefix position, fitted on all 1,000 style-A development reports (`export_folded_classifier.py`; `folded/EXPORT_CHECK.md` shows that it reproduces the unfolded classifier on the saved vectors for 400 of 400 reports). The comparator "saved GPU-based records" is the same classifier applied to the saved hidden vectors of the same reports, which were extracted earlier with the CUDA build of llama.cpp on a laptop GPU. The CPU records matched them in 358 of 400 reports; the cause of the difference was not confirmed, because the two later GPU diagnostic runs did not use the GPU (the CUDA build listed no device) and are therefore not included here.

## Scripts

`deploy_bench.py` (benchmark and memory measurement), `export_folded_classifier.py`, `prepare_cpu_runtime.py`, `analyze_deployment_results.py`, the `STEP*.bat` files and `COMMANDS_WINDOWS.md` (exact commands), `tests/` (self-tests with a fake server). `RESULTS_SUMMARY_2026-11-15.md` is the summary written on the day.
