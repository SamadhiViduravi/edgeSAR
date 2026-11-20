r"""EXPLORATORY ONLY. Not for the paper. Run from the V1 folder:
    .\.venv\Scripts\python -m packages.allocation.explore_funnel

It reads the frozen pilot files (it never calls a model) and runs ALL 1,400 pilot cases through the POC mission
simulator, Q4 against FP16. It answers: how often does a changed decision change the task table, the assignment,
the route, the verification times, and how often is the change harmful?

POC rules that make these numbers exploratory (they must be fixed BEFORE any held-out run):
  - truth = the gold task table   - all tasks known at t = 0   - harmful = a new miss or one victim >= 30 s later
  - the 30 s threshold was chosen by me, after seeing the cases
"""
import sys
sys.dont_write_bytecode = True
import json, random, statistics, time, math
from collections import defaultdict
from packages.allocation.decisions import PILOT_DIR, apply_decision
from packages.allocation.mission import run_mission
from packages.allocation.world import UAVS
import common

cases = common.load_cases(PILOT_DIR / "data" / "cases.jsonl")
def runs(name):
    d = {}
    for line in open(PILOT_DIR / "runs" / (name + ".jsonl"), encoding="utf-8"):
        r = json.loads(line); d[r["case_id"]] = r["text"]
    return d
F, Q = runs("f16_P1"), runs("q4_P1")
def norm_of(text, case):
    obj, _ = common.parse_decision(text)
    return common.validate(obj, case)[0]

def sig(res):
    pairs = frozenset((v["landmark"], v["uav"]) for v in res["visits"])
    routes = tuple(tuple(v["landmark"] for v in sorted((x for x in res["visits"] if x["uav"] == u.id), key=lambda x: x["start"])) for u in UAVS)
    return pairs, routes

HARM = 30.0
rows = []; t0 = time.time()
for c in cases:
    gold = common.gold_norm(c)
    truth = {t["landmark"]: t["sensor"] for t in apply_decision(c, gold)}
    nf, nq = norm_of(F[c["id"]], c), norm_of(Q[c["id"]], c)
    tf, tq = apply_decision(c, nf), apply_decision(c, nq)
    rf, rq = run_mission(UAVS, tf, truth), run_mission(UAVS, tq, truth)
    L0 = common.strict_key(nf) != common.strict_key(nq)
    L1 = common.effect(nf, c) != common.effect(nq, c)
    pf, of = sig(rf); pq, oq = sig(rq)
    L2 = pf != pq; L3 = of != oq
    d = {}
    for v in truth:
        a = rf["verify_time"].get(v); b = rq["verify_time"].get(v)
        d[v] = (600.0 if b is None else b) - (600.0 if a is None else a)
    L4 = any(abs(x) > 0.5 for x in d.values())
    newmiss = any(rq["verify_time"].get(v) is None and rf["verify_time"].get(v) is not None for v in truth)
    fixmiss = any(rf["verify_time"].get(v) is None and rq["verify_time"].get(v) is not None for v in truth)
    worse = any(x >= HARM for x in d.values()); better = any(x <= -HARM for x in d.values())
    mean = statistics.mean(d.values()) if d else 0.0
    rows.append(dict(id=c["id"], L0=L0, L1=L1, L2=L2, L3=L3, L4=L4, newmiss=newmiss, fixmiss=fixmiss,
                     worse=worse, better=better, mean=mean, route_only=(L3 and not L2),
                     fq=(common.strict_key(nf) == common.strict_key(gold), common.strict_key(nq) == common.strict_key(gold))))
print("seconds", round(time.time() - t0, 1), "cases", len(rows))
n = len(rows)
def k(f): return sum(1 for r in rows if f(r))
print("L0 decision differs      ", k(lambda r: r["L0"]), "(%.1f%%)" % (100*k(lambda r: r["L0"])/n))
print("L1 task table differs    ", k(lambda r: r["L1"]), "(%.1f%%)" % (100*k(lambda r: r["L1"])/n))
l1 = [r for r in rows if r["L1"]]
for name in ["L2", "L3", "L4"]:
    print(name, "differs among L1:", sum(1 for r in l1 if r[name]), "of", len(l1))
print("route changed but same (task,UAV) pairs:", sum(1 for r in l1 if r["route_only"]))
print("L4 changed but L2 same:", sum(1 for r in l1 if r["L4"] and not r["L2"]))
print("L2 changed but L4 same (absorbed):", sum(1 for r in l1 if r["L2"] and not r["L4"]))
print("Q4 creates a NEW miss vs FP16:", sum(1 for r in l1 if r["newmiss"]), "| Q4 FIXES a miss:", sum(1 for r in l1 if r["fixmiss"]))
print("some victim >= %ds later with Q4:" % HARM, sum(1 for r in l1 if r["worse"]), "| >= %ds earlier:" % HARM, sum(1 for r in l1 if r["better"]))
print("both worse and better in same case:", sum(1 for r in l1 if r["worse"] and r["better"]))
harm = lambda r: r["newmiss"] or r["worse"]
print("HARMFUL (new miss or >=30s later):", sum(1 for r in l1 if harm(r)))
print("hidden harm (mean not worse, but harmful):", sum(1 for r in l1 if harm(r) and r["mean"] <= 0))
print("harm where Q4 mean RMIVT is LOWER than FP16:", sum(1 for r in l1 if harm(r) and r["mean"] < -0.5))
fq = [r for r in rows]
print("FP16 matches gold:", sum(1 for r in rows if r["fq"][0]), "Q4 matches gold:", sum(1 for r in rows if r["fq"][1]), "of", n)
print("among harmful: FP16 right / Q4 wrong:", sum(1 for r in l1 if harm(r) and r["fq"][0] and not r["fq"][1]),
      "| both wrong:", sum(1 for r in l1 if harm(r) and not r["fq"][0] and not r["fq"][1]))

