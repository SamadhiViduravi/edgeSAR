"""Copy only the server executable and DLLs; never recurse into model folders."""
import argparse
import shutil
import subprocess
from pathlib import Path


def excluded(name):
    name = name.lower()
    return any(x in name for x in ("cuda", "cublas", "cufft", "curand", "cusparse", "cusolver", "nvrtc", "nvjit", "vulkan", "sycl", "rocm", "ggml-hip"))


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Source and CPU destination must be different folders.")
    if not (source / "llama-server.exe").is_file():
        raise FileNotFoundError("llama-server.exe was not found in " + str(source))
    files = [p for p in source.iterdir() if p.is_file() and
             (p.name.lower() == "llama-server.exe" or p.suffix.lower() == ".dll") and not excluded(p.name)]
    destination.mkdir(parents=True, exist_ok=True)
    stale = [p.name for p in destination.glob("*.dll") if excluded(p.name)]
    if stale:
        raise ValueError("Use a clean CPU destination; GPU DLLs already present: " + ", ".join(stale))
    required = sum(p.stat().st_size for p in files)
    if shutil.disk_usage(destination).free < required + 100 * 2**20:
        raise OSError("Not enough space for the CPU runtime plus 100 MiB headroom.")
    for p in files:
        shutil.copy2(p, destination / p.name)
    print("Copied %d runtime files (%.1f MiB). No subfolders or model weights copied." % (len(files), required / 2**20))
    return destination / "llama-server.exe"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--destination", required=True)
    args = ap.parse_args()
    server = prepare(args.source, args.destination)
    subprocess.run([str(server), "--version"], check=True)
