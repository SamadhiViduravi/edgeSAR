#!/bin/bash
# Sensitivity runs on the development set (level M, seeds 1-3). Each takes about a minute.
# usage: bash tools/run_sensitivity.sh      (from the edgesar_shield folder; set EDGESAR_ROOT if the older folders are not next to it)
set -e
ARMS="A0 A1 A6 A8 A8c A10 A12 OBS"
run() { tag=$1; shift; python3 -B tools/run_dev.py --tag "$tag" --levels M --seeds 1 2 3 --arms $ARMS "$@" > "results/dev_${tag}.log" 2>&1; }
run b05 --b 0.05
run b20 --b 0.20
run b30 --b 0.30
run a05 --alpha 0.05
run a20 --alpha 0.20
run K4  --K 4
run dv30  --d-v 30
run dv120 --d-v 120
run legacy --allocator legacy_greedy_s1
run ac02 --alloc-cost 0.2
run ac10 --alloc-cost 1.0
echo done > results/dev_sensitivity.done