# fairness tests that already can run on the current core
bad_det = bad_shuf = 0
rng = random.Random(7)
for c in cases[:700]:
    gold = common.gold_norm(c); truth = {t["landmark"]: t["sensor"] for t in apply_decision(c, gold)}
    for text in (F[c["id"]], Q[c["id"]]):
        tab = apply_decision(c, norm_of(text, c))
        a = run_mission(UAVS, tab, truth); b = run_mission(UAVS, tab, truth)
        if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True): bad_det += 1
        key = lambda r: sorted((v["uav"], v["landmark"], round(v["start"], 6), round(v["arrive"], 6), v["result"]) for v in r["visits"])
        for _ in range(3):
            t2 = tab[:]; rng.shuffle(t2)
            if key(run_mission(UAVS, t2, truth)) != key(a): bad_shuf += 1
print("determinism failures:", bad_det, "| task-order shuffle failures:", bad_shuf, "(of", 700*2, "tables x 3 shuffles)")

print("\n" + "=" * 70 + "\nPART 2: flip types, table size, harm against the correct answer\n" + "=" * 70)
import json, math
from collections import defaultdict
cases = common.load_cases(PILOT_DIR / "data" / "cases.jsonl")
def runs(name):
    return {json.loads(l)["case_id"]: json.loads(l)["text"] for l in open(PILOT_DIR / "runs" / (name + ".jsonl"), encoding="utf-8")}
F, Q = runs("f16_P1"), runs("q4_P1")
def norm_of(text, case):
    obj, _ = common.parse_decision(text); return common.validate(obj, case)
def delays(r_test, r_ref, truth):
    out = {}
    for v in truth:
        a = r_ref["verify_time"].get(v); b = r_test["verify_time"].get(v)
        out[v] = (600.0 if b is None else b) - (600.0 if a is None else a)
    return out
def harmful(r_test, r_ref, truth, thr=30.0):
    newmiss = any(r_test["verify_time"].get(v) is None and r_ref["verify_time"].get(v) is not None for v in truth)
    return newmiss or any(x >= thr for x in delays(r_test, r_ref, truth).values())

by_tr = defaultdict(lambda: [0, 0, 0, 0]); by_n = defaultdict(lambda: [0, 0])
hf = hq = 0; only_q = only_f = 0
status = {"F": defaultdict(int), "Q": defaultdict(int)}
for c in cases:
    gold = common.gold_norm(c); gt = apply_decision(c, gold)
    truth = {t["landmark"]: t["sensor"] for t in gt}
    rg = run_mission(UAVS, gt, truth)
    nf, sf = norm_of(F[c["id"]], c); nq, sq = norm_of(Q[c["id"]], c)
    status["F"][sf] += 1; status["Q"][sq] += 1
    tf, tq = apply_decision(c, nf), apply_decision(c, nq)
    rf, rq = run_mission(UAVS, tf, truth), run_mission(UAVS, tq, truth)
    hF, hQ = harmful(rf, rg, truth), harmful(rq, rg, truth)
    hf += hF; hq += hQ; only_q += (hQ and not hF); only_f += (hF and not hQ)
    ef, eq = common.effect(nf, c), common.effect(nq, c)
    lab = common.transition(ef, eq)
    if lab:
        h = harmful(rq, rf, truth)
        ver = any(abs(x) > 0.5 for x in delays(rq, rf, truth).values())
        pairs = lambda r: frozenset((v["landmark"], v["uav"]) for v in r["visits"])
        b = by_tr[lab.split(":")[0] if ":" in lab else lab]
        b[0] += 1; b[1] += (pairs(rf) != pairs(rq)); b[2] += ver; b[3] += h
        n = max(len(tf), len(tq)); key = "1-2 tasks" if n <= 2 else ("3 tasks" if n == 3 else "4+ tasks")
        by_n[key][0] += 1; by_n[key][1] += h
print("harm vs the correct answer (gold), over all 1400 cases:  FP16 =", hf, " Q4 =", hq,
      "| only Q4 harmful:", only_q, "| only FP16 harmful:", only_f)
print("status FP16:", dict(status["F"])); print("status Q4:", dict(status["Q"]))
print("\nflip type (Q4 vs FP16) | n | assignment changed | verification changed | harmful")
for k, v in sorted(by_tr.items(), key=lambda kv: -kv[1][0]):
    if v[0] >= 8: print("%-28s %4d  %4d (%2.0f%%)  %4d (%2.0f%%)  %4d (%2.0f%%)" % (k, v[0], v[1], 100*v[1]/v[0], v[2], 100*v[2]/v[0], v[3], 100*v[3]/v[0]))
print("\nharm rate by table size (table-changing flips):")
for k, v in by_n.items(): print("  %-10s n=%3d harmful=%3d (%.0f%%)" % (k, v[0], v[1], 100*v[1]/v[0]))
