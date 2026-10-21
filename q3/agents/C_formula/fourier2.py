import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=4, suppress=True)
from numpy.fft import rfft, irfft
F=rfft(W,axis=1)
P=(np.abs(F)**2).mean(0)
print('periodic(period1) power by m:', P[:30])
def pred(M):
    return np.clip(20*(1-((M-W)**2).mean(1)/(2*TGT)),0,20)
for m in range(4,16):
    G=F.copy(); G[:,m+1:]=0; M=irfft(G,n=100,axis=1); print('periodic m<=',m, pred(M).sum().round(1), 'rms resid %.4f'%np.sqrt(((M-W)**2).mean()))
# per-t power spectrum example
for i in [0,20,40]:
    print(i, np.abs(F[i,:20]).round(2))
