"""
EdgeSAR heads test - get one hidden-state vector per report from a running llama-server.

`extract_features` is the loop. It is separate from the server start-up so it can be tested with a fake server.
It saves every 100 reports, and starts again where it stopped if you run it a second time.
"""
import json
import os
import time

import numpy as np

from heads_common import CFG, EmbedClient, PILOT, describe_error, feat_path, meta_path, now_text, prompt_for, sha256_file


def extract_features(client, cases, variant, model_key, feat_dir, extra_meta=None, limit=None,
                     save_every=100, say=print, max_prompt_tokens=None):
    """Returns the path of the finished .npy file. Skips work that is already finished."""
    feat_dir.mkdir(parents=True, exist_ok=True)
    out = feat_path(model_key, variant, feat_dir)
    partial = out.with_name(out.stem + ".partial.npy")
    n = len(cases) if limit is None else min(int(limit), len(cases))
    ids = [c["id"] for c in cases[:n]]

    ids_file = feat_dir / "case_ids.json"
    if ids_file.exists():
        if json.loads(ids_file.read_text(encoding="utf-8")) != ids:
            raise RuntimeError("%s lists different cases than the ones now loaded. Use a new features folder." % ids_file)
    else:
        ids_file.write_text(json.dumps(ids), encoding="utf-8")

    if out.exists():
        say("   %s %s: already finished, skipped." % (model_key, variant))
        return out

    X, done = None, 0
    if partial.exists():
        X = np.load(partial)
        if X.shape[0] != n:
            raise RuntimeError("%s does not match the number of cases. Delete it and start again." % partial)
        done = int(np.sum(~np.isnan(X[:, 0])))
        say("   %s %s: continuing from report %d of %d" % (model_key, variant, done, n))

    t0 = time.perf_counter()
    t_start_rows = done
    tok_max = 0
    try:
        for i in range(done, n):
            text = prompt_for(cases[i], variant)
            try:
                vec, ntok = client.embed(text)
            except Exception as e:           # one retry, then stop with a clear message
                time.sleep(2.0)
                try:
                    vec, ntok = client.embed(text)
                except Exception as e2:
                    raise RuntimeError("The server failed on report %s (%s). Progress is saved. Read the last lines "
                                       "of the server log in the logs folder, then run the same command again."
                                       % (cases[i]["id"], describe_error(e2)))
            if not np.all(np.isfinite(vec)):
                raise RuntimeError("The vector for %s has NaN or infinity. Stop and check the server log." % cases[i]["id"])
            if X is None:
                X = np.full((n, vec.shape[0]), np.nan, dtype=np.float32)
            elif vec.shape[0] != X.shape[1]:
                raise RuntimeError("Vector length changed from %d to %d." % (X.shape[1], vec.shape[0]))
            X[i] = vec
            if ntok:
                tok_max = max(tok_max, int(ntok))
                if max_prompt_tokens and ntok >= max_prompt_tokens:
                    raise RuntimeError("A prompt has %d tokens and the server batch is %d. Raise -b and -ub in "
                                       "heads_config.json (server_args)." % (ntok, max_prompt_tokens))
            if (i + 1) % save_every == 0 or i + 1 == n:
                np.save(partial, X)
                el = time.perf_counter() - t0
                rate = (i + 1 - t_start_rows) / max(el, 1e-9)
                eta = (n - i - 1) / max(rate, 1e-9)
                say("   %s %s: %d / %d   %.1f reports/s   about %.1f min left" % (model_key, variant, i + 1, n, rate, eta / 60.0))
    except BaseException:
        if X is not None:                    # Ctrl+C or an error: keep what we have
            np.save(partial, X)
        raise

    tmp = out.with_name(out.stem + ".tmp.npy")
    np.save(tmp, X)
    os.replace(tmp, out)
    if partial.exists():
        partial.unlink()
    seconds = time.perf_counter() - t0
    meta = {"model_key": model_key, "variant": variant, "n": n, "dim": int(X.shape[1]),
            "prompt_tokens_max": tok_max or None, "seconds_this_session": round(seconds, 1),
            "ms_per_report": round(1000.0 * seconds / max(1, n - t_start_rows), 1),
            "client_mode": client.mode, "rows_per_response_max": client.rows_seen,
            "server_args": CFG["server_args"], "prompt_id": CFG["prompt_id"],
            "prefix_text": CFG["prefix_text"] if variant == "prefix" else None,
            "cases_sha256": sha256_file(PILOT / "data" / "cases.jsonl"), "finished": now_text()}
    if extra_meta:
        meta.update(extra_meta)
    meta_path(model_key, variant, feat_dir).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out


