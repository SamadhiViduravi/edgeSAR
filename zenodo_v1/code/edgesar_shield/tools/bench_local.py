"""
Measure speed and memory of the WHOLE chain on YOUR computer (iteration 1, priority 5).  Nothing here changes any result.

    python tools/bench_local.py --llama-dir D:\\llama --models-dir D:\\llama\\models --n 100
    python tools/bench_local.py --shield-only                    (no llama.cpp: only the Shield/allocator part, from saved vectors)
    python tools/bench_local.py ... --cpu                        (llama-server with -ngl 0, i.e. CPU only)

What is measured (every number is wall-clock time or process memory on this machine):
  A. per precision (f16, Q8_0, Q4_K_M):   model file size, server start time, peak memory of the llama-server process (and GPU memory if nvidia-smi exists),
     time to embed one report (the real prompt of the pilot), p50 / p95 / max over --n development reports (sequential, one at a time)
  B. the heads (scikit-learn):             time to turn one vector into the three head outputs
  C. the Shield on saved vectors:          time of one decision (candidates, signatures, requirement checks, fallback) for A1, A6, A8, B3, G1 as the
                                           simulator runs it, and milliseconds per allocator run (the simulation ASSUMES 20 ms per run; this checks it)
  D. memory of this Python process (peak)
  Totals per report = embed + heads + Shield decision (p50 and p95 added separately; they are not the same reports).
Needs: pip install psutil   (optional: memory of llama-server). Output: results/bench_<time>/BENCH.md and bench.json
"""
import argparse
import json
import platform
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np                                                # noqa: E402

from shield import paths                                          # noqa: E402


def pct(xs, p):
    return float(np.percentile(xs, p)) if len(xs) else float("nan")


def own_peak_mb():
    """Peak memory of this Python process in MB (works on Linux, macOS and Windows)."""
    try:
        import psutil
        mi = psutil.Process().memory_info()
        return float(getattr(mi, "peak_wset", 0) or mi.rss) / 2 ** 20
    except Exception:
        pass
    try:
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / 1024.0 if sys.platform != "darwin" else r / 2 ** 20
    except Exception:
        return float("nan")


class MemoryWatcher:
    """Samples the resident memory of a process (and its children) every 50 ms; keeps the maximum.  Needs psutil."""

    def __init__(self, pid):
        self.pid, self.peak, self.stop_flag, self.ok = pid, 0.0, False, False
        try:
            import psutil
            self.ps = psutil
            self.proc = psutil.Process(pid)
            self.ok = True
        except Exception:
            self.ok = False
        self.gpu_peak = float("nan")

    def _gpu(self):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
            vals = [float(x) for x in out.stdout.split() if x.strip()]
            return max(vals) if vals else float("nan")
        except Exception:
            return float("nan")

    def _run(self):
        n = 0
        while not self.stop_flag:
            try:
                procs = [self.proc] + self.proc.children(recursive=True)
                mem = sum(p.memory_info().rss for p in procs) / 2 ** 20
                self.peak = max(self.peak, mem)
            except Exception:
                pass
            if n % 10 == 0:
                g = self._gpu()
                if g == g:
                    self.gpu_peak = g if self.gpu_peak != self.gpu_peak else max(self.gpu_peak, g)
            n += 1
            time.sleep(0.05)

    def __enter__(self):
        if self.ok:
            self.t = threading.Thread(target=self._run, daemon=True)
            self.t.start()
        return self

    def __exit__(self, *a):
        self.stop_flag = True
        if self.ok:
            self.t.join(timeout=2)


def bench_precision(model_key, exe, models_dir, cases, n, ngl, out_dir, port, attach=None, attach_pid=None):
    import extract_fresh_vectors as ex
    pc = __import__("shield.candidates", fromlist=["pilot"]).pilot()[0]
    prompts = [pc.build_prompt(c, ex.PROMPT_ID) for c in cases[:n]]
    gguf = Path(models_dir) / ex.GGUF_FILE[model_key]
    rec = {"model": model_key, "gguf_bytes": gguf.stat().st_size if gguf.exists() else ex.GGUF_BYTES[model_key], "ngl": ngl}
    srv = None
    try:
        if attach:
            base, pid = attach, attach_pid
            rec["start_s"] = None
        else:
            srv = ex.LlamaServer(exe, gguf, Path(out_dir) / ("server_%s.log" % model_key), ngl=ngl, port=port)
            rec["start_s"] = round(srv.start(), 2)
            base, pid = srv.base, srv.proc.pid
        client = ex.EmbedClient(base)
        client.embed(prompts[0])                                  # warm-up, not timed
        times = []
        with MemoryWatcher(pid) if pid else MemoryWatcher(0) as mw:
            for p in prompts:
                t0 = time.perf_counter()
                client.embed(p)
                times.append((time.perf_counter() - t0) * 1000.0)
        rec.update({"n": len(times), "embed_ms_p50": pct(times, 50), "embed_ms_p95": pct(times, 95), "embed_ms_max": max(times), "embed_ms_mean": statistics.mean(times),
                    "server_peak_rss_mb": mw.peak if mw.ok else None, "gpu_peak_used_mb": mw.gpu_peak if mw.gpu_peak == mw.gpu_peak else None,
                    "psutil": mw.ok})
        rec["times_ms"] = [round(t, 2) for t in times]
    finally:
        if srv is not None:
            srv.stop()
    return rec


