"""
The readout as the runtime sees it.  For a report id the service returns the model's output: the merged candidate records with their scores,
the pilot-style record (argmax of each head), and the pilot's confidence.  It holds NO labels and no truth.
"""
import hashlib

import numpy as np

from .readout import REC


def uniform01(seed, key):
    """A fixed pseudo-random number in [0, 1) for (seed, key): the same report always gets the same number (used for tie-breaking and the random gate)."""
    h = hashlib.sha256(("%s|%s" % (seed, key)).encode("utf-8")).hexdigest()
    return int(h[:12], 16) / float(16 ** 12)


class Service:
    def __init__(self, cands, hier, conf):
        self._cands = cands          # report id -> merged candidate list, best first
        self._hier = hier            # report id -> candidate dict (key, norm, score) of the pilot-style record
        self._conf = conf            # report id -> pilot confidence

    def candidates(self, rid):
        return self._cands[rid]

    def pilot_record(self, rid):
        """The pilot rule's record as a candidate dict (key, norm, score): action argmax, then sensor and priority argmax."""
        return self._hier[rid]

    def confidence(self, rid):
        return self._conf[rid]

    def top_score(self, rid):
        return self._cands[rid][0]["score"]


def pilot_confidence(pa, ps, pp, action):
    conf = float(np.max(pa))
    if action in REC:
        conf = min(conf, float(np.max(ps)), float(np.max(pp)))
    return conf
