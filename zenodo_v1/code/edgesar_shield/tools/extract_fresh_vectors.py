"""
GPU step (kept apart from everything else): one hidden-state vector per FRESH report, for each of the three precisions.

    python tools/extract_fresh_vectors.py --cases fresh/cases_fresh.jsonl --expect-cases-sha256 <hash from generation_manifest.json> ^
           --llama-dir D:\\llama --models-dir D:\\llama\\models --out fresh\\vectors

What it does, in this order (it stops at the first FAIL and tells you why):
  1. checks the pilot files (SHA-256) and the cases file (SHA-256 you give it);
  2. builds the prompt of every report with the PILOT'S OWN build_prompt (prompt P1) and hashes the prompts;
  3. for each model (f16, Q8_0, Q4_K_M; one server at a time):  checks the model file's SHA-256 against the audited value;
     starts  llama-server -m <gguf> --host 127.0.0.1 --port 8091 -ngl 99 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024
     (exactly the command that made the saved development vectors, see edgesar_heads/logs/server_extract_*.log);
     checks the llama.cpp build (b11901-5320c87ff), that the start token is added once, that the same prompt twice gives the same vector,
     and that 20 DEVELOPMENT reports embedded now reproduce the SAVED development vectors (so fresh and development vectors are comparable);
  4. embeds every fresh report in order (saves every 100; run the same command again to continue after Ctrl+C);
  5. checks the server log: the token counts in the log are the token counts of our requests, in the same order (no report lost or swapped);
  6. optional CPU check: restarts the server with -ngl 0 and re-embeds 100 fresh reports; the GPU and CPU vectors must agree (cosine);
  7. writes  <model>_end.npy,  <model>_end.meta.json,  case_ids.json,  extraction_manifest.json  into --out.

Attach mode (for testing, or if you start llama-server yourself):  --server-url http://127.0.0.1:8091 --server-log <log file> --one-model f16
Nothing in the pilot, the heads or the V1 folders is written.  Run it ONLY after docs/EVAL_PLAN_FRESH.md is frozen.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                                # noqa: E402

from shield import paths                                          # noqa: E402

MODELS = ["f16", "Q8_0", "Q4_K_M"]
GGUF_FILE = {"f16": "Llama-3.2-1B-Instruct-f16.gguf", "Q8_0": "Llama-3.2-1B-Instruct-Q8_0.gguf", "Q4_K_M": "Llama-3.2-1B-Instruct-Q4_K_M.gguf"}
GGUF_SHA256 = {"f16": "1f33ad43d2b85b908ff06fe7002b69806a57359b9b2617ca27d7bdea428ae146",
               "Q8_0": "da49f51ced8c15546e7779beb677fb53eb5d0b3b38ac4607ac60d58d77074823",
               "Q4_K_M": "26bac8efd811cb41a80db4393dbe5c8360abd54b98954ec766aa4ba7dacc0bc5"}
GGUF_BYTES = {"f16": 2479595360, "Q8_0": 1321082720, "Q4_K_M": 807694176}
LLAMA_BUILD = "b11901-5320c87ff"
PROMPT_ID = "P1"
# the command of the saved development vectors (edgesar_heads/logs/server_extract_*.log), without the paths
SERVER_FLAGS = {"host": "127.0.0.1", "port": 8091, "ngl": 99, "ctx": 4096, "np": 1, "threads": 6,
                "extra": ["--embeddings", "--pooling", "last", "-b", "1024", "-ub", "1024"]}
BOS_ID = 128000
MIN_COS_ANCHOR = 0.9999           # fresh re-embedding of development reports vs the saved development vectors
MIN_COS_CPU = 0.999               # GPU vs CPU


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# =====================================================================================================================
# talking to llama-server
# =====================================================================================================================
def http_json(url, payload=None, timeout=120):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data is not None else {},
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


class EmbedClient:
    """One vector per prompt from /v1/embeddings (falls back to /embedding). Returns (float32 vector, prompt tokens or None)."""

    def __init__(self, base, timeout=120):
        self.base, self.timeout, self.mode = base.rstrip("/"), timeout, None

    @staticmethod
    def _vec(emb):
        a = np.asarray(emb, dtype=np.float32)
        if a.ndim == 2:
            a = a[-1]
        if a.ndim != 1 or a.size == 0:
            raise ValueError("unexpected embedding shape %s" % (a.shape,))
        return a

    def embed(self, text):
        if self.mode in (None, "v1"):
            try:
                _, b = http_json(self.base + "/v1/embeddings", {"input": text, "encoding_format": "float"}, self.timeout)
                self.mode = "v1"
                return self._vec(b["data"][0]["embedding"]), (b.get("usage") or {}).get("prompt_tokens")
            except urllib.error.HTTPError as e:
                if self.mode == "v1" or e.code not in (404, 405, 501):
                    raise
        _, b = http_json(self.base + "/embedding", {"content": text}, self.timeout)
        self.mode = "native"
        item = b[0] if isinstance(b, list) else b
        return self._vec(item["embedding"]), None

    def tokenize(self, text):
        _, b = http_json(self.base + "/tokenize", {"content": text, "add_special": True, "parse_special": True}, self.timeout)
        return b.get("tokens")

    def props(self):
        try:
            return http_json(self.base + "/props", None, 30)[1]
        except Exception:
            return {}


class LlamaServer:
    """The exact command of the development extraction. Output goes to a log file whose first line is the command."""

    def __init__(self, exe, model, log_path, ngl=None, port=None):
        f = SERVER_FLAGS
        self.exe, self.model, self.log_path = str(exe), str(model), Path(log_path)
        self.port = port or f["port"]
        self.cmd = [self.exe, "-m", self.model, "--host", f["host"], "--port", str(self.port), "-ngl", str(f["ngl"] if ngl is None else ngl),
                    "-c", str(f["ctx"]), "-np", str(f["np"]), "-t", str(f["threads"])] + list(f["extra"])
        self.proc = None
        self.base = "http://%s:%d" % (f["host"], self.port)

    def start(self, timeout_s=300):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.log_path, "w", encoding="utf-8")
        self._fh.write("COMMAND: %s\n\n" % " ".join(self.cmd))
        self._fh.flush()
        self.proc = subprocess.Popen(self.cmd, stdout=self._fh, stderr=subprocess.STDOUT)
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if self.proc.poll() is not None:
                raise RuntimeError("llama-server stopped while loading (exit code %s). Read %s" % (self.proc.returncode, self.log_path))
            try:
                st, body = http_json(self.base + "/health", None, 5)
                if st == 200:
                    return time.time() - t0
            except Exception:
                pass
            time.sleep(1.0)
        raise RuntimeError("llama-server did not become ready in %d s. Read %s" % (timeout_s, self.log_path))

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except Exception:
                self.proc.kill()
        if getattr(self, "_fh", None):
            self._fh.close()


# =====================================================================================================================
# checks (pure functions, tested with a fake server)
# =====================================================================================================================
def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def compare_vectors(A, B):
    """Row-wise comparison of two arrays: (min cosine, max abs difference)."""
    cs = [cosine(a, b) for a, b in zip(A, B)]
    return float(min(cs)), float(np.max(np.abs(np.asarray(A) - np.asarray(B))))


def check_command_line(log_path):
    """The first line of the server log must carry the development flags."""
    try:
        first = Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except Exception:
        return "CHECK", "no server log to read the command line from"
    need = ["--embeddings", "--pooling last", "-b 1024", "-ub 1024", "-np 1", "-c 4096", "-ngl 99", "-t 6"]
    missing = [n for n in need if n not in first]
    if missing and "-ngl 0" in first:                      # the CPU check is allowed to differ in -ngl only
        missing = [m for m in missing if m != "-ngl 99"]
    return ("PASS", "command line has the development flags") if not missing else ("FAIL", "command line is missing: %s" % ", ".join(missing))


def parse_log_tokens(log_text):
    return [int(x) for x in re.findall(r"stop processing: n_tokens = (\d+)", log_text)]


def check_log_order(log_path, tokens):
    """The token counts the server logged for its last len(tokens) requests must equal the counts it reported to us, in order."""
    try:
        logged = parse_log_tokens(Path(log_path).read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return "CHECK", "no server log"
    if not logged:
        return "CHECK", "the log has no 'stop processing: n_tokens' lines (log level too low?); order not checked"
    if len(logged) < len(tokens):
        return "FAIL", "the log lists %d requests but we sent %d" % (len(logged), len(tokens))
    tail = logged[-len(tokens):]
    if tail == list(tokens):
        return "PASS", "server log: %d requests, token counts equal ours in the same order" % len(tokens)
    bad = next(i for i, (a, b) in enumerate(zip(tail, tokens)) if a != b)
    return "FAIL", "server log and client disagree at request %d (log %d tokens, we got %d)" % (bad, tail[bad], tokens[bad])


def check_bos(client, prompts, n=3):
    """The server must add exactly one start token; the pilot prompt text has none."""
    toks = []
    for p in prompts[:n]:
        t = client.tokenize(p)
        if not t:
            return "CHECK", "the server's /tokenize gave nothing; start token not checked"
        toks.append(t)
    ok = all(t[0] == BOS_ID and (len(t) < 2 or t[1] != BOS_ID) for t in toks)
    return ("PASS", "start token added once (id %d)" % BOS_ID) if ok else ("FAIL", "start token is not added exactly once: %s" % [t[:3] for t in toks])


def anchor_check(client, anchor_cases, anchor_X, build_prompt, n=20, seed=7):
    """Embed n development reports now; they must reproduce the saved development vectors."""
    rng = np.random.RandomState(seed)
    pick = sorted(rng.choice(len(anchor_cases), size=min(n, len(anchor_cases)), replace=False))
    V = np.stack([client.embed(build_prompt(anchor_cases[i], PROMPT_ID))[0] for i in pick])
    mc, md = compare_vectors(V, anchor_X[pick])
    ok = mc >= MIN_COS_ANCHOR
    return ("PASS" if ok else "FAIL"), "re-embedded %d development reports vs the saved development vectors: min cosine %.7f, max |diff| %.2e (need cosine >= %.4f)" % (len(pick), mc, md, MIN_COS_ANCHOR)


# =====================================================================================================================
# the extraction loop (resumable)
# =====================================================================================================================
def extract_one_model(client, prompts, ids, out_npy, say, save_every=100, ubatch=1024):
    n = len(prompts)
    partial = out_npy.with_name(out_npy.stem + ".partial.npy")
    ntok_file = out_npy.with_name(out_npy.stem + ".partial_tokens.json")
    X, toks, done = None, [], 0
    if partial.exists():
        X = np.load(partial)
        toks = json.loads(ntok_file.read_text()) if ntok_file.exists() else []
        if X.shape[0] != n:
            raise RuntimeError("%s does not match the number of reports. Delete it and start again." % partial)
        done = int(np.sum(~np.isnan(X[:, 0])))
        if len(toks) != done:
            toks = []          # token list incomplete: the log-order check will say CHECK
        say("   continuing from report %d of %d" % (done, n))
    t0 = time.perf_counter()
    start = done
    try:
        for i in range(done, n):
            try:
                vec, nt = client.embed(prompts[i])
            except Exception:
                time.sleep(2.0)
                vec, nt = client.embed(prompts[i])               # one retry, then the error stops the run
            if not np.all(np.isfinite(vec)):
                raise RuntimeError("the vector of %s has NaN or infinity" % ids[i])
            if X is None:
                X = np.full((n, vec.shape[0]), np.nan, dtype=np.float32)
            elif vec.shape[0] != X.shape[1]:
                raise RuntimeError("vector length changed from %d to %d" % (X.shape[1], vec.shape[0]))
            if nt is not None and nt >= ubatch:
                raise RuntimeError("a prompt has %d tokens but the server batch is %d" % (nt, ubatch))
            X[i] = vec
            toks.append(nt if nt is not None else -1)
            if (i + 1) % save_every == 0 or i + 1 == n:
                np.save(partial, X)
                ntok_file.write_text(json.dumps(toks))
                rate = (i + 1 - start) / max(time.perf_counter() - t0, 1e-9)
                say("   %d / %d   %.1f reports/s   about %.1f min left" % (i + 1, n, rate, (n - i - 1) / max(rate, 1e-9) / 60.0))
    except BaseException:
        if X is not None:
            np.save(partial, X)
            ntok_file.write_text(json.dumps(toks))
        raise
    tmp = out_npy.with_name(out_npy.stem + ".tmp.npy")
    np.save(tmp, X)
    os.replace(tmp, out_npy)
    for p in (partial, ntok_file):
        if p.exists():
            p.unlink()
    return X, toks, time.perf_counter() - t0, start


# =====================================================================================================================
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--expect-cases-sha256", required=True, help="SHA-256 of cases_fresh.jsonl (from generation_manifest.json)")
    ap.add_argument("--out", default=str(paths.HERE / "fresh" / "vectors"))
    ap.add_argument("--llama-dir", default=None, help="folder with llama-server(.exe)")
    ap.add_argument("--models-dir", default=None, help="folder with the three .gguf files")
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--limit", type=int, default=None, help="first N reports only (quick test; writes to <out>_limitN)")
    ap.add_argument("--anchor", type=int, default=20, help="development reports re-embedded and compared with the saved vectors (0 = skip)")
    ap.add_argument("--cpu-check", type=int, default=100, help="fresh reports re-embedded on the CPU (0 = skip)")
    ap.add_argument("--anchor-cases", default=None)
    ap.add_argument("--anchor-features", default=None, help="folder with <model>_end.npy of the development vectors")
    ap.add_argument("--server-url", default=None, help="attach mode: use a server that is already running (needs --one-model and --server-log)")
    ap.add_argument("--server-log", default=None)
    ap.add_argument("--one-model", default=None)
    ap.add_argument("--skip-hash-check", action="store_true", help="attach/test mode only: do not hash the gguf file")
    ap.add_argument("--allow-build-mismatch", action="store_true")
    a = ap.parse_args(argv)

    say = lambda s: print(s, flush=True)                                                          # noqa: E731
    problems = []
    # ---- 1. inputs
    bad = paths.check_pins()
    if bad:
        sys.exit("STOP. The older folders are not the audited ones:\n  " + "\n  ".join(bad))
    cases_path = Path(a.cases)
    got = sha256_file(cases_path)
    if got != a.expect_cases_sha256:
        sys.exit("STOP. cases file hash %s is not the expected %s." % (got, a.expect_cases_sha256))
    cases = [json.loads(l) for l in open(cases_path, encoding="utf-8") if l.strip()]
    if a.limit:
        cases = cases[:a.limit]
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids):
        sys.exit("STOP. report ids are not unique.")
    sys.path.insert(0, str(paths.PILOT))
    import common as pc                                                                           # noqa: E402  (pilot, read-only)
    prompts = [pc.build_prompt(c, PROMPT_ID) for c in cases]
    prompts_sha = sha256_text("\n<<<END>>>\n".join(prompts))
    out = Path(a.out if not a.limit else str(a.out) + "_limit%d" % a.limit)
    out.mkdir(parents=True, exist_ok=True)
    ids_file = out / "case_ids.json"
    if ids_file.exists() and json.loads(ids_file.read_text()) != ids:
        sys.exit("STOP. %s lists different reports. Use a new output folder." % ids_file)
    ids_file.write_text(json.dumps(ids))
    say("Reports: %d   prompts sha256: %s\nOutput: %s" % (len(cases), prompts_sha[:16], out))

    # anchor data (development)
    anchor_cases = anchor_X = None
    ac = Path(a.anchor_cases) if a.anchor_cases else paths.PILOT / "data" / "cases.jsonl"
    af = Path(a.anchor_features) if a.anchor_features else paths.HEADS / "features"
    if a.anchor:
        anchor_cases = [json.loads(l) for l in open(ac, encoding="utf-8") if l.strip()]

    manifest = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "script_sha256": sha256_file(Path(__file__)), "cases_file": str(cases_path),
                "cases_sha256": got, "reports": len(cases), "report_ids_sha256": sha256_text(",".join(ids)), "prompt_id": PROMPT_ID,
                "prompts_sha256": prompts_sha, "server_flags": SERVER_FLAGS, "expected_build": LLAMA_BUILD, "models": {}, "checks": []}

    def record(model, status, text):
        manifest["checks"].append({"model": model, "status": status, "text": text})
        say("   [%s] %s" % (status, text))
        if status == "FAIL":
            problems.append((model, text))

    # ---- 2. models
    models = [a.one_model] if a.server_url else a.models
    for mk in models:
        say("\n=== %s ===" % mk)
        out_npy = out / ("%s_end.npy" % mk)
        meta_f = out / ("%s_end.meta.json" % mk)
        if out_npy.exists() and meta_f.exists():
            say("   already finished, skipped")
            manifest["models"][mk] = json.loads(meta_f.read_text())
            continue
        srv = None
        try:
            if a.server_url:
                client = EmbedClient(a.server_url)
                log_path = Path(a.server_log)
                model_file = None
            else:
                exe = Path(a.llama_dir) / ("llama-server.exe" if os.name == "nt" else "llama-server")
                model_file = Path(a.models_dir) / GGUF_FILE[mk]
                if not model_file.exists():
                    sys.exit("STOP. model file not found: %s" % model_file)
                if not a.skip_hash_check:
                    h = sha256_file(model_file)
                    record(mk, "PASS" if h == GGUF_SHA256[mk] else "FAIL", "model file sha256 %s %s the audited value" % (h[:16], "equals" if h == GGUF_SHA256[mk] else "DIFFERS FROM"))
                    if h != GGUF_SHA256[mk]:
                        break
                log_path = out.parent / "logs" / ("server_fresh_%s.log" % mk)
                srv = LlamaServer(exe, model_file, log_path)
                say("   starting: %s" % " ".join(srv.cmd))
                load_s = srv.start()
                say("   server ready in %.1f s" % load_s)
                client = EmbedClient(srv.base)
            props = client.props()
            build = props.get("build_info")
            if build is not None:
                ok = LLAMA_BUILD in str(build)
                record(mk, "PASS" if ok else ("CHECK" if a.allow_build_mismatch else "FAIL"), "llama.cpp build %s (expected %s)" % (build, LLAMA_BUILD))
            else:
                record(mk, "CHECK", "server did not report its build")
            if problems:
                break
            st, tx = check_command_line(log_path) if not a.server_url else ("CHECK", "attach mode: command line not checked")
            record(mk, st, tx)
            st, tx = check_bos(client, prompts)
            record(mk, st, tx)
            v1, _ = client.embed(prompts[0])
            v2, _ = client.embed(prompts[0])
            d = float(np.max(np.abs(v1 - v2)))
            record(mk, "PASS" if d == 0.0 else ("CHECK" if d < 1e-4 else "FAIL"), "same prompt twice: max |difference| %.2e" % d)
            if a.anchor:
                Xd = np.load(af / ("%s_end.npy" % mk)).astype(np.float64)
                st, tx = anchor_check(client, anchor_cases, Xd, pc.build_prompt, n=a.anchor)
                record(mk, st, tx)
            if problems:
                break
            # the two warm-up embeddings above and the anchor requests are in the log too: remember how many tokens they had, in order
            # (they are before the fresh reports in the log; the order check looks at the LAST len(tokens) entries only)
            X, toks, secs, start = extract_one_model(client, prompts, ids, out_npy, say, ubatch=1024)
            nt_ok = all(t >= 0 for t in toks) and len(toks) == len(ids)
            if nt_ok:
                st, tx = check_log_order(log_path, toks[start:])          # this session's requests only (a restarted server has a new log)
            else:
                st, tx = "CHECK", "token counts were not recorded for every request (resumed run or old server); order not checked"
            record(mk, st, tx)
            meta = {"model_key": mk, "n": len(ids), "dim": int(X.shape[1]), "prompt_tokens_max": max(toks) if toks and max(toks) >= 0 else None,
                    "prompt_id": PROMPT_ID, "prompts_sha256": prompts_sha, "cases_sha256": got, "report_ids_sha256": manifest["report_ids_sha256"],
                    "seconds_this_session": round(secs, 1), "ms_per_report": round(1000 * secs / max(1, len(ids) - start), 1),
                    "model_file": None if model_file is None else str(model_file), "model_sha256": GGUF_SHA256[mk], "model_bytes": GGUF_BYTES[mk],
                    "server_command": None if a.server_url else " ".join(srv.cmd), "llama_build": build, "server_flags": SERVER_FLAGS,
                    "vectors_sha256": sha256_file(out_npy), "finished": time.strftime("%Y-%m-%d %H:%M:%S"), "client_mode": client.mode}
            meta_f.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            manifest["models"][mk] = meta
            if srv is not None:
                srv.stop()
                srv = None
                if a.cpu_check:
                    cpu_check(a, mk, X, prompts, ids, out, record, say)
        except Exception as e:
            record(mk, "FAIL", "stopped: %s" % e)
            say("\nSTOPPED on %s. Progress is saved; run the same command again to continue.\nLast lines of the server log:\n%s" % (mk, tail(log_path if 'log_path' in dir() else None)))
            break
        finally:
            if srv is not None:
                srv.stop()
    manifest["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    manifest["result"] = "FAIL" if problems else "OK"
    (out / "extraction_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    say("\nRESULT: %s   (%d FAIL)" % (manifest["result"], len(problems)))
    say("Send back: %s\\*.meta.json, extraction_manifest.json, and the logs folder next to it. The .npy files stay on the disk you give to the analysis." % out)
    return 0 if not problems else 1


def cpu_check(a, mk, X_gpu, prompts, ids, out, record, say):
    """Restart the same server with -ngl 0 and re-embed a fixed sample of the fresh reports."""
    rng = np.random.RandomState(11)
    pick = sorted(rng.choice(len(ids), size=min(a.cpu_check, len(ids)), replace=False))
    exe = Path(a.llama_dir) / ("llama-server.exe" if os.name == "nt" else "llama-server")
    srv = LlamaServer(exe, Path(a.models_dir) / GGUF_FILE[mk], out.parent / "logs" / ("server_fresh_%s_cpu.log" % mk), ngl=0, port=SERVER_FLAGS["port"])
    say("   CPU check: %d reports with -ngl 0 (slow)" % len(pick))
    try:
        srv.start()
        client = EmbedClient(srv.base)
        V = np.stack([client.embed(prompts[i])[0] for i in pick])
    finally:
        srv.stop()
    mc, md = compare_vectors(V, X_gpu[pick])
    record(mk, "PASS" if mc >= MIN_COS_CPU else "FAIL", "CPU vs GPU on %d fresh reports: min cosine %.6f, max |diff| %.2e (need cosine >= %.3f)" % (len(pick), mc, md, MIN_COS_CPU))


def tail(p, n=15):
    try:
        return "\n".join(Path(p).read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except Exception:
        return "(no log)"


if __name__ == "__main__":
    sys.exit(main())
