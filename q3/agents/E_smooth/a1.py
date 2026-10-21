import sys,os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
print(len(W), set(len(r) for r in W))
# implied target from W
for i in range(51):
    s=sum(v*v for v in W[i])/200
    print(i, TGT[i], round(s,4), round(20*(2*s/TGT[i]-1) if False else s/TGT[i],4))
