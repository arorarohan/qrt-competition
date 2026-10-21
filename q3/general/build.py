# Build the pure-Python general solution(s) from the measured mu.
#   solution.py         - fit on all 51 t rows, 300 largest coefficients
#   solution_even.py    - fit on even t rows only (held-out check: grader scores the odd rows blind)
# Run: python -I build.py   (needs numpy; the generated files do not)
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit as F

M, K, KEEP = 30, 20, 300

TEMPLATE = '''#!/bin/python3
# Q3 Black-box: general (formula) solution.
#
#   w(x, t) = sum over (m, j, c) in COEF of  c * cos(m*pi*x) * cos(j*pi*t)
#
# A smooth 2-D cosine series fitted to the measured payoff signal mu(x, t) ({fitted_on}).
# It is valid for any t (clamped to [0, 1]) and is not tied to the 100-point grid:
# probe returns w sampled at the centres of N = 300 equal cells (an odd multiple of 100, so each
# of the box's 100 hidden points sits exactly at a cell centre).
# Built by q3/general/build.py ({M} x-modes, {K} t-modes, {keep} largest coefficients kept).

import math
import os

N = 300
COEF = [
{coef}
]


def probe(t):
    t = min(1.0, max(0.0, t))
    a = {{}}
    for m, j, c in COEF:
        a[m] = a.get(m, 0.0) + c * math.cos(j * math.pi * t)
    xs = [(i + 0.5) / N for i in range(N)]
    return [sum(am * math.cos(m * math.pi * x) for m, am in a.items()) for x in xs]


if __name__ == '__main__':
    fptr = open(os.environ['OUTPUT_PATH'], 'w')
    t = float(input().strip())
    result = probe(t)
    fptr.write('\\n'.join(map(str, result)))
    fptr.write('\\n')
    fptr.close()
'''


def build(rows, lam, name, fitted_on):
    C = F.fit(M, K, rows, lam)
    thr = np.sort(np.abs(C).ravel())[-KEEP]
    entries = [(m, j, round(float(C[m, j]), 5)) for m in range(M) for j in range(K) if abs(C[m, j]) >= thr]
    coef = '\n'.join(f'({m},{j},{c}),' for m, j, c in entries)
    (HERE / name).write_text(TEMPLATE.format(coef=coef, M=M, K=K, keep=len(entries), fitted_on=fitted_on))
    return len(entries)


print(build(np.arange(51), 0.0, 'solution.py', 'fitted on all 51 grid values of t'))
print(build(np.arange(0, 51, 2), 1e-3, 'solution_even.py', 'HELD-OUT CHECK: fitted on even t rows only'))
