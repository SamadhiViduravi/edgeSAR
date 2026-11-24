"""Print the CPU-deployment memory values reported in Section V-I of the manuscript, from the raw results.json files.

Usage (from the repository root or from deployment_check/):
    python deployment_check/memory_for_paper.py

Only the Python standard library is needed. Units: MiB (bytes / 2**20). deploy_bench.py uses MB = 2**20, so every
"MB" in the files of this folder is a MiB. See MEMORY_FIELDS_NOTE.md for what each raw field measures.
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = sorted(glob.glob(os.path.join(HERE, "out", "*", "results.json")))


def per_run(path):
    r = json.load(open(path, encoding="utf-8"))
    kids = r["os_peaks"]["children"]
    server = sum(c["peak_ws_mb"] for c in kids if c["name"].lower().startswith("llama-server"))
    orch = r["os_peaks"]["orchestrator"]["peak_ws_mb"]
    m = r["memory"]
    return {
        "run": os.path.basename(os.path.dirname(path)),
        "llama_server_peak_ws": server,                                    # os_peaks.children[llama-server.exe].peak_ws_mb
        "orchestrator_peak_ws": orch,                                      # os_peaks.orchestrator.peak_ws_mb
        "server_plus_orchestrator": server + orch,                         # bounds the combined working set of these two processes
        "other_children_at_end": {c["name"]: round(c["peak_ws_mb"], 1) for c in kids if not c["name"].lower().startswith("llama-server")},
        "sampled_combined_ws_whole_run": m["combined_ws_peak_sampled_mb_whole_run"],  # orchestrator + all child processes, every 50 ms
        "job_peak_commit": m["job_peak_commit_mb"],                        # all processes in the Windows job
        "job_limit": m["job_limit_mb"],
        "embed_ms_mean": r["latency_ms"]["embed_ms"]["mean"],
    }


rows = [per_run(p) for p in RUNS]
if not rows:
    raise SystemExit("no out/*/results.json found next to this script")
print("| Run | llama-server peak WS | orchestrator peak WS | sum of the two | sampled combined WS (all processes) | job peak commit | cap |")
print("|---|---:|---:|---:|---:|---:|---|")
for x in rows:
    print("| %s | %.1f | %.1f | %.1f | %.1f | %.1f | %s |" % (x["run"], x["llama_server_peak_ws"], x["orchestrator_peak_ws"],
          x["server_plus_orchestrator"], x["sampled_combined_ws_whole_run"], x["job_peak_commit"], x["job_limit"] or "none"))


def rng(key, nd=0):
    v = [x[key] for x in rows]
    return "%s to %s" % (format(round(min(v), nd), ",.%df" % nd), format(round(max(v), nd), ",.%df" % nd))


print()
print("Values in the manuscript (Section V-I), MiB:")
print("  llama-server peak working set:          ", rng("llama_server_peak_ws"))
print("  orchestrator peak working set:          ", rng("orchestrator_peak_ws"))
print("  llama-server + orchestrator:            ", rng("server_plus_orchestrator"))
print("  sampled combined working set (50 ms):   ", rng("sampled_combined_ws_whole_run"))
print("  job peak committed memory:              ", rng("job_peak_commit"))
print("  mean time per report, s:                ", "%.2f to %.2f" % (min(x["embed_ms_mean"] for x in rows) / 1000, max(x["embed_ms_mean"] for x in rows) / 1000))
print("  other child processes alive at the end (counted in the summaries' 'server' and 'sum' fields):",
      sorted({k for x in rows for k in x["other_children_at_end"]}))
