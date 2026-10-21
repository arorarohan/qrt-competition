"""Rebuild the denoised variants (same maths as the JS used on the grader) and write solution.py
from a per-row choice of variant.  Usage: python -I build.py  (edit CHOICE below)."""
import sys,os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import W, TGT
from svd import lowrank, jacobi
import math
wts=[1/math.sqrt(t) for t in TGT]
def smx(M,a):
    return [[a*(r[k-1] if k>0 else r[k])+(1-2*a)*r[k]+a*(r[k+1] if k<99 else r[k]) for k in range(100)] for r in M]
def rescale(M,p=1.0):
    out=[]
    for i,r in enumerate(M):
        e=sum(v*v for v in r)/200; s=(TGT[i]/e)**(0.5*p); out.append([v*s for v in r])
    return out
def lrW(M,r): return lowrank(M,r,wts)[1]
def lrU(M,r): return lowrank(M,r,None)[1]
VARIANTS = {
    'base': lambda: W,
    'lr12': lambda: lrW(W,12), 'lr13': lambda: lrW(W,13), 'lr14': lambda: lrW(W,14),
    'lr16': lambda: lrW(W,16), 'lr20': lambda: lrW(W,20), 'lr30': lambda: lrW(W,30),
    'smx01': lambda: smx(W,0.1),
    'sx10_lr16': lambda: smx(lrW(W,16),0.1), 'sx05_lr16': lambda: smx(lrW(W,16),0.05),
    'sx20_lr16': lambda: smx(lrW(W,16),0.2), 'lrU13': lambda: lrU(W,13),
    'lr16_sx10': lambda: lrW(smx(W,0.1),16),
    'sc_sx05_lr16': lambda: rescale(smx(lrW(W,16),0.05)), 'sch_sx05_lr16': lambda: rescale(smx(lrW(W,16),0.05),0.5),
    'sc_base': lambda: rescale(W), 'sc_lr13': lambda: rescale(lrW(W,13)), 'sc_sx10_lr16': lambda: rescale(smx(lrW(W,16),0.1)),
}
def checksum(M): return round(sum(sum(r) for r in M),4)
if __name__=='__main__':
    import json
    CHOICE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'choice.json')))
    cache={}
    rows=[]
    for i,name in enumerate(CHOICE):
        if name not in cache: cache[name]=VARIANTS[name]()
        rows.append([round(v,5) for v in cache[name][i]])
    for n,M in cache.items(): print(n, checksum(M))
    body = ',\n'.join('['+','.join(repr(v) for v in r)+']' for r in rows)
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'template.py')).read()
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'solution.py'),'w').write(src.replace('@@W@@', body))
    print('wrote solution.py')
