"""
Windows-safe launcher for run_ppr.py and run_ppr2.py.

The two runners start their worker processes with "fork", which does not exist on Windows. This launcher runs the same runner in ONE
process instead (no fork, no pool). The runner files themselves are not changed, so their recorded SHA-256 values stay valid.
Every fold has its own fixed seed, so the order of the folds does not change any result.

    python run_serial.py run_ppr.py  --root "D:\\1 Samadhi UNI\\aFYP\\Claude" --out out_laptop
    python run_serial.py run_ppr2.py --root "D:\\1 Samadhi UNI\\aFYP\\Claude" --out out2_laptop

Expect about 75 minutes for run_ppr.py and about 20 minutes for run_ppr2.py on one CPU core. Add --smoke for a 1-minute code check.
"""
import multiprocessing as mp
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True


class _SerialPool:
    def __init__(self, n=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def imap_unordered(self, fn, tasks):
        for t in tasks:
            yield fn(t)


class _SerialContext:
    def Pool(self, n=None):
        return _SerialPool(n)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("run_ppr.py", "run_ppr2.py"):
        sys.exit("usage: python run_serial.py run_ppr.py|run_ppr2.py --root <folder> --out <folder> [--smoke]")
    here = Path(__file__).resolve().parent
    script = sys.argv[1]
    sys.argv = [str(here / script)] + sys.argv[2:]
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    mp.get_context = lambda method=None: _SerialContext()      # the runners call mp.get_context("fork").Pool(n)
    runpy.run_path(str(here / script), run_name="__main__")


if __name__ == "__main__":
    main()