def bench_heads_and_shield(n_reports):
    """B and C: heads on one vector, and the Shield decisions on saved vectors (development fold 0, level M, seed 1)."""
    from shield.alloc import make_allocator
    from shield.data import DevData
    from shield.devset import DevSet, build_service
    from shield.policy import CommitPolicy, RiskGate, ShieldPolicy, rate_threshold
    from shield.policy2 import GateFB, ObserverV2, ShieldV2
    from shield.readout import Heads
    from shield.sim import Sim, SimConfig

    ds = DevSet()
    D = ds.D
    fit, cal, ev = D.split(0)
    heads = Heads(D.cases, D.X["Q4_K_M"], fit, D.group)
    X = D.X["Q4_K_M"][ev[:n_reports]]
    heads.proba(X[:1])
    ht = []
    for i in range(len(X)):
        t0 = time.perf_counter()
        heads.proba(X[i:i + 1])
        ht.append((time.perf_counter() - t0) * 1000.0)
    out = {"heads_ms_p50": pct(ht, 50), "heads_ms_p95": pct(ht, 95), "heads_ms_max": max(ht)}
    cfg = SimConfig(budget_fraction=0.10)
    sim = Sim(make_allocator("cbba_bounded"), cfg)
    k, q, K, b = 0, ds.q_hat(0, "q4", 0.10), 8, 0.10
    base = build_service(ds, 0, "q4")
    obs = ObserverV2(base, q, K)
    for e in ds.make_episodes(ds.folds[0]["cal"], "M", 1100, 20):
        sim.run(e, obs, "observer")
    th = {n: rate_threshold([r[n] for r in obs.rows], b) for n in ("conf", "s2")}
    p_flag = float(np.mean([r["s2_flag"] for r in obs.rows]))
    th["gfb"] = rate_threshold([r["conf"] for r in obs.rows], p_flag)
    pol = {"A1": CommitPolicy(base), "A6": RiskGate(base, "conf", *th["conf"], seed=1),
           "A8": ShieldPolicy(base, q, K, "shield", True, *rate_threshold([r["a8"] for r in obs.rows], b), seed=1),
           "B3": ShieldV2(base, q, K, *th["s2"], seed=1), "G1": GateFB(base, q, K, *th["conf"], *th["gfb"], seed=1)}
    eps = ds.make_episodes(ds.folds[0]["eval"], "M", 1, 20)
    res = {}
    for name, p in pol.items():
        dec_ms, alloc_ms_per_run, runs = [], [], []
        for e in eps:
            r = sim.run(e, p, name)
            dec_ms += [x["wall_ms"] for x in r["log"]["reports"]]
            if r["log"]["policy_runs"]:
                alloc_ms_per_run.append(r["log"]["policy_alloc_ms"] / r["log"]["policy_runs"])
            runs += [x["runs"] for x in r["log"]["reports"]]
        res[name] = {"decisions": len(dec_ms), "decision_ms_p50": pct(dec_ms, 50), "decision_ms_p95": pct(dec_ms, 95), "decision_ms_p99": pct(dec_ms, 99),
                     "decision_ms_max": max(dec_ms), "allocator_ms_per_run_median": pct(alloc_ms_per_run, 50) if alloc_ms_per_run else None,
                     "allocator_runs_per_decision_mean": float(np.mean(runs))}
    out["shield"] = res
    out["python_peak_mb"] = own_peak_mb()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llama-dir")
    ap.add_argument("--models-dir")
    ap.add_argument("--n", type=int, default=100, help="development reports per precision")
    ap.add_argument("--cpu", action="store_true", help="llama-server with -ngl 0")
    ap.add_argument("--shield-only", action="store_true")
    ap.add_argument("--port", type=int, default=8092)
    ap.add_argument("--attach-url", help="testing: use a server that is already running (one precision only)")
    ap.add_argument("--attach-pid", type=int)
    a = ap.parse_args()
    out_dir = paths.RESULTS / ("bench_" + time.strftime("%Y%m%dT%H%M%S"))
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {"when": time.strftime("%Y-%m-%d %H:%M:%S"), "platform": platform.platform(), "machine": platform.machine(), "processor": platform.processor(),
           "python": platform.python_version(), "cpu_count": __import__("os").cpu_count(), "mode": "CPU (-ngl 0)" if a.cpu else "as the development extraction (-ngl 99)"}
    try:
        import psutil
        rec["ram_total_gb"] = round(psutil.virtual_memory().total / 2 ** 30, 1)
    except Exception:
        rec["ram_total_gb"] = None
    if not a.shield_only:
        import extract_fresh_vectors as ex
        from shield.devset import DevSet
        ds = DevSet()
        _, _, ev = ds.D.split(0)
        cases = [ds.cases[int(i)] for i in ev]
        exe = None
        if not a.attach_url:
            exe = next((p for p in (Path(a.llama_dir) / "llama-server.exe", Path(a.llama_dir) / "llama-server", Path(a.llama_dir) / "build" / "bin" / "llama-server") if p.exists()), None)
            if exe is None:
                raise SystemExit("llama-server not found under --llama-dir")
        models = ["Q4_K_M"] if a.attach_url else ex.MODELS
        rec["precisions"] = []
        for m in models:
            print("measuring", m, flush=True)
            rec["precisions"].append(bench_precision(m, exe, a.models_dir or ".", cases, a.n, 0 if a.cpu else 99, out_dir, a.port, a.attach_url, a.attach_pid))
    print("measuring heads and Shield on saved vectors ...", flush=True)
    rec.update(bench_heads_and_shield(min(a.n, 200)))
    (out_dir / "bench.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    L = ["# Speed and memory on this computer", "", "%s; %s; Python %s; RAM %s GB; mode: %s; %s." % (rec["platform"], rec["processor"] or rec["machine"], rec["python"], rec["ram_total_gb"], rec["mode"], rec["when"]), ""]
    if "precisions" in rec:
        L += ["## The model (llama.cpp server, one report at a time)", "",
              "| precision | file (MB) | start (s) | server peak memory (MB) | GPU memory used (MB) | embed p50 (ms) | p95 (ms) | max (ms) |", "|---|---|---|---|---|---|---|---|"]
        for p in rec["precisions"]:
            f = lambda v, d=0: "n/a" if v is None else ("%.*f" % (d, v))   # noqa: E731
            L.append("| %s | %.0f | %s | %s | %s | %.0f | %.0f | %.0f |" % (p["model"], p["gguf_bytes"] / 2 ** 20, f(p["start_s"], 1), f(p["server_peak_rss_mb"]), f(p["gpu_peak_used_mb"]),
                                                                      p["embed_ms_p50"], p["embed_ms_p95"], p["embed_ms_max"]))
        L += ["", "Server memory needs `pip install psutil`; GPU memory needs nvidia-smi (it is the whole GPU in use, so close other GPU programs first).", ""]
    L += ["## Heads and Shield (saved vectors, development fold 0, level M)", "", "Heads: p50 %.2f ms, p95 %.2f ms per report. Python process peak memory: %.0f MB." % (rec["heads_ms_p50"], rec["heads_ms_p95"], rec["python_peak_mb"]), "",
          "| policy | decision p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | allocator runs / decision | allocator ms / run (median) |", "|---|---|---|---|---|---|---|"]
    for n, s in rec["shield"].items():
        L.append("| %s | %.2f | %.2f | %.2f | %.2f | %.2f | %s |" % (n, s["decision_ms_p50"], s["decision_ms_p95"], s["decision_ms_p99"], s["decision_ms_max"], s["allocator_runs_per_decision_mean"],
                                                                 "-" if s["allocator_ms_per_run_median"] is None else "%.2f" % s["allocator_ms_per_run_median"]))
    L += ["", "The simulation charges 20 ms of decision time per allocator run. If the measured value is far from 20 ms the assumption (docs/DEVIATIONS.md D-12) must be revisited.", ""]
    if "precisions" in rec:
        L += ["## One report from text to decision (p50 + p50 + p50; p95 + p95 + p95 is an upper bound)", "", "| precision | Shield-2 (B3) p50 (ms) | B3 p95-sum (ms) | no gate (A1) p50 (ms) |", "|---|---|---|---|"]
        for p in rec["precisions"]:
            b3, a1 = rec["shield"]["B3"], rec["shield"]["A1"]
            L.append("| %s | %.0f | %.0f | %.0f |" % (p["model"], p["embed_ms_p50"] + rec["heads_ms_p50"] + b3["decision_ms_p50"], p["embed_ms_p95"] + rec["heads_ms_p95"] + b3["decision_ms_p95"],
                                                   p["embed_ms_p50"] + rec["heads_ms_p50"] + a1["decision_ms_p50"]))
    (out_dir / "BENCH.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print("saved:", out_dir)


if __name__ == "__main__":
    main()
