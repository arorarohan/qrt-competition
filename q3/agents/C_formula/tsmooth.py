import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
from numpy.fft import rfft, irfft
def dct_trunc(Z,K):
    E=np.concatenate([Z,Z[:,::-1]],1); F=rfft(E,axis=1); F[:,K:]=0
    return irfft(F,n=200,axis=1)[:,:100]
def pred(M): return np.clip(20*(1-((M-W)**2).mean(1)/(2*TGT)),0,20).sum()
for K in [26,28,30,32,35]:
    D=dct_trunc(W,K)
    for a in [0,0.05,0.1,0.15]:
        S=D.copy(); S[1:-1]=(1-2*a)*D[1:-1]+a*(D[:-2]+D[2:])
        print(K,a,'%.2f'%pred(S))