# ------------------------------------------------------------------ smoke checks (used by 01_smoke_embed.py)
def _cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def smoke_checks(client, tokenize, cases, sample_ids=None):
    """
    Small checks that the vectors are real and repeatable. `tokenize(text)` returns the token list the server
    would use (start token added, special tokens parsed).
    Returns (lines, vectors) where lines = [(status, text)] with status PASS / CHECK / FAIL, and
    vectors = {(case_id, variant): vector} so two models can be compared.
    """
    lines, vecs = [], {}

    def add(st, txt):
        lines.append((st, txt))

    # one case of each true action (development) and one held-out case
    picks, seen = [], set()
    for c in cases:
        if c["split"] == "dev" and c["gold"]["action"] not in seen:
            seen.add(c["gold"]["action"])
            picks.append(c)
    picks.append(next(c for c in cases if c["split"] == "held"))
    if sample_ids:
        picks = [c for c in cases if c["id"] in sample_ids]

    times = []
    for variant in CFG["variants"]:
        vs, diffs, tok_bad, tok_checked = [], [], [], 0
        for c in picks:
            text = prompt_for(c, variant)
            t0 = time.perf_counter()
            v1, nt1 = client.embed(text)
            times.append(time.perf_counter() - t0)
            v2, _ = client.embed(text)
            vecs[(c["id"], variant)] = v1
            vs.append(v1)
            diffs.append(float(np.max(np.abs(v1 - v2))))
            if nt1 is not None:
                tok_checked += 1
                want = len(tokenize(text))
                if nt1 != want:
                    tok_bad.append("%s: server %d, tokenizer %d" % (c["id"], nt1, want))
        worst = max(diffs)
        if worst == 0.0:
            add("PASS", "%s: the same prompt sent twice gives the identical vector (%d of %d reports)" % (variant, len(diffs), len(diffs)))
        elif worst < 1e-4:
            add("CHECK", "%s: the same prompt twice differs by up to %.2e (tiny; GPU rounding). Probably fine." % (variant, worst))
        else:
            add("FAIL", "%s: the same prompt twice differs by up to %.2e. The vector is not repeatable." % (variant, worst))
        if tok_checked == 0:
            add("CHECK", "%s: the server did not report a token count, so the token check was skipped." % variant)
        elif tok_bad:
            add("FAIL", "%s: token count differs between server and tokenizer (%s)" % (variant, "; ".join(tok_bad)))
        else:
            add("PASS", "%s: the server counts the same tokens as the tokenizer (%d reports; start token added once)" % (variant, tok_checked))
        dim = vs[0].shape[0]
        add("PASS" if np.all([np.all(np.isfinite(v)) for v in vs]) else "FAIL", "%s: all vectors finite, length %d" % (variant, dim))
        norms = [float(np.linalg.norm(v)) for v in vs]
        add("PASS", "%s: vector length (L2 norm) %.3f to %.3f %s" % (
            variant, min(norms), max(norms), "(normalised by the server; that is fine)" if abs(norms[0] - 1) < 1e-3 else ""))
        cs = [_cos(vs[i], vs[j]) for i in range(len(vs)) for j in range(i + 1, len(vs))]
        if max(cs) > 0.999999:
            add("FAIL", "%s: two different reports give the SAME vector (cosine %.7f). The report is not being read." % (variant, max(cs)))
        elif max(cs) > 0.999:
            add("CHECK", "%s: some different reports give almost the same vector (cosine up to %.5f). The heads may still work, tell Claude." % (variant, max(cs)))
        else:
            add("PASS", "%s: different reports give different vectors (cosine %.4f to %.4f)" % (variant, min(cs), max(cs)))
    same = [_cos(vecs[(c["id"], "end")], vecs[(c["id"], "prefix")]) for c in picks] if len(CFG["variants"]) > 1 else []
    if same:
        add("FAIL" if max(same) > 0.999999 else "PASS", "'end' and 'prefix' vectors are different (cosine %.4f to %.4f)" % (min(same), max(same)))
    if client.rows_seen > 1:
        add("CHECK", "The server sent one vector per token (pooling is not 'last'). The kit takes the last row, which is the "
                     "same token. Fine, but check the server log shows 'pooling: last'.")
    add("PASS", "time per report: median %.0f ms (embedding mode: %s)" % (1000 * float(np.median(times)), client.mode))
    return lines, vecs
