# Decision quality against GOLD: D_cap2048_nommap_ctx1024_100reports

Reports in this run: **100**. Saved arm: `C2p` (made earlier from GPU vectors). Live = this CPU run. Exploratory; style B has been inspected many times.

| | live (CPU) | saved (GPU vectors) |
|---|---|---|
| Whole record equals gold | 69 of 100 (69.0%) | 74 of 100 (74.0%) |
| Action equals gold | 92 of 100 (92.0%) | 93 of 100 (93.0%) |
| Sensor equals gold (reports whose gold has a sensor: 37) | 17 | 20 |
| Priority equals gold (reports whose gold has a priority: 37) | 25 | 28 |

Live record identical to saved record: **87 of 100**.

| Gold comparison, per report | count |
|---|---|
| both right | 69 |
| only live right | 0 |
| only saved right | 5 |
| both wrong | 26 |

Exact two-sided sign test on the 5 reports where exactly one is right: p = 0.062. (A large p only says that a difference is not shown; it does not show equality.)

Self-check of this script: gold comparison of the saved records reproduces the saved `record_ok` column on 100 of 100 reports.

What this does NOT show: it does not show that either pipeline is good enough for a real mission, and it says nothing about memory. Mission replay results are in `DEPLOYMENT_REPORT.md`.
