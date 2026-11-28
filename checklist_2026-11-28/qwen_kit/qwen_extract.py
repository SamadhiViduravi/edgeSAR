"""
EdgeSAR - second model family (exploratory; item 5 of the supervisor's checklist, 28 Nov 2026).

Hidden-state vectors of Qwen2.5-1.5B-Instruct: the FP16 GGUF file of the Qwen team and a Q4_K_M file made from it with
llama-quantize (no importance matrix), with the SAME llama.cpp build (b11901), server settings (--embeddings --pooling last,
-b 1024 -ub 1024, -c 4096, -np 1, -t 6), system prompt (P1), user message and positions (end, prefix) as the Llama 3.2 1B
study. Only the chat format differs: Qwen's ChatML tokens instead of the Llama-3 header tokens.

    python qwen_extract.py --check     about 3 minutes. For FP16 and Q4_K_M: starts the server, checks the prompt format,
                                       embeds 20 development reports twice (the two vectors must agree, cosine >= 0.9999),
                                       and prints a time estimate. Nothing is saved except logs/ and check_report.json.
    python qwen_extract.py             the full run: position `prefix` first (FP16 then Q4_K_M; development reports, then
                                       fresh reports), then position `end`. Saves every 100 reports; if it stops, run the
                                       same command again and it continues.

Put this folder next to edgesar_pilot and edgesar_fresh_2026-11-18. It reads those folders and writes only into this folder.
"""
import argparse
import copy
import hashlib
import json
import sys
import time
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "edgesar_pilot"
FRESH = HERE.parent / "edgesar_fresh_2026-11-18"
if not (PILOT / "common.py").exists():
    sys.exit("Cannot find edgesar_pilot next to this folder (%s)." % PILOT)
sys.path.insert(0, str(PILOT))
import numpy as np                       # noqa: E402
import common as pc                      # noqa: E402  (pilot: system prompt and user message, read only)
import run_model as rm                   # noqa: E402  (pilot: llama-server starter, read only)

MODELS = {"f16": "qwen2.5-1.5b-instruct-fp16.gguf", "Q4_K_M": "qwen2.5-1.5b-instruct-Q4_K_M.gguf"}
F16_SHA256 = "fc89e330deb3fd8fa560f1c0f35a1e2b8da96d59e13445559ed190307a6f5649"   # Hugging Face, Qwen/Qwen2.5-1.5B-Instruct-GGUF
PILOT_COMMON_SHA256 = "332ec94d84fa385b2fae2b2949cd8cbf7463a1de2527236f0b2a78ba47f3c91a"  # frozen 28 Oct 2026
SERVER_ARGS = ["--embeddings", "--pooling", "last", "-b", "1024", "-ub", "1024"]
UB = 1024
PORT = 8093
PREFIX_TEXT = "{\"action\":\""
VARIANTS = ["prefix", "end"]
NGL_TRY = [99, 24, 20, 16, 12]           # all layers on the GPU; fewer only if the 4 GB GPU runs out of memory
Q4_MIN_BYTES = 800_000_000             # a complete Qwen2.5-1.5B Q4_K_M file is about 1.1 GB
ANCHOR_IDS = ["c%04d" % i for i in range(1, 1001, 50)]
MIN_COS = 0.9999


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def prompt_for(case, variant):
    """Same system prompt (P1) and user message as the Llama study, in Qwen's chat format."""
    base = ("<|im_start|>system\n" + pc.system_prompt("P1") + "<|im_end|>\n"
            "<|im_start|>user\n" + pc.user_message(case) + "<|im_end|>\n"
            "<|im_start|>assistant\n")
    if variant == "end":
        return base
    if variant == "prefix":
        return base + PREFIX_TEXT
    raise ValueError(variant)


def http_json(url, payload=None, timeout=120):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def embed(base, text, timeout=120):
    _, body = http_json(base + "/v1/embeddings", {"input": text, "encoding_format": "float"}, timeout)
    arr = np.asarray(body["data"][0]["embedding"], dtype=np.float32)
    rows = 1
    if arr.ndim == 2:
        rows = arr.shape[0]
        arr = arr[-1]
    ntok = (body.get("usage") or {}).get("prompt_tokens")
    return arr, rows, ntok


def tokenize(base, text, add_special):
    _, body = http_json(base + "/tokenize", {"content": text, "add_special": add_special, "parse_special": True}, 30)
    return body["tokens"]


