import sys,os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import math
# second differences along x and t, rms per row
print("row  tgt  rms_d2x  rms_d2t  max|d2x| at  plateaus(x-equal-runs)")
for i in range(51):
    r=W[i]
    d2x=[r[k-1]-2*r[k]+r[k+1] for k in range(1,99)]
    if 0<i<50: d2t=[W[i-1][k]-2*r[k]+W[i+1][k] for k in range(100)]
    else: d2t=[0]
    eq=sum(1 for k in range(99) if r[k]==r[k+1])
    eqt=sum(1 for k in range(100) if i<50 and r[k]==W[i+1][k])
    km=max(range(98),key=lambda k:abs(d2x[k]))
    print(i,TGT[i],round(math.sqrt(sum(v*v for v in d2x)/len(d2x)),4),round(math.sqrt(sum(v*v for v in d2t)/len(d2t)),4),round(d2x[km],3),km+1,eq,eqt)
