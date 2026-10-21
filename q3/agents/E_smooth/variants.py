import sys,os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
from svd import lowrank
import math
wts=[1/math.sqrt(t) for t in TGT]
def dist(V):
    per=[10*sum((a-b)**2 for a,b in zip(V[i],W[i]))/100/TGT[i] for i in range(51)]
    return sum(per), max(per)
def smx(r,a):
    return [a*(r[k-1] if k>0 else r[k])+(1-2*a)*r[k]+a*(r[k+1] if k<99 else r[k]) for k in range(100)]
res={}
for r in [11,12,13,14,15,16,18,20,25]:
    _,V=lowrank(W,r,wts); res['lr%d'%r]=V
    d=dist(V); print('lr',r,round(d[0],3),round(d[1],3), 'chk', round(sum(sum(row) for row in V),4))
for a in [0.1,0.2]:
    V=[smx(row,a) for row in W]; d=dist(V); print('smx',a,round(d[0],3),round(d[1],3))
