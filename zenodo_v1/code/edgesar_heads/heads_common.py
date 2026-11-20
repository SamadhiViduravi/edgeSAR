"""
EdgeSAR heads test - shared helpers.

What this folder does (in one line): read the model's hidden state after the prompt, train three tiny
classifiers ("heads": action, sensor, priority) on it, and ask how much their answers change when the
model is shrunk (FP16 -> Q8_0 -> Q4_K_M).

The PILOT code in ../edgesar_pilot is imported READ-ONLY. Nothing in the pilot folder is written or changed
(bytecode writing is switched off, and logs go to this folder). Before anything runs, the pilot files are
checked against the fingerprints you froze on 28 Oct 2026.
"""
import copy
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True          # do not write __pycache__ into the frozen pilot folder

import numpy as np

HERE = Path(__file__).resolve().parent


def load_heads_config(path=None):
    p = Path(path) if path else HERE / "heads_config.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


CFG = load_heads_config()
CFG_SHA = hashlib.sha256((HERE / "heads_config.json").read_bytes()).hexdigest()
PILOT = Path(os.environ.get("EDGESAR_PILOT_DIR") or (HERE / CFG["pilot_dir"])).resolve()
if not (PILOT / "common.py").exists():
    sys.exit("Cannot find the pilot folder: %s\nPut edgesar_heads next to edgesar_pilot, or change pilot_dir in heads_config.json." % PILOT)
if str(PILOT) not in sys.path:
    sys.path.insert(0, str(PILOT))

import common as pc          # noqa: E402  (pilot: schema, prompt, validator, statistics) - read only
import baselines as pb       # noqa: E402  (pilot: Rule engine, TF-IDF/LR, decision assembly) - read only

FEAT_DIR = HERE / "features"
OUT_DIR = HERE / "results_heads"
LOG_DIR = HERE / "logs"

# model key in config.json -> name used in the pilot report, and the pilot run file with its generative answers
ARM_NAME = {"f16": "FP16", "Q8_0": "Q8", "Q4_K_M": "Q4"}
GEN_RUN = {"f16": "f16_P1", "Q8_0": "q8_P1", "Q4_K_M": "q4_P1"}

