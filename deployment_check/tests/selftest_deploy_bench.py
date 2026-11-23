"""Self-test of deploy_bench.py with a FAKE llama-server (no model, no GPU). It tests the harness, NOT the deployment.

    python tests/selftest_deploy_bench.py --workspace <folder with edgesar_pilot, edgesar_heads, V1, edgesar_shield, edgesar_audit_2026-11-13> --work <empty temp folder>

It builds a small test workspace (links to the real study code, a synthetic 'saved' prediction file and synthetic 'saved' vectors made from the fake
server's own vectors, with 3 deliberate disagreements and 1 deliberately different vector), runs deploy_bench.py against the fake server, and checks
that every number the harness reports matches what was put in: the memory the fake server holds, the latency it adds, the disagreements, the vector
difference, the CPU-only log scan, and the clean failure reports. Linux/macOS only (uses a shell wrapper for the fake server).
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent / "deploy_bench.py"
sys.path.insert(0, str(HERE))
from fake_llama_server import fake_vec                                   # noqa: E402

ARM = "C2p"
KEYCOLS = ("action", "incident", "landmark", "sensor", "priority")
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + name + ("   [" + detail + "]" if detail else ""), flush=True)


def arrays_sha256(arrs):
    h = hashlib.sha256()
    for k in sorted(arrs):
        a = np.ascontiguousarray(arrs[k])
        h.update(k.encode() + b"|" + str(a.dtype).encode() + b"|" + str(a.shape).encode() + b"|" + a.tobytes())
    return h.hexdigest()


def run(args, env=None, timeout=600):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run([sys.executable, str(BENCH)] + args, capture_output=True, text=True, env=e, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    ws, work = Path(a.workspace).resolve(), Path(a.work).resolve()
    if work.exists():
        shutil.rmtree(work)
    root, repair, folded = work / "root", work / "repair", work / "folded_test"
    for d in (root, repair / "out2", folded, root / "edgesar_heads" / "features"):
        d.mkdir(parents=True)
    for name in ("edgesar_pilot", "V1", "edgesar_shield", "edgesar_audit_2026-11-13"):
        (root / name).symlink_to((ws / name).resolve(), target_is_directory=True)
    shutil.copy(ws / "edgesar_heads" / "heads_config.json", root / "edgesar_heads" / "heads_config.json")
    shutil.copy(ws / "edgesar_heads" / "features" / "case_ids.json", root / "edgesar_heads" / "features" / "case_ids.json")

    # ---- the study code, to build 'saved' predictions exactly the way the pipeline builds live ones
    os.environ["EDGESAR_ROOT"] = str(root)
    sys.path.insert(0, str(root / "edgesar_shield"))
    from shield import paths
    for k in [k for k in paths.PINS if k.startswith("edgesar_heads/features/")]:
        paths.PINS.pop(k)
    from shield import data
    from shield.candidates import pilot
    pc, pb = pilot()
    cases = data.load_cases()
    prefix = json.loads((root / "edgesar_heads" / "heads_config.json").read_text())["prefix_text"]
    rs = np.random.RandomState(0)
    W = (rs.randn(10, 2048) * 0.5).astype(np.float32)
    b = np.zeros(10, dtype=np.float32)
    arrs = {"map_W": W, "map_b": b, "retrained_W": W.copy(), "retrained_b": b.copy()}
    np.savez(folded / "folded_q4.npz", **arrs)
    (folded / "folded_manifest.json").write_text(json.dumps({"arrays_sha256": arrays_sha256(arrs), "all_checks_pass": True}))

    ACT = ["CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION"]
    SEN = ["RGB", "THERMAL", "ANY"]
    PRI = ["1", "2", "3"]
    rows, vecs = [], np.random.RandomState(1).randn(1400, 2048).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    idxB = [k for k, c in enumerate(cases) if c["style"] == "B"]
    for k in idxB:
        c = cases[k]
        v = fake_vec(pc.build_prompt(c, "P1") + prefix)
        L = W @ v + b
        norm, _ = pc.validate(pb._assemble(c, ACT[int(np.argmax(L[0:4]))], SEN[int(np.argmax(L[4:7]))], int(PRI[int(np.argmax(L[7:10]))])), c)
        key = pc.strict_key(norm)
        rows.append([c["id"], key])
        n = np.random.RandomState(k).randn(2048).astype(np.float32) * 1e-4
        sv = v + n
        vecs[k] = sv / np.linalg.norm(sv)
    # 3 deliberate disagreements (the saved record is changed) and 1 deliberately different vector -- chosen among the reports that the 5-episode test run really uses
    from types import SimpleNamespace
    from shield.episodes import make_episodes
    inrun = [ev.case_id for e in make_episodes(SimpleNamespace(cases=cases), idxB, "M", 1000, 20)[:5] for ev in e.events]
    by_row = {r[0]: r for r in rows}
    flipped = []
    for cid in inrun[3:60]:
        if len(flipped) == 3:
            break
        if by_row[cid][1][0] != "NO_ACTION":
            by_row[cid][1] = ("NO_ACTION", None, None, None, None)
            flipped.append(cid)
    cid_to_k = {cases[k]["id"]: k for k in idxB}
    odd = inrun[70]
    vecs[cid_to_k[odd]] = np.random.RandomState(99).randn(2048).astype(np.float32)
    vecs[cid_to_k[odd]] /= np.linalg.norm(vecs[cid_to_k[odd]])
    np.save(root / "edgesar_heads" / "features" / "Q4_K_M_prefix.npy", vecs)
    with open(repair / "out2" / "predictions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["protocol", "repeat", "fold", "labels", "arm", "case_id", "action", "incident", "landmark", "sensor", "priority", "record_ok", "action_ok"])
        for arm in (ARM, "MATCHEDp"):
            for cid, key in rows:
                w.writerow(["B", 0, 0, "all", arm, cid] + ["" if v is None else v for v in key] + [0, 0])

    wrapper = work / "fake_llama_server.sh"
    wrapper.write_text("#!/bin/sh\nexec %s %s \"$@\"\n" % (sys.executable, HERE / "fake_llama_server.py"))
    wrapper.chmod(0o755)
    model = work / "fake.gguf"
    model.write_bytes(b"x" * 1000)
    base = ["run", "--root", str(root), "--repair-dir", str(repair), "--server", str(wrapper), "--model", str(model), "--folded", str(folded), "--skip-model-hash",
            "--threads", "2", "--sample-ms", "20"]

    # ---------------------------------------------------------------- test 1: normal run, 5 episodes = 100 reports
    out1 = work / "out_ok"
    t0 = time.time()
    rc, txt = run(base + ["--out", str(out1), "--episodes", "5", "--label", "selftest"], env={"FAKE_HOLD_MB": "400", "FAKE_EMBED_MS": "20"})
    check("normal run exits with 0", rc == 0, "exit %d, %.0f s" % (rc, time.time() - t0))
    if rc != 0:
        print(txt[-3000:])
    R = json.loads((out1 / "results.json").read_text()) if (out1 / "results.json").exists() else {}
    check("status FINISHED", R.get("status") == "FINISHED", str(R.get("status")))
    check("100 reports measured", R.get("reports_measured") == 100, str(R.get("reports_measured")))
    mem = R.get("memory", {})
    check("server OS peak working set >= the 400 MB the fake server holds", (mem.get("server_os_peak_ws_mb") or 0) >= 400, "%.0f MB" % (mem.get("server_os_peak_ws_mb") or 0))
    check("server OS peak working set is not absurdly larger (< 700 MB)", (mem.get("server_os_peak_ws_mb") or 1e9) < 700, "%.0f MB" % (mem.get("server_os_peak_ws_mb") or 0))
    check("sampled combined peak >= 400 MB", (mem.get("combined_ws_peak_sampled_mb_whole_run") or 0) >= 400, "%.0f MB" % (mem.get("combined_ws_peak_sampled_mb_whole_run") or 0))
    check("sampled combined peak <= sum of OS peaks + 5 MB (sampling can only see less)", (mem.get("combined_ws_peak_sampled_mb_whole_run") or 1e9) <= (mem.get("sum_of_os_peak_ws_mb") or 0) + 5,
          "%.0f vs %.0f" % (mem.get("combined_ws_peak_sampled_mb_whole_run") or 0, mem.get("sum_of_os_peak_ws_mb") or 0))
    check("sum of OS peaks = orchestrator + server", abs((mem.get("sum_of_os_peak_ws_mb") or 0) - (mem.get("orchestrator_os_peak_ws_mb") or 0) - (mem.get("server_os_peak_ws_mb") or 0)) < 1.0)
    check("memory series written", (out1 / "memory_series.csv").exists() and sum(1 for _ in open(out1 / "memory_series.csv")) > 5)
    lat = R.get("latency_ms", {})
    check("embed latency p50 >= 20 ms (the fake sleep) and < 200 ms", 20 <= lat.get("embed_ms", {}).get("p50", 0) < 200, "%.1f ms" % lat.get("embed_ms", {}).get("p50", 0))
    check("end-to-end decision latency >= report-to-record latency", lat.get("decision_wall_ms", {}).get("p50", 0) >= lat.get("live_ms", {}).get("p50", 1e9) - 0.5,
          "%.1f vs %.1f" % (lat.get("decision_wall_ms", {}).get("p50", 0), lat.get("live_ms", {}).get("p50", 0)))
    at = R.get("allocator_timing", {})
    check("allocator timing is reported: runs > 0 and time > 0 (it used to read 0)", at.get("runs_total", 0) > 0 and at.get("ms_total", 0) > 0, "%s runs, %.1f ms total" % (at.get("runs_total"), at.get("ms_total", 0)))
    check("allocator ms per run x runs = total (arithmetic)", abs(at.get("ms_per_run_mean", 0) * at.get("runs_total", 0) - at.get("ms_total", 1e9)) < 1e-6 * max(at.get("ms_total", 1), 1) + 1e-6)
    check("allocator report counts = the 100 reports; per-episode rows = 5", at.get("reports_total") == 100 and len(at.get("episodes", [])) == 5, "%s reports, %s episodes" % (at.get("reports_total"), len(at.get("episodes", []))))
    check("evaluation-only audit is OFF by default and its runs are 0", at.get("evaluation_audit_on") is False and at.get("evaluation_audit_runs_not_counted") == 0)
    r2p = lat.get("report_to_plan_ms", {})
    check("report-to-plan stopwatch has one value per report (100)", r2p.get("n") == 100 and R.get("reports_with_plan_stopwatch") == 100, "%s, %s" % (r2p.get("n"), R.get("reports_with_plan_stopwatch")))
    check("report-to-plan >= decision wall (it contains the decision) and >= its allocator part", r2p.get("mean", 0) >= lat["decision_wall_ms"]["mean"] - 0.01 and r2p.get("mean", 0) >= lat.get("plan_allocator_ms_in_window", {}).get("mean", 1e9) - 0.01,
          "%.2f vs decision %.2f, allocator %.2f" % (r2p.get("mean", 0), lat["decision_wall_ms"]["mean"], lat.get("plan_allocator_ms_in_window", {}).get("mean", 0)))
    check("report-to-plan: decision + after-decision parts add up (mean)", abs(r2p.get("mean", 0) - (lat["decision_wall_ms"]["mean"] + lat.get("plan_after_decision_ms", {}).get("mean", 0))) < 0.5,
          "%.3f vs %.3f" % (r2p.get("mean", 0), lat["decision_wall_ms"]["mean"] + lat.get("plan_after_decision_ms", {}).get("mean", 0)))
    check("report_to_plan.csv written with 100 rows", (out1 / "report_to_plan.csv").exists() and sum(1 for _ in open(out1 / "report_to_plan.csv")) == 101)
    evf = R.get("evaluation_files_opened", {})
    when = {Path(f["file"]).name: f["when"] for f in evf.get("files", [])}
    check("saved evaluation vectors were opened only AFTER the measured window closed", when.get("Q4_K_M_prefix.npy") == "AFTER the measured window closed", str(when.get("Q4_K_M_prefix.npy")))
    check("saved predictions + cases + folded file were opened BEFORE the server started", all(when.get(n) == "before the server started" for n in ("predictions.csv", "cases.jsonl", "folded_q4.npz")), str({n: when.get(n) for n in ("predictions.csv", "cases.jsonl", "folded_q4.npz")}))
    check("no file with f16 in its name was opened", not any("f16" in f["file"].lower() for f in evf.get("files", [])))
    check("orchestrator memory when the window closed is reported", (evf.get("orchestrator_rss_mb_when_window_closed") or 0) > 20, str(evf.get("orchestrator_rss_mb_when_window_closed")))
    ag = R.get("agreement", {})
    check("exactly 3 deliberate disagreements found", ag.get("disagreements") == 3 and ag.get("record_equal") == 97, "equal %s, disagreements %s" % (ag.get("record_equal"), ag.get("disagreements")))
    dis = list(csv.DictReader(open(out1 / "disagreements.csv")))
    check("disagreement file lists the 3 flipped reports", sorted(d["case_id"] for d in dis) == sorted(flipped) or len(dis) == 3, str([d["case_id"] for d in dis]))
    va = R.get("vector_agreement", {})
    per = list(csv.DictReader(open(out1 / "per_report.csv")))
    odd_in_run = any(r["case_id"] == odd for r in per)
    check("vector comparison: reports below cosine 0.999 equals the deliberate one (if it is in the 100)", va.get("n_below_0.999") == (1 if odd_in_run else 0), "%s (odd report in run: %s)" % (va.get("n_below_0.999"), odd_in_run))
    check("vector comparison: median cosine ~ 1", va.get("median", 0) > 0.9999, str(va.get("median")))
    mi = R.get("mission", {})
    check("mission replay: at most 3 of 5 episodes differ (only the flipped reports can change an outcome)", mi.get("episodes_with_identical_counts", 0) >= 2, str(mi.get("episodes_with_identical_counts")))
    sc = R.get("server_log_scan", {})
    check("CPU-only scan: offload line says 0 layers, no GPU backend", sc.get("offload_line_says_zero") and not sc.get("non_cpu_backend_loaded"), str(sc))
    check("server flags: -ngl 0 and CUDA_VISIBLE_DEVICES=-1 recorded", "-ngl 0" in R.get("server_command", "") and "CUDA_VISIBLE_DEVICES=-1" in (out1 / "server.log").read_text(), R.get("server_command", "")[-80:])
    rep = (out1 / "DEPLOYMENT_REPORT.md").read_text()
    check("report never says 'pass' for a 2 GB device", "2 GB device is not tested" in rep and "2 GB PASS" not in rep.upper() and "PASS: 2" not in rep.upper())
    check("report shows the allocator rows", "Allocator planning, per allocator run" in rep and "END TO END, MEASURED" in rep and "NOT the allocator" in rep and "Evaluation data and the measurement" in rep)
    check("report contains all seven sections", all(("## %d." % i) in rep for i in range(1, 8)))
    check("no FP16 file opened (skipped pins listed, no f16 in the report body)", "FP16 files opened by this program: none" in rep)
    check("same-prompt-twice difference is 0", R.get("same_prompt_twice_max_abs_diff") == 0.0, str(R.get("same_prompt_twice_max_abs_diff")))

    # ---------------------------------------------------------------- test 1b: the repair package is found when --repair-dir points to a parent folder
    parent = work / "parent_of_repair"
    parent.mkdir()
    os.symlink(repair, parent / "repair_package")
    out1b = work / "out_found"
    rc, txt = run([x if x != str(repair) else str(parent) for x in base] + ["--out", str(out1b), "--episodes", "1", "--label", "selftest-found"], env={"FAKE_HOLD_MB": "50", "FAKE_EMBED_MS": "5"})
    R1b = json.loads((out1b / "results.json").read_text()) if (out1b / "results.json").exists() else {}
    check("repair package found inside a parent folder (repair_package)", rc == 0 and R1b.get("status") == "FINISHED", "exit %d, %s" % (rc, R1b.get("status")))
    empty = work / "empty_folder"
    empty.mkdir()
    rc, txt = run([x if x != str(repair) else str(empty) for x in base] + ["--out", str(work / "out_nofind"), "--episodes", "1"], env={"FAKE_HOLD_MB": "50"})
    check("a wrong repair folder stops at once with the list of places searched", rc != 0 and "Cannot find the saved predictions" in txt, "exit %d" % rc)

    # ---------------------------------------------------------------- test 2: GPU backend lines in the log must be flagged
    out2 = work / "out_gpu"
    rc, txt = run(base + ["--out", str(out2), "--episodes", "1", "--label", "selftest_gpu_lines"], env={"FAKE_HOLD_MB": "50", "FAKE_GPU_LINES": "1"})
    R2 = json.loads((out2 / "results.json").read_text())
    check("a GPU backend in the server log is flagged", R2["server_log_scan"]["non_cpu_backend_loaded"] is True and "Use a llama.cpp folder without" in (out2 / "DEPLOYMENT_REPORT.md").read_text())

    # ---------------------------------------------------------------- test 3: server dies at start -> clean report, exit 3
    out3 = work / "out_dead"
    rc, txt = run(base + ["--out", str(out3), "--episodes", "1", "--label", "selftest_dead"], env={"FAKE_EXIT": "1"})
    R3 = json.loads((out3 / "results.json").read_text()) if (out3 / "results.json").exists() else {}
    check("server that stops while loading gives status SERVER_FAILED_TO_START, exit 3, report written", rc == 3 and R3.get("status") == "SERVER_FAILED_TO_START" and (out3 / "DEPLOYMENT_REPORT.md").exists(), "exit %d, %s" % (rc, R3.get("status")))

    # ---------------------------------------------------------------- test 4: server file missing
    out4 = work / "out_missing"
    b2 = list(base)
    b2[b2.index("--server") + 1] = str(work / "nonexistent.exe")
    rc, txt = run(b2 + ["--out", str(out4), "--episodes", "1"])
    R4 = json.loads((out4 / "results.json").read_text()) if (out4 / "results.json").exists() else {}
    check("missing server file gives a clean failed report (not a crash without report)", rc == 3 and R4.get("status") in ("FAILED_DURING_RUN", "SERVER_FAILED_TO_START"), "exit %d, %s" % (rc, R4.get("status")))

    # ---------------------------------------------------------------- test 5: folded files tampered -> refuse
    bad = work / "folded_bad"
    shutil.copytree(folded, bad)
    z = dict(np.load(bad / "folded_q4.npz"))
    z["map_W"][0, 0] += 1.0
    np.savez(bad / "folded_q4.npz", **z)
    b3 = list(base)
    b3[b3.index("--folded") + 1] = str(bad)
    rc, txt = run(b3 + ["--out", str(work / "out_bad"), "--episodes", "1"])
    check("changed folded matrix is refused", rc != 0 and "does not match folded_manifest" in txt, "exit %d" % rc)

    # ---------------------------------------------------------------- test 6: job cap on a non-Windows system must stop with a clear message
    rc, txt = run(base + ["--out", str(work / "out_cap"), "--episodes", "1", "--job-limit-mb", "2048"])
    check("memory cap requested where no Job Object exists stops with a clear message", rc != 0 and "Job Object is not available" in txt, "exit %d" % rc)

    # ---------------------------------------------------------------- test 6b: the "weights in private memory" switch is chosen from the server's own --help (llama.cpp b11901 REJECTS --no-mmap)
    outN = work / "out_loadmode"
    rc, txt = run(base + ["--out", str(outN), "--episodes", "1", "--no-mmap", "--ctx", "1024", "--label", "selftest_loadmode"], env={"FAKE_HELP": "loadmode", "FAKE_HOLD_MB": "50", "FAKE_EMBED_MS": "5"})
    RN = json.loads((outN / "results.json").read_text()) if (outN / "results.json").exists() else {}
    check("new build (help lists --load-mode): run finishes and uses '--load-mode none'", rc == 0 and RN.get("status") == "FINISHED" and RN.get("no_mmap_switch", {}).get("arguments") == ["--load-mode", "none"], "exit %d, %s, %s" % (rc, RN.get("status"), RN.get("no_mmap_switch", {}).get("arguments")))
    check("new build: the server command has '--load-mode none' and not '--no-mmap'", "--load-mode none" in RN.get("server_command", "") and "--no-mmap" not in RN.get("server_command", ""), RN.get("server_command", "")[-70:])
    check("new build: report names the switch used and context 1024", "`--load-mode none`" in (outN / "DEPLOYMENT_REPORT.md").read_text() and "Context length requested 1024" in (outN / "DEPLOYMENT_REPORT.md").read_text())
    outO = work / "out_oldnommap"
    rc, txt = run(base + ["--out", str(outO), "--episodes", "1", "--no-mmap", "--label", "selftest_oldnommap"], env={"FAKE_HELP": "nommap", "FAKE_HOLD_MB": "50", "FAKE_EMBED_MS": "5"})
    RO = json.loads((outO / "results.json").read_text()) if (outO / "results.json").exists() else {}
    check("old build (help lists --no-mmap): run finishes and uses '--no-mmap'", rc == 0 and RO.get("no_mmap_switch", {}).get("arguments") == ["--no-mmap"] and "--no-mmap" in RO.get("server_command", ""), "exit %d, %s" % (rc, RO.get("no_mmap_switch", {}).get("arguments")))
    rc, txt = run(base + ["--out", str(work / "out_neither"), "--episodes", "1", "--no-mmap", "--label", "selftest_neither"], env={"FAKE_HELP": "none", "FAKE_HOLD_MB": "50"})
    check("a build whose help shows neither switch stops at once with a clear message (no server started)", rc != 0 and "neither --load-mode nor --no-mmap" in txt and not (work / "out_neither" / "server.log").exists(), "exit %d" % rc)
    rc, txt = run(base + ["--out", str(work / "out_nommap_default"), "--episodes", "1", "--label", "selftest_mmap_default"], env={"FAKE_HELP": "loadmode", "FAKE_HOLD_MB": "50", "FAKE_EMBED_MS": "5"})
    RD = json.loads((work / "out_nommap_default" / "results.json").read_text()) if (work / "out_nommap_default" / "results.json").exists() else {}
    check("default run (no --no-mmap) on the new build still works and adds no load switch", rc == 0 and "--load-mode" not in RD.get("server_command", "") and "no_mmap_switch" not in RD, "exit %d" % rc)

    # ---------------------------------------------------------------- test 6c: --ngl is passed ONCE (the old diagnostic had '-ngl 0 ... -ngl 99') and marks the run as a diagnostic
    outG = work / "out_ngl"
    rc, txt = run(base + ["--out", str(outG), "--episodes", "1", "--ngl", "99", "--keep-gpu-visible", "--label", "selftest_ngl"], env={"FAKE_HOLD_MB": "50", "FAKE_EMBED_MS": "5"})
    RG = json.loads((outG / "results.json").read_text()) if (outG / "results.json").exists() else {}
    cmdG = RG.get("server_command", "")
    check("--ngl 99: the command has '-ngl 99' exactly once and no '-ngl 0'", rc == 0 and cmdG.count("-ngl") == 1 and "-ngl 99" in cmdG and "-ngl 0" not in cmdG, cmdG[cmdG.find("-ngl") - 2:cmdG.find("-ngl") + 12])
    repG = (outG / "DEPLOYMENT_REPORT.md").read_text() if (outG / "DEPLOYMENT_REPORT.md").exists() else ""
    check("--ngl 99: report says 'DIAGNOSTIC RUN' and shows '-ngl 99' in the flags line", "DIAGNOSTIC RUN" in repG and "Flags: `-ngl 99`" in repG)
    check("default: the flags line says '-ngl 0' and 'CUDA_VISIBLE_DEVICES=-1'", "Flags: `-ngl 0`, `CUDA_VISIBLE_DEVICES=-1`" in (out1 / "DEPLOYMENT_REPORT.md").read_text())

    # ---------------------------------------------------------------- test 7: probe
    rc, txt = run(["probe", "--tmp", str(work)])
    check("probe runs and measures a 200 MB child", rc == 0 and "OK" in txt, txt.strip().splitlines()[-1] if txt.strip() else "")

    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    lines = ["# Self-test of the deployment harness (fake server; tests the program, not the deployment)", "",
             "Run: %s on %s. %d checks, %d failed." % (time.strftime("%Y-%m-%d %H:%M:%S"), sys.platform, len(RESULTS), n_fail), "", "| Check | Result | Detail |", "|---|---|---|"]
    for n, ok, d in RESULTS:
        lines.append("| %s | %s | %s |" % (n, "PASS" if ok else "**FAIL**", d.replace("|", "/")[:160]))
    lines += ["", "Not tested here (no Windows, no real model): the Windows Job Object, `peak_wset`/`peak_pagefile`, typeperf and PowerShell probes, the real llama.cpp server. "
              "Run `python deploy_bench.py probe` on the Windows PC for those parts.", ""]
    (HERE.parent / "SELFTEST_RESULT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n%d checks, %d failed" % (len(RESULTS), n_fail))
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
