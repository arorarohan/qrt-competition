import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=2, suppress=True)
for k in [5,15,20,25,30,35,40,45,55,60,65,70,75,80,85,90,95]:
    print('x=%.3f'%X[k], W[:,k])
