# how well does interpolation in t work? leave-one-out on interior rows
import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
def hr(M,i): return max(0,20*(1-((M-W[i])**2).mean()/(2*TGT[i])))
lin=[];cub=[];near=[]
for i in range(2,49):
    lin.append(hr((W[i-1]+W[i+1])/2,i))
    cub.append(hr((-W[i-3 if i>=3 else i-1]*0+ (-W[i-2]+9*W[i-1]+9*W[i+1]-W[i+2])/16),i))
    near.append(hr(W[i-1],i))
n=len(lin)
print('LOO (h=0.02 from both neighbours, i.e. spacing 0.04) avg hr per case: nearest %.2f linear %.2f cubic %.2f'%(sum(near)/n,sum(lin)/n,sum(cub)/n))
# estimated midpoint quality: model error scales h^2 for linear -> error/4, sq err/16
lossl=[20-v for v in lin]; print('linear LOO avg loss %.2f -> est. midpoint loss at spacing 0.02 ~ %.2f per case'%(sum(lossl)/n, sum(lossl)/n/16))
lossn=[20-v for v in near]; print('nearest-row loss at dt=0.02: %.2f, so at dt=0.01 ~ %.2f per case'%(sum(lossn)/n, sum(lossn)/n/4))
