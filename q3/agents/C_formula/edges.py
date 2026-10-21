# per-t model: mu(x) = c0 + sum_j a_j * sigmoid((x-b_j)/w) + static ripple; greedy edge selection
import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=3, suppress=True)
from numpy.fft import rfft, irfft
def pred(M): return np.clip(20*(1-((M-W)**2).mean(1)/(2*TGT)),0,20)
F=rfft(W,axis=1); G=np.zeros_like(F); G[:,:9]=F[:,:9]; A=irfft(G,n=100,axis=1)
s=(W-A).mean(0)  # static ripple estimate
R=W-s
cands=np.arange(-0.1,1.1001,0.005)
def basis(bs,w):
    return np.column_stack([np.ones(100)]+[0.5*(1+np.tanh((X-b)/w)) for b in bs])
def fitrow(y,nedge,w):
    bs=[]
    for _ in range(nedge):
        best=None
        for b in cands:
            Bm=basis(bs+[b],w); c,*_=np.linalg.lstsq(Bm,y,rcond=None); e=((Bm@c-y)**2).sum()
            if best is None or e<best[0]: best=(e,b)
        bs.append(best[1])
        # refine all positions (coordinate descent)
        for it in range(3):
            for j in range(len(bs)):
                bestj=None
                for b in bs[j]+np.arange(-0.03,0.0301,0.0025):
                    tb=bs.copy(); tb[j]=b; Bm=basis(tb,w); c,*_=np.linalg.lstsq(Bm,y,rcond=None); e=((Bm@c-y)**2).sum()
                    if bestj is None or e<bestj[0]: bestj=(e,b)
                bs[j]=bestj[1]
    Bm=basis(bs,w); c,*_=np.linalg.lstsq(Bm,y,rcond=None)
    return Bm@c, bs, c
import sys
for w in [0.012,0.02]:
  for ne in [4,6,8]:
    M=np.zeros_like(W); info=[]
    for i in range(51):
        m,bs,c=fitrow(R[i],ne,w); M[i]=m+s; info.append((bs,c))
    print('w=%.3f edges=%d pred %.1f'%(w,ne,pred(M).sum()), flush=True)
    if ne==6 and w==0.02:
        for i in range(0,51,5): print(' t=%.2f'%T[i], 'b=',np.round(sorted(info[i][0]),3))
