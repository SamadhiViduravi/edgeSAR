"""Decision QUALITY of a deployment run (does not touch the run, reads its per_report.csv; standard library only).

For the reports of one run it compares, against the GOLD record of the dataset:
  live   = the record the CPU pipeline made (per_report.csv, column record_key)
  saved  = the record saved earlier from GPU vectors (repair_package/out2/predictions.csv, same arm)
and counts reports where only one of them is right (exact two-sided sign test on those, exploratory).
Writes QUALITY_vs_GOLD.md into the run folder.

  python analyze_deployment_results.py --run out\\A_cpu_mmap_ctx4096_400reports --cases <...>\\edgesar_pilot\\data\\cases.jsonl --predictions <...>\\out2\\predictions.csv --arm C2p
"""
import argparse
import ast
import csv
import json
import math
from pathlib import Path

KEYCOLS = ("action", "incident", "landmark", "sensor", "priority")


def gold_key(g):
    return tuple(g.get(c) for c in KEYCOLS)


def sign_test_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--arm", default="C2p")
    a = ap.parse_args()
    run = Path(a.run)
    gold = {}
    with open(a.cases, encoding="utf-8") as f:
        for l in f:
            if l.strip():
                d = json.loads(l)
                gold[d["id"]] = gold_key(d["gold"])
    saved, saved_ok = {}, {}
    with open(a.predictions, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["protocol"] == "B" and r["labels"] == "all" and r["arm"] == a.arm:
                saved[r["case_id"]] = tuple(None if r[c] == "" else (int(r[c]) if c == "priority" else r[c]) for c in KEYCOLS)
                saved_ok[r["case_id"]] = r["record_ok"] == "1"
    live = {}
    with open(run / "per_report.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            live[r["case_id"]] = tuple(ast.literal_eval(r["record_key"]))
    ids = sorted(live)
    # self-check of this script: the saved record compared with gold must reproduce the saved record_ok column
    chk = sum(1 for i in ids if (saved[i] == gold[i]) == saved_ok[i])
    both = live_only = saved_only = neither = 0
    act_l = act_s = 0
    sp_l = sp_s = sp_n = 0
    pri_l = pri_s = pri_n = 0
    same = 0
    for i in ids:
        lr, sr, g = live[i] == gold[i], saved[i] == gold[i], gold[i]
        both += lr and sr
        live_only += lr and not sr
        saved_only += sr and not lr
        neither += (not lr) and (not sr)
        act_l += live[i][0] == g[0]
        act_s += saved[i][0] == g[0]
        same += live[i] == saved[i]
        if g[3] is not None:                                    # sensor/priority exist in gold: count how often each is right (whatever action was chosen)
            sp_n += 1
            sp_l += live[i][3] == g[3]
            sp_s += saved[i][3] == g[3]
        if g[4] is not None:
            pri_n += 1
            pri_l += live[i][4] == g[4]
            pri_s += saved[i][4] == g[4]
    n = len(ids)
    p = sign_test_p(live_only, saved_only)
    L = ["# Decision quality against GOLD: %s" % run.name, "",
         "Reports in this run: **%d**. Saved arm: `%s` (made earlier from GPU vectors). Live = this CPU run. Exploratory; style B has been inspected many times." % (n, a.arm), "",
         "| | live (CPU) | saved (GPU vectors) |", "|---|---|---|",
         "| Whole record equals gold | %d of %d (%.1f%%) | %d of %d (%.1f%%) |" % (both + live_only, n, 100.0 * (both + live_only) / n, both + saved_only, n, 100.0 * (both + saved_only) / n),
         "| Action equals gold | %d of %d (%.1f%%) | %d of %d (%.1f%%) |" % (act_l, n, 100.0 * act_l / n, act_s, n, 100.0 * act_s / n),
         "| Sensor equals gold (reports whose gold has a sensor: %d) | %d | %d |" % (sp_n, sp_l, sp_s),
         "| Priority equals gold (reports whose gold has a priority: %d) | %d | %d |" % (pri_n, pri_l, pri_s), "",
         "Live record identical to saved record: **%d of %d**." % (same, n), "",
         "| Gold comparison, per report | count |", "|---|---|",
         "| both right | %d |" % both, "| only live right | %d |" % live_only, "| only saved right | %d |" % saved_only, "| both wrong | %d |" % neither, "",
         "Exact two-sided sign test on the %d reports where exactly one is right: p = %.3f. (A large p only says that a difference is not shown; it does not show equality.)" % (live_only + saved_only, p), "",
         "Self-check of this script: gold comparison of the saved records reproduces the saved `record_ok` column on %d of %d reports." % (chk, n), "",
         "What this does NOT show: it does not show that either pipeline is good enough for a real mission, and it says nothing about memory. Mission replay results are in `DEPLOYMENT_REPORT.md`."]
    (run / "QUALITY_vs_GOLD.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
