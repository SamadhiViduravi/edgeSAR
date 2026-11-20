"""Step 4: CBBA, the simplest version.

CBBA = Consensus-Based Bundle Algorithm (Choi, Brunet and How, 2009). UAVs bid on tasks, then they
agree (consensus) on who wins each task, with no central boss.

This is a SIMPLIFIED version, and the report must say so:
  - each UAV holds ONE task at a time (a bundle of size 1),
  - all UAVs hear each other perfectly (no lost messages),
  - tasks that nobody can take now wait, and are allocated later when a UAV becomes free (Step 5).
"""
from packages.allocation.bids import bid

MAX_ROUNDS = 100


def _beats(new_bid, new_uav, old_bid, old_uav):
    """Does the new bid beat the old winner? Equal bids: the lower UAV id wins, so luck never decides."""
    if new_bid != old_bid:
        return new_bid > old_bid
    return new_uav < old_uav


def allocate(uavs, tasks, positions, now=0.0, banned=None):
    """uavs: the free UAVs. tasks: the waiting tasks. positions: {uav_id: (x, y)}.
    banned: {task_id: set of UAV ids that must not bid on it} (a UAV that already failed there).
    Returns (assignment, rounds). assignment = {uav_id: task_id, or None if the UAV got nothing}."""
    banned = banned or {}
    holds = {u.id: None for u in uavs}     # the task each UAV holds now
    winner = {}                            # task_id -> (bid, uav_id): the best bid seen so far
    for rounds in range(1, MAX_ROUNDS + 1):
        # BUILD phase: every UAV without a task picks the best task it could still win
        picks = {}
        for u in uavs:
            if holds[u.id] is not None:
                continue
            options = []
            for t in tasks:
                if u.id in banned.get(t["id"], ()):
                    continue                                   # this UAV already failed on this task
                b = bid(u, t, positions[u.id], now)
                if b is None:
                    continue                                   # wrong camera: cannot bid
                if t["id"] in winner and not _beats(b, u.id, *winner[t["id"]]):
                    continue                                   # cannot beat the current winner
                options.append((b, t["id"]))
            if options:
                picks[u.id] = min(options, key=lambda o: (-o[0], o[1]))   # highest bid, then lower task id
        if not picks:
            return holds, rounds - 1                           # nobody wants anything new: agreement
        # CONSENSUS phase: the highest bid wins each task. A UAV that is outbid becomes free again.
        for uav_id in sorted(picks):
            b, task_id = picks[uav_id]
            if task_id in winner:
                if not _beats(b, uav_id, *winner[task_id]):
                    continue
                holds[winner[task_id][1]] = None               # the old winner loses the task
            winner[task_id] = (b, uav_id)
            holds[uav_id] = task_id
    raise RuntimeError("CBBA did not reach agreement")