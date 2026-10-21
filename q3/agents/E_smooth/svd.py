import sys,os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import math
def jacobi(A):
    n=len(A); A=[r[:] for r in A]; V=[[float(i==j) for j in range(n)] for i in range(n)]
    for sweep in range(60):
        off=sum(A[i][j]**2 for i in range(n) for j in range(n) if i!=j)
        if off<1e-22: break
        for p in range(n):
            for q in range(p+1,n):
                if abs(A[p][q])<1e-15: continue
                th=(A[q][q]-A[p][p])/(2*A[p][q])
                t=(1 if th>=0 else -1)/(abs(th)+math.sqrt(th*th+1))
                c=1/math.sqrt(t*t+1); s=t*c
                for k in range(n):
                    akp,akq=A[k][p],A[k][q]
                    A[k][p]=c*akp-s*akq; A[k][q]=s*akp+c*akq
                for k in range(n):
                    apk,aqk=A[p][k],A[q][k]
                    A[p][k]=c*apk-s*aqk; A[q][k]=s*apk+c*aqk
                for k in range(n):
                    vkp,vkq=V[k][p],V[k][q]
                    V[k][p]=c*vkp-s*vkq; V[k][q]=s*vkp+c*vkq
    ev=[A[i][i] for i in range(n)]
    order=sorted(range(n),key=lambda i:-ev[i])
    return [ev[i] for i in order],[[V[k][i] for k in range(n)] for i in order]
def lowrank(M,r,weights=None):
    # rows weighted by 1/sqrt(tgt) so error is in hr units
    n=len(M); w=weights or [1]*n
    X=[[v*w[i] for v in M[i]] for i in range(n)]
    G=[[sum(a*b for a,b in zip(X[i],X[j])) for j in range(n)] for i in range(n)]
    ev,U=jacobi(G)
    out=[[0.0]*100 for _ in range(n)]
    for j in range(r):
        u=U[j]; v=[sum(u[i]*X[i][k] for i in range(n)) for k in range(100)]
        for i in range(n):
            for k in range(100): out[i][k]+=u[i]*v[k]
    return ev,[[out[i][k]/w[i] for k in range(100)] for i in range(n)]
if __name__=='__main__':
    wts=[1/math.sqrt(t) for t in TGT]
    ev,_=lowrank(W,0,wts)
    tot=sum(ev)
    print([round(e,3) for e in ev[:51]])
    for r in [10,15,20,25,30,35,40,45]:
        print(r, 'residual hr-loss if truth were lowrank:', round(10*sum(ev[r:])/100,3))
