# Speed and memory on this computer

Linux-6.18.44-fc-v445-x86_64-with-glibc2.39; x86_64; Python 3.13.17; RAM 7.8 GB; mode: as the development extraction (-ngl 99); 2026-11-13 19:37:06.

## Heads and Shield (saved vectors, development fold 0, level M)

Heads: p50 0.58 ms, p95 0.91 ms per report. Python process peak memory: 251 MB.

| policy | decision p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | allocator runs / decision | allocator ms / run (median) |
|---|---|---|---|---|---|---|
| A1 | 0.00 | 0.01 | 0.01 | 0.01 | 0.00 | - |
| A6 | 0.01 | 0.01 | 0.02 | 0.03 | 0.00 | - |
| A8 | 0.28 | 1.15 | 1.42 | 1.73 | 2.28 | 0.15 |
| B3 | 0.28 | 1.17 | 1.59 | 1.99 | 2.31 | 0.15 |
| G1 | 0.01 | 0.60 | 0.74 | 0.99 | 0.92 | 0.14 |

The simulation charges 20 ms of decision time per allocator run. If the measured value is far from 20 ms the assumption (docs/DEVIATIONS.md D-12) must be revisited.

