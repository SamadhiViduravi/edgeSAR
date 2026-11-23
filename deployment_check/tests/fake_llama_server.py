"""A FAKE llama-server for testing deploy_bench.py without any model (standard library + numpy). NOT a deployment tool.

It accepts the flags deploy_bench.py passes, prints log lines in llama.cpp's style, holds FAKE_HOLD_MB of real memory (so the memory measurement can be
checked against a known number), answers /health, /props and /v1/embeddings (a vector that depends only on the prompt text, unit length, 2048 numbers).
Environment: FAKE_HOLD_MB (default 300), FAKE_EMBED_MS (default 20), FAKE_LOAD_S (default 0.5), FAKE_EXIT=1 (exit at once), FAKE_GPU_LINES=1 (log a CUDA backend).
"""
import hashlib
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np


def fake_vec(prompt):
    seed = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16)
    v = np.random.RandomState(seed).randn(2048).astype(np.float64)
    return (v / np.linalg.norm(v)).astype(np.float32)


def arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            self._send({"status": "ok"})
        elif self.path == "/props":
            self._send({"build_info": "fake-b0-test", "default_generation_settings": {"n_ctx": int(arg("-c", 4096))}, "total_slots": 1})
        else:
            self._send({}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n).decode())
        if self.path == "/v1/embeddings":
            time.sleep(float(os.environ.get("FAKE_EMBED_MS", "20")) / 1000.0)
            text = body["input"]
            self._send({"data": [{"embedding": fake_vec(text).tolist()}], "usage": {"prompt_tokens": max(1, len(text) // 4)}})
        else:
            self._send({}, 404)


def main():
    if "--version" in sys.argv:
        print("version: 0 (fake-test)")
        return
    mode = os.environ.get("FAKE_HELP", "nommap")
    if "--help" in sys.argv or "-h" in sys.argv:
        if mode == "loadmode":
            print("----- common params -----\n\n-ngl, --gpu-layers N   max layers on GPU\n--load-mode {auto,mmap,mmap+mlock,dio,none,mlock}\n                        how weights are loaded (default: auto);\n                        none = no mmap, no mlock\n-t, --threads N")
        elif mode == "nommap":
            print("----- common params -----\n\n--no-mmap   do not memory-map the model\n-t, --threads N")
        else:
            print("----- common params -----\n\n-t, --threads N")
        return
    if mode == "loadmode" and "--no-mmap" in sys.argv:
        print("error: invalid argument: --no-mmap", flush=True)
        sys.exit(1)
    if mode == "loadmode" and "--load-mode" in sys.argv and sys.argv[sys.argv.index("--load-mode") + 1] != "none":
        print("error: bad load mode", flush=True)
        sys.exit(1)
    if os.environ.get("FAKE_EXIT") == "1":
        print("fake server: exiting at once", flush=True)
        sys.exit(7)
    print("COMMAND-LINE-SEEN:", " ".join(sys.argv[1:]), flush=True)
    print("load_backend: loaded CPU backend from /fake/libggml-cpu-test.so", flush=True)
    if os.environ.get("FAKE_GPU_LINES") == "1":
        print("load_backend: loaded CUDA backend from /fake/ggml-cuda.dll", flush=True)
    print("load_tensors: offloaded 0/17 layers to GPU", flush=True)
    hold = int(float(os.environ.get("FAKE_HOLD_MB", "300")) * 2 ** 20)
    buf = bytearray(hold)
    for i in range(0, hold, 4096):                       # touch every page so it is really resident
        buf[i] = 1
    time.sleep(float(os.environ.get("FAKE_LOAD_S", "0.5")))
    port = int(arg("--port", 8093))
    print("srv  load_model: model loaded, listening on 127.0.0.1:%d" % port, flush=True)
    HTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    main()
