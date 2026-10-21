import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
np.set_printoptions(linewidth=250, precision=2, suppress=True)
for i in [0,10,20,25,30,40,50]:
    print(i, W[i])
U,S,Vt=np.linalg.svd(W,full_matrices=False)
print('sv',S[:15])
for r in [1,2,3,4,5,6,8,10,15,20]:
    M=(U[:,:r]*S[:r])@Vt[:r]; print(r, score(M)[0])
# sign map
for i in range(51):
    print('%4.2f '%T[i]+''.join('#' if v>0.3 else '+' if v>0.1 else '.' if v>-0.1 else '-' if v>-0.3 else '=' for v in W[i]))
