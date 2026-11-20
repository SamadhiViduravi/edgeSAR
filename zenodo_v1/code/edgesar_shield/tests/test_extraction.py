"""
Checks of the GPU extraction script and the fresh generator WITHOUT a GPU: a fake llama-server (standard library HTTP server) answers
/health, /props, /tokenize and /v1/embeddings with vectors that depend only on the prompt text, and writes a log in llama-server's format.

Run:  python -m pytest -q tests/test_extraction.py
"""
import hashlib
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import numpy as np                                                # noqa: E402
import pytest                                                     # noqa: E402

import extract_fresh_vectors as ex                                # noqa: E402
import gen_episodes_fresh as gen                                  # noqa: E402
from shield import paths                                          # noqa: E402

DIM = 32


def fake_vec(text, salt=0.0):
    h = hashlib.sha256(text.encode("utf-8")).digest()
    rng = np.random.RandomState(int.from_bytes(h[:4], "little"))
    v = rng.randn(DIM).astype(np.float32)
    return v / np.linalg.norm(v) + np.float32(salt)


def fake_ntok(text):
    return 600 + len(text) % 60


class Fake:
    """state shared with the handler"""
    salt = 0.0
    log = None
    bos_twice = False
    fail_at = None
    count = 0
    swap_log = False


def make_handler(state):
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
                return self._send({"status": "ok"})
            if self.path == "/props":
                return self._send({"build_info": "b11901-5320c87ff"})
            self._send({}, 404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode())
            if self.path == "/tokenize":
                t = [128000] + list(range(1, 6))
                if state.bos_twice:
                    t = [128000, 128000] + list(range(1, 6))
                return self._send({"tokens": t})
            if self.path == "/v1/embeddings":
                text = body["input"]
                state.count += 1
                if state.fail_at is not None and state.fail_at <= state.count < state.fail_at + 2:
                    return self._send({"error": "boom"}, 500)
                nt = fake_ntok(text)
                with open(state.log, "a") as f:
                    f.write("slot release: id  0 | task %d | stop processing: n_tokens = %d, truncated = 0\n" % (2 * state.count, nt + (1 if state.swap_log and state.count == 12 else 0)))
                return self._send({"data": [{"embedding": fake_vec(text, state.salt).tolist()}], "usage": {"prompt_tokens": nt}})
            self._send({}, 404)
    return H


@pytest.fixture()
def server(tmp_path):
    st = Fake()
    st.log = tmp_path / "server.log"
    st.log.write_text("COMMAND: llama-server -m x.gguf --host 127.0.0.1 --port 8091 -ngl 99 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024\n\n")
    httpd = HTTPServer(("127.0.0.1", 0), make_handler(st))
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    st.url = "http://127.0.0.1:%d" % httpd.server_address[1]
    yield st
    httpd.shutdown()


def tiny_inputs(tmp_path, n=12):
    cases = [{"id": "f%06d" % (i + 1), "style": "A", "open": [{"id": "I1", "landmark": "Clinic Gate", "sensor": "RGB", "priority": 2}], "source": "UAV1",
              "time": "10:%02d" % i, "text": "Report number %d at Clinic Gate." % i, "gold": {"action": "NO_ACTION"}, "type": "NO_ACTION", "subtype": "chatter",
              "split": "fresh_eval", "episode": "FE0001", "pos": i, "family": "FE0001"} for i in range(n)]
    f = tmp_path / "cases_fresh.jsonl"
    f.write_text("\n".join(json.dumps(c) for c in cases) + "\n")
    return f, cases


