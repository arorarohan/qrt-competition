import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=2, suppress=True)
from numpy.fft import rfft, irfft, rfftfreq
E=np.concatenate([W,W[:,::-1]],1)  # period 2 in x (200 samples)
f=rfftfreq(200, d=0.01)  # cycles per unit x
F=rfft(E,axis=1)
P=(np.abs(F)**2).mean(0)
print('mean power by freq (cyc/unit):')
for j in range(0,60,2): print('%5.1f %.3g'%(f[j],P[j]), end=' | ')
print()
# log power slope -> Gaussian kernel? ln P ~ -(2 pi f sigma)^2 
for j in range(2,60,4):
    print(f[j], np.log(P[j]))
