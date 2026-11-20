"""
Step 2 of the heads test: get the hidden-state vectors (the "fingerprints") for all 1,400 reports, for each model.

    python 02_extract.py                    all three models, both prompt variants (about 30 to 60 minutes, my estimate)
    python 02_extract.py --models f16       one model only
    python 02_extract.py --limit 50         first 50 reports only, into a separate folder (for a quick look)

It starts one llama-server per model file (never two at once), asks it for the vector of every prompt,
saves to features\\<model>_<variant>.npy, and stops the server. You can press Ctrl+C and run it again: it continues.
Run 01_smoke_embed.py first.
"""
import argparse
import json
import sys

import heads_common as hc
from heads_common import CFG, EmbedClient, check_pilot_frozen, feat_path, load_cases
from heads_extract import extract_features


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=CFG["models"])
    ap.add_argument("--variants", nargs="*", default=CFG["variants"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ngl", type=int, default=None)
    args = ap.parse_args()

    check_pilot_frozen()
    cases = load_cases()
    feat_dir = hc.FEAT_DIR if args.limit is None else hc.HERE / ("features_limit%d" % args.limit)
    print("Features go to: %s" % feat_dir)

    for mk in args.models:
        todo = [v for v in args.variants if not feat_path(mk, v, feat_dir).exists()]
        if not todo:
            print("%s: all finished, skipped." % mk)
            continue
        print("\n=== %s (%s) ===" % (mk, ", ".join(todo)))
        srv, cfg, rm = hc.make_server(mk, "extract_" + mk)
        if not srv.model.exists():
            print("Model file not found: %s\nCheck paths in the pilot config.json." % srv.model)
            sys.exit(1)
        if args.ngl is not None:
            srv.ngl = args.ngl
        try:
            srv.start()
            print("   server ready in %.1f s" % srv.load_s)
            pre = srv.preflight(cases[0])
            print("   special tokens ok: %s, start token added once: %s" % (pre["special_tokens_ok"], pre["bos_added_once"]))
            if pre["bos_added_once"] is False:
                print("STOP: the start token is not added exactly once. Tell Claude before you continue.")
                sys.exit(1)
            client = EmbedClient(srv.base, timeout=cfg["server"].get("request_timeout_s", 120))
            gpu = rm.gpu_info()
            for v in todo:
                extract_features(client, cases, v, mk, feat_dir, limit=args.limit,
                                 extra_meta={"model_file": str(srv.model), "gpu": gpu, "props_build": srv.props().get("build_info")},
                                 max_prompt_tokens=hc.ubatch_limit())
            print("   done: %s" % mk)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            hc.fail_with_log(srv, e)
        finally:
            srv.stop()
    print("\nAll done. Next:  python 03_heads.py")


if __name__ == "__main__":
    main()
