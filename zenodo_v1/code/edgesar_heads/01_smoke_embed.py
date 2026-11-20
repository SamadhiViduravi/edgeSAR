"""
Step 1 of the heads test: a 2-minute check that the model can give us usable hidden-state vectors.

    python 01_smoke_embed.py                       FP16 and Q4_K_M (so we can also see how far the vector moves)
    python 01_smoke_embed.py --models f16          one model only

What it checks, and why:
  - the server accepts --embeddings --pooling last and returns one vector per prompt;
  - the same prompt twice gives the same vector (if not, nothing later can be trusted);
  - the server counts the same number of tokens as the tokenizer (start token added once, special tokens parsed);
  - different reports give different vectors (the report is really being read);
  - the longest pilot prompt (667 tokens) fits in the server batch.
It writes results_heads\\smoke_report.txt. Send me that file.
"""
import argparse
import sys

import numpy as np

import heads_common as hc
from heads_common import CFG, EmbedClient, check_pilot_frozen, load_cases
from heads_extract import smoke_checks, _cos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=["f16", "Q4_K_M"])
    ap.add_argument("--ngl", type=int, default=None)
    args = ap.parse_args()

    check_pilot_frozen()
    cases = load_cases()
    hc.OUT_DIR.mkdir(exist_ok=True)
    report, all_vecs, failed = [], {}, False

    longest = max(cases, key=lambda c: len(hc.prompt_for(c, "prefix")))
    for mk in args.models:
        print("\n=== %s ===" % mk)
        srv, cfg, rm = hc.make_server(mk, "smoke_" + mk)
        if not srv.model.exists():
            print("Model file not found: %s" % srv.model)
            sys.exit(1)
        if args.ngl is not None:
            srv.ngl = args.ngl
        try:
            srv.start()
            pre = srv.preflight(cases[0])
            report.append("[%s] server ready in %.1f s. special tokens ok: %s, start token added once: %s" % (
                mk, srv.load_s, pre["special_tokens_ok"], pre["bos_added_once"]))
            client = EmbedClient(srv.base)
            tok = lambda text: srv.tokenize(text, add_special=True, parse_special=True)
            longest_tokens = len(tok(hc.prompt_for(longest, "prefix")))
            limit = hc.ubatch_limit()
            st = "PASS" if longest_tokens < limit else "FAIL"
            report.append("%s [%s] longest prompt = %d tokens, server batch (-ub) = %d" % (st, mk, longest_tokens, limit))
            lines, vecs = smoke_checks(client, tok, cases)
            for st, txt in lines:
                report.append("%s [%s] %s" % (st, mk, txt))
            all_vecs[mk] = vecs
            gpu = rm.gpu_info()
            if gpu:
                report.append("[%s] GPU memory used while the server is up: %.0f MB of %.0f MB" % (mk, gpu["vram_used_mb"], gpu["vram_total_mb"]))
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            hc.fail_with_log(srv, e)
        finally:
            srv.stop()

    if len(all_vecs) >= 2:
        a, b = list(all_vecs)[:2]
        for variant in CFG["variants"]:
            cs = [_cos(all_vecs[a][k], all_vecs[b][k]) for k in all_vecs[a] if k[1] == variant]
            report.append("[info] same prompt, %s vs %s, variant '%s': cosine %.4f to %.4f (1.0 = the shrunk model's vector did not move)"
                          % (a, b, variant, min(cs), max(cs)))

    failed = any(l.startswith("FAIL") for l in report)
    report.append("")
    report.append("RESULT: %s" % ("FAIL - do not run step 2 yet, send me this file" if failed else
                                  "no FAIL. If you see CHECK lines, send me this file before step 2."))
    text = "\n".join(report)
    print("\n" + text)
    (hc.OUT_DIR / "smoke_report.txt").write_text(text + "\n", encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
