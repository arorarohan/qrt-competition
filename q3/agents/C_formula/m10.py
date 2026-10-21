import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
from numpy.fft import rfft
F=rfft(W,axis=1)/50
for m in [1,2,3,4,5,6,7,8,10,12,13]:
    print('m=%d'%m)
    print(' amp ', ' '.join('%.2f'%a for a in np.abs(F[:,m])))
    print(' ph  ', ' '.join('%+.1f'%a for a in np.angle(F[:,m])))
