import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
print(W.shape)
print('0.5 mean mu^2 vs TGT ratio:', np.round(0.5*(W**2).mean(1)/TGT,3))
print('self score', score(W)[0])
chars=' .:-=+*#%@'
mx=np.abs(W).max()
for i in range(51):
    print('%4.2f '%T[i] + ''.join(('+' if v>0 else '-') if abs(v)<0.05 else chars[min(9,int(abs(v)/mx*10))] if v>0 else chars[min(9,int(abs(v)/mx*10))].lower() for v in W[i]))
