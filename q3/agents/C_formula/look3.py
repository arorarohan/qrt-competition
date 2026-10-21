import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=3, suppress=True)
jump = W[:,52:55].mean(1)-W[:,45:48].mean(1)
anti = [np.corrcoef(W[i], -W[i,::-1])[0,1] for i in range(51)]
for i in range(51): print('%.2f jump %6.3f anti %6.3f rms %.3f mean %.3f'%(T[i],jump[i],anti[i],np.sqrt((W[i]**2).mean()),W[i].mean()))
# derivative in x at center for each t: profile around 0.5 normalized
print('edge profiles (cols 40..60) normalized:')
for i in range(10,45,4):
    seg=W[i,40:61]; print('%.2f'%T[i], (seg-seg[:5].mean())/(seg[-5:].mean()-seg[:5].mean()))