def gpu_mib():
    """(used, total) GPU memory in MiB from nvidia-smi, or None."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[0]
        u, t = (float(x) for x in out.split(","))
        return u, t
    except Exception:
        return None


def memory_gb():
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return None
        return m.ullAvailPhys / 1e9, m.ullTotalPhys / 1e9, m.ullAvailPageFile / 1e9
    except Exception:
        return None


def memory_report():
    mem, g = memory_gb(), gpu_mib()
    if mem:
        print("   free memory: %.1f GB of %.1f GB RAM; %.1f GB can still be committed" % mem)
        if mem[0] < 3.0 or mem[2] < 4.0:
            print("   WARNING: little free memory. Close other programs (Blender, browsers, games) or restart the laptop.")
    if g:
        print("   GPU memory in use before starting: %.0f of %.0f MiB" % g)
        if g[0] > 800:
            print("   WARNING: another program is using the GPU memory. Close it (or restart the laptop) and run this again.")


def last_log_line(path):
    try:
        lines = [l.strip() for l in open(path, encoding="utf-8", errors="replace") if l.strip()]
        return lines[-1][:200] if lines else ""
    except Exception:
        return ""


def start_server(mk, tag):
    cfg = copy.deepcopy(pc.load_config())
    cfg["server"]["port"] = PORT
    cfg["server"]["extra_args"] = list(SERVER_ARGS)
    model = Path(cfg["paths"]["models_dir"]) / MODELS[mk]
    if not model.exists():
        sys.exit("Model file not found: %s\nRun STEP_Q1_download_and_quantize.bat first." % model)
    if mk == "Q4_K_M" and model.stat().st_size < Q4_MIN_BYTES:
        sys.exit("STOP: the Q4_K_M file is incomplete (%.2f GB). Run STEP_Q1_download_and_quantize.bat again." % (model.stat().st_size / 1e9))
    (HERE / "logs").mkdir(exist_ok=True)
    memory_report()
    last = None
    for ngl in NGL_TRY:
        srv = rm.Server(cfg, model, tag, ngl_override=ngl)
        srv.log_path = HERE / "logs" / ("server_%s_ngl%d.log" % (tag, ngl))
        try:
            srv.start()
            print("   server ready in %.1f s (GPU layers: %s)" % (srv.load_s, ngl))
            return srv, ngl, model
        except Exception as e:                      # usually: out of GPU memory; try fewer GPU layers
            last = e
            srv.stop()
            print("   could not start with -ngl %d: %s" % (ngl, last_log_line(srv.log_path)))
            time.sleep(5)
    sys.exit("STOP: llama-server did not start. If the lines above say 'out of memory' or 'mem_buffer', close other programs or "
             "restart the laptop and run this again. Otherwise send me this window text.")


def preflight(base, cases):
    info = {}
    for s in ("<|im_start|>", "<|im_end|>"):
        t = tokenize(base, s, add_special=False)
        if len(t) != 1:
            sys.exit("STOP: %s is not one special token for this model file (got %d tokens)." % (s, len(t)))
    im_start = tokenize(base, "<|im_start|>", add_special=False)[0]
    toks = tokenize(base, prompt_for(cases[0], "prefix"), add_special=True)
    info["first_token_is_im_start"] = bool(toks[0] == im_start)
    info["tokens_added_before_prompt"] = toks.index(im_start) if im_start in toks else None
    longest = sorted(cases, key=lambda c: len(prompt_for(c, "prefix")), reverse=True)[:40]
    mx = max(len(tokenize(base, prompt_for(c, "prefix"), add_special=True)) for c in longest)
    info["max_prompt_tokens_of_40_longest"] = mx
    if mx >= UB:
        sys.exit("STOP: a prompt has %d tokens, more than the batch size %d. Send me this message." % (mx, UB))
    return info


def extract(base, cases, variant, mk, part, out_dir, meta):
    out = out_dir / ("qwen_%s_%s_%s.npy" % (mk, variant, part))
    partial = out.with_name(out.stem + ".partial.npy")
    if out.exists():
        print("   %s %s %s: already finished, skipped." % (mk, variant, part))
        return
    n = len(cases)
    X, done = None, 0
    if partial.exists():
        X = np.load(partial)
        done = int(np.sum(~np.isnan(X[:, 0])))
        print("   %s %s %s: continuing from report %d of %d" % (mk, variant, part, done, n))
    t0 = time.time()
    tmax = 0
    for i in range(done, n):
        text = prompt_for(cases[i], variant)
        try:
            vec, rows, ntok = embed(base, text)
        except Exception:
            time.sleep(2.0)
            vec, rows, ntok = embed(base, text)
        if rows != 1 and i == done:
            print("   note: the server sent %d rows; the last row is used" % rows)
        if not np.all(np.isfinite(vec)):
            sys.exit("STOP: the vector of %s has NaN or infinity." % cases[i]["id"])
        if X is None:
            X = np.full((n, vec.shape[0]), np.nan, dtype=np.float32)
        X[i] = vec
        if ntok:
            tmax = max(tmax, int(ntok))
            if ntok >= UB:
                sys.exit("STOP: report %s has %d prompt tokens (batch %d). Send me this message." % (cases[i]["id"], ntok, UB))
        if (i + 1) % 100 == 0 or i + 1 == n:
            np.save(partial, X)
            rate = (i + 1 - done) / max(time.time() - t0, 1e-9)
            print("   %s %s %s: %d / %d  (%.1f reports/s, about %.0f min left)" % (mk, variant, part, i + 1, n, rate, (n - i - 1) / max(rate, 1e-9) / 60))
    np.save(out, X)
    partial.unlink(missing_ok=True)
    m = dict(meta)
    m.update({"variant": variant, "part": part, "reports": n, "dim": int(X.shape[1]), "max_prompt_tokens": tmax,
              "minutes": round((time.time() - t0) / 60, 2), "sha256": sha(out)})
    (out_dir / ("qwen_%s_%s_%s.meta.json" % (mk, variant, part))).write_text(json.dumps(m, indent=1), encoding="utf-8")
    print("   %s %s %s finished in %.1f min" % (mk, variant, part, (time.time() - t0) / 60))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if sha(PILOT / "common.py") != PILOT_COMMON_SHA256:
        sys.exit("STOP: edgesar_pilot/common.py is not the frozen file.")
    dev = pc.load_cases(PILOT / "data" / "cases.jsonl")
    man = json.loads((FRESH / "generation_manifest.json").read_text(encoding="utf-8"))
    if sha(FRESH / "cases_fresh.jsonl") != man["cases_sha256"]:
        sys.exit("STOP: cases_fresh.jsonl is not the generated file.")
    fresh = [json.loads(l) for l in open(FRESH / "cases_fresh.jsonl", encoding="utf-8") if l.strip()]
    byid = {c["id"]: c for c in dev}
    out_dir = HERE / "vectors"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "case_ids_dev.json").write_text(json.dumps([c["id"] for c in dev]), encoding="utf-8")
    (out_dir / "case_ids_fresh.json").write_text(json.dumps([c["id"] for c in fresh]), encoding="utf-8")
    cfg = pc.load_config()
    models_dir = Path(cfg["paths"]["models_dir"])
    report_path = HERE / ("check_report.json" if a.check else "extraction_report.json")
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() and not a.check else {}
    report.setdefault("models", {})
    print("Development reports: %d. Fresh reports: %d." % (len(dev), len(fresh)))
    for mk in MODELS:
        p = models_dir / MODELS[mk]
        if mk not in report["models"]:
            print("Hashing %s ..." % p.name)
            h = sha(p) if p.exists() else None
            report["models"][mk] = {"file": p.name, "sha256": h}
            if mk == "f16" and h != F16_SHA256:
                sys.exit("STOP: the FP16 file is not the Qwen file (SHA-256 differs). Download it again with STEP_Q1.")
    plan = [("prefix", "f16"), ("prefix", "Q4_K_M"), ("end", "f16"), ("end", "Q4_K_M")]
    if a.check:
        plan = [("prefix", "f16"), ("prefix", "Q4_K_M")]
    for variant, mk in plan:
        print("\n=== Qwen2.5-1.5B %s, position %s ===" % (mk, variant))
        srv, ngl, model = start_server(mk, "qwen_%s_%s" % (mk, variant))
        try:
            info = preflight(srv.base, dev + fresh)
            info["ngl"] = ngl
            info["build_info"] = srv.props().get("build_info")
            print("   prompt format OK: %s" % info)
            if a.check:
                cs, t0 = [], time.time()
                for cid in ANCHOR_IDS:
                    v1, _, _ = embed(srv.base, prompt_for(byid[cid], variant))
                    v2, _, _ = embed(srv.base, prompt_for(byid[cid], variant))
                    cs.append(float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))))
                per = (time.time() - t0) / (2 * len(ANCHOR_IDS))
                info.update({"repeat_min_cos": min(cs), "dim": int(v1.shape[0]), "seconds_per_report": round(per, 3)})
                print("   repeat check: lowest cosine %.7f; vector length %d; %.2f s per report" % (min(cs), v1.shape[0], per))
                print("   estimated time for this model: about %.0f min per position (8,400 reports)" % (per * 8400 / 60))
                if min(cs) < MIN_COS:
                    sys.exit("STOP: the same report gave different vectors. Send me this whole window text.")
                report["models"][mk]["check_" + variant] = info
            else:
                meta = {"model": mk, "model_file": model.name, "model_sha256": report["models"][mk]["sha256"], "ngl": ngl,
                        "build_info": info["build_info"], "server_args": SERVER_ARGS}
                report["models"][mk]["run_" + variant] = info
                report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
                extract(srv.base, dev, variant, mk, "dev", out_dir, meta)
                extract(srv.base, fresh, variant, mk, "fresh", out_dir, meta)
        except KeyboardInterrupt:
            print("\nStopped by you. Progress is saved. Run the same command again to continue.")
            raise
        finally:
            srv.stop()
        report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    if a.check:
        print("\nCHECK PASSED for both models. Now run STEP_Q3_extract.bat (and tell me the time estimate above).")
    else:
        print("\nALL DONE. The vectors are in %s. Tell Claude: 'Qwen extraction finished'." % out_dir)


if __name__ == "__main__":
    main()