def run_main(server, tmp_path, f, extra=()):
    sys.path.insert(0, str(paths.PILOT))
    import common as pc
    # the 'development' anchor: three pilot-style cases and their vectors from the same fake model
    dev = tmp_path / "dev"
    dev.mkdir(exist_ok=True)
    dcases = [json.loads(l) for l in open(paths.PILOT / "data" / "cases.jsonl") if l.strip()][:30]
    (dev / "cases.jsonl").write_text("\n".join(json.dumps(c) for c in dcases) + "\n")
    np.save(dev / "f16_end.npy", np.stack([fake_vec(pc.build_prompt(c, "P1")) for c in dcases]).astype(np.float32))
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    args = ["--cases", str(f), "--expect-cases-sha256", sha, "--out", str(tmp_path / "vectors"), "--server-url", server.url,
            "--server-log", str(server.log), "--one-model", "f16", "--anchor", "5", "--anchor-cases", str(dev / "cases.jsonl"),
            "--anchor-features", str(dev), "--cpu-check", "0"] + list(extra)
    return ex.main(args)


def test_happy_path_writes_vectors_manifest_and_passes_all_checks(server, tmp_path):
    f, cases = tiny_inputs(tmp_path)
    assert run_main(server, tmp_path, f) == 0
    out = tmp_path / "vectors"
    X = np.load(out / "f16_end.npy")
    assert X.shape == (12, DIM) and np.all(np.isfinite(X))
    man = json.loads((out / "extraction_manifest.json").read_text())
    assert man["result"] == "OK" and man["reports"] == 12 and man["prompt_id"] == "P1"
    texts = " | ".join(c["text"] for c in man["checks"])
    assert "log: 12 requests" in texts or "server log: 12 requests" in texts
    assert "re-embedded 5 development reports" in texts
    meta = json.loads((out / "f16_end.meta.json").read_text())
    assert meta["model_sha256"] == ex.GGUF_SHA256["f16"] and meta["cases_sha256"] == man["cases_sha256"] and len(meta["vectors_sha256"]) == 64
    assert json.loads((out / "case_ids.json").read_text()) == [c["id"] for c in cases]


def test_vectors_are_in_report_order(server, tmp_path):
    f, cases = tiny_inputs(tmp_path)
    run_main(server, tmp_path, f)
    sys.path.insert(0, str(paths.PILOT))
    import common as pc
    X = np.load(tmp_path / "vectors" / "f16_end.npy")
    for i in (0, 5, 11):
        assert np.allclose(X[i], fake_vec(pc.build_prompt(cases[i], "P1")), atol=1e-6)


def test_wrong_cases_hash_stops_before_any_embedding(server, tmp_path):
    f, _ = tiny_inputs(tmp_path)
    with pytest.raises(SystemExit):
        ex.main(["--cases", str(f), "--expect-cases-sha256", "0" * 64, "--out", str(tmp_path / "v"), "--server-url", server.url,
                 "--server-log", str(server.log), "--one-model", "f16", "--anchor", "0", "--cpu-check", "0"])
    assert server.count == 0


def test_anchor_check_fails_when_the_new_vectors_do_not_match_the_saved_development_vectors(server, tmp_path):
    f, _ = tiny_inputs(tmp_path)
    server.salt = 0.5                       # a different model / settings: every vector is shifted
    assert run_main(server, tmp_path, f) == 1
    man = json.loads((tmp_path / "vectors" / "extraction_manifest.json").read_text())
    assert man["result"] == "FAIL" and any("development vectors" in c["text"] and c["status"] == "FAIL" for c in man["checks"])
    assert not (tmp_path / "vectors" / "f16_end.npy").exists()


def test_start_token_added_twice_is_a_fail(server, tmp_path):
    f, _ = tiny_inputs(tmp_path)
    server.bos_twice = True
    assert run_main(server, tmp_path, f) == 1


def test_log_order_mismatch_is_detected(server, tmp_path):
    f, _ = tiny_inputs(tmp_path, n=12)
    server.swap_log = True                  # the server log disagrees with what the client was told for one request
    assert run_main(server, tmp_path, f) == 1
    man = json.loads((tmp_path / "vectors" / "extraction_manifest.json").read_text())
    assert any(c["status"] == "FAIL" and "disagree" in c["text"] for c in man["checks"])


