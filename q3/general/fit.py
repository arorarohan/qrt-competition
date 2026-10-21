# Fit w(x,t) = sum_{m<M, j<K} C[m][j] * cos(m*pi*x) * cos(j*pi*t) to the measured mu (agent A table).
# Score proxy (exact under the model): hr_i = 20 * (1 - mean_k (w - mu)^2 / (2 * T_i)).
# Run: python -I fit.py   (needs numpy)
import json, runpy, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
MU = np.array(runpy.run_path(str(HERE.parent / 'agents' / 'A_polish' / 'solution.py'), run_name='x')['W'])
T = 0.5 * (MU ** 2).mean(axis=1)                       # true target per row (A solved these; matches TGT)
ts = np.arange(51) / 50
xs = (np.arange(100) + 0.5) / 100


def basis_x(M, x=xs):
    return np.cos(np.pi * np.outer(x, np.arange(M)))   # (len x, M)


def basis_t(K, t):
    return np.cos(np.pi * np.outer(t, np.arange(K)))   # (len t, K)


def fit(M, K, rows, lam=0.0):
    """Weighted LS (row weight 1/T) of mu[rows] onto the tensor basis, small ridge lam."""
    X, P = basis_x(M), basis_t(K, ts[rows])
    D = 1 / T[rows]
    # x-basis is orthogonal on the cell-centre grid: project rows onto it first
    A = MU[rows] @ X / (X ** 2).sum(axis=0)             # (rows, M) coefficients per row
    G = P.T @ (D[:, None] * P) + lam * np.eye(K)
    return np.linalg.solve(G, P.T @ (D[:, None] * A)).T  # C: (M, K)


def predict(C, t):
    M, K = C.shape
    return basis_t(K, np.atleast_1d(t)) @ C.T @ basis_x(M).T  # (len t, 100)


def score(pred, rows):
    e2 = ((pred - MU[rows]) ** 2).mean(axis=1)
    return 20 * (1 - e2 / (2 * T[rows]))


if __name__ == '__main__':
    even, odd = np.arange(0, 51, 2), np.arange(1, 51, 2)
    # baseline: linear interpolation of the even rows onto the odd rows (what a table+interp would do at gap 0.04)
    lin = (MU[odd - 1] + MU[odd + 1]) / 2
    print(f'baseline lin-interp held-out mean hr/case {score(lin, odd).mean():.3f}')
    print(' M   K  ncoef  grid_total  heldout_mean_hr(odd rows, fit on even)')
    res = []
    for M in (20, 30, 40, 50, 60, 100):
        for K in (12, 16, 20, 24, 26):
            C = fit(M, K, np.arange(51))
            grid = score(predict(C, ts), np.arange(51)).sum()
            Ce = fit(M, K, even, lam=1e-3)
            ho = score(predict(Ce, ts[odd]), odd).mean()
            res.append((M, K, grid, ho))
            print(f'{M:3d} {K:3d} {M*K:6d} {grid:10.2f} {ho:8.3f}')
    if len(sys.argv) > 2:
        M, K = int(sys.argv[1]), int(sys.argv[2])
        C = fit(M, K, np.arange(51))
        (HERE / f'coef_{M}x{K}.json').write_text(json.dumps(np.round(C, 5).tolist()))
        print('saved', M, K)
