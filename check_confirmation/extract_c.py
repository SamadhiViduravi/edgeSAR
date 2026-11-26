"""
GPU step of the check confirmation (PROTOCOL_CHECK_CONFIRM.md): prefix hidden-state vectors of the NEW reports (set C, 5,000 reports) for
FP16, Q4_K_M and Q3_K_M, and of the 1,400 DEVELOPMENT reports for Q3_K_M (the only precision without saved development vectors).
Same code and server settings as the saved vectors (edgesar_heads: heads_common.make_server, heads_extract.extract_features, prompt P1,
position `prefix`, llama-server --embeddings --pooling last, -ngl 99, models from edgesar_pilot/config.json).

    python extract_c.py

1. Anchor check: for FP16 and Q4_K_M, 20 development reports are embedded again and compared with the SAVED development vectors; every
   cosine must be at least 0.9999, otherwise it stops.
2. If the Q3_K_M file does not exist, it is made from the FP16 file with llama-quantize (same tool and recipe as Q4_K_M, no importance matrix).
3. Vectors: FP16 and Q4_K_M of set C; Q3_K_M of the development reports and of set C. Saves every 100 reports; run it again to continue.

Run it from this folder (it must sit next to edgesar_heads and edgesar_pilot). It writes only into this folder (vectors_C/ and logs/).
"""
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MIN_COS = 0.9999
ANCHOR_IDS = ["c%04d" % i for i in range(1, 1001, 50)]          # 20 development style-A reports: c0001, c0051, ..., c0951
V = "prefix"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def main():
    heads = (HERE.parent / "edgesar_heads").resolve()
    if not (heads / "heads_common.py").exists():
        sys.exit("Cannot find edgesar_heads at %s. Put this folder next to edgesar_heads." % heads)
    sys.path.insert(0, str(heads))
    import numpy as np
    import heads_common as hc
    from heads_extract import extract_features

    hc.check_pilot_frozen()
    man = json.loads((HERE / "generation_manifest_C.json").read_text(encoding="utf-8"))
    cases_file = HERE / "cases_C.jsonl"
    if sha(cases_file) != man["cases_sha256"]:
        sys.exit("STOP: cases_C.jsonl is not the generated file (SHA-256 differs from generation_manifest_C.json).")
    new = [json.loads(l) for l in open(cases_file, encoding="utf-8") if l.strip()]
    dev = hc.load_cases()
    byid = {c["id"]: c for c in dev}
    dev_pos = {c["id"]: i for i, c in enumerate(dev)}
    out = HERE / "vectors_C"
    out_dev = out / "dev"
    out.mkdir(parents=True, exist_ok=True)
    hc.LOG_DIR = HERE / "logs"
    hc.LOG_DIR.mkdir(exist_ok=True)
    report_path = out / "extraction_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    report.update({"started_or_continued": hc.now_text(), "cases_sha256": man["cases_sha256"], "new_reports": len(new)})
    report.setdefault("anchor", {})
    report.setdefault("models", {})

    # make Q3_K_M with llama-quantize if it is missing (same recipe as make_quants.py)
    pc = hc.pc
    cfg = pc.load_config()
    models_dir = Path(cfg["paths"]["models_dir"])
    q3 = models_dir / cfg["models"]["Q3_K_M"]
    if not q3.exists():
        bin_dir = Path(cfg["paths"]["llama_bin_dir"])
        exe = next((bin_dir / n for n in ("llama-quantize.exe", "llama-quantize") if (bin_dir / n).exists()), None)
        if exe is None:
            sys.exit("STOP: %s is missing and llama-quantize was not found in %s." % (q3, bin_dir))
        print("Making %s with llama-quantize (about 1 minute) ..." % q3.name)
        with open(hc.LOG_DIR / "quantize_Q3_K_M.log", "w", encoding="utf-8", errors="replace") as lg:
            r = subprocess.run([str(exe), str(models_dir / cfg["models"]["f16"]), str(q3), "Q3_K_M"], stdout=lg, stderr=subprocess.STDOUT,
                               cwd=str(exe.parent))
        if r.returncode != 0 or not q3.exists():
            sys.exit("STOP: llama-quantize failed. Read logs/quantize_Q3_K_M.log and send it to Claude.")
        report["q3_made_now"] = True
    report["model_files"] = {k: {"file": cfg["models"][k], "bytes": (models_dir / cfg["models"][k]).stat().st_size}
                             for k in ("f16", "Q4_K_M", "Q3_K_M")}
    report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")

    plan = [("f16", [("C", new, out)]), ("Q4_K_M", [("C", new, out)]), ("Q3_K_M", [("dev", dev, out_dev), ("C", new, out)])]
    for mk, jobs in plan:
        print("\n=== %s ===" % mk)
        srv, scfg, rm = hc.make_server(mk, "checkC_" + mk)
        if not srv.model.exists():
            sys.exit("Model file not found: %s" % srv.model)
        try:
            srv.start()
            print("   server ready in %.1f s" % srv.load_s)
            pre = srv.preflight(new[0])
            if pre["bos_added_once"] is False:
                sys.exit("STOP: the start token is not added exactly once.")
            client = hc.EmbedClient(srv.base, timeout=scfg["server"].get("request_timeout_s", 120))
            gpu = rm.gpu_info()
            print("   GPU: %s" % (gpu,))
            saved = hc.load_features(mk, V)
            if saved is not None:                       # FP16 and Q4_K_M: today's vectors must equal the saved development vectors
                cs = []
                for cid in ANCHOR_IDS:
                    vec, _ = client.embed(hc.prompt_for(byid[cid], V))
                    s = saved[dev_pos[cid]].astype(np.float64)
                    vec = vec.astype(np.float64)
                    cs.append(float(vec @ s / (np.linalg.norm(vec) * np.linalg.norm(s))))
                ok = min(cs) >= MIN_COS
                report["anchor"][mk] = {"min_cos": min(cs), "mean_cos": float(np.mean(cs)), "pass": ok, "gpu": gpu}
                report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
                print("   anchor: 20 development reports, cosine to the saved vectors min %.7f" % min(cs))
                if not ok:
                    print("\nSTOP: ANCHOR CHECK FAILED for %s (lowest cosine %.6f < %.4f). Send this whole window text to Claude." % (mk, min(cs), MIN_COS))
                    sys.exit(3)
                print("   ANCHOR CHECK PASS")
            for name, cs_, od in jobs:
                t0 = time.time()
                extract_features(client, cs_, V, mk, od, extra_meta={"model_file": str(srv.model), "gpu": gpu, "set": name,
                                                                     "cases_sha256": man["cases_sha256"], "props_build": srv.props().get("build_info")},
                                 max_prompt_tokens=hc.ubatch_limit())
                print("   %s %s reports finished in %.1f min" % (mk, name, (time.time() - t0) / 60))
            report["models"][mk] = {name: sha(od / ("%s_%s.npy" % (mk, V))) for name, _, od in jobs}
            report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("\nStopped by you. Progress is saved. Run the same command again to continue.")
            raise
        except Exception as e:
            hc.fail_with_log(srv, e)
        finally:
            srv.stop()
    # the analysis reads the development Q3 vectors from vectors_C/dev_Q3_K_M_prefix.npy and vectors_C/dev_case_ids.json
    shutil.copyfile(out_dev / "Q3_K_M_prefix.npy", out / "dev_Q3_K_M_prefix.npy")
    shutil.copyfile(out_dev / "case_ids.json", out / "dev_case_ids.json")
    report["finished"] = hc.now_text()
    report["files"] = {p.name: sha(p) for p in sorted(out.glob("*.npy"))}
    report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("\nALL DONE. The vectors are in %s. Tell Claude: 'extraction finished'." % out)


if __name__ == "__main__":
    main()