def test_resume_after_a_failure_continues_and_gives_the_same_vectors(server, tmp_path):
    f, cases = tiny_inputs(tmp_path, n=12)
    server.fail_at = 15                     # fails twice in a row (the retry fails as well) at fresh report 8 of 12
    # the two warm-up embeddings + 5 anchor requests come first (7 requests), so request 15 is fresh report 8 of 12
    old = ex.extract_one_model

    def small_save(*a, **k):
        k["save_every"] = 3
        return old(*a, **k)
    ex.extract_one_model = small_save
    try:
        assert run_main(server, tmp_path, f) == 1
        part = list((tmp_path / "vectors").glob("*.partial.npy"))
        assert part, "partial file must be kept"
        server.fail_at = None
        server.count = 0
        server.log.write_text(server.log.read_text().splitlines()[0] + "\n\n")      # fresh log, as after a restart
        assert run_main(server, tmp_path, f) == 0
    finally:
        ex.extract_one_model = old
    X = np.load(tmp_path / "vectors" / "f16_end.npy")
    sys.path.insert(0, str(paths.PILOT))
    import common as pc
    for i in range(12):
        assert np.allclose(X[i], fake_vec(pc.build_prompt(cases[i], "P1")), atol=1e-6)


def test_command_line_check():
    p = Path(__file__).parent / "_cmd.log"
    p.write_text("COMMAND: llama-server -m a.gguf --host 127.0.0.1 --port 8091 -ngl 99 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024\n")
    assert ex.check_command_line(p)[0] == "PASS"
    p.write_text("COMMAND: llama-server -m a.gguf --port 8091 -ngl 99 -c 4096 -np 1 -t 6 --embeddings --pooling mean -b 1024 -ub 1024\n")
    assert ex.check_command_line(p)[0] == "FAIL"
    p.write_text("COMMAND: llama-server -m a.gguf --port 8091 -ngl 0 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024\n")
    assert ex.check_command_line(p)[0] == "PASS"                    # the CPU check differs in -ngl only
    p.unlink()


def test_compare_vectors():
    a = np.eye(3)
    assert ex.compare_vectors(a, a) == (1.0, 0.0)
    assert ex.compare_vectors(a, a[::-1])[0] == 0.0


# ---------------------------------------------------------------- the fresh generator
def test_generator_is_deterministic_unique_and_does_not_reuse_development_reports():
    dev = [json.loads(l) for l in open(paths.PILOT / "data" / "cases.jsonl") if l.strip()]
    c1, s1 = gen.generate(5, 2, 3, 20, dev)
    c2, s2 = gen.generate(5, 2, 3, 20, dev)
    assert c1 == c2 and s1 == s2
    keys = [gen.case_key(c) for c in c1]
    assert len(set(keys)) == len(keys) == 100
    assert not (set(keys) & {gen.case_key(c) for c in dev})
    assert [c["split"] for c in c1].count("fresh_cal") == 40 and [c["split"] for c in c1].count("fresh_eval") == 60
    mix = {}
    for c in c1:
        mix[c["type"]] = mix.get(c["type"], 0) + 1
    assert mix == {"CREATE": 25, "UPDATE": 20, "CLOSE": 15, "NO_ACTION": 40}
    assert {c["episode"] for c in c1 if c["split"] == "fresh_cal"} == {"FC001", "FC002"}
    c3, _ = gen.generate(6, 2, 3, 20, dev)
    assert [c["text"] for c in c3] != [c["text"] for c in c1]


def test_generated_gold_is_valid_for_the_open_table():
    """Every gold record names an incident that is in the report's open table (when it names one) and uses only known landmarks."""
    sys.path.insert(0, str(paths.PILOT))
    import common as pc
    dev = [json.loads(l) for l in open(paths.PILOT / "data" / "cases.jsonl") if l.strip()]
    cases, _ = gen.generate(9, 1, 2, 20, dev)
    for c in cases:
        g = c["gold"]
        ids = {i["id"] for i in c["open"]}
        if g["action"] in ("UPDATE_INCIDENT", "CLOSE_INCIDENT"):
            assert g["incident"] in ids
        if "landmark" in g:
            assert g["landmark"] in pc.LANDMARKS
        assert pc.build_prompt(c, "P1")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
