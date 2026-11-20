"""
Paired-precision readout repair (PPR): library for the feasibility experiment (PROTOCOL_REPAIR_FEASIBILITY.md).

Read-only on the project folders. Everything is fitted on the training indices that the caller passes in.
One solver is used for every head: multinomial logistic regression with an L2 penalty (the scikit-learn objective
C * sum_i w_i * CE(t_i, softmax(o_i + W s_i + b)) + 0.5 * ||W||^2), with optional soft targets t_i, fixed offsets o_i and weights w_i,
solved by L-BFGS in the row space of the standardised training matrix (the optimum of the penalised problem lies in that space).
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

sys.dont_write_bytecode = True

ACTIONS = ["CREATE_VERIFICATION", "UPDATE_INCIDENT", "CLOSE_INCIDENT", "NO_ACTION"]
SENSORS = ["RGB", "THERMAL", "ANY"]
PRIOS = ["1", "2", "3"]
REC = ("CREATE_VERIFICATION", "UPDATE_INCIDENT")
HEADS = {"action": ACTIONS, "sensor": SENSORS, "prio": PRIOS}
C_GRID = [0.0003, 0.003, 0.03, 0.3, 3]
INNER = 3
LAMBDA_GRID = [0.01, 0.1, 1.0, 10.0, 100.0]
TOL = 1e-9


# ------------------------------------------------------------------ data
class Data:
    def __init__(self, root):
        root = Path(root)
        self.pilot, self.heads, self.v1 = root / "edgesar_pilot", root / "edgesar_heads", root / "V1"
        for p in (self.pilot, self.heads, self.v1):
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
        import common as pc
        import baselines as pb
        self.pc, self.pb = pc, pb
        with open(self.pilot / "data" / "cases.jsonl", encoding="utf-8") as f:
            self.cases = [json.loads(l) for l in f if l.strip()]
        ids = json.loads((self.heads / "features" / "case_ids.json").read_text(encoding="utf-8"))
        assert ids == [c["id"] for c in self.cases], "vector rows are not in case order"
        self.X = {}
        for m in ("f16", "Q8_0", "Q4_K_M"):
            for v in ("end", "prefix"):
                self.X[(m, v)] = np.load(self.heads / "features" / ("%s_%s.npy" % (m, v))).astype(np.float64)
        self.N = len(self.cases)
        self.split = np.array([c["split"] for c in self.cases])
        self.y = {"action": np.array([c["gold"]["action"] for c in self.cases]),
                  "sensor": np.array([c["gold"].get("sensor", "") for c in self.cases]),
                  "prio": np.array([str(c["gold"].get("priority", "")) for c in self.cases])}
        self.is_rec = np.isin(self.y["action"], REC)
        self.template = np.array([template_key(c["text"], pc.LANDMARKS) for c in self.cases])
        self.gold_key = [pc.strict_key(pc.gold_norm(c)) for c in self.cases]

    def onehot(self, head, idx):
        cls = HEADS[head]
        T = np.zeros((len(idx), len(cls)))
        for r, i in enumerate(idx):
            v = self.y[head][i]
            if v in cls:
                T[r, cls.index(v)] = 1.0
        return T

    def record(self, i, a, s, p):
        norm, _ = self.pc.validate(self.pb._assemble(self.cases[i], a, s, int(p)), self.cases[i])
        return norm


def template_key(text, landmarks):
    """The report text with landmarks, incident ids, sources and numbers masked (same function as audit 04)."""
    t = text
    for lm in sorted(landmarks, key=len, reverse=True):
        t = t.replace(lm, "<L>")
    t = re.sub(r"\bI\d+\b", "<I>", t)
    t = re.sub(r"\b(UAV\d|Ground team|Command post)\b", "<S>", t, flags=re.I)
    t = re.sub(r"\d+", "<N>", t)
    return t.lower()


def group_folds(groups, k, seed):
    """Assign whole groups to k folds: groups in a seeded random order, each to the currently smallest fold. Returns fold id per row."""
    groups = np.asarray(groups)
    uniq, counts = np.unique(groups, return_counts=True)
    order = np.random.default_rng(seed).permutation(len(uniq))
    order = sorted(order, key=lambda j: -counts[j])            # big groups first (stable w.r.t. the seeded order)
    size = np.zeros(k, int)
    fold_of = {}
    for j in order:
        f = int(np.argmin(size))
        fold_of[uniq[j]] = f
        size[f] += counts[j]
    return np.array([fold_of[g] for g in groups])


# ------------------------------------------------------------------ solver
class Scaler:
    def __init__(self, X):
        self.mu = X.mean(0)
        sd = X.std(0)
        self.sd = np.where(sd > 0, sd, 1.0)

    def __call__(self, X):
        return (X - self.mu) / self.sd


def softmax(Z):
    return np.exp(Z - logsumexp(Z, axis=1, keepdims=True))


def _solve(Z, T, C, O=None, w=None, x0=None):
    """min C*sum_i w_i*CE(T_i, softmax(O_i + Z_i W' + b)) + 0.5*||W||^2. Z: n x r. Returns (W r x K as K x r, b, x)."""
    n, r = Z.shape
    K = T.shape[1]
    O = np.zeros((n, K)) if O is None else O
    w = np.ones(n) if w is None else w
    scale = C * w.sum()                                        # objective is divided by this so the tolerance is scale-free

    def fun(x):
        W = x[:K * r].reshape(K, r)
        b = x[K * r:]
        L = O + Z @ W.T + b
        lse = logsumexp(L, axis=1)
        logp = L - lse[:, None]
        f = -C * np.sum(w[:, None] * T * logp) + 0.5 * np.sum(W * W)
        G = C * w[:, None] * (np.exp(logp) * T.sum(1, keepdims=True) - T)
        gW = G.T @ Z + W
        gb = G.sum(0)
        return f / scale, np.concatenate([gW.ravel(), gb]) / scale

    x0 = np.zeros(K * r + K) if x0 is None else x0
    res = minimize(fun, x0, jac=True, method="L-BFGS-B", options={"maxiter": 20000, "maxfun": 40000, "gtol": TOL, "ftol": 1e-15, "maxcor": 30})
    return res.x[:K * r].reshape(K, r), res.x[K * r:], res.x, res


class Head:
    """Scaler + linear logits. predict_logits(X_raw, offset) = offset + ((X - mu)/sd) W' + b."""

    def __init__(self, scaler, W, b, C, classes):
        self.scaler, self.W, self.b, self.C, self.classes = scaler, W, b, C, classes

    def logits(self, X, offset=None):
        L = self.scaler(X) @ self.W.T + self.b
        return L if offset is None else L + offset

    def proba(self, X, offset=None):
        return softmax(self.logits(X, offset))


class _Reduced:
    """Row-space (n <= d) or column-space (n > d) representation of a standardised matrix S, without a full SVD.
    Z = coordinates of the training rows (n x r); project(S_new) gives the coordinates of new rows; lift(Wz) gives W in the original space."""

    def __init__(self, S):
        n, d = S.shape
        self.S, self.row = S, n <= d
        if self.row:
            ev, E = np.linalg.eigh(S @ S.T)
        else:
            ev, E = np.linalg.eigh(S.T @ S)
        keep = ev > ev[-1] * 1e-12
        self.E, self.rt = E[:, keep], np.sqrt(ev[keep])
        self.Z = self.E * self.rt if self.row else S @ self.E

    def project(self, Snew):
        return (Snew @ self.S.T) @ (self.E / self.rt) if self.row else Snew @ self.E

    def lift(self, Wz):
        return ((Wz / self.rt) @ self.E.T) @ self.S if self.row else Wz @ self.E.T


def _fit_fixed(X, T, C, O=None, w=None, scaler=None, x0=None):
    sc = Scaler(X) if scaler is None else scaler
    R = _Reduced(sc(X))
    Wz, b, x, res = _solve(R.Z, T, C, O, w, x0 if (x0 is not None and len(x0) == T.shape[1] * (R.Z.shape[1] + 1)) else None)
    return sc, R.lift(Wz), b, x, res


def fit_head(X, T, groups, classes, O=None, w=None, scaler=None, c_grid=C_GRID, fixed_C=None, seed=0):
    """Fit one head. C is chosen by INNER-fold grouped cross-validation on the (weighted) cross-entropy to T (hard or soft targets).
    scaler=None: the scaler is fitted on X (and refitted inside each inner fold). scaler given: it is kept fixed (anchored arms)."""
    n = len(X)
    w = np.ones(n) if w is None else w
    if fixed_C is None:
        f = group_folds(groups, INNER, seed)
        loss = np.zeros(len(c_grid))
        for k in range(INNER):
            tr, va = f != k, f == k
            if va.sum() == 0 or tr.sum() == 0:
                continue
            sc = Scaler(X[tr]) if scaler is None else scaler
            R = _Reduced(sc(X[tr]))
            Z, Zva = R.Z, R.project(sc(X[va]))
            x = None
            for ci, C in enumerate(c_grid):                    # warm start along the grid
                Wz, b, x, _ = _solve(Z, T[tr], C, None if O is None else O[tr], w[tr], x)
                L = Zva @ Wz.T + b + (0 if O is None else O[va])
                logp = L - logsumexp(L, axis=1, keepdims=True)
                loss[ci] += -np.sum(w[va, None] * T[va] * logp)
        C = c_grid[int(np.argmin(loss))]                       # ties: the smaller C (argmin takes the first)
    else:
        C = fixed_C
    sc, W, b, _, res = _fit_fixed(X, T, C, O, w, scaler)
    return Head(sc, W, b, C, classes)


# ------------------------------------------------------------------ label-free maps (pairs only)
class Recentre:
    """C1: x_Q - delta, delta = mean(x_Q - x_F) over the pair bank."""

    def __init__(self, F, Q):
        self.delta = (Q - F).mean(0)

    def __call__(self, Xq):
        return Xq - self.delta


class AffineMap:
    """C2: g(x_Q) = mu_F + sd * ((I + D) s_Q), s_Q = (x_Q - mu_Q)/sd, D = ridge fit of (s_F - s_Q) on s_Q (dual form), lambda chosen on
    held-out pairs. lambda -> infinity gives C1."""

    def __init__(self, F, Q, groups, seed=0, lam_grid=LAMBDA_GRID):
        self.muF, self.muQ = F.mean(0), Q.mean(0)
        sd = F.std(0)
        self.sd = np.where(sd > 0, sd, 1.0)
        sF, sQ = (F - self.muF) / self.sd, (Q - self.muQ) / self.sd
        f = group_folds(groups, INNER, seed)
        err = np.zeros(len(lam_grid))
        base = 0.0
        for k in range(INNER):
            tr, va = f != k, f == k
            Kt = sQ[tr] @ sQ[tr].T
            ev, E = np.linalg.eigh(Kt)
            ev = np.clip(ev, 0, None)
            unit = np.trace(Kt) / tr.sum()
            R = sF[tr] - sQ[tr]
            ER = E.T @ R
            Kva = sQ[va] @ sQ[tr].T
            KvaE = Kva @ E
            for li, c in enumerate(lam_grid):
                pred = sQ[va] + KvaE @ (ER / (ev + c * unit)[:, None])
                err[li] += np.sum((pred - sF[va]) ** 2)
            base += np.sum((sQ[va] - sF[va]) ** 2)
        self.cv_err = {float(c): float(e) for c, e in zip(lam_grid, err)}
        self.cv_err_recentre_only = float(base)
        self.c = lam_grid[int(np.argmin(err))]
        K = sQ @ sQ.T
        self.A = np.linalg.solve(K + self.c * (np.trace(K) / len(K)) * np.eye(len(K)), sF - sQ)
        self.sQ_bank = sQ

    def __call__(self, Xq):
        s = (Xq - self.muQ) / self.sd
        return self.muF + self.sd * (s + (s @ self.sQ_bank.T) @ self.A)


# ------------------------------------------------------------------ records and metrics
def assemble(data, idx, P):
    """P = {'action': n x 4, 'sensor': n x 3, 'prio': n x 3} probabilities or logits for the reports idx. Returns list of normalised records."""
    out = []
    for r, i in enumerate(idx):
        a = ACTIONS[int(P["action"][r].argmax())]
        s = SENSORS[int(P["sensor"][r].argmax())]
        p = PRIOS[int(P["prio"][r].argmax())]
        out.append(data.record(int(i), a, s, p))
    return out
