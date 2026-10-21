import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=3, suppress=True)
# per-row truncated real Fourier (DCT-II with even extension handles non-periodic ends)
from numpy.fft import rfft, irfft
def dct_trunc(Z,K):
    # even extension -> no boundary jumps
    E=np.concatenate([Z,Z[:,::-1]],1)
    F=rfft(E,axis=1); F[:,K:]=0
    return irfft(F,n=200,axis=1)[:,:100]
def pred(M):
    hr=20*(1-((M-W)**2).mean(1)/(2*TGT)); return np.clip(hr,0,20)
for K in [5,8,10,12,15,20,25,30,40,50]:
    print('DCT K',K, pred(dct_trunc(W,K)).sum().round(1))
# 2D: also truncate in t
def dct2(Z,K,L):
    M=dct_trunc(Z,K)
    E=np.concatenate([M,M[::-1]],0)
    F=rfft(E,axis=0); F[L:]=0
    return irfft(F,n=102,axis=0)[:51]
for K,L in [(20,10),(20,15),(20,20),(30,20),(30,26),(40,26)]:
    print('2D',K,L,pred(dct2(W,K,L)).sum().round(1))
print('W itself', pred(W).sum())
