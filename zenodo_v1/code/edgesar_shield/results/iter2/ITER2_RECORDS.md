# Iteration 2: whole-record results (secondary outcome, protocol section 4)

Status: SECONDARY. The primary mission-level verdict stays NOT SHOWN. 1000 records, 100 family clusters. Intervals: cluster bootstrap over families (records of one family are not independent). McNemar p is exact and treats records as independent, so it is optimistic. Precision = repaired / (repaired + newly wrong). Reference = plain Q4 at the same position and readout unless the second name says otherwise. Integrity (accuracies equal to the mission run): True.

| arm | ref | acc arm | acc ref | repaired | newly wrong | net | precision | diff pp | 95% CI (cluster) | McNemar p |
|---|---|---|---|---|---|---|---|---|---|---|
| dommp | q4p | 79.7 | 78.2 | 52 | 37 | +15 | 0.58 | +1.50 | -0.50 to +3.60 | 0.137 |
| domap | q4ap | 80.2 | 78.7 | 40 | 25 | +15 | 0.62 | +1.50 | -0.10 to +3.20 | 0.082 |
| domm | q4 | 70.8 | 74.3 | 52 | 87 | -35 | 0.37 | -3.50 | -5.80 to -1.20 | 0.004 |
| doma | q4a | 75.9 | 76.7 | 50 | 58 | -8 | 0.46 | -0.80 | -2.50 to +0.90 | 0.501 |
| genmp | q4p | 78.2 | 78.2 | 44 | 44 | +0 | 0.50 | +0.00 | -1.90 to +1.90 | 1.000 |
| genap | q4ap | 80.2 | 78.7 | 42 | 27 | +15 | 0.61 | +1.50 | -0.10 to +3.20 | 0.091 |
| genm | q4 | 73.5 | 74.3 | 73 | 81 | -8 | 0.47 | -0.80 | -3.40 to +1.90 | 0.573 |
| gena | q4a | 77.5 | 76.7 | 63 | 55 | +8 | 0.53 | +0.80 | -1.40 to +3.00 | 0.519 |
| q5mp | q4p | 81.9 | 78.2 | 66 | 29 | +37 | 0.69 | +3.70 | +2.00 to +5.40 | 0.000 |
| q5ap | q4ap | 82.2 | 78.7 | 58 | 23 | +35 | 0.72 | +3.50 | +2.00 to +5.10 | 0.000 |
| q5m | q4 | 75.3 | 74.3 | 67 | 57 | +10 | 0.54 | +1.00 | -1.30 to +3.20 | 0.419 |
| q5a | q4a | 77.6 | 76.7 | 58 | 49 | +9 | 0.54 | +0.90 | -1.10 to +2.90 | 0.439 |
| dxmp | q4p | 79.9 | 78.2 | 52 | 35 | +17 | 0.60 | +1.70 | -0.20 to +3.60 | 0.086 |
| dxap | q4ap | 80.6 | 78.7 | 40 | 21 | +19 | 0.66 | +1.90 | +0.40 to +3.40 | 0.020 |
| dxm | q4 | 75.2 | 74.3 | 79 | 70 | +9 | 0.53 | +0.90 | -1.30 to +3.10 | 0.512 |
| dxa | q4a | 76.7 | 76.7 | 51 | 51 | +0 | 0.50 | +0.00 | -1.80 to +1.80 | 1.000 |
| q4ap | q4p | 78.7 | 78.2 | 38 | 33 | +5 | 0.54 | +0.50 | -0.90 to +2.00 | 0.635 |
| q4a | q4 | 76.7 | 74.3 | 63 | 39 | +24 | 0.62 | +2.40 | +0.70 to +4.20 | 0.022 |
| q4p | f16p | 78.2 | 81.7 | 34 | 69 | -35 | 0.33 | -3.50 | -5.40 to -1.70 | 0.001 |
| q4 | f16 | 74.3 | 79.3 | 35 | 85 | -50 | 0.29 | -5.00 | -7.10 to -2.90 | 0.000 |
| dommp | genmp | 79.7 | 78.2 | 38 | 23 | +15 | 0.62 | +1.50 | +0.10 to +3.00 | 0.072 |
| dxmp | genmp | 79.9 | 78.2 | 40 | 23 | +17 | 0.63 | +1.70 | +0.30 to +3.10 | 0.043 |
| dommp | dxmp | 79.7 | 79.9 | 21 | 23 | -2 | 0.48 | -0.20 | -1.30 to +1.00 | 0.880 |
| domm | genm | 70.8 | 73.5 | 54 | 81 | -27 | 0.40 | -2.70 | -5.30 to -0.20 | 0.025 |
| dxm | genm | 75.2 | 73.5 | 82 | 65 | +17 | 0.56 | +1.70 | -0.80 to +4.10 | 0.187 |
| domm | dxm | 70.8 | 75.2 | 51 | 95 | -44 | 0.35 | -4.40 | -6.70 to -2.10 | 0.000 |
| dommp | f16p | 79.7 | 81.7 | 23 | 43 | -20 | 0.35 | -2.00 | -3.60 to -0.30 | 0.019 |
| genmp | f16p | 78.2 | 81.7 | 18 | 53 | -35 | 0.25 | -3.50 | -5.00 to -2.10 | 0.000 |
| dxmp | f16p | 79.9 | 81.7 | 29 | 47 | -18 | 0.38 | -1.80 | -3.40 to -0.20 | 0.050 |
| q5mp | f16p | 81.9 | 81.7 | 32 | 30 | +2 | 0.52 | +0.20 | -1.30 to +1.70 | 0.899 |
| q5ap | f16p | 82.2 | 81.7 | 30 | 25 | +5 | 0.55 | +0.50 | -0.80 to +1.80 | 0.590 |
