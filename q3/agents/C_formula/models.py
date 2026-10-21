import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=3, suppress=True)
from numpy.fft import rfft, irfft
def pred(M): return np.clip(20*(1-((M-W)**2).mean(1)/(2*TGT)),0,20)
F=rfft(W,axis=1)
def keep(ms, F=F):
    G=np.zeros_like(F); G[:,ms]=F[:,ms]; return irfft(G,n=100,axis=1)
A=keep(list(range(9)))
H=W-A; s=H.mean(0)
B=A+s
Fs=rfft(s)/50
print('static pattern coeffs amp:', np.abs(Fs[:51]).round(3))
print('static phases m=10..14', np.angle(Fs[10:15]).round(2))
C=keep(list(range(9))+[10,12,13])
for name,M in [('A lowpass8',A),('B A+static',B),('C lp8+10,12,13 per t',C)]:
    r=M-W; print(name, 'pred %.1f'%pred(M).sum(), 'resid rms %.4f'%np.sqrt((r**2).mean()))
r=B-W
P=(np.abs(rfft(r,axis=1))**2).mean(0)/100
print('B residual power/100 by m (white => flat = sigma^2):', P.round(5))
print('B resid rms by t:', np.sqrt((r**2).mean(1)).round(3))
