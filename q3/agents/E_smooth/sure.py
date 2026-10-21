import sys,os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import math
def sig(r):
    d4=[r[k-2]-4*r[k-1]+6*r[k]-4*r[k+1]+r[k+2] for k in range(2,98)]
    return math.sqrt(sum(v*v for v in d4)/len(d4)/70)
def smx(r,a):
    out=[]
    for k in range(100):
        l=r[k-1] if k>0 else r[k]; h=r[k+1] if k<99 else r[k]
        out.append(a*l+(1-2*a)*r[k]+a*h)
    return out
def smt(i,a):
    if i==0 or i==50: return W[i][:]
    return [a*W[i-1][k]+(1-2*a)*W[i][k]+a*W[i+1][k] for k in range(100)]
tot={}
for name,fn,diag in [('x',lambda i,a:smx(W[i],a),lambda a:1-2*a),('t',smt,lambda a:1-2*a)]:
  for a in [0.05,0.1,0.15,0.2,0.25]:
    gain=0
    for i in range(51):
        s=sig(W[i]); y=W[i]; f=fn(i,a)
        rss=sum((u-v)**2 for u,v in zip(f,y))
        risk=rss-100*s*s+2*s*s*100*diag(a)   # SURE estimate of sum (f-mu)^2
        risk0=100*s*s                        # raw data risk
        gain+=10*(risk0-risk)/100/TGT[i]
    print(name,a,round(gain,3))
