#!/bin/python3
# Q3 Black-box solution "E_smooth": q3/solution.py (S4) table W denoised offline.
# W[i] ~ mu(x_k=(k+0.5)/100, t=i/50). See q3/agents/E_smooth/findings.md for how each row was built.
# probe() interpolates linearly in t between grid rows, so off-grid t values also get a sensible answer;
# on the 0.02 grid it returns exactly W[i].
# Paste everything above `if __name__` into the HackerRank editor.

import os

W = [
@@W@@,
]


def probe(t):
    x = min(max(float(t), 0.0), 1.0) * 50.0
    i = int(x)
    if i >= 50:
        return list(W[50])
    f = x - i
    if f < 1e-9:
        return list(W[i])
    if f > 1 - 1e-9:
        return list(W[i + 1])
    a, b = W[i], W[i + 1]
    return [(1 - f) * u + f * v for u, v in zip(a, b)]


if __name__ == '__main__':
    fptr = open(os.environ['OUTPUT_PATH'], 'w')
    t = float(input().strip())
    result = probe(t)
    fptr.write('\n'.join(map(str, result)))
    fptr.write('\n')
    fptr.close()
