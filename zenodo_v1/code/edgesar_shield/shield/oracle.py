"""
Diagnostic only (arm A12).  NOT a system that could be deployed: it is told, from the labels, which reports the Q4 readout gets wrong, and spends
the verification budget on exactly those.  It answers one question: how much could ANY gate gain in this environment with this verifier?

This module is the only place outside the engine, the scorer and the calibration helpers that reads labels.  The runtime modules
(service.py, candidates.py, policy.py, cover.py) never import it; tests/test_policy.py checks that.
"""
from .sim import Decision, apply_record, canon_table


def wrong_table_ids(ds, svc, idx):
    """Report ids whose table after the readout's pilot-style record differs from the table after the gold record (ids ignored)."""
    out = set()
    for i in idx:
        i = int(i)
        c = ds.cases[i]
        rec = svc.pilot_record(c["id"])
        if canon_table(apply_record(c["open"], rec["norm"])) != canon_table(apply_record(c["open"], ds.label_norm[i])):
            out.add(c["id"])
    return out


class ListGate:
    """Ask for verification exactly on the reports in `ids` (while the budget lasts); commit the readout's record otherwise."""

    def __init__(self, service, ids):
        self.svc, self.ids = service, set(ids)

    def on_report(self, view):
        rec = self.svc.pilot_record(view.case_id)
        if view.budget_left > 0 and view.case_id in self.ids:
            return Decision("ESCALATE", "ESCALATE", record=rec["norm"], diag={"oracle_list": True})
        return Decision("COMMIT", "COMMIT", table=apply_record(view.open_table, rec["norm"]), record=rec["norm"])
