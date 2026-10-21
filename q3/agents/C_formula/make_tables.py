import os, json; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
from numpy.fft import rfft, irfft
def dct_trunc(Z,K):
    E=np.concatenate([Z,Z[:,::-1]],1); F=rfft(E,axis=1); F[:,K:]=0
    return irfft(F,n=200,axis=1)[:,:100]
def pred(M): return np.clip(20*(1-((M-W)**2).mean(1)/(2*TGT)),0,20).sum()
loo=W.copy()
for i in range(1,50): loo[i]=(W[i-1]+W[i+1])/2
T_={'dct30':dct_trunc(W,30),'dct40':dct_trunc(W,40),'loo_lin':loo}
for k,v in T_.items(): print(k, 'pred %.1f'%pred(v))
json.dump({k:np.round(v,4).tolist() for k,v in T_.items()}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'tables.json'),'w'))
