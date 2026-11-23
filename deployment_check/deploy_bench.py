"""DEPLOYMENT BENCHMARK of the Q4 system: Q4 model (llama.cpp, CPU only) + folded classifier + allocator.   Q4 ONLY: no FP16 file is opened.

What one run does (python deploy_bench.py run ...):
  1. starts llama-server on the Q4 GGUF with CPU-only flags (the flags of the saved vectors, except -ngl 0), as a child process;
  2. for every report of the chosen mission episodes (style-B reports, level M, arrival seed 1 = the same episodes as the wording-shift check)
     builds the pilot prompt (+ the `prefix` text), asks the server for the hidden vector, applies the FOLDED classifier (one 10 x 2048 matrix),
     assembles the record with the pilot assembler and lets the bounded CBBA allocator and the simulator use it (always-commit policy);
  3. while this runs, a sampler thread measures the memory of this process AND of llama-server (every 50 ms), and on Windows a Job Object
     measures the peak committed memory of all processes together;
  4. afterwards (outside the measured window) it compares the live decisions with the SAVED predictions of the same arm, the live vectors with the
     saved vectors, and the live mission outcome with a replay of the saved records.
It writes DEPLOYMENT_REPORT.md, results.json, per_report.csv, memory_series.csv, server.log, live_vectors_q4_prefix.npy into --out.

It NEVER prints a pass/fail for "a 2 GB device". It reports measured numbers for THIS computer under THIS test, and lists what the test cannot show.

  python deploy_bench.py probe                                (30 seconds: checks that the Windows measurement parts work on this computer)
  python deploy_bench.py run --root <workspace> --repair-dir <edgesar_repair_2026-11-14> --server <llama-server.exe> --model <Q4 gguf> --out <folder> [options]
Needs: Python 3.10+, numpy, scipy, scikit-learn (imported by the study code), psutil.
"""
import argparse
import csv
import ctypes
import hashlib
import json
import math
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

try:
    import psutil
except Exception:                                               # pragma: no cover
    psutil = None

HERE = Path(__file__).resolve().parent
ACTIONS = ["CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION"]
SENSORS = ["RGB", "THERMAL", "ANY"]
PRIOS = ["1", "2", "3"]
PROMPT_ID = "P1"
PREFIX_TEXT = '{"action":"'
KEYCOLS = ("action", "incident", "landmark", "sensor", "priority")
ARM_SAVED = {"map": "C2p", "retrained": "MATCHEDp"}
Q4_SHA256 = "26bac8efd811cb41a80db4393dbe5c8360abd54b98954ec766aa4ba7dacc0bc5"      # audited Q4_K_M file (extract_fresh_vectors.py)
Q4_BYTES = 807694176
MB = float(2 ** 20)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            h.update(ch)
    return h.hexdigest()


def arrays_sha256(arrs):
    h = hashlib.sha256()
    for k in sorted(arrs):
        a = np.ascontiguousarray(arrs[k])
        h.update(k.encode() + b"|" + str(a.dtype).encode() + b"|" + str(a.shape).encode() + b"|" + a.tobytes())
    return h.hexdigest()


def find_repair_dir(rd, root):
    """The saved predictions (out2/predictions.csv of the repair package) are in different places in different copies of the workspace: look in the likely ones."""
    rd, root = Path(rd), Path(root)
    cands = [rd, rd / "repair_package", rd / "repair_pkg" / "edgesar_repair_2026-11-14",
             root / "edgesar_shield" / "repair_pkg" / "edgesar_repair_2026-11-14", root / "edgesar_shield" / "repair_package",
             root / "edgesar_repair_2026-11-14", root / "repair_pkg" / "edgesar_repair_2026-11-14", root / "repair_package"]
    for c in cands:
        if (c / "out2" / "predictions.csv").exists():
            return c.resolve()
    sys.exit("Cannot find the saved predictions (out2\\predictions.csv of the repair package). Looked in:\n  " + "\n  ".join(str(c) for c in cands) +
             "\nGive the right folder with --repair-dir.")


def pct(xs, p):
    return float(np.percentile(xs, p)) if len(xs) else float("nan")


def lat_stats(xs):
    xs = list(xs)
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": float(np.mean(xs)), "p50": pct(xs, 50), "p95": pct(xs, 95), "p99": pct(xs, 99), "max": float(max(xs)), "min": float(min(xs))}


# =====================================================================================================================
# Windows Job Object: peak committed memory of ALL processes of the run, and an optional hard cap
# =====================================================================================================================
class _IO(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _BASIC(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32), ("SchedulingClass", ctypes.c_uint32)]


class _EXT(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BASIC), ("IoInfo", _IO), ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


JOB_LIMIT_JOB_MEMORY = 0x0200
JOB_EXT_INFO_CLASS = 9
TRACKING_LIMIT_MB = 1024 * 1024                                  # 1 TB: "no real cap", only makes sure the job keeps its peak counters


class WinJob:
    """This process (and every child it starts) goes into one job. `limit_mb` is a hard cap on the COMMITTED memory of the whole job."""

    def __init__(self, limit_mb=None):
        self.ok, self.err, self.limit_mb, self.h, self.k = False, None, limit_mb, None, None
        if os.name != "nt":
            self.err = "not Windows"
            return
        try:
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            k.CreateJobObjectW.restype = ctypes.c_void_p
            k.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
            k.SetInformationJobObject.restype = ctypes.c_int
            k.SetInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
            k.QueryInformationJobObject.restype = ctypes.c_int
            k.QueryInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
            k.AssignProcessToJobObject.restype = ctypes.c_int
            k.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            k.GetCurrentProcess.restype = ctypes.c_void_p
            h = k.CreateJobObjectW(None, None)
            if not h:
                raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
            info = _EXT()
            info.BasicLimitInformation.LimitFlags = JOB_LIMIT_JOB_MEMORY
            info.JobMemoryLimit = int((limit_mb or TRACKING_LIMIT_MB) * MB)
            if not k.SetInformationJobObject(h, JOB_EXT_INFO_CLASS, ctypes.byref(info), ctypes.sizeof(info)):
                raise OSError(ctypes.get_last_error(), "SetInformationJobObject failed")
            if not k.AssignProcessToJobObject(h, k.GetCurrentProcess()):
                raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject failed (this program may already run inside another job; try a plain cmd.exe window)")
            self.k, self.h, self.ok = k, h, True
        except Exception as e:                                   # keep going without the job
            self.err = "%s: %s" % (type(e).__name__, e)

    def contains(self, pid):
        """True/False: is this process inside this job (so the cap and the peak counter cover it)? None if it cannot be asked."""
        if not self.ok:
            return None
        try:
            k = self.k
            k.OpenProcess.restype = ctypes.c_void_p
            k.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
            k.IsProcessInJob.restype = ctypes.c_int
            k.IsProcessInJob.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
            k.CloseHandle.argtypes = [ctypes.c_void_p]
            hp = k.OpenProcess(0x1000, 0, int(pid))                      # PROCESS_QUERY_LIMITED_INFORMATION
            if not hp:
                return None
            r = ctypes.c_int(0)
            ok = k.IsProcessInJob(hp, self.h, ctypes.byref(r))
            k.CloseHandle(hp)
            return bool(r.value) if ok else None
        except Exception:
            return None

    def peaks_mb(self):
        if not self.ok:
            return None
        info = _EXT()
        if not self.k.QueryInformationJobObject(self.h, JOB_EXT_INFO_CLASS, ctypes.byref(info), ctypes.sizeof(info), None):
            return None
        return {"peak_job_commit_mb": info.PeakJobMemoryUsed / MB, "peak_process_commit_mb": info.PeakProcessMemoryUsed / MB}


# =====================================================================================================================
# memory sampler (this process + every child, i.e. llama-server)
# =====================================================================================================================
def os_peak_ws_mb(pid):
    """Peak working set / resident memory of one process as the OS recorded it (no sampling gaps)."""
    try:
        if os.name == "nt":
            return psutil.Process(pid).memory_info().peak_wset / MB
        for line in open("/proc/%d/status" % pid):
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) / 1024.0
    except Exception:
        return None
    return None


def os_peak_commit_mb(pid):
    try:
        if os.name == "nt":
            return psutil.Process(pid).memory_info().peak_pagefile / MB
    except Exception:
        return None
    return None


def one_proc(p):
    mi = p.memory_info()
    priv = getattr(mi, "private", None)
    if priv is None:                                              # Linux (self-test only): resident minus shared
        priv = mi.rss - getattr(mi, "shared", 0)
    return mi.rss, priv


class Sampler(threading.Thread):
    daemon = True

    def __init__(self, interval=0.05):
        super().__init__()
        self.me = psutil.Process(os.getpid())
        self.interval, self.stop_evt = interval, threading.Event()
        self.series = []                                          # (t, orch_ws, srv_ws, orch_priv, srv_priv, avail_bytes, n_children)
        self.pid_peak, self.pid_name, self.errors = {}, {}, 0

    def run(self):
        while not self.stop_evt.is_set():
            t = time.perf_counter()
            try:
                o_ws, o_pr = one_proc(self.me)
                s_ws = s_pr = 0
                kids = self.me.children(recursive=True)
                for c in kids:
                    try:
                        w, p = one_proc(c)
                        s_ws += w
                        s_pr += p
                        self.pid_peak[c.pid] = max(self.pid_peak.get(c.pid, 0), w)
                        if c.pid not in self.pid_name:
                            self.pid_name[c.pid] = c.name()
                    except Exception:
                        self.errors += 1
                self.pid_peak[self.me.pid] = max(self.pid_peak.get(self.me.pid, 0), o_ws)
                self.series.append((t, o_ws, s_ws, o_pr, s_pr, psutil.virtual_memory().available, len(kids)))
            except Exception:
                self.errors += 1
            self.stop_evt.wait(self.interval)

    def stop(self):
        self.stop_evt.set()
        self.join(timeout=5)

    def peak_between(self, t0, t1, col):
        v = [s[col] for s in self.series if t0 <= s[0] <= t1]
        return max(v) / MB if v else None

    def combined_peak_between(self, t0, t1, ws=True):
        a, b = (1, 2) if ws else (3, 4)
        v = [s[a] + s[b] for s in self.series if t0 <= s[0] <= t1]
        return max(v) / MB if v else None

    def min_available_between(self, t0, t1):
        v = [s[5] for s in self.series if t0 <= s[0] <= t1]
        return min(v) / MB if v else None


