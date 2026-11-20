"""Part D of PROTOCOL_PRACTICAL_ADVANTAGE.md: variance and sample size for the confirmation design, from the paired per-episode records of Part B (level M, prefix).
   python power_design.py out_trace/records_M.json.gz out_trace/DESIGN_NUMBERS.json"""
import gzip, json, sys
import numpy as np
from math import ceil
from scipy.stats import norm
recs = json.load(gzip.open(sys.argv[1], "rt", encoding="utf-8"))
by = {}
for r in recs:
    by.setdefault(r["arm"], {})[(r["fold"], r["seed"], r["episode"])] = r
def per_ep(arm, ids):
    m = np.array([by[arm][i]["counts"]["late"] + by[arm][i]["counts"]["unverified"] for i in ids], float)
    n = np.array([by[arm][i]["counts"]["n"] for i in ids], float)
    return m, n
def weighted(arm, ids, w={3: 3.0, 2: 2.0, 1: 1.0}):
    # inc rows: [ns, iid, landmark, sensor, priority, created, deadline, verified_at, class]
    mm, nn = [], []
    for i in ids:
        a = b = 0.0
        for x in by[arm][i]["inc"]:
            if x[8] in ("resolved_external",): continue
            wt = w[int(x[4])]; b += wt
            if x[8] in ("late", "unverified"): a += wt
        mm.append(a); nn.append(b)
    return np.array(mm), np.array(nn)
ids_all = sorted(set(by["alnp"]) & set(by["q4p"]))
out = {"episodes": len(ids_all)}
def est(arm_x, arm_y, ids, fn=per_ep):
    mx, n = fn(arm_x, ids); my, n2 = fn(arm_y, ids); assert np.allclose(n, n2)
    R = (mx.sum() - my.sum()) / n.sum()
    d = (mx - my) - R * n
    nbar = n.mean(); E = len(ids)
    se = np.sqrt(d.var(ddof=1) / E) / nbar
    return R, se, np.sqrt(d.var(ddof=1)) / nbar, nbar
R, se, s_ep, nbar = est("alnp", "q4p", ids_all)
out["primary"] = {"diff_pp": 100 * R, "se_pp_naive_150_episodes": 100 * se, "sd_per_episode_pp": 100 * s_ep, "mean_incidents_per_episode": nbar}
out["by_seed"] = {}
for s in (1, 2, 3):
    ids = [i for i in ids_all if i[1] == s]
    R_, se_, s_, _ = est("alnp", "q4p", ids); out["by_seed"][str(s)] = {"episodes": len(ids), "diff_pp": 100 * R_, "sd_per_episode_pp": 100 * s_, "se_pp": 100 * se_}
# dependence: the 3 seeds reuse the same reports, so the naive SE (150 episodes) is optimistic. Compare with report-level pooling over seeds:
# average the 3 seeds' paired differences for each (fold, episode index) is not available (episodes are re-partitioned per seed), so use the per-seed SE
# (50 episodes, independent reports inside a seed) as the cautious estimate for the development interval.
out["conservative_se_pp_one_seed_avg"] = float(np.mean([out["by_seed"][s]["se_pp"] for s in ("1", "2", "3")]))
# secondary endpoint: weighted by priority (3,2,1)
Rw, sew, sw, nw = est("alnp", "q4p", ids_all, weighted)
out["secondary_priority_weighted"] = {"diff_pp": 100 * Rw, "sd_per_episode_pp": 100 * sw}
# sample size for non-inferiority: reject H0: diff >= margin when upper 97.5% bound < margin. N = ((z_a + z_b) * s / (margin - true))^2 episodes
za = norm.ppf(0.975)
rows = []
for margin in (0.15, 0.25, 0.5):
    for true in (-0.15, 0.0, 0.10):
        for power in (0.8, 0.9):
            zb = norm.ppf(power)
            for infl, label in ((1.0, "sd as in development"), (1.5, "sd x1.5"), (2.0, "sd x2")):
                s = 100 * s_ep * infl
                N = ((za + zb) * s / (margin - true)) ** 2
                rows.append({"margin_pp": margin, "true_diff_pp": true, "power": power, "sd_inflation": infl, "episodes": int(ceil(N)), "reports": int(ceil(N)) * 20})
out["sample_size"] = rows
# minimum detectable margin with 150 and 500, 1000 episodes at 90% power, true diff 0
out["detectable_margin"] = {str(E): round(float((za + norm.ppf(0.9)) * 100 * s_ep / np.sqrt(E)), 3) for E in (150, 300, 500, 1000, 1100)}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "sample_size"}, indent=1))
