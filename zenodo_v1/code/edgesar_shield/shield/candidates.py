"""
Candidate records and the conformal set (plan sections 4.1 and 4.2).

For one report, the three heads give probabilities for action (4), sensor (3) and priority (3).  Location and incident link come from the
pilot's deterministic parser (`baselines._assemble`), and every combination is checked by the pilot's own `validate` against the open table.
A combination is (action) for CLOSE and NO_ACTION, and (action, sensor, priority) for CREATE and UPDATE:  at most 9 + 9 + 1 + 1 = 20 combinations.
(The plan text says 4 + 9 + 9 = 22; that counts CREATE and UPDATE twice. The real maximum is 20.)
Combinations that give the same normalised record add their scores.  Score = product of the head probabilities.  Because the sensor and priority
heads are trained on record rows only, they are conditional distributions, so the scores of all combinations add up to 1.

Two different "top" records exist and both are kept:
    hier   the pilot's rule: argmax of the action head, then argmax of the sensor head and of the priority head (what A1-A5 commit)
    top    the single most probable candidate by score (the plan's r_hat for the Shield)
They differ when a record action wins the action head but its best (sensor, priority) pair is so uncertain that "no action" is a more probable
single record. How often is measured and reported (docs/DEVIATIONS.md).
"""
import numpy as np

from . import paths
from .readout import ACTIONS, PRIOS, REC, SENSORS

_PILOT = {}


def pilot():
    """The pilot's common.py and baselines.py, loaded read-only after the fingerprints are checked."""
    if not _PILOT:
        paths.require_pins()
        paths.add_pilot_to_path()
        import baselines as pb          # noqa: E402
        import common as pc             # noqa: E402
        _PILOT["pc"], _PILOT["pb"] = pc, pb
    return _PILOT["pc"], _PILOT["pb"]


def combos():
    out = []
    for ai, a in enumerate(ACTIONS):
        if a in REC:
            out += [(ai, si, pi) for si in range(len(SENSORS)) for pi in range(len(PRIOS))]
        else:
            out.append((ai, None, None))
    return out


COMBOS = combos()


class Enumerator:
    """Per-report cache of what each combination assembles to. The mapping depends on the report text and the open table only."""

    def __init__(self, case):
        pc, pb = pilot()
        self.case = case
        self.rows = []
        for ai, si, pi in COMBOS:
            a = ACTIONS[ai]
            s = SENSORS[si] if si is not None else "ANY"
            p = int(PRIOS[pi]) if pi is not None else 2
            norm, status = pc.validate(pb._assemble(case, a, s, p), case)
            self.rows.append((ai, si, pi, pc.strict_key(norm), norm))

    def hier_norm(self, pa, ps, pp):
        ai, si, pi = int(np.argmax(pa)), int(np.argmax(ps)), int(np.argmax(pp))
        for a, s, p, key, norm in self.rows:
            if a == ai and (s is None or (s == si and p == pi)):
                return norm
        raise RuntimeError("combination not found")

    def candidates(self, pa, ps, pp):
        """Merged candidates, best first. Returns a list of dicts {key, norm, score}. Ties are broken by the record key (deterministic)."""
        acc = {}
        order = []
        for ai, si, pi, key, norm in self.rows:
            w = float(pa[ai]) * (float(ps[si]) if si is not None else 1.0) * (float(pp[pi]) if pi is not None else 1.0)
            if key in acc:
                acc[key][0] += w
            else:
                acc[key] = [w, norm]
                order.append(key)
        out = [{"key": k, "norm": acc[k][1], "score": acc[k][0]} for k in order]
        out.sort(key=lambda c: (-c["score"], str(c["key"])))
        return out


def conformal_set(cands, q):
    """Candidates with 1 - score <= q (a small tolerance for floating-point sums)."""
    return [c for c in cands if 1.0 - c["score"] <= q + 1e-12]
