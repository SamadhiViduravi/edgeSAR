"""
The feasible fallback ("cover"), plan section 4.7.  Runtime information only.

Given the candidate records that cannot be told apart safely, build ONE task table that serves every one of them:
  * union of the tasks implied by all candidates; tasks at the same location become one task;
  * required cameras = union of the candidates' cameras (in this fleet RGB+THERMAL means UAV-02);
  * priority = the maximum, so the deadline is the earliest;
  * an open incident is closed only if EVERY candidate closes it;
  * an existing incident keeps its id when a task of that incident stays at the same location, so its clock (created time, deadline) is kept.
The cover is planned with the same allocator and its tasks are checked against R1 (camera) and R2 (believed deadline), and R3 (a UAV exists).
Extra trips and distance are real costs: the simulator counts them.  Nothing here assumes the cover can always be completed.
"""
from .core import req_of, sensor_of
from .sim import apply_record


def build_cover(open_table, members, tag=0, rhat=None, camera="union", priority="max", max_members=None):
    """open_table: the system's current rows (id, landmark, sensor, priority).  members: candidate dicts with a normalised record.
    `tag` makes the ids of new cover tasks unique per decision. Returns the cover table (rows with id, landmark, sensor, req, priority, cover)
    and a small description.

    Defaults are the plan (section 4.7): camera = union over candidates, priority = maximum over candidates.
    Development variants (exploratory, see docs/DEVIATIONS.md):
        camera="rhat"    at a location where the committed record r_hat already has a task, keep r_hat's cameras (no camera union there)
        priority="rhat"  same for the priority
        max_members=m    cover only the m best members (the committed record is always kept)
    """
    base_ids = {r["id"] for r in open_table}
    if max_members is not None and len(members) > max_members:
        top = list(members[:max_members])
        if rhat is not None and not any(m["norm"] == rhat for m in top):
            top += [m for m in members if m["norm"] == rhat][:1]
        members = top
    rh = {}
    if rhat is not None and (camera == "rhat" or priority == "rhat"):
        for row in apply_record(open_table, rhat):
            e = rh.setdefault(row["landmark"], {"req": set(), "pri": 0})
            e["req"] |= set(req_of(row["sensor"]))
            e["pri"] = max(e["pri"], row["priority"])
    by_loc = {}
    for m in members:
        for row in apply_record(open_table, m["norm"]):
            e = by_loc.setdefault(row["landmark"], {"req": set(), "pri": 0, "ids": set()})
            e["req"] |= set(req_of(row["sensor"]))
            e["pri"] = max(e["pri"], row["priority"])
            e["ids"].add(row["id"])
    rows, used, n_new = [], set(), 0
    for loc in sorted(by_loc):
        e = by_loc[loc]
        keep = sorted(i for i in e["ids"] if i in base_ids and i not in used)
        if keep:
            rid, is_cover = keep[0], False
        else:
            n_new += 1
            rid, is_cover = "C%s_%d" % (tag, n_new), True
        used.add(rid)
        req = set(e["req"])
        pri = e["pri"]
        if loc in rh:
            if camera == "rhat":
                req = set(rh[loc]["req"])
            if priority == "rhat":
                pri = rh[loc]["pri"]
        req = tuple(sorted(req))
        rows.append({"id": rid, "landmark": loc, "sensor": sensor_of(frozenset(req)), "req": req, "priority": pri, "cover": is_cover})
    return rows, {"n_members": len(members), "n_tasks": len(rows), "n_new": n_new,
                  "closed": sorted(base_ids - used)}


def uncovered_rows(cover_rows, table):
    """Rows of `table` (one candidate's complete table) that no cover row serves: a cover row serves a row when it is at the same landmark,
    asks for at least the same cameras (a UAV that can do the cover task can do the row) and has at least the same priority (deadline no later).
    Rows of a candidate that closes an incident are simply absent from its table."""
    out = []
    for r in table:
        need = set(req_of(r["sensor"])) if "req" not in r else set(r["req"])
        if not any(c["landmark"] == r["landmark"] and set(c["req"]) >= need and c["priority"] >= r["priority"] for c in cover_rows):
            out.append(r["id"])
    return out
