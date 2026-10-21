import sys,os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import math
print(W[20]); print(W[0]); print(W[45])
for i in range(51):
    r=W[i]
    d4=[r[k-2]-4*r[k-1]+6*r[k]-4*r[k+1]+r[k+2] for k in range(2,98)]
    s=math.sqrt(sum(v*v for v in d4)/len(d4))/math.sqrt(70)
    # loss if row had iid noise s: 10*s^2/tgt
    print(i, round(s,4), round(10*s*s/TGT[i],4))
