# writes solution.py: S4 table W projected onto the first 30 DCT-II modes in x (Run Code 1019.60),
# with linear interpolation in t for off-grid t.
import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
from numpy.fft import rfft, irfft
E=np.concatenate([W,W[:,::-1]],1); F=rfft(E,axis=1); F[:,30:]=0
D=irfft(F,n=200,axis=1)[:,:100]
rows=',\n'.join('['+','.join('%.4f'%v for v in r)+']' for r in D)
src='''#!/bin/python3
# Q3 Black-box: S4 table (solution.py in q3/) denoised by keeping the first 30 DCT-II modes in x per t.
# Run Code score 1019.60 / 1020 (S4 raw table: 1019.40). Off-grid t: linear interpolation in t.

import os

W = [
%s,
]


def probe(t):
    u = min(max(float(t), 0.0), 1.0) * 50
    i = min(int(u), 49)
    f = u - i
    if f < 1e-9:
        return W[i]
    if f > 1 - 1e-9:
        return W[i + 1]
    return [(1 - f) * a + f * b for a, b in zip(W[i], W[i + 1])]


if __name__ == '__main__':
    fptr = open(os.environ['OUTPUT_PATH'], 'w')
    t = float(input().strip())
    result = probe(t)
    fptr.write('\n'.join(map(str, result)))
    fptr.write('\n')
    fptr.close()
''' % rows
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'solution.py'),'w').write(src)
# self-check
ns={}; exec(src.split("if __name__")[0], ns)
err=max(abs(ns['probe'](i/50)[k]-D[i,k]) for i in range(51) for k in range(100))
print('max grid err', err, 'probe(0.31) len', len(ns['probe'](0.31)), 'probe(1.0) ok', ns['probe'](1.0)==ns['W'][50])
