"""
Run the pilot: start llama-server for one model file, send every case, save the raw answers, stop the server.

  python run_model.py --list          show the plan and what is already done
  python run_model.py --smoke         20 cases on the first model (about 1 minute): checks everything works
  python run_model.py --all           run every session in config.json (safe to stop and start again: it resumes)
  python run_model.py --only s3_q4    run one session only
  options: --limit N (first N cases of each run, for tests)  --ngl N (GPU layers)  --config FILE

One server per model, models run one after another (never two at the same time).
Greedy decoding (temperature 0, top-k 1), fixed seed, no prompt cache, batch of one: the same prompt must give the same answer.
"""
import argparse
import atexit
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import (ROOT, SPECIAL_STRINGS, build_grammar, build_prompt, load_cases, load_config,
                    load_subsets, parse_decision, schema_ok)


# ------------------------------------------------------------------ tiny HTTP helper (standard library only)
def http_json(url, payload=None, timeout=120):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def gpu_info():
    """Best effort: name and memory used (MB) from nvidia-smi. Returns None if not available."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total,driver_version",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            name, used, total, drv = [x.strip() for x in out.stdout.strip().splitlines()[0].split(",")]
            return {"gpu": name, "vram_used_mb": float(used), "vram_total_mb": float(total), "driver": drv}
    except Exception:
        pass
    return None


# ------------------------------------------------------------------ server wrapper
class Server:
    def __init__(self, cfg, model_path, tag, ngl_override=None):
        s = cfg["server"]
        self.cfg = cfg
        self.model = Path(model_path)
        self.tag = tag
        self.host, self.port = s["host"], int(s["port"])
        self.base = "http://%s:%d" % (self.host, self.port)
        self.ctx = int(s["ctx"])
        self.ngl = int(ngl_override if ngl_override is not None else s["ngl"])
        self.threads = int(s["threads"])
        self.start_timeout = int(s.get("start_timeout_s", 300))
        self.req_timeout = int(s.get("request_timeout_s", 120))
        self.extra = list(s.get("extra_args", []))
        self.proc = None
        self.load_s = None
        self.log_path = ROOT / "logs" / ("server_%s.log" % tag)

    def exe(self):
        d = Path(self.cfg["paths"]["llama_bin_dir"])
        for name in ("llama-server.exe", "llama-server"):
            if (d / name).exists():
                return d / name
        raise FileNotFoundError("llama-server not found in %s. Check paths.llama_bin_dir in config.json." % d)

    def start(self):
        if port_in_use(self.host, self.port):
            raise RuntimeError("Port %d is already in use (is an old llama-server still running? Close it, or change "
                               "server.port in config.json)." % self.port)
        exe = self.exe()
        cmd = [str(exe), "-m", str(self.model), "--host", self.host, "--port", str(self.port),
               "-ngl", str(self.ngl), "-c", str(self.ctx), "-np", "1", "-t", str(self.threads)] + self.extra
        self.log_path.parent.mkdir(exist_ok=True)
        logf = open(self.log_path, "w", encoding="utf-8", errors="replace")
        logf.write("COMMAND: %s\n\n" % " ".join(cmd))
        logf.flush()
        self.proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=str(exe.parent))
        atexit.register(self.stop)
        t0 = time.time()
        while True:
            if self.proc.poll() is not None:
                raise RuntimeError("llama-server stopped while loading. Read the last lines of %s" % self.log_path)
            try:
                st, _ = http_json(self.base + "/health", timeout=5)
                if st == 200:
                    break
            except urllib.error.HTTPError:
                pass  # 503 = still loading
            except Exception:
                pass
            if time.time() - t0 > self.start_timeout:
                self.stop()
                raise RuntimeError("llama-server did not become ready in %d s. See %s" % (self.start_timeout, self.log_path))
            time.sleep(1.0)
        self.load_s = time.time() - t0

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except Exception:
                self.proc.kill()
        self.proc = None

    # -------------------------------------------------------------- helpers
    def tokenize(self, text, add_special=False, parse_special=True):
        _, body = http_json(self.base + "/tokenize", {"content": text, "add_special": add_special,
                                                      "parse_special": parse_special}, timeout=30)
        return body["tokens"]

    def props(self):
        try:
            return http_json(self.base + "/props", timeout=10)[1]
        except Exception:
            return {}

    def preflight(self, sample_case):
        """Checks that the prompt format is understood by this model file. Returns a dict for the log."""
        info = {"special_tokens_ok": True, "bos_added_once": None}
        for s in SPECIAL_STRINGS:
            toks = self.tokenize(s, add_special=False, parse_special=True)
            if len(toks) != 1:
                info["special_tokens_ok"] = False
                raise RuntimeError("This model file does not treat %s as one special token (got %d tokens). "
                                   "It is not a Llama-3 style model file, so the prompt format would be wrong." % (s, len(toks)))
        bos = self.tokenize("<|begin_of_text|>", add_special=False, parse_special=True)
        prompt = build_prompt(sample_case, "P1")
        with_special = self.tokenize(prompt, add_special=True, parse_special=True)
        if len(bos) == 1:
            info["bos_added_once"] = (with_special[0] == bos[0] and with_special[1] != bos[0])
        info["prompt_tokens"] = len(with_special)
        return info

    def complete(self, prompt, grammar, n_predict, seed):
        body = {"prompt": prompt, "n_predict": n_predict, "temperature": 0, "top_k": 1, "top_p": 1.0, "min_p": 0.0,
                "repeat_penalty": 1.0, "repeat_last_n": 0, "seed": seed, "cache_prompt": False, "stream": False,
                "stop": ["<|eot_id|>"]}
        if grammar:
            body["grammar"] = grammar
        t0 = time.perf_counter()
        _, r = http_json(self.base + "/completion", body, timeout=self.req_timeout)
        return r, (time.perf_counter() - t0) * 1000.0


# ------------------------------------------------------------------ one run (one prompt, one subset, one grammar setting)
def read_done(path):
    done = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        done[rec["case_id"]] = rec
                    except Exception:
                        pass
    return done


def do_run(srv, run, ids, cases_by_id, cfg, out_dir, prefix=""):
    name = prefix + run["run"]
    path = out_dir / (name + ".jsonl")
    done = read_done(path)
    todo = [i for i in ids if i not in done]
    grammar = build_grammar() if run.get("grammar", True) else None
    n_pred = int(cfg["decode"]["n_predict"])
    seed = int(cfg["decode"]["seed"])
    print("  run %-22s %4d cases, %d already done" % (name, len(ids), len(ids) - len(todo)))
    if not todo:
        return
    errors = 0
    t_start = time.time()
    walls = []
    with open(path, "a", encoding="utf-8") as f:
        for n, cid in enumerate(todo, 1):
            case = cases_by_id[cid]
            prompt = build_prompt(case, run["prompt"])
            r = None
            for attempt in range(3):
                try:
                    r, wall = srv.complete(prompt, grammar, n_pred, seed)
                    break
                except Exception as e:  # connection hiccup: wait and try again
                    if srv.proc is not None and srv.proc.poll() is not None:
                        raise RuntimeError("llama-server died. See %s" % srv.log_path)
                    time.sleep(2.0)
                    r = None
                    last_err = str(e)
            if r is None:
                errors += 1
                rec = {"case_id": cid, "run": name, "error": last_err}
                if errors >= 5:
                    raise RuntimeError("5 failed requests in this run. Last error: %s" % last_err)
            else:
                tm = r.get("timings", {}) or {}
                rec = {"case_id": cid, "run": name, "model": run.get("model"), "prompt_id": run["prompt"],
                       "grammar": grammar is not None, "text": r.get("content", ""),
                       "stop_type": r.get("stop_type"), "tokens_evaluated": r.get("tokens_evaluated"),
                       "tokens_predicted": r.get("tokens_predicted"), "wall_ms": round(wall, 2),
                       "prompt_ms": tm.get("prompt_ms"), "predicted_ms": tm.get("predicted_ms"),
                       "prompt_n": tm.get("prompt_n"), "predicted_n": tm.get("predicted_n"),
                       "prompt_per_s": tm.get("prompt_per_second"), "predicted_per_s": tm.get("predicted_per_second")}
                walls.append(wall)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if n % 50 == 0 or n == len(todo):
                el = time.time() - t_start
                eta = el / n * (len(todo) - n)
                print("    %4d/%d  avg %.2fs/call  ETA %.1f min" % (n, len(todo), el / n, eta / 60.0))


# ------------------------------------------------------------------ sessions
def model_file(cfg, key):
    return Path(cfg["paths"]["models_dir"]) / cfg["models"][key]


def run_session(cfg, session, cases_by_id, subsets, args, env, out_dir, prefix=""):
    mp = model_file(cfg, session["model"])
    if not mp.exists():
        raise FileNotFoundError("Model file not found: %s\n(If it is a Q8_0 or Q4_K_M file, run make_quants.py first.)" % mp)
    print("\n== session %s  (model %s, %.2f GB)" % (session["name"], session["model"], mp.stat().st_size / 1e9))
    srv = Server(cfg, mp, session["name"], args.ngl)
    srv.start()
    try:
        first_case = next(iter(cases_by_id.values()))
        pre = srv.preflight(first_case)
        g = gpu_info()
        props = srv.props()
        env.setdefault("sessions", {})[session["name"]] = {
            "model_key": session["model"], "model_file": str(mp), "model_gb": round(mp.stat().st_size / 1e9, 3),
            "load_seconds": round(srv.load_s, 1), "preflight": pre, "gpu_after_load": g,
            "server_build": props.get("build_info"), "ngl": srv.ngl, "ctx": srv.ctx}
        print("   loaded in %.1f s. special tokens ok: %s, start token added once: %s%s" % (
            srv.load_s, pre["special_tokens_ok"], pre["bos_added_once"],
            (", VRAM used %.0f MB" % g["vram_used_mb"]) if g else ""))
        if pre["bos_added_once"] is False:
            print("   WARNING: the start-of-text token is not added exactly once. Results may be worse than they should be.")
        for run in session["runs"]:
            run = dict(run, model=session["model"])
            if args.only_run and run["run"] != args.only_run:
                continue
            ids = subsets[run["subset"]]
            if args.limit:
                ids = ids[:args.limit]
            do_run(srv, run, ids, cases_by_id, cfg, out_dir, prefix)
    finally:
        srv.stop()
        time.sleep(1.0)


def smoke_report(cfg, cases_by_id, out_dir, prefix):
    session = cfg["sessions"][0]
    run = session["runs"][0]
    path = out_dir / (prefix + run["run"] + ".jsonl")
    recs = list(read_done(path).values())
    n = len(recs)
    ok = sum(1 for r in recs if "text" in r and schema_ok(parse_decision(r["text"])[0]))
    walls = [r["wall_ms"] for r in recs if "wall_ms" in r]
    print("\nSMOKE TEST RESULT")
    print("  calls: %d, valid under the schema: %d (%.0f%%)" % (n, ok, 100.0 * ok / max(1, n)))
    if walls:
        print("  median time per call: %.2f s   (full run = about %.1f hours per model for %d calls)" % (
            statistics.median(walls) / 1000.0, statistics.mean(walls) * 1400 / 3.6e6, 1400))
    for r in recs[:5]:
        c = cases_by_id[r["case_id"]]
        print("  - report: %s" % c["text"][:110])
        print("    gold  : %s" % json.dumps(c["gold"], separators=(",", ":")))
        print("    model : %s" % r.get("text", r.get("error")))
    if ok < n:
        print("  Some outputs are not valid. Look at logs/ and tell Claude.")
    print("  If this looks sane, run:  python run_model.py --all")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", default=None, help="session name, e.g. s3_q4")
    ap.add_argument("--only-run", default=None, help="run name inside the session")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ngl", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    cases = load_cases(ROOT / cfg["cases"]["file"])
    cases_by_id = {c["id"]: c for c in cases}
    subsets = load_subsets()
    out_dir = ROOT / "runs"
    out_dir.mkdir(exist_ok=True)
    (ROOT / "results").mkdir(exist_ok=True)

    if args.list:
        for s in cfg["sessions"]:
            print(s["name"], "model:", s["model"], "(optional: only runs with --only %s)" % s["name"] if s.get("optional") else "")
            for r in s["runs"]:
                n = len(subsets[r["subset"]])
                d = len(read_done(out_dir / (r["run"] + ".jsonl")))
                print("   %-22s prompt %s, subset %-9s (%d cases), grammar %s, done %d" % (
                    r["run"], r["prompt"], r["subset"], n, r.get("grammar", True), d))
        return

    env = {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
           "started": time.strftime("%Y-%m-%d %H:%M:%S"), "gpu": gpu_info()}
    env_path = ROOT / "results" / "env.json"
    if env_path.exists():
        try:
            old = json.load(open(env_path, encoding="utf-8"))
            env["sessions"] = old.get("sessions", {})
        except Exception:
            pass

    try:
        if args.smoke:
            session = dict(cfg["sessions"][0])
            session["runs"] = [dict(session["runs"][0])]
            args.limit = 20
            run_session(cfg, session, cases_by_id, subsets, args, env, out_dir, prefix="smoke_")
            smoke_report(cfg, cases_by_id, out_dir, "smoke_")
        elif args.all or args.only:
            sessions = [s for s in cfg["sessions"]
                        if (not args.only or s["name"] == args.only) and (args.only or not s.get("optional"))]
            if not sessions:
                sys.exit("No session called '%s'. Use  python run_model.py --list  to see the names." % args.only)
            missing = sorted({str(model_file(cfg, s["model"])) for s in sessions if not model_file(cfg, s["model"]).exists()})
            if missing:
                sys.exit("These model files are missing:\n  " + "\n  ".join(missing) +
                         "\nDownload the FP16 file (README step 3), then run  python make_quants.py  (README step 5).")
            for s in sessions:
                run_session(cfg, s, cases_by_id, subsets, args, env, out_dir)
            print("\nAll requested runs finished. Next:  python analyze.py")
        else:
            ap.print_help()
    finally:
        json.dump(env, open(env_path, "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    main()