# fingerprints frozen on 28 Oct 2026 (results/freeze_hashes_2026-10-28.txt)
FROZEN = {
    "data/cases.jsonl": "3c51f0b4b1481242da6855c80bff8e976971fd461bd67767a68797cb7826c8b7",
    "common.py": "332ec94d84fa385b2fae2b2949cd8cbf7463a1de2527236f0b2a78ba47f3c91a",
    "baselines.py": "e410b94c788e848aeca21b3c0cb37a9c216f957c712f67238cb4b3896bf105a7",
    "analyze.py": "ecf606d0938b17befe8f2f6cd226c073fc4804839d086f054a0854eae7fbeeb7",
    "run_model.py": "8ae232dd1926bd8e69caa1ec70389612de66a512ed88489f38dd6176d563f340",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pilot_frozen(strict=True):
    """The pilot files must be exactly the ones you froze. Returns a list of problems (empty = fine)."""
    bad = []
    for rel, want in FROZEN.items():
        p = PILOT / rel
        if not p.exists():
            bad.append("missing: %s" % p)
        elif sha256_file(p) != want:
            bad.append("CHANGED since the freeze: %s" % p)
    if bad and strict:
        print("\nSTOP. The pilot folder is not the frozen one:\n  " + "\n  ".join(bad))
        print("The heads test must read exactly the frozen pilot files. Restore them (or fix pilot_dir in "
              "heads_config.json) and run again.")
        sys.exit(2)
    return bad


# ------------------------------------------------------------------ cases and labels
def load_cases():
    return pc.load_cases(PILOT / "data" / "cases.jsonl")


def case_split_indexes(cases):
    dev = [i for i, c in enumerate(cases) if c["split"] == "dev"]
    held = [i for i, c in enumerate(cases) if c["split"] == "held"]
    return dev, held


def prompt_for(case, variant):
    """'end'    = the exact pilot prompt (P1). The vector is the hidden state of its last token.
       'prefix' = the same prompt followed by {"action":"  - the place where the model picks the action."""
    base = pc.build_prompt(case, CFG["prompt_id"])
    if variant == "end":
        return base
    if variant == "prefix":
        return base + CFG["prefix_text"]
    raise ValueError("unknown variant %r" % variant)


# ------------------------------------------------------------------ tiny HTTP helper (standard library only)
def http_json(url, payload=None, timeout=120):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:                                   # keep the server's own message; it says what is wrong
            e.detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            e.detail = ""
        raise


def describe_error(e):
    detail = getattr(e, "detail", "")
    return str(e) + ((" - server says: " + detail) if detail else "")


def tail_log(path, n=15):
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return "(no log file)"


def fail_with_log(srv, exc):
    """Stop with a clear message and the last lines of the server log (so you can send them to me)."""
    print("\nSTOPPED: %s" % describe_error(exc))
    print("Last lines of %s:\n%s" % (srv.log_path, tail_log(srv.log_path)))
    sys.exit(1)


class EmbedClient:
    """Asks a running llama-server (started with --embeddings --pooling last) for one vector per prompt."""

    def __init__(self, base_url, timeout=120):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.mode = None            # "v1" (/v1/embeddings) or "native" (/embedding), found on the first call
        self.rows_seen = 1          # >1 means the server sent one vector per token (pooling not 'last')

    @staticmethod
    def _to_vector(emb):
        arr = np.asarray(emb, dtype=np.float32)
        rows = 1
        if arr.ndim == 2:
            rows = arr.shape[0]
            arr = arr[-1]            # one row per token (no pooling) or one pooled row: the last row is what we want
        if arr.ndim != 1 or arr.size == 0:
            raise ValueError("unexpected embedding shape %s" % (arr.shape,))
        return arr, rows

    def _v1(self, text):
        _, body = http_json(self.base + "/v1/embeddings", {"input": text, "encoding_format": "float"}, self.timeout)
        vec, rows = self._to_vector(body["data"][0]["embedding"])
        usage = body.get("usage") or {}
        return vec, rows, usage.get("prompt_tokens")

    def _native(self, text):
        _, body = http_json(self.base + "/embedding", {"content": text}, self.timeout)
        item = body[0] if isinstance(body, list) else body
        vec, rows = self._to_vector(item["embedding"])
        return vec, rows, None

    def embed(self, text):
        """Returns (vector float32, number of prompt tokens or None)."""
        if self.mode is None:
            try:
                vec, rows, ntok = self._v1(text)
                self.mode = "v1"
            except urllib.error.HTTPError as e:
                if e.code in (404, 405, 501):
                    vec, rows, ntok = self._native(text)
                    self.mode = "native"
                else:
                    raise
        else:
            vec, rows, ntok = self._v1(text) if self.mode == "v1" else self._native(text)
        self.rows_seen = max(self.rows_seen, rows)
        return vec, ntok


# ------------------------------------------------------------------ the server (pilot class, our arguments)
def make_server(model_key, tag):
    """Pilot Server class, started with the embedding arguments, its log written to THIS folder."""
    import run_model as rm         # pilot code, imported read-only
    cfg = copy.deepcopy(pc.load_config())
    cfg["server"]["port"] = int(CFG["port"])
    cfg["server"]["extra_args"] = list(CFG["server_args"])
    if os.environ.get("EDGESAR_LLAMA_BIN_DIR"):          # only used by the tests (a fake server)
        cfg["paths"]["llama_bin_dir"] = os.environ["EDGESAR_LLAMA_BIN_DIR"]
    if os.environ.get("EDGESAR_MODELS_DIR"):
        cfg["paths"]["models_dir"] = os.environ["EDGESAR_MODELS_DIR"]
    srv = rm.Server(cfg, rm.model_file(cfg, model_key), tag)
    LOG_DIR.mkdir(exist_ok=True)
    srv.log_path = LOG_DIR / ("server_%s.log" % tag)
    return srv, cfg, rm


# ------------------------------------------------------------------ feature files
def feat_path(model_key, variant, feat_dir=None):
    return Path(feat_dir or FEAT_DIR) / ("%s_%s.npy" % (model_key, variant))


def meta_path(model_key, variant, feat_dir=None):
    return Path(feat_dir or FEAT_DIR) / ("%s_%s.meta.json" % (model_key, variant))


def load_features(model_key, variant, feat_dir=None):
    p = feat_path(model_key, variant, feat_dir)
    if not p.exists():
        return None
    return np.load(p)


def now_text():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def ubatch_limit():
    """The -ub value in server_args (longest prompt the server can take in one piece)."""
    a = CFG["server_args"]
    return int(a[a.index("-ub") + 1]) if "-ub" in a else 512
