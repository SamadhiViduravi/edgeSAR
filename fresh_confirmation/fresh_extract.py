"""
GPU step of the fresh confirmation (PROTOCOL_FRESH_CONFIRM.md): hidden-state vectors of the FRESH reports, made with EXACTLY the code and
server settings that made the saved development vectors (edgesar_heads: heads_common.make_server, heads_extract.extract_features,
prompt P1, positions `end` and `prefix`, llama-server --embeddings --pooling last -b 1024 -ub 1024, -ngl 99, models from edgesar_pilot/config.json).

    python fresh_extract.py --check      about 2 minutes: for f16 and Q4_K_M, re-embeds 20 DEVELOPMENT reports and compares them with the
                                         SAVED development vectors (both positions). Every cosine must be at least 0.9999. Nothing else is done.
    python fresh_extract.py              the full run: the same check first (it stops if the check fails), then all fresh reports,
                                         f16 then Q4_K_M, `end` then `prefix`. Saves every 100 reports; run it again to continue after a stop.

Run it from this folder (it must sit next to edgesar_heads and edgesar_pilot). It writes only into this folder (vectors/ and logs/).
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MODELS = ["f16", "Q4_K_M"]
VARIANTS = ["end", "prefix"]
MIN_COS = 0.9999
ANCHOR_IDS = ["c%04d" % i for i in range(1, 1001, 50)]          # 20 development style-A reports: c0001, c0051, ..., c0951


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heads-dir", default=str(HERE.parent / "edgesar_heads"))
    ap.add_argument("--cases", default=str(HERE / "cases_fresh.jsonl"))
    ap.add_argument("--out", default=str(HERE / "vectors"))
    ap.add_argument("--check", action="store_true", help="only the anchor check on 20 development reports")
    a = ap.parse_args()
    heads = Path(a.heads_dir).resolve()
    if not (heads / "heads_common.py").exists():
        sys.exit("Cannot find edgesar_heads at %s. Put this folder next to edgesar_heads." % heads)
    sys.path.insert(0, str(heads))
    import numpy as np
    import heads_common as hc
    from heads_extract import extract_features

    hc.check_pilot_frozen()
    man = json.loads((HERE / "generation_manifest.json").read_text(encoding="utf-8"))
    if sha(a.cases) != man["cases_sha256"]:
        sys.exit("STOP: cases_fresh.jsonl is not the generated file (SHA-256 differs from generation_manifest.json).")
    fresh = [json.loads(l) for l in open(a.cases, encoding="utf-8") if l.strip()]
    dev = hc.load_cases()
    byid = {c["id"]: c for c in dev}
    dev_pos = {c["id"]: i for i, c in enumerate(dev)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    hc.LOG_DIR = HERE / "logs"                       # server logs go to THIS folder, not into edgesar_heads
    hc.LOG_DIR.mkdir(exist_ok=True)
    saved = {(m, v): hc.load_features(m, v) for m in MODELS for v in VARIANTS}
    for k, X in saved.items():
        if X is None:
            sys.exit("STOP: saved development vectors %s_%s.npy not found in %s" % (k[0], k[1], hc.FEAT_DIR))
    report = {"started": hc.now_text(), "cases_sha256": man["cases_sha256"], "fresh_reports": len(fresh), "anchor": {}, "models": {}}
    print("Fresh reports: %d. Models: %s. Positions: %s." % (len(fresh), MODELS, VARIANTS))
    for mk in MODELS:
        print("\n=== %s ===" % mk)
        srv, cfg, rm = hc.make_server(mk, "fresh_" + mk)
        if not srv.model.exists():
            sys.exit("Model file not found: %s" % srv.model)
        try:
            srv.start()
            print("   server ready in %.1f s" % srv.load_s)
            pre = srv.preflight(fresh[0])
            if pre["bos_added_once"] is False:
                sys.exit("STOP: the start token is not added exactly once.")
            client = hc.EmbedClient(srv.base, timeout=cfg["server"].get("request_timeout_s", 120))
            gpu = rm.gpu_info()
            print("   GPU: %s" % (gpu,))
            # ---- anchor check: today's vectors of 20 development reports must equal the saved ones
            worst = 1.0
            rows = {}
            for v in VARIANTS:
                cs = []
                for cid in ANCHOR_IDS:
                    vec, _ = client.embed(hc.prompt_for(byid[cid], v))
                    s = saved[(mk, v)][dev_pos[cid]].astype(np.float64)
                    vec = vec.astype(np.float64)
                    cs.append(float(vec @ s / (np.linalg.norm(vec) * np.linalg.norm(s))))
                rows[v] = {"min_cos": min(cs), "mean_cos": float(np.mean(cs))}
                worst = min(worst, min(cs))
                print("   anchor %s: 20 development reports, cosine to the saved vectors min %.7f, mean %.7f" % (v, min(cs), float(np.mean(cs))))
            ok = worst >= MIN_COS
            report["anchor"][mk] = {"positions": rows, "pass": ok, "gpu": gpu}
            (out / "extraction_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
            if not ok:
                print("\nSTOP: ANCHOR CHECK FAILED for %s (lowest cosine %.6f < %.4f). The vectors made now are not the same as the saved ones "
                      "(often: the GPU is not used, or another llama.cpp build). Send this whole window text to Claude." % (mk, worst, MIN_COS))
                sys.exit(3)
            print("   ANCHOR CHECK PASS")
            if a.check:
                continue
            for v in VARIANTS:
                t0 = time.time()
                extract_features(client, fresh, v, mk, out, extra_meta={"model_file": str(srv.model), "gpu": gpu, "fresh_cases_sha256": man["cases_sha256"],
                                                                     "props_build": srv.props().get("build_info")},
                                 max_prompt_tokens=hc.ubatch_limit())
                print("   %s %s finished in %.1f min" % (mk, v, (time.time() - t0) / 60))
            report["models"][mk] = {v: sha(out / ("%s_%s.npy" % (mk, v))) for v in VARIANTS}
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("\nStopped by you. Progress is saved. Run the same command again to continue.")
            raise
        except Exception as e:
            hc.fail_with_log(srv, e)
        finally:
            srv.stop()
    report["finished"] = hc.now_text()
    (out / "extraction_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    if a.check:
        print("\nCHECK FINISHED: both models PASS. Now run STEP2.")
    else:
        print("\nALL DONE. The vectors are in %s. Tell Claude: 'extraction finished'." % out)


if __name__ == "__main__":
    main()
