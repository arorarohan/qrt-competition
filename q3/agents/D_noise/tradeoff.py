import json, math, numpy as np
TGT=np.array([0.0287,0.0247,0.0203,0.0217,0.0216,0.0161,0.019,0.0416,0.0725,0.0968,0.1234,0.1711,0.2343,0.2871,0.3154,0.3267,0.3312,0.3316,0.3318,0.3371,0.3461,0.3525,0.3534,0.3472,0.3314,0.3085,0.2831,0.2542,0.222,0.1945,0.1738,0.1515,0.1227,0.095,0.0773,0.0686,0.0623,0.0561,0.0515,0.0479,0.0443,0.0408,0.0374,0.0335,0.0297,0.0272,0.0257,0.0241,0.0232,0.0239,0.0246])
a,b=np.load('agents/D_noise/sig_ab.npy'); t=np.arange(51)/50; sig=a+b*t
Phi=lambda x: 0.5*(1+np.vectorize(math.erf)(x/math.sqrt(2)))
phi=lambda x: np.exp(-x*x/2)/math.sqrt(2*math.pi)
def Eclip(m,s,lo,hi):  # E[clip(X,lo,hi)], X~N(m,s)
    A=(lo-m)/s; B=(hi-m)/s
    return lo*Phi(A)+hi*(1-Phi(B))+m*(Phi(B)-Phi(A))+s*(phi(A)-phi(B))
def per_case(c):
    m=20*(2*c-c*c)*np.ones(51)                   # mean score units
    s=20*c*sig*np.sqrt(2*TGT)/10/TGT              # std of 20*raw/T
    return m,s
print('raw-score noise std at c=1 (payoff units), selected t:',{round(x,2):round(float(sig[i]*math.sqrt(2*TGT[i])/10),4) for i,x in enumerate(t) if i%10==0})
print('same in hr points (20*std/T):',{round(x,2):round(float(20*sig[i]*math.sqrt(2*TGT[i])/10/TGT[i]),2) for i,x in enumerate(t) if i%10==0})
print('\n c | det hr total | noisy clip[0,20] | noisy clip[0,inf) (floor only) | noisy cap only(-inf,20] | Sharpe mean/std (avg over t)')
for c in [0.5,0.6,0.7,0.75,0.8,0.85,0.9,0.95,1.0]:
    m,s=per_case(c)
    det=m.sum(); both=Eclip(m,s,0,20).sum(); fl=Eclip(m,s,0,1e9).sum(); cap=Eclip(m,s,-1e9,20).sum()
    sh=(m/s).mean()
    print(f'{c:4} | {det:7.1f} | {both:7.1f} | {fl:7.1f} | {cap:7.1f} | {sh:5.2f}')
# optimal c per case under clip[0,20]
cs=np.linspace(0.3,1.0,701); best=[]
for i in range(51):
    vals=[Eclip(np.array([20*(2*c-c*c)]),np.array([20*c*sig[i]*math.sqrt(2*TGT[i])/10/TGT[i]]),0,20)[0] for c in cs]
    j=int(np.argmax(vals)); best.append((round(cs[j],3),round(vals[j],2),round(vals[-1],2)))
print('\nper-case optimal c under clip[0,20]:',[x[0] for x in best])
print('total with per-case c*:',round(sum(x[1] for x in best),1),'vs c=1:',round(sum(x[2] for x in best),1))
# empirical: noisy-clipped score of actual runs
R=json.load(open('agents/D_noise/runs_raw.json'))
for k in ['Wa','Wb','Wc','Wd','We','Ha','Hb','X19a','X19b']:
    raw=np.array(R[k][0]); print(k,'hr',round(sum(R[k][1]),1),'noisy clip[0,20] score',round(float(np.clip(20*raw/TGT,0,20).sum()),1),'uncapped',round(float((20*raw/TGT).sum()),1))
