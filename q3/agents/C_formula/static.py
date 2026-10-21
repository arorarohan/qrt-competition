import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=3, suppress=True)
from numpy.fft import rfft, irfft
F=rfft(W,axis=1)
G=F.copy(); G[:,:9]=0; H=irfft(G,n=100,axis=1)
s=H.mean(0)
print('highpass rms', np.sqrt((H**2).mean()), 'static part rms', np.sqrt((s**2).mean()), 'resid rms', np.sqrt(((H-s)**2).mean()))
print('static highpass pattern:', s)
# pattern by k mod 10
print('mean of H by k%10:', np.array([H[:,j::10].mean() for j in range(10)]))
print('mean of W - smooth by k%10:')
G2=F.copy(); G2[:,9:]=0; L=irfft(G2,n=100,axis=1); R=W-L
print(np.array([R[:,j::10].mean() for j in range(10)]))
print('per-t mean by k%10 rows sample'); 
for i in [0,10,20,30,40,50]: print(i, np.array([R[i,j::10].mean() for j in range(10)]))
