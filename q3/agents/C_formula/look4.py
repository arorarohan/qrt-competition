import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=2, suppress=True)
S=(W+W[:,::-1])/2; A=(W-W[:,::-1])/2
print('energy sym/anti per t'); print(np.round((S**2).mean(1),3)); print(np.round((A**2).mean(1),3))
def m(Z,name):
    print(name)
    for i in range(0,51):
        print('%4.2f '%T[i]+''.join('#' if v>0.6 else '+' if v>0.2 else '.' if v>-0.2 else '-' if v>-0.6 else '=' for v in Z[i,:50]))
m(S,'sym (x<0.5 shown)'); m(A,'anti (x<0.5, negated sign means left side)')
print('rms 2nd diff in t', np.sqrt((np.diff(W,2,axis=0)**2).mean()), 'in x', np.sqrt((np.diff(W,2,axis=1)**2).mean()))