# =====================================================================================================================
# paging, GPU and system facts (best effort; every probe says why it failed)
# =====================================================================================================================
def run_text(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return -1, "%s: %s" % (type(e).__name__, e)


PS_SCRIPT = ("$o=[ordered]@{};"
             "$o.cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name);"
             "$o.cs=(Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory,AutomaticManagedPagefile);"
             "$o.pagefile=@(Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage);"
             "$o.os=(Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,FreePhysicalMemory,TotalVisibleMemorySize);"
             "$o | ConvertTo-Json -Depth 4 -Compress")


def windows_facts():
    if os.name != "nt":
        return {"available": False, "why": "not Windows"}
    rc, txt = run_text(["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_SCRIPT], 60)
    try:
        d = json.loads(txt[txt.index("{"):])
        d["available"] = True
        return d
    except Exception:
        return {"available": False, "why": "PowerShell query failed: %s" % txt[:200].replace("\n", " ")}


def gpu_facts():
    rc, txt = run_text(["nvidia-smi", "--query-gpu=name,memory.used,memory.total,driver_version", "--format=csv,noheader,nounits"], 15)
    if rc != 0:
        return {"available": False, "why": txt[:150].replace("\n", " ")}
    try:
        name, used, total, drv = [x.strip() for x in txt.strip().splitlines()[0].split(",")]
        return {"available": True, "name": name, "used_mb": float(used), "total_mb": float(total), "driver": drv}
    except Exception:
        return {"available": False, "why": "could not read: " + txt[:100]}


def vmstat_linux():
    out = {}
    try:
        for line in open("/proc/vmstat"):
            k, v = line.split()
            if k in ("pgmajfault", "pswpin", "pswpout"):
                out[k] = int(v)
    except Exception:
        pass
    return out


class PagingProbe:
    """Windows: typeperf counters once per second (hard page faults = Pages Input/sec). Linux (self-test): /proc/vmstat counters."""
    COUNTERS = [r"\Memory\Pages Input/sec", r"\Memory\Page Faults/sec", r"\Memory\Available MBytes"]

    def __init__(self, out_dir):
        self.csv, self.proc, self.t_epoch0, self.why = Path(out_dir) / "typeperf_memory.csv", None, None, None
        self.vm0 = vmstat_linux()

    def start(self):
        if os.name != "nt":
            return
        try:
            self.t_epoch0 = time.time()
            self.proc = subprocess.Popen(["typeperf"] + self.COUNTERS + ["-si", "1", "-o", str(self.csv), "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self.why = "typeperf could not start: %s" % e

    def stop(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=10)
            except Exception:
                pass

    def stats(self, t_from_epoch, t_to_epoch):
        """Counter statistics for rows that fall (approximately, 1 s resolution) in the wall-clock window."""
        res = {"source": "typeperf" if os.name == "nt" else "/proc/vmstat"}
        if os.name != "nt":
            vm1 = vmstat_linux()
            res.update({k: vm1.get(k, 0) - self.vm0.get(k, 0) for k in self.vm0})
            return res
        if self.why or not self.csv.exists():
            return dict(res, available=False, why=self.why or "typeperf wrote no file (counter names are language-specific; non-English Windows may fail)")
        try:
            rows = list(csv.reader(open(self.csv, encoding="utf-8", errors="replace")))
            data = [r for r in rows[1:] if len(r) >= 4]
            vals = []
            for i, r in enumerate(data):
                t = self.t_epoch0 + 1.0 * (i + 1)                 # rows come once per second from the start of typeperf (approximate)
                try:
                    vals.append((t, float(r[1]), float(r[2]), float(r[3])))
                except ValueError:
                    continue
            win = [v for v in vals if t_from_epoch <= v[0] <= t_to_epoch]
            if not win:
                return dict(res, available=False, why="no counter rows in the window")
            return dict(res, available=True, rows_in_window=len(win), time_alignment="approximate (1 s rows, start time of typeperf)",
                        pages_input_per_s_max=max(v[1] for v in win), pages_input_per_s_mean=float(np.mean([v[1] for v in win])),
                        page_faults_per_s_max=max(v[2] for v in win), available_mbytes_min=min(v[3] for v in win),
                        pages_input_total_estimate=float(sum(v[1] for v in win)))
        except Exception as e:
            return dict(res, available=False, why="could not read typeperf file: %s" % e)


# =====================================================================================================================
# llama-server
# =====================================================================================================================
def http_json(url, payload=None, timeout=300):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data is not None else {}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def nommap_args(exe):
    """llama.cpp changed this switch: older builds have --no-mmap; newer ones (b11901) REJECT it ("invalid argument: --no-mmap") and use --load-mode <value>.
    Read the server's own --help and choose; returns (arguments, help excerpt for the record)."""
    rc, t = run_text([str(exe), "--help"], 90)
    i = t.find("--load-mode")
    if i >= 0:
        seg = t[i:i + 900]
        if re.search(r"\bnone\b", seg):
            return ["--load-mode", "none"], seg[:700]
        raise RuntimeError("This llama-server has --load-mode but its help does not show a value 'none' (weights in private memory). Help text:\n" + seg)
    if "--no-mmap" in t:
        return ["--no-mmap"], ""
    raise RuntimeError("This llama-server's --help shows neither --load-mode nor --no-mmap, so weights in private memory cannot be requested. Help began: " + t[:300])


class Server:
    def __init__(self, exe, model, port, ctx, threads, batch, ubatch, no_mmap, extra, log_path, keep_gpu_visible=False, ngl=0, nommap_flags=None):
        self.exe, self.model, self.port, self.log_path = str(exe), str(model), int(port), Path(log_path)
        self.cmd = [self.exe, "-m", self.model, "--host", "127.0.0.1", "--port", str(self.port), "-ngl", str(int(ngl)), "-c", str(ctx), "-np", "1", "-t", str(threads),
                    "--embeddings", "--pooling", "last", "-b", str(batch), "-ub", str(ubatch)] + (list(nommap_flags or ["--no-mmap"]) if no_mmap else []) + list(extra)
        self.env = dict(os.environ)
        if not keep_gpu_visible:
            self.env["CUDA_VISIBLE_DEVICES"] = "-1"
        self.proc, self.base = None, "http://127.0.0.1:%d" % self.port

    def start(self, timeout_s=600):
        # Refuse an occupied port before launching: never measure an unrelated server.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if os.name == "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", self.port))
            except OSError as exc:
                raise RuntimeError("Port %d is unavailable; close the existing server or use --port. %s" % (self.port, exc)) from exc
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.log_path, "w", encoding="utf-8")
        self._fh.write("COMMAND: %s\nCUDA_VISIBLE_DEVICES=%s\n\n" % (" ".join(self.cmd), self.env.get("CUDA_VISIBLE_DEVICES")))
        self._fh.flush()
        self.proc = subprocess.Popen(self.cmd, stdout=self._fh, stderr=subprocess.STDOUT, env=self.env, cwd=str(Path(self.exe).resolve().parent))
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if self.proc.poll() is not None:
                raise RuntimeError("llama-server stopped while loading (exit code %s). Read %s. If a memory cap (--job-limit-mb) was set, "
                                   "this can be the effect of the cap; the log says more." % (self.proc.returncode, self.log_path))
            try:
                st, _ = http_json(self.base + "/health", None, 5)
                if st == 200:
                    return time.time() - t0
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError("llama-server was not ready after %d s. Read %s" % (timeout_s, self.log_path))

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=30)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        if getattr(self, "_fh", None):
            self._fh.close()

    def log_text(self):
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""


def scan_server_log(text):
    """Evidence about CPU-only operation, from llama-server's own log."""
    off = re.findall(r"offloaded\s+(\d+)\s*/\s*(\d+)\s+layers to GPU", text)
    backends = re.findall(r"load_backend: loaded (\S+) backend from (.+)", text)
    gpu_words = sorted({w for w in ("CUDA", "Vulkan", "Metal", "SYCL", "HIP", "ROCm") if re.search(r"\b%s\b" % w, text)})
    cuda_loaded = [b for b in backends if b[0].upper() not in ("CPU",)]
    return {"offloaded_layers": ["%s/%s" % o for o in off], "backends_loaded": ["%s (%s)" % (b[0], b[1].strip()[-60:]) for b in backends],
            "gpu_words_in_log": gpu_words, "non_cpu_backend_loaded": bool(cuda_loaded),
            "offload_line_says_zero": bool(off) and all(int(a) == 0 for a, _ in off)}


class EmbedClient:
    def __init__(self, base, timeout=600):
        self.base, self.timeout = base.rstrip("/"), timeout

    def embed(self, text):
        _, b = http_json(self.base + "/v1/embeddings", {"input": text, "encoding_format": "float"}, self.timeout)
        a = np.asarray(b["data"][0]["embedding"], dtype=np.float32)
        if a.ndim == 2:
            a = a[-1]
        return a, (b.get("usage") or {}).get("prompt_tokens")


# =====================================================================================================================
# the live pipeline: report -> prompt -> Q4 vector -> folded classifier -> record
# =====================================================================================================================
class LivePipeline:
    def __init__(self, pc, pb, client, W, b, dtype):
        self.pc, self.pb, self.client = pc, pb, client
        self.W, self.b, self.dtype = W.astype(dtype), b.astype(dtype), dtype
        self.rows = {}                                            # case id -> dict of timings and outputs

    def decide(self, case):
        pc, pb = self.pc, self.pb
        t0 = time.perf_counter()
        prompt = pc.build_prompt(case, PROMPT_ID) + PREFIX_TEXT
        t1 = time.perf_counter()
        vec, ntok = self.client.embed(prompt)
        t2 = time.perf_counter()
        L = self.W @ vec.astype(self.dtype) + self.b
        a, s, p = int(np.argmax(L[0:4])), int(np.argmax(L[4:7])), int(np.argmax(L[7:10]))
        t3 = time.perf_counter()
        norm, _ = pc.validate(pb._assemble(case, ACTIONS[a], SENSORS[s], int(PRIOS[p])), case)
        key = pc.strict_key(norm)
        t4 = time.perf_counter()
        self.rows[case["id"]] = {"id": case["id"], "prompt_tokens": ntok, "prompt_chars": len(prompt), "build_ms": (t1 - t0) * 1e3, "embed_ms": (t2 - t1) * 1e3,
                                 "classifier_us": (t3 - t2) * 1e6, "assemble_ms": (t4 - t3) * 1e3, "live_ms": (t4 - t0) * 1e3,
                                 "key": key, "vec": vec, "logits": L.astype(np.float64)}
        return {"key": key, "norm": norm, "score": 1.0}


class LiveService:
    """Same interface as shield.service.Service for CommitPolicy; the record comes from the live pipeline the first time a report is asked for."""

    def __init__(self, byid, pipe):
        self.byid, self.pipe, self.cache = byid, pipe, {}

    def pilot_record(self, rid):
        if rid not in self.cache:
            self.cache[rid] = self.pipe.decide(self.byid[rid])
        return self.cache[rid]

    def candidates(self, rid):
        return [self.pilot_record(rid)]

    def confidence(self, rid):
        return 1.0

    def top_score(self, rid):
        return 1.0


def load_saved_keys(path, arm):
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["protocol"] == "B" and r["labels"] == "all" and r["arm"] == arm:
                out[r["case_id"]] = tuple(None if r[c] == "" else (int(r[c]) if c == "priority" else r[c]) for c in KEYCOLS)
    return out


def eval_lines(res):
    """Report lines: which data files this program opened and WHEN (the saved evaluation vectors must be opened only after the measured window)."""
    ev = res.get("evaluation_files_opened") or {}
    if not ev:
        return []
    seen = {}
    for f in ev.get("files", []):
        key = (Path(f["file"]).name, f["when"])
        seen.setdefault(key, f["seconds_after_server_start"])
    f16 = sorted({Path(f["file"]).name for f in ev.get("files", []) if "f16" in f["file"].lower()})
    L = ["* **Evaluation data and the measurement.** Data files this program opened (name, when; the measured window closes at %.1f s after the server started):" % ev.get("measured_window_closes_at_s", float("nan"))]
    for (name, when), t in sorted(seen.items(), key=lambda kv: kv[1]):
        L.append("  * `%s`: %s (%.1f s)" % (name, when, t))
    L.append("  * Saved evaluation vectors (`Q4_K_M_prefix.npy`) and the saved predictions are used only to compare results; the peaks above were read BEFORE any of these comparison steps. FP16 files opened: %s." % (", ".join(f16) if f16 else "none"))
    L.append("  * This program's own memory (resident) when the window closed: %.0f MB; after the comparison step: %.0f MB." % (ev.get("orchestrator_rss_mb_when_window_closed", float("nan")), ev.get("orchestrator_rss_mb_now", float("nan"))))
    return L


def fmt(v, d=1):
    return "n/a" if v is None or (isinstance(v, float) and v != v) else ("%.*f" % (d, v))


# =====================================================================================================================
# probe: do the Windows measurement parts work on this computer?
# =====================================================================================================================
def cmd_capcheck(a):
    """INTERNAL (started by `probe` in a fresh process): put THIS process in a job with a hard cap, then try to allocate more than the cap, once in this
    process and once in a child process. Prints one line starting with CAPCHECK."""
    job = WinJob(limit_mb=a.mb)
    if not job.ok:
        print("CAPCHECK %s" % json.dumps({"job": "unavailable", "why": job.err}))
        return 2

    def try_alloc(mb):
        try:
            buf = bytearray(int(mb) * 2 ** 20)
            buf[::4096] = b"1" * len(buf[::4096])
            del buf
            return True
        except MemoryError:
            return False
    child_code = ("try:\n b=bytearray(%d*2**20); b[::4096]=b'1'*len(b[::4096]); print('ALLOC_OK')\n"
                  "except MemoryError:\n print('ALLOC_BLOCKED')")

    def child_alloc(mb):
        p = subprocess.run([sys.executable, "-c", child_code % mb], capture_output=True, text=True, timeout=120)
        return "ALLOC_OK" in p.stdout, (p.stdout + p.stderr).strip()[:200]
    r = {"job": "ok", "cap_mb": a.mb, "self_50mb_allowed": try_alloc(50), "self_2x_cap_blocked": not try_alloc(2 * a.mb)}
    ok_small, _ = child_alloc(50)
    ok_big, txt = child_alloc(2 * a.mb)
    r["child_50mb_allowed"], r["child_2x_cap_blocked"], r["child_big_output"] = ok_small, (not ok_big), txt
    r["child_in_job"] = None
    print("CAPCHECK %s" % json.dumps(r))
    return 0


def cmd_probe(a):
    ok = True
    print("probe: Python %s, psutil %s, numpy %s, %s" % (platform.python_version(), getattr(psutil, "__version__", "MISSING"), np.__version__, platform.platform()))
    print("ctypes structure sizes (must be 64 / 48 / 144): %d / %d / %d" % (ctypes.sizeof(_BASIC), ctypes.sizeof(_IO), ctypes.sizeof(_EXT)))
    if psutil is None:
        print("FAIL: psutil is missing. Run:  pip install psutil")
        return 1
    job = WinJob(limit_mb=None)
    print("job object:", "OK" if job.ok else "NOT AVAILABLE (%s)" % job.err)
    code = "import time; a=bytearray(200*2**20); a[::4096]=b'1'*len(a[::4096]); time.sleep(4)"
    child = subprocess.Popen([sys.executable, "-c", code])
    smp = Sampler(0.05)
    smp.start()
    time.sleep(3.5)
    smp.stop()
    mx = max((s[2] for s in smp.series), default=0) / MB
    print("child process holding 200 MB: sampled child working set peak = %.0f MB  %s" % (mx, "OK" if 150 < mx < 400 else "UNEXPECTED"))
    ok &= 150 < mx < 400
    print("OS peak working set of the child (peak_wset / VmHWM): %s MB" % fmt(os_peak_ws_mb(child.pid), 0))
    print("OS peak commit of the child (peak_pagefile; Windows only): %s MB" % fmt(os_peak_commit_mb(child.pid), 0))
    pk = job.peaks_mb()
    print("job peak commit (all processes together): %s" % (("%.0f MB" % pk["peak_job_commit_mb"]) if pk else "not available"))
    if job.ok:
        ok &= bool(pk) and pk["peak_job_commit_mb"] > 150
    child.wait()
    if os.name == "nt":
        cp = subprocess.run([sys.executable, str(Path(__file__).resolve()), "capcheck", "--mb", "400"], capture_output=True, text=True, timeout=180)
        line = next((l for l in cp.stdout.splitlines() if l.startswith("CAPCHECK ")), None)
        if line is None:
            print("memory cap check: FAILED to run:", (cp.stdout + cp.stderr).strip()[:300])
            ok = False
        else:
            cr = json.loads(line[len("CAPCHECK "):])
            if cr.get("job") != "ok":
                print("memory cap check: job object unavailable (%s)" % cr.get("why"))
                ok = False
            else:
                good = cr["self_50mb_allowed"] and cr["self_2x_cap_blocked"] and cr["child_50mb_allowed"] and cr["child_2x_cap_blocked"]
                print("memory cap check (cap %d MB): the program itself: 50 MB allowed=%s, %d MB blocked=%s; a CHILD process: 50 MB allowed=%s, %d MB blocked=%s  %s"
                      % (cr["cap_mb"], cr["self_50mb_allowed"], 2 * cr["cap_mb"], cr["self_2x_cap_blocked"], cr["child_50mb_allowed"], 2 * cr["cap_mb"], cr["child_2x_cap_blocked"], "OK" if good else "CAP DOES NOT WORK AS EXPECTED"))
                ok &= good
    else:
        print("memory cap check: skipped (Windows only)")
    gp = gpu_facts()
    print("nvidia-smi:", ("%s, %.0f of %.0f MB used" % (gp["name"], gp["used_mb"], gp["total_mb"])) if gp.get("available") else "not available (%s) - fine on a PC without NVIDIA" % gp.get("why"))
    wf = windows_facts()
    print("PowerShell system facts:", "OK (cpu: %s)" % wf.get("cpu") if wf.get("available") else "not available (%s)" % wf.get("why"))
    if os.name == "nt":
        tp = PagingProbe(a.tmp or ".")
        tp.start()
        time.sleep(4)
        tp.stop()
        st = tp.stats(0, time.time() + 10)
        print("typeperf counters:", "OK (%d rows)" % st.get("rows_in_window", 0) if st.get("available") else "not available (%s)" % st.get("why"))
    print("")
    print("PROBE RESULT:", "all parts that matter work" if ok else "SOME PARTS FAILED - send this text to Claude/ChatGPT before the real run")
    return 0 if ok else 1


# =====================================================================================================================
# run
# =====================================================================================================================
def cmd_run(a):
    if psutil is None:
        sys.exit("psutil is missing. Run:  pip install psutil")
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    warnings = []
    root = Path(a.root).resolve()
    EVAL_OPENS = []                                                       # (perf_counter time, path) of every data file opened that is not the model or a Python file

    def _audit_hook(event, args):
        if event == "open":
            try:
                pth = str(args[0])
            except Exception:
                return
            pl_ = pth.replace("\\", "/").lower()
            if "site-packages" in pl_ or "dist-info" in pl_ or "/pip/" in pl_:
                return
            if pl_.endswith((".npy", ".npz", ".csv", ".jsonl", ".json")) or "f16" in pl_:
                EVAL_OPENS.append((time.perf_counter(), pth))
    sys.addaudithook(_audit_hook)
    rd = find_repair_dir(a.repair_dir, root)
    t_begin = time.time()
    res = {"label": a.label, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "command_line": " ".join(sys.argv), "status": "STARTED"}
    folded = Path(a.folded).resolve()

    # ---------------------------------------------------------------- job object first, so that every later process is inside it
    job = WinJob(limit_mb=a.job_limit_mb)
    if a.job_limit_mb and not job.ok:
        sys.exit("A memory cap was requested (--job-limit-mb) but the Windows Job Object is not available: %s" % job.err)
    if not job.ok and os.name == "nt":
        warnings.append("Job Object not available (%s): the 'all processes together' commit peak is missing." % job.err)

    # ---------------------------------------------------------------- study code (read only). The vector pins are skipped on purpose: this program never opens an FP16 file.
    os.environ["EDGESAR_ROOT"] = str(root)
    sys.path.insert(0, str(root / "edgesar_shield"))
    from shield import paths
    skipped = [k for k in list(paths.PINS) if k.startswith("edgesar_heads/features/")]
    for k in skipped:
        paths.PINS.pop(k)
    bad = paths.check_pins(root)
    if bad:
        sys.exit("Input check failed:\n  " + "\n  ".join(bad))
    from types import SimpleNamespace
    from shield import data
    from shield.alloc import make_allocator
    from shield.candidates import pilot
    from shield.episodes import EPISODE_REPORTS, make_episodes
    from shield.policy import CommitPolicy
    from shield.service import Service
    from shield.sim import Sim, SimConfig
    pc, pb = pilot()

    class TimedSim(Sim):
        """The study's simulator, unchanged, plus a stopwatch from 'the report is handled' to 'the plan that follows its table update is ready'
        (the policy decision, the table update and the allocator replan; events that fall in between, if any, are included)."""

        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.plan_lat = []
            self._cur = None
            self._apply_pending = False

        def _on_report(self, t, ev, policy, oracle):
            self._cur = {"case_id": ev.case_id, "t0": time.perf_counter(), "alloc0": self.engine_alloc.ms + self.policy_alloc.ms}
            self._apply_pending = False
            super()._on_report(t, ev, policy, oracle)
            self._cur["t_decided"] = time.perf_counter()

        def _on_apply(self, t, ns, table, t_ref):
            super()._on_apply(t, ns, table, t_ref)
            self._apply_pending = True

        def _replan(self, now):
            super()._replan(now)
            c = self._cur
            if c is not None and self._apply_pending and "t_decided" in c:
                t1 = time.perf_counter()
                self.plan_lat.append({"case_id": c["case_id"], "report_to_plan_ms": (t1 - c["t0"]) * 1e3, "decision_ms": (c["t_decided"] - c["t0"]) * 1e3,
                                      "after_decision_ms": (t1 - c["t_decided"]) * 1e3, "allocator_ms_in_window": self.engine_alloc.ms + self.policy_alloc.ms - c["alloc0"]})
                self._cur = None
                self._apply_pending = False

    cases = data.load_cases()
    byid = {c["id"]: c for c in cases}
    idxB = [k for k, c in enumerate(cases) if c["style"] == "B"]
    assert len(idxB) == 400
    heads_cfg = json.loads((root / "edgesar_heads" / "heads_config.json").read_text(encoding="utf-8"))
    assert heads_cfg["prompt_id"] == PROMPT_ID and heads_cfg["prefix_text"] == PREFIX_TEXT, "prompt settings differ from the saved vectors"

    # ---------------------------------------------------------------- folded classifier (the only trained thing at run time)
    man = json.loads((folded / "folded_manifest.json").read_text(encoding="utf-8"))
    z = np.load(folded / "folded_q4.npz")
    arrs = {k: z[k] for k in z.files}
    if arrays_sha256(arrs) != man["arrays_sha256"]:
        sys.exit("folded_q4.npz does not match folded_manifest.json")
    if not man.get("all_checks_pass") and not a.allow_unchecked:
        sys.exit("folded_manifest.json says the export check did not pass; refusing (use --allow-unchecked only for tests)")
    W, b = arrs[a.classifier + "_W"], arrs[a.classifier + "_b"]
    dtype = np.float32 if a.dtype == "float32" else np.float64

    # ---------------------------------------------------------------- facts before the run
    res["system_before"] = {"python": platform.python_version(), "numpy": np.__version__, "psutil": psutil.__version__, "platform": platform.platform(),
                            "machine": platform.machine(), "logical_cpus": os.cpu_count(), "physical_cpus": psutil.cpu_count(logical=False),
                            "ram_total_mb": psutil.virtual_memory().total / MB, "ram_available_mb": psutil.virtual_memory().available / MB,
                            "swap_or_pagefile_total_mb": psutil.swap_memory().total / MB, "swap_or_pagefile_used_mb": psutil.swap_memory().used / MB,
                            "windows": windows_facts(), "gpu": gpu_facts()}
    try:
        bat = psutil.sensors_battery()
        res["system_before"]["on_battery"] = None if bat is None else (not bat.power_plugged)
    except Exception:
        pass
    if res["system_before"]["gpu"].get("available"):
        res["system_before"]["gpu_used_mb_before"] = res["system_before"]["gpu"]["used_mb"]
    model = Path(a.model).resolve()
    msz = model.stat().st_size
    res["model"] = {"path": str(model), "bytes": msz, "bytes_expected": Q4_BYTES, "size_ok": msz == Q4_BYTES}
    if not a.skip_model_hash:
        print("hashing the model file (a few seconds) ...", flush=True)
        res["model"]["sha256"] = sha256_file(model)
        res["model"]["sha256_expected"] = Q4_SHA256
        res["model"]["sha256_ok"] = res["model"]["sha256"] == Q4_SHA256
        if not res["model"]["sha256_ok"]:
            sys.exit("The model file is not the audited Q4_K_M file (SHA-256 differs). Refusing this benchmark; keep the original model and report the mismatch.")
    rc, vtxt = run_text([str(Path(a.server)), "--version"], 60)
    res["server_version_text"] = " ".join(vtxt.split())[:300]

    # ---------------------------------------------------------------- episodes (same as the wording-shift check: style B, level, arrival seed)
    ds = SimpleNamespace(cases=cases)
    eps_all = make_episodes(ds, idxB, a.level, a.seed * 1000, EPISODE_REPORTS)
    eps = eps_all[:a.episodes]
    rep_ids = [ev.case_id for e in eps for ev in e.events]
    warm_ids = [cases[k]["id"] for k in idxB[:2]]

    saved = load_saved_keys(rd / "out2" / "predictions.csv", ARM_SAVED[a.classifier])
    if len(saved) != 400 or not set(rep_ids).issubset(saved):
        sys.exit("Saved predictions do not cover the 400 style-B reports for arm %s; refusing incomplete comparison." % ARM_SAVED[a.classifier])

    # ---------------------------------------------------------------- which switch gives "weights in private memory" on THIS llama-server build
    nommap_flags = None
    if a.no_mmap:
        try:
            nommap_flags, nommap_help = nommap_args(a.server)
        except RuntimeError as e:
            sys.exit(str(e))
        res["no_mmap_switch"] = {"arguments": nommap_flags, "help_excerpt": nommap_help}
        print("weights in private memory: using", " ".join(nommap_flags), flush=True)
    if a.ngl:
        warnings.append("DIAGNOSTIC RUN: -ngl %d (layers on the GPU) is not CPU-only. Do not quote these numbers as deployment results." % a.ngl)

    # ---------------------------------------------------------------- start everything that measures
    orch_baseline_mb = psutil.Process().memory_info().rss / MB
    paging = PagingProbe(out)
    paging.start()
    sampler = Sampler(a.sample_ms / 1000.0)
    sampler.start()
    T = {}
    srv = Server(a.server, model, a.port, a.ctx, a.threads, a.batch, a.ubatch, a.no_mmap, a.extra_arg or [], out / "server.log", a.keep_gpu_visible, a.ngl, nommap_flags)
    res["server_command"] = " ".join(srv.cmd)
    pipe = svc = None
    live_res = []
    sim_error = None
    try:
        T["server_start"] = time.perf_counter()
        T["server_start_epoch"] = time.time()
        try:
            res["server_load_s"] = srv.start()
        except RuntimeError as e:
            res["status"] = "SERVER_FAILED_TO_START"
            res["error"] = str(e)
            raise
        T["ready"] = time.perf_counter()
        T["ready_epoch"] = time.time()
        if job.ok:
            res["job_membership"] = {"this_program_in_job": job.contains(os.getpid()), "llama_server_in_job": job.contains(srv.proc.pid)}
            if not all(v is True for v in res["job_membership"].values()):
                message = "Job Object membership is not confirmed for every process (%s): the cap and the job peak may not cover llama-server." % json.dumps(res["job_membership"])
                if a.job_limit_mb:
                    raise RuntimeError(message)
                warnings.append(message)
        try:
            _, props = http_json(srv.base + "/props", None, 30)
            res["server_props"] = {"build_info": props.get("build_info"), "n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx"), "total_slots": props.get("total_slots")}
        except Exception as e:
            res["server_props"] = {"error": str(e)}
        res["gpu_after_ready"] = gpu_facts()
        if a.ngl:
            g0, g1 = res["system_before"].get("gpu", {}), res["gpu_after_ready"]
            if g0.get("available") and g1.get("available"):
                grew = g1["used_mb"] - g0["used_mb"]
                res["gpu_memory_growth_mb"] = grew
                if grew < 300:
                    warnings.append("GPU NOT USED: GPU memory grew by only %.0f MB after the server was ready although -ngl %d was requested. This run is a CPU run. Do not read it as a GPU result." % (grew, a.ngl))
            else:
                warnings.append("GPU use could not be checked (nvidia-smi not available).")
        client = EmbedClient(srv.base)
        pipe = LivePipeline(pc, pb, client, W, b, dtype)
        svc = LiveService(byid, pipe)
        # warm-up (counted inside the memory window, excluded from the latency statistics)
        tw = time.perf_counter()
        v1, ntok1 = client.embed(pc.build_prompt(byid[warm_ids[0]], PROMPT_ID) + PREFIX_TEXT)
        res["first_request_ms"] = (time.perf_counter() - tw) * 1e3
        v2, _ = client.embed(pc.build_prompt(byid[warm_ids[0]], PROMPT_ID) + PREFIX_TEXT)
        res["same_prompt_twice_max_abs_diff"] = float(np.abs(v1 - v2).max())
        client.embed(pc.build_prompt(byid[warm_ids[1]], PROMPT_ID) + PREFIX_TEXT)
        T["warm_done"] = time.perf_counter()
        # ---------------- the measured mission run
        sim = TimedSim(make_allocator("cbba_bounded"), SimConfig(audit_gold_plan=bool(a.keep_evaluation_audit)))
        T["run_start"] = time.perf_counter()
        T["run_start_epoch"] = time.time()
        done = 0
        for ei, e in enumerate(eps):
            te0 = time.perf_counter()
            r = sim.run(e, CommitPolicy(svc), "live")
            live_res.append(r)
            done += len(r["log"]["reports"])
            el = time.perf_counter() - T["run_start"]
            print("episode %d/%d done; %d/%d reports; %.1f s per report; about %.0f s left" % (ei + 1, len(eps), done, len(rep_ids), el / done, el / done * (len(rep_ids) - done)), flush=True)
        T["run_end"] = time.perf_counter()
        T["run_end_epoch"] = time.time()
        res["gpu_after_run"] = gpu_facts()
        # ---------------- read the OS peak counters while every process is still alive
        me = psutil.Process()
        kids = me.children(recursive=True)
        res["os_peaks"] = {"orchestrator": {"pid": me.pid, "peak_ws_mb": os_peak_ws_mb(me.pid), "peak_commit_mb": os_peak_commit_mb(me.pid)},
                           "children": [{"pid": c.pid, "name": c.name(), "peak_ws_mb": os_peak_ws_mb(c.pid), "peak_commit_mb": os_peak_commit_mb(c.pid)} for c in kids]}
        try:
            res["server_page_faults_total"] = int(sum(getattr(c.memory_info(), "num_page_faults", 0) or 0 for c in kids))
        except Exception:
            pass
        res["job_peaks"] = job.peaks_mb()
        T["measure_end"] = time.perf_counter()
        T["measure_end_epoch"] = time.time()
    except Exception as e:
        if "error" not in res:
            res["status"] = "FAILED_DURING_RUN"
            res["error"] = "%s: %s" % (type(e).__name__, e)
        sim_error = e
    finally:
        sampler.stop()
        paging.stop()
        res["server_log_scan"] = scan_server_log(srv.log_text())
        res["job_peaks_final"] = job.peaks_mb()
        srv.stop()
    T.setdefault("measure_end", time.perf_counter())
    T.setdefault("measure_end_epoch", time.time())
    rss_at_window_end = psutil.Process().memory_info().rss / MB

    def evaluation_files_summary():
        """Which data files were opened, and was it before the measurement window closed (they would then be part of the measured memory)?"""
        t_ref = T.get("server_start", T["measure_end"])
        files = []
        for tt, pth in EVAL_OPENS:
            if "typeperf" in pth.lower() or pth.lower().endswith("server.log"):
                continue
            try:
                if Path(pth).resolve().is_relative_to(out.resolve()):          # files this program WRITES into the output folder are not inputs
                    continue
            except Exception:
                pass
            where = "before the server started" if tt < t_ref else ("during the measured window" if tt <= T["measure_end"] else "AFTER the measured window closed")
            files.append({"file": pth, "seconds_after_server_start": tt - t_ref, "when": where})
        return {"measured_window_closes_at_s": T["measure_end"] - t_ref, "files": files,
                "orchestrator_rss_mb_when_window_closed": rss_at_window_end, "orchestrator_rss_mb_now": psutil.Process().memory_info().rss / MB}

    # ---------------------------------------------------------------- memory results
    t0m, t1m = T["server_start"] - 1.0, T["measure_end"]
    mem = {"orchestrator_baseline_after_imports_mb": orch_baseline_mb, "sampler_interval_ms": a.sample_ms, "samples": len(sampler.series), "sampler_errors": sampler.errors}
    mem["combined_ws_peak_sampled_mb_whole_run"] = sampler.combined_peak_between(t0m, t1m, True)
    mem["combined_private_peak_sampled_mb_whole_run"] = sampler.combined_peak_between(t0m, t1m, False)
    mem["server_ws_peak_sampled_mb_whole_run"] = sampler.peak_between(t0m, t1m, 2)
    mem["orchestrator_ws_peak_sampled_mb_whole_run"] = sampler.peak_between(t0m, t1m, 1)
    mem["server_private_peak_sampled_mb_whole_run"] = sampler.peak_between(t0m, t1m, 4)
    if "ready" in T:
        mem["server_ws_at_ready_mb"] = next((s[2] / MB for s in sampler.series if s[0] >= T["ready"]), None)
        mem["server_ws_peak_load_phase_mb"] = sampler.peak_between(t0m, T["ready"], 2)
    if "run_start" in T and "run_end" in T:
        mem["combined_ws_peak_sampled_mb_steady"] = sampler.combined_peak_between(T["run_start"], T["run_end"], True)
        mem["combined_private_peak_sampled_mb_steady"] = sampler.combined_peak_between(T["run_start"], T["run_end"], False)
        mem["system_available_min_mb_steady"] = sampler.min_available_between(T["run_start"], T["run_end"])
        mem["system_available_min_mb_whole_run"] = sampler.min_available_between(t0m, t1m)
    peaks = res.get("os_peaks")
    if peaks:
        parts = [peaks["orchestrator"]["peak_ws_mb"]] + [c["peak_ws_mb"] for c in peaks["children"]]
        mem["sum_of_os_peak_ws_mb"] = float(sum(p for p in parts if p is not None)) if all(p is not None for p in parts) else None
        mem["orchestrator_os_peak_ws_mb"] = peaks["orchestrator"]["peak_ws_mb"]
        mem["server_os_peak_ws_mb"] = float(sum(c["peak_ws_mb"] for c in peaks["children"] if c["peak_ws_mb"] is not None))
        cparts = [peaks["orchestrator"]["peak_commit_mb"]] + [c["peak_commit_mb"] for c in peaks["children"]]
        mem["sum_of_os_peak_commit_mb"] = float(sum(p for p in cparts if p is not None)) if cparts and all(p is not None for p in cparts) else None
    jp = res.get("job_peaks") or res.get("job_peaks_final")
    mem["job_peak_commit_mb"] = jp["peak_job_commit_mb"] if jp else None
    mem["job_limit_mb"] = a.job_limit_mb
    mem["process_names_seen"] = sorted(set(sampler.pid_name.values()))
    res["memory"] = mem
    with open(out / "memory_series.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seconds_since_server_start", "orchestrator_ws_mb", "server_ws_mb", "orchestrator_private_mb", "server_private_mb", "system_available_mb", "children"])
        last = -9
        for s in sampler.series:
            if s[0] - last >= 0.5:
                last = s[0]
                w.writerow(["%.2f" % (s[0] - T.get("server_start", t0m)), "%.1f" % (s[1] / MB), "%.1f" % (s[2] / MB), "%.1f" % (s[3] / MB), "%.1f" % (s[4] / MB), "%.0f" % (s[5] / MB), s[6]])

    # ---------------------------------------------------------------- paging
    if "run_start_epoch" in T:
        res["paging_steady"] = paging.stats(T["run_start_epoch"], T.get("run_end_epoch", T["measure_end_epoch"]))
        res["paging_whole_run"] = paging.stats(T["server_start_epoch"], T["measure_end_epoch"])
    res["system_after"] = {"ram_available_mb": psutil.virtual_memory().available / MB, "swap_or_pagefile_used_mb": psutil.swap_memory().used / MB, "windows": windows_facts(), "gpu": gpu_facts()}

    # ---------------------------------------------------------------- if the run did not finish, say so and stop here
    if res["status"] in ("SERVER_FAILED_TO_START", "FAILED_DURING_RUN") or not live_res:
        res["warnings"] = warnings
        res["evaluation_files_opened"] = evaluation_files_summary()
        write_outputs(out, res, a, [], None, None)
        print("\nRUN DID NOT FINISH: %s\n%s\nReport written to %s" % (res["status"], res.get("error"), out / "DEPLOYMENT_REPORT.md"))
        return 3
    res["status"] = "FINISHED"

    # ---------------------------------------------------------------- latency (steady state only: the warm-up requests are not in pipe.rows' episodes)
    rows = []
    for r in live_res:
        for rep in r["log"]["reports"]:
            lr = pipe.rows[rep["case_id"]]
            rows.append(dict(lr, decision_wall_ms=rep["wall_ms"], allocator_runs=rep["runs"], other_ms=rep["wall_ms"] - lr["live_ms"], episode=r["episode"]))
    # allocator planning time: the study's own timer around EVERY allocator run (replans after events + runs a policy asks for)
    ep_alloc = []
    for r in live_res:
        lg = r["log"]
        n_rep = len(lg["reports"])
        tot_ms = float(lg.get("engine_alloc_ms", 0.0)) + float(lg.get("policy_alloc_ms", 0.0))
        tot_runs = int(lg.get("engine_runs", 0)) + int(lg.get("policy_runs", 0))
        ep_alloc.append({"episode": r["episode"], "reports": n_rep, "allocator_runs": tot_runs, "allocator_ms_total": tot_ms,
                         "engine_runs": int(lg.get("engine_runs", 0)), "engine_ms": float(lg.get("engine_alloc_ms", 0.0)),
                         "policy_runs": int(lg.get("policy_runs", 0)), "policy_ms": float(lg.get("policy_alloc_ms", 0.0)),
                         "ms_per_run": tot_ms / max(tot_runs, 1), "ms_per_report": tot_ms / max(n_rep, 1), "eval_runs_not_counted": int(lg.get("eval_runs", 0))})
    res["allocator_timing"] = {
        "episodes": ep_alloc,
        "runs_total": sum(x["allocator_runs"] for x in ep_alloc), "ms_total": sum(x["allocator_ms_total"] for x in ep_alloc),
        "reports_total": sum(x["reports"] for x in ep_alloc),
        "ms_per_run_mean": sum(x["allocator_ms_total"] for x in ep_alloc) / max(sum(x["allocator_runs"] for x in ep_alloc), 1),
        "ms_per_run_episode_means": lat_stats([x["ms_per_run"] for x in ep_alloc]),
        "ms_per_report_episode_values": lat_stats([x["ms_per_report"] for x in ep_alloc]),
        "policy_runs_total": sum(x["policy_runs"] for x in ep_alloc),
        "evaluation_audit_runs_not_counted": sum(x["eval_runs_not_counted"] for x in ep_alloc),
        "evaluation_audit_on": bool(a.keep_evaluation_audit),
        "note": ("Allocator = the study's bounded CBBA, run in this program (same process as the classifier). 'ms per report' = all allocator time in an episode divided by its reports. "
                 "The always-commit policy asks for 0 allocator runs inside the decision; the planning happens in the replans after each event (including the table update after a report)."),
    }
    res["allocator_timing"]["ms_per_report_mean"] = res["allocator_timing"]["ms_total"] / max(res["allocator_timing"]["reports_total"], 1)
    res["latency_ms"] = {k: lat_stats([x[k] for x in rows]) for k in ("embed_ms", "live_ms", "decision_wall_ms", "other_ms", "build_ms", "assemble_ms", "classifier_us")}
    # MEASURED: from the moment a report is handled to the moment the plan after its table update is ready (stopwatch in TimedSim)
    pl = {x["case_id"]: x for x in sim.plan_lat}
    res["reports_with_plan_stopwatch"] = len(pl)
    if len(pl) != len(rows):
        warnings.append("Report-to-plan stopwatch has %d of %d reports (a report whose table update was not followed by a replan is missing)." % (len(pl), len(rows)))
    res["latency_ms"]["report_to_plan_ms"] = lat_stats([x["report_to_plan_ms"] for x in pl.values()])
    res["latency_ms"]["plan_allocator_ms_in_window"] = lat_stats([x["allocator_ms_in_window"] for x in pl.values()])
    res["latency_ms"]["plan_after_decision_ms"] = lat_stats([x["after_decision_ms"] for x in pl.values()])
    if a.keep_evaluation_audit:
        warnings.append("The study's evaluation-only plan audit was ON: the report-to-plan times include its extra allocator runs. Do not quote them.")
    with open(out / "report_to_plan.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "report_to_plan_ms", "decision_ms", "after_decision_ms", "allocator_ms_in_window"])
        for x in sim.plan_lat:
            w.writerow([x["case_id"], "%.3f" % x["report_to_plan_ms"], "%.3f" % x["decision_ms"], "%.3f" % x["after_decision_ms"], "%.3f" % x["allocator_ms_in_window"]])
    res["latency_ms"]["prompt_tokens"] = lat_stats([x["prompt_tokens"] for x in rows if x["prompt_tokens"]])
    res["latency_ms"]["embed_tokens_per_s_mean"] = float(np.mean([x["prompt_tokens"] / (x["embed_ms"] / 1e3) for x in rows if x["prompt_tokens"]]))
    res["reports_measured"] = len(rows)
    res["run_seconds"] = T["run_end"] - T["run_start"]
    res["max_prompt_tokens"] = max([x["prompt_tokens"] or 0 for x in rows])
    if res["max_prompt_tokens"] and res["max_prompt_tokens"] > a.ctx:
        warnings.append("A prompt had %d tokens but the context is %d: the server may have truncated it." % (res["max_prompt_tokens"], a.ctx))

    # ---------------------------------------------------------------- agreement with the SAVED predictions (outside the measured window)
    ids = [x["id"] for x in rows]
    sv = {i: saved.get(i) for i in ids}
    live = {x["id"]: x["key"] for x in rows}
    agree = {"reports": len(ids), "saved_arm": ARM_SAVED[a.classifier], "reports_with_saved_row": sum(1 for i in ids if sv[i] is not None)}
    agree["record_equal"] = sum(1 for i in ids if sv[i] == live[i])
    agree["action_equal"] = sum(1 for i in ids if sv[i] is not None and sv[i][0] == live[i][0])
    both_rec = [i for i in ids if sv[i] is not None and sv[i][3] is not None and live[i][3] is not None]
    agree["sensor_equal_where_both_record_actions"] = "%d of %d" % (sum(1 for i in both_rec if sv[i][3] == live[i][3]), len(both_rec))
    agree["priority_equal_where_both_record_actions"] = "%d of %d" % (sum(1 for i in both_rec if sv[i][4] == live[i][4]), len(both_rec))
    # head-level (argmax of each head) agreement with the folded classifier applied to the SAVED vector
    vec_path = root / "edgesar_heads" / "features" / "Q4_K_M_prefix.npy"
    cos_info, drift = {}, None
    if vec_path.exists() and not a.no_saved_vectors:
        case_ids = json.loads((root / "edgesar_heads" / "features" / "case_ids.json").read_text(encoding="utf-8"))
        pos = {cid: k for k, cid in enumerate(case_ids)}
        SV = np.load(vec_path, mmap_mode="r")
        LV = np.stack([pipe.rows[i]["vec"] for i in ids])
        S = np.stack([np.asarray(SV[pos[i]], dtype=np.float32) for i in ids])
        cs = (LV * S).sum(1) / (np.linalg.norm(LV, axis=1) * np.linalg.norm(S, axis=1))
        cos_info = {"min": float(cs.min()), "median": float(np.median(cs)), "mean": float(cs.mean()), "n_below_0.999": int((cs < 0.999).sum()),
                    "max_abs_component_diff": float(np.abs(LV - S).max()), "note": "live CPU Q4 vector vs the saved GPU Q4 vector of the same report"}
        LL = np.stack([pipe.rows[i]["logits"] for i in ids])
        SL = (S.astype(np.float64) @ W.astype(np.float64).T + b.astype(np.float64))
        drift = {"max_abs_logit_diff_live_vs_saved_vector": float(np.abs(LL - SL).max()), "median_abs_logit_diff": float(np.median(np.abs(LL - SL)))}
        np.save(out / "live_vectors_q4_prefix.npy", LV.astype(np.float32))
    res["vector_agreement"] = cos_info
    res["logit_drift"] = drift
    dis = [i for i in ids if sv[i] != live[i]]
    agree["disagreements"] = len(dis)
    with open(out / "disagreements.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "saved_key", "live_key", "live_action_margin", "live_sensor_margin", "live_priority_margin"])
        for i in dis:
            L = pipe.rows[i]["logits"]
            m = lambda v: float(np.sort(v)[-1] - np.sort(v)[-2])     # noqa: E731
            w.writerow([i, sv[i], live[i], "%.4f" % m(L[0:4]), "%.4f" % m(L[4:7]), "%.4f" % m(L[7:10])])
    res["agreement"] = agree

    # ---------------------------------------------------------------- mission-level agreement: replay the SAVED records through the same episodes
    cands, hier, conf = {}, {}, {}
    for i in ids:
        k = sv[i]
        if k is None:
            continue
        nm = {c: v for c, v in zip(KEYCOLS, k) if v is not None}
        c = {"key": pc.strict_key(nm), "norm": nm, "score": 1.0}
        cands[i], hier[i], conf[i] = [c], c, 1.0
    saved_svc = Service(cands, hier, conf)
    sim2 = Sim(make_allocator("cbba_bounded"), SimConfig(audit_gold_plan=bool(a.keep_evaluation_audit)))
    eq_ep = 0
    tot = {"live": [0, 0], "saved": [0, 0]}
    for e, rl in zip(eps, live_res):
        rs = sim2.run(e, CommitPolicy(saved_svc), "saved")
        cl, cs_ = rl["counts"], rs["counts"]
        eq_ep += int(cl == cs_)
        for nm_, c_ in (("live", cl), ("saved", cs_)):
            tot[nm_][0] += c_["late"] + c_["unverified"]
            tot[nm_][1] += c_["n"]
    res["mission_interpretation"] = "Replay checks decision consistency. Measured CPU inference wall time is NOT injected as simulated mission delay; these counts do not validate real-time mission performance."
    res["mission"] = {"level": a.level, "arrival_seed": a.seed, "episodes": len(eps), "reports": len(ids), "episodes_with_identical_counts": eq_ep,
                      "missed_incidents_live": tot["live"][0], "missed_incidents_saved_replay": tot["saved"][0], "incidents": tot["live"][1],
                      "missed_share_live": tot["live"][0] / max(tot["live"][1], 1), "missed_share_saved_replay": tot["saved"][0] / max(tot["saved"][1], 1)}
    warnings.append(res["mission_interpretation"])
    res["warnings"] = warnings
    res["seconds_total"] = time.time() - t_begin
    res["evaluation_files_opened"] = evaluation_files_summary()
    write_outputs(out, res, a, rows, W, b)
    print("\nDone. Report: %s" % (out / "DEPLOYMENT_REPORT.md"))
    return 0


# =====================================================================================================================
# outputs
# =====================================================================================================================
def write_outputs(out, res, a, rows, W, b):
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        return o
    (out / "results.json").write_text(json.dumps(clean(res), indent=1, default=str), encoding="utf-8")
    if rows:
        with open(out / "per_report.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["episode", "case_id", "prompt_tokens", "build_ms", "embed_ms", "classifier_us", "assemble_ms", "live_ms", "decision_wall_ms", "allocator_runs", "other_ms", "record_key"])
            for r in rows:
                w.writerow([r["episode"], r["id"], r["prompt_tokens"], "%.3f" % r["build_ms"], "%.2f" % r["embed_ms"], "%.1f" % r["classifier_us"], "%.3f" % r["assemble_ms"],
                            "%.2f" % r["live_ms"], "%.2f" % r["decision_wall_ms"], r["allocator_runs"], "%.2f" % r["other_ms"], r["key"]])
    mem = res.get("memory", {})
    sb = res.get("system_before", {})
    wf = sb.get("windows", {}) if isinstance(sb.get("windows"), dict) else {}
    L = ["# Deployment benchmark of the Q4 system: %s" % res.get("label", ""), "",
         "Status: **%s**. %s" % (res["status"], ("Error: " + res["error"]) if res.get("error") else ""),
         "This report gives MEASURED NUMBERS for this computer under this test. It does **not** say that a 2 GB device passes (see section 7).", "",
         "## 1. What was run", "",
         "* Command: `%s`" % res.get("command_line", ""),
         "* llama-server command: `%s` (environment: CUDA_VISIBLE_DEVICES=%s)" % (res.get("server_command", ""), "-1" if not a.keep_gpu_visible else "unchanged"),
         "* Context length requested %d, batch %d, ubatch %d, threads %d, weights %s, classifier `%s` (%s), mission level %s, arrival seed %d, %d episodes."
         % (a.ctx, a.batch, a.ubatch, a.threads, ("loaded into private memory (`%s`, chosen from this llama-server's own --help)" % " ".join(res.get("no_mmap_switch", {}).get("arguments", []))) if a.no_mmap else "memory-mapped from the file (llama.cpp default)", a.classifier, a.dtype, a.level, a.seed, a.episodes),
         "* Server says: %s" % json.dumps(res.get("server_props", {})),
         "* Model file: %s, %s bytes, SHA-256 %s (%s)" % (res.get("model", {}).get("path"), res.get("model", {}).get("bytes"), (res.get("model", {}).get("sha256") or "not checked")[:16], "audited file" if res.get("model", {}).get("sha256_ok") else "NOT confirmed"),
         "* Software: Python %s, numpy %s, psutil %s, %s. llama-server `--version`: %s" % (sb.get("python"), sb.get("numpy"), sb.get("psutil"), sb.get("platform"), res.get("server_version_text")),
         "* Computer: %s; %s logical / %s physical CPUs; RAM %s MB total, %s MB free before; pagefile/swap %s MB total, %s MB used before; on battery: %s."
         % (wf.get("cpu", sb.get("machine")), sb.get("logical_cpus"), sb.get("physical_cpus"), fmt(sb.get("ram_total_mb"), 0), fmt(sb.get("ram_available_mb"), 0), fmt(sb.get("swap_or_pagefile_total_mb"), 0), fmt(sb.get("swap_or_pagefile_used_mb"), 0), sb.get("on_battery")),
         "* Folded classifier: 10 x 2048 matrix + 10 bias = 20,490 numbers. FP16 files opened by this program: none (the 4 vector pins of the study code were skipped on purpose; the other 10 pinned files were verified).", ""]
    if res["status"] == "FINISHED":
        la = res["latency_ms"]
        L += ["## 2. Memory (MB). Definitions first", "",
              "* **Working set** = memory resident in RAM (Windows task manager 'memory'); includes memory-mapped model pages. **Private/commit** = memory that must be backed by RAM or pagefile (does not include mapped model file pages).",
              "* **Sampled combined** = largest sum of this program + llama-server seen at one instant (every %d ms; can miss a very short spike). **Sum of OS peaks** = peak of each process added up (an upper bound: the peaks may not coincide). **Job peak** = peak committed memory of all processes together, measured by Windows." % a.sample_ms, "",
              "| Measure | MB |", "|---|---|",
              "| Sum of OS peak working sets (upper bound, all processes) | %s |" % fmt(mem.get("sum_of_os_peak_ws_mb"), 0),
              "| Combined working set, sampled, whole run (load + warm-up + mission) | %s |" % fmt(mem.get("combined_ws_peak_sampled_mb_whole_run"), 0),
              "| Combined working set, sampled, mission phase only | %s |" % fmt(mem.get("combined_ws_peak_sampled_mb_steady"), 0),
              "| Combined private bytes, sampled, whole run | %s |" % fmt(mem.get("combined_private_peak_sampled_mb_whole_run"), 0),
              "| Job peak commit, all processes together (Windows only) | %s |" % fmt(mem.get("job_peak_commit_mb"), 0),
              "| llama-server OS peak working set | %s |" % fmt(mem.get("server_os_peak_ws_mb"), 0),
              "| llama-server private bytes, sampled peak (compare Run A: weights in private memory should add about the model size) | %s |" % fmt(mem.get("server_private_peak_sampled_mb_whole_run"), 0),
              "| This program (orchestrator + study code + scikit-learn imports) OS peak working set | %s |" % fmt(mem.get("orchestrator_os_peak_ws_mb"), 0),
              "| This program after imports, before the server started | %s |" % fmt(mem.get("orchestrator_baseline_after_imports_mb"), 0),
              "| Model file size on disk | %s |" % fmt(res["model"]["bytes"] / MB, 0), "",
              "Memory cap used in this run: %s. Comparison line used in the project: 2048 MB. Largest measured value above: **%s MB** (sum of OS peak working sets), job commit peak %s MB." %
              (("%d MB hard cap on committed memory of all processes (Job Object)" % a.job_limit_mb) if a.job_limit_mb else "none", fmt(mem.get("sum_of_os_peak_ws_mb"), 0), fmt(mem.get("job_peak_commit_mb"), 0)),
              "Job Object membership, asked after the server was ready (Windows only; the cap and the job peak cover only processes inside the job): %s." % json.dumps(res.get("job_membership")),
              "This is a statement about this PC. A 2 GB device also has to hold its operating system and other programs, see section 7.", ""] + eval_lines(res) + [""
              ,
              "## 3. Latency (milliseconds per report; first request and load time are separate)", "",
              "| Part | mean | p50 | p95 | p99 | max |", "|---|---|---|---|---|---|"]
        for k, nm in (("embed_ms", "Q4 forward pass on CPU (prompt -> vector), incl. HTTP"), ("live_ms", "Report to record (prompt build + vector + folded classifier + assembler)"),
                      ("other_ms", "Table update and validation inside the decision (decision time minus the line above; NOT the allocator)"), ("decision_wall_ms", "Whole decision, report arrives -> record committed")):
            s = la[k]
            L.append("| %s | %.1f | %.1f | %.1f | %.1f | %.1f |" % (nm, s["mean"], s["p50"], s["p95"], s["p99"], s["max"]))
        at = res["allocator_timing"]
        L += ["| Allocator planning, per allocator run (study CBBA, all runs of the mission; mean) | %.1f | | | | |" % at["ms_per_run_mean"],
              "| Allocator planning, per report (all allocator time of an episode / its reports; mean of episodes) | %.1f | | | | |" % at["ms_per_report_episode_values"]["mean"],
              ]
        for k, nm in (("plan_after_decision_ms", "After the decision: table update + replan (MEASURED)"), ("plan_allocator_ms_in_window", "  of which allocator planning inside that window (MEASURED)"),
                      ("report_to_plan_ms", "**Report arrives -> record committed -> new plan ready (END TO END, MEASURED)**")):
            s = la[k]
            if "mean" in s:
                L.append("| %s | %.1f | %.1f | %.1f | %.1f | %.1f |" % (nm, s["mean"], s["p50"], s["p95"], s["p99"], s["max"]))
        s = la["classifier_us"]
        L += ["| Folded classifier alone (microseconds) | %.1f | %.1f | %.1f | %.1f | %.1f |" % (s["mean"], s["p50"], s["p95"], s["p99"], s["max"]), "",
              "* Server load time (process start to ready): %.1f s. First request (includes touching the weights): %.0f ms. Same prompt twice: max |difference| of the two vectors = %.2e." % (res.get("server_load_s", float("nan")), res.get("first_request_ms", float("nan")), res.get("same_prompt_twice_max_abs_diff", float("nan"))),
              "* Prompt tokens: mean %.0f, max %d; context %d. Mean prompt speed %.0f tokens/s. %d reports in %.0f s." % (la["prompt_tokens"]["mean"], res["max_prompt_tokens"], a.ctx, la["embed_tokens_per_s_mean"], res["reports_measured"], res["run_seconds"]),
              "* Latency includes a 50 ms memory-sampler thread and a Python HTTP client. Allocator: %d runs in %d reports (%d from policy requests, the rest replans after events); the study's bounded CBBA on 20-report episodes. Evaluation-only audit runs (never part of a deployment): %s (%d runs, not counted above)." % (at["runs_total"], at["reports_total"], at["policy_runs_total"], "ON" if at["evaluation_audit_on"] else "OFF", at["evaluation_audit_runs_not_counted"]), "",
              "## 4. Agreement with the saved predictions", "",
              "Live CPU decisions (Q4 server -> folded `%s` classifier) against the saved style-B records of arm `%s` (made earlier on the GPU, float64, unfolded):" % (a.classifier, res["agreement"]["saved_arm"]), "",
              "| Check | Result |", "|---|---|",
              "| Whole record equal to the saved record | %d of %d |" % (res["agreement"]["record_equal"], res["agreement"]["reports"]),
              "| Action equal | %d of %d |" % (res["agreement"]["action_equal"], res["agreement"]["reports"]),
              "| Sensor equal (where both are record actions) | %s |" % res["agreement"]["sensor_equal_where_both_record_actions"],
              "| Priority equal (where both are record actions) | %s |" % res["agreement"]["priority_equal_where_both_record_actions"]]
        if res.get("vector_agreement"):
            v, d = res["vector_agreement"], res["logit_drift"]
            L += ["| Live CPU vector vs saved GPU vector: cosine min / median | %.6f / %.6f (%d reports below 0.999) |" % (v["min"], v["median"], v["n_below_0.999"]),
                  "| Max |logit difference|, live vs the same classifier on the saved vector | %.3e (median %.3e) |" % (d["max_abs_logit_diff_live_vs_saved_vector"], d["median_abs_logit_diff"])]
        m = res["mission"]
        L += ["", "Mission level (same episodes: level %s, arrival seed %d, %d episodes, %d reports): missed incidents with live records %d of %d (%.2f%%), with the saved records replayed %d of %d (%.2f%%); "
              "%d of %d episodes have identical outcome counts." % (m["level"], m["arrival_seed"], m["episodes"], m["reports"], m["missed_incidents_live"], m["incidents"], 100 * m["missed_share_live"],
                                                                     m["missed_incidents_saved_replay"], m["incidents"], 100 * m["missed_share_saved_replay"], m["episodes_with_identical_counts"], m["episodes"]),
              "Disagreements are listed in `disagreements.csv` with the margin of the live logits (a small margin means a near tie).", ""]
        ps, pw = res.get("paging_steady", {}), res.get("paging_whole_run", {})
        gp0, gp1, gp2 = sb.get("gpu", {}), res.get("gpu_after_ready", {}), res.get("gpu_after_run", {})
        sa = res.get("system_after", {})
        scan = res.get("server_log_scan", {})
        L += ["## 5. Paging conditions", "",
              "* System free RAM: %s MB before the run, lowest %s MB during the mission phase (lowest %s MB during the whole run), %s MB after." % (fmt(sb.get("ram_available_mb"), 0), fmt(mem.get("system_available_min_mb_steady"), 0), fmt(mem.get("system_available_min_mb_whole_run"), 0), fmt(sa.get("ram_available_mb"), 0)),
              "* Pagefile/swap in use: %s MB before, %s MB after." % (fmt(sb.get("swap_or_pagefile_used_mb"), 0), fmt(sa.get("swap_or_pagefile_used_mb"), 0)),
              "* Windows pagefile detail before: `%s`; after: `%s`" % (json.dumps(wf.get("pagefile")), json.dumps((sa.get("windows") or {}).get("pagefile"))),
              "* Hard page faults (pages read from disk per second, `Pages Input/sec`): mission phase %s; whole run %s." % (json.dumps({k: v for k, v in ps.items() if k != "source"}), json.dumps({k: v for k, v in pw.items() if k != "source"})),
              "* Page faults of the server process in total (soft and hard): %s." % res.get("server_page_faults_total", "n/a"),
              "* Reading: if free RAM stayed high and `Pages Input/sec` is near zero in the mission phase, the PC was not short of memory, so these peaks are not distorted by paging. This says nothing about a computer that has only 2 GB.", "",
              "## 6. CPU-only evidence", "",
              "* Flags: `-ngl %d`, `CUDA_VISIBLE_DEVICES=%s`. Server log: layers offloaded to GPU = %s; backends loaded = %s; GPU words in log = %s." % (a.ngl, "unchanged" if a.keep_gpu_visible else "-1", scan.get("offloaded_layers"), scan.get("backends_loaded"), scan.get("gpu_words_in_log")),
              "* GPU memory in use (nvidia-smi): before start %s MB, after the server was ready %s MB, after the mission %s MB." % (fmt(gp0.get("used_mb"), 0), fmt(gp1.get("used_mb"), 0), fmt(gp2.get("used_mb"), 0)),
              "* %s" % (("A non-CPU backend was loaded by llama-server (see the log). Use a llama.cpp folder without `ggml-cuda.dll` for the number you quote." if scan.get("non_cpu_backend_loaded")
                         else ("No non-CPU backend line was found in the server log (%d backend lines read)." % len(scan.get("backends_loaded", []))) if scan.get("backends_loaded")
                         else "The server log has no 'load_backend' lines, so the backends could not be checked from the log; read server.log yourself.") if scan else "(server log not scanned)"), ""]
    else:
        L += ["## Run did not finish", "", res.get("error", ""), "", "Memory numbers up to the failure:", "```", json.dumps(clean(mem), indent=1, default=str), "```", ""]
    L += ["## 7. What this report cannot show", "",
          "1. **A 2 GB device is not tested.** The numbers are for this PC. On a 2 GB device the operating system, the file cache and other programs use part of the RAM; the pipeline must fit in what is left, and a Windows PC with 2 GB is a different case from a small Linux board.",
          "2. A Job Object cap limits **committed** memory. With memory-mapped weights the model file pages are not counted by the cap but are counted in the working set; run both `--no-mmap` and the default and read both numbers.",
          "3. CPU speed, thread count and cooling differ on a target device; latency here is for this CPU only.",
          "4. Energy was not measured. Quantisation of the model itself, the offline FP16 alignment preparation and training are not part of this deployment measurement.",
          "5. The orchestrator process also holds the study code (simulator, scikit-learn imports). A stripped-down build would use less; that build was not made or measured.",
          "6. The decisions are for 400 style-B reports of one synthetic dataset; agreement says the pipeline reproduces the saved records, not that the records are good.", ""]
    if res.get("warnings"):
        L += ["## Warnings", ""] + ["* " + w for w in res["warnings"]] + [""]
    (out / "DEPLOYMENT_REPORT.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--tmp", default=".")
    c = sub.add_parser("capcheck")
    c.add_argument("--mb", type=int, default=400)
    r = sub.add_parser("run")
    r.add_argument("--root", required=True, help="workspace folder with edgesar_pilot, edgesar_heads, V1, edgesar_shield")
    r.add_argument("--repair-dir", required=True, help="edgesar_repair_2026-11-14 (for the saved predictions out2\\predictions.csv)")
    r.add_argument("--server", required=True, help="path of llama-server.exe (use a folder WITHOUT ggml-cuda.dll for the final number)")
    r.add_argument("--model", required=True, help="Llama-3.2-1B-Instruct-Q4_K_M.gguf")
    r.add_argument("--folded", default=str(HERE / "folded"), help="folder with folded_q4.npz and folded_manifest.json")
    r.add_argument("--out", required=True)
    r.add_argument("--label", default="run")
    r.add_argument("--classifier", choices=["map", "retrained"], default="map")
    r.add_argument("--dtype", choices=["float32", "float64"], default="float32")
    r.add_argument("--episodes", type=int, default=20, help="mission episodes of 20 reports each (20 = all 400 style-B reports)")
    r.add_argument("--level", choices=["L", "M", "H"], default="M")
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--ctx", type=int, default=4096, help="context length (-c); the saved vectors used 4096")
    r.add_argument("--batch", type=int, default=1024)
    r.add_argument("--ubatch", type=int, default=1024)
    r.add_argument("--threads", type=int, default=6)
    r.add_argument("--no-mmap", action="store_true", help="load the weights into private memory (the program picks the right llama-server switch for its build)")
    r.add_argument("--ngl", type=int, default=0, help="layers on the GPU. Default 0 = CPU only. Only for the diagnostic run.")
    r.add_argument("--job-limit-mb", type=int, default=None, help="Windows only: hard cap on committed memory of all processes of this run")
    r.add_argument("--port", type=int, default=8093)
    r.add_argument("--sample-ms", type=int, default=50)
    r.add_argument("--extra-arg", action="append", help="extra llama-server argument (repeat for several)")
    r.add_argument("--keep-gpu-visible", action="store_true", help="do not set CUDA_VISIBLE_DEVICES=-1")
    r.add_argument("--skip-model-hash", action="store_true")
    r.add_argument("--no-saved-vectors", action="store_true")
    r.add_argument("--keep-evaluation-audit", action="store_true", help="keep the study's evaluation-only plan audit (2 extra allocator runs per report; never part of a deployment). Default: off")
    r.add_argument("--allow-unchecked", action="store_true")
    a = ap.parse_args()
    sys.exit(cmd_probe(a) if a.cmd == "probe" else cmd_capcheck(a) if a.cmd == "capcheck" else cmd_run(a))


if __name__ == "__main__":
    main()
