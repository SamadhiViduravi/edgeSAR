"""Compare two folders of per-episode record files (records_{L,M,H}_s{1,2,3}.json.gz) from two runs, ignoring only the wall-clock timing fields
(`wall_ms`, `ms`). Use it to check a fresh run against the shipped one (numpy not needed).
   python compare_records.py <folder_new> <folder_saved>
Exit code 0 = every record equal apart from timings."""
import gzip, json, sys
from pathlib import Path


def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k not in ("wall_ms", "ms")}
    if isinstance(o, list): return [strip(v) for v in o]
    return o


def main(a, b):
    a, b = Path(a), Path(b); bad = 0
    for lev in "LMH":
        for s in (1, 2, 3):
            n = "records_%s_s%d.json.gz" % (lev, s)
            x, y = strip(json.load(gzip.open(a / n, "rt"))), strip(json.load(gzip.open(b / n, "rt")))
            ok = x == y; bad += not ok
            print("%s: %d records, %s" % (n, len(x), "equal" if ok else "DIFFERENT"))
    print("RESULT:", "PASS (all records equal apart from timings)" if bad == 0 else "FAIL (%d files differ)" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(*sys.argv[1:3])
