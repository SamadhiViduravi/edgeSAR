# Decision quality against GOLD: A_cpu_mmap_ctx4096_400reports

Reports in this run: **400**. Saved arm: `C2p` (made earlier from GPU vectors). Live = this CPU run. Exploratory; style B has been inspected many times.

| | live (CPU) | saved (GPU vectors) |
|---|---|---|
| Whole record equals gold | 273 of 400 (68.2%) | 285 of 400 (71.2%) |
| Action equals gold | 375 of 400 (93.8%) | 377 of 400 (94.2%) |
| Sensor equals gold (reports whose gold has a sensor: 180) | 109 | 112 |
| Priority equals gold (reports whose gold has a priority: 180) | 111 | 118 |

Live record identical to saved record: **358 of 400**.

| Gold comparison, per report | count |
|---|---|
| both right | 268 |
| only live right | 5 |
| only saved right | 17 |
| both wrong | 110 |

Exact two-sided sign test on the 22 reports where exactly one is right: p = 0.017. (A large p only says that a difference is not shown; it does not show equality.)

Self-check of this script: gold comparison of the saved records reproduces the saved `record_ok` column on 400 of 400 reports.

What this does NOT show: it does not show that either pipeline is good enough for a real mission, and it says nothing about memory. Mission replay results are in `DEPLOYMENT_REPORT.md`.
