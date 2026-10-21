import json, numpy as np
import math
class stats:
    skew=staticmethod(lambda z: np.float64(((z-z.mean())**3).mean()/z.std()**3))
    kurtosis=staticmethod(lambda z: np.float64(((z-z.mean())**4).mean()/z.std()**4-3))
src=open('solution.py').read().rsplit('if __name__',1)[0]; ns={}; exec(src,ns); W=np.array(ns['W'])
TGT=np.array([0.0287,0.0247,0.0203,0.0217,0.0216,0.0161,0.019,0.0416,0.0725,0.0968,0.1234,0.1711,0.2343,0.2871,0.3154,0.3267,0.3312,0.3316,0.3318,0.3371,0.3461,0.3525,0.3534,0.3472,0.3314,0.3085,0.2831,0.2542,0.222,0.1945,0.1738,0.1515,0.1227,0.095,0.0773,0.0686,0.0623,0.0561,0.0515,0.0479,0.0443,0.0408,0.0374,0.0335,0.0297,0.0272,0.0257,0.0241,0.0232,0.0239,0.0246])
R=json.load(open('agents/D_noise/runs_raw.json'))
spike=lambda a: np.where(np.arange(100)==50,a,0.0)*np.ones((51,1))
tab={'W':W,'H':0.5*W,'C':np.ones((51,100)),'N':np.ones((51,100)),'S':spike(10),'Sp':spike(3),'X':1.9*W,'E':0.8*W}
def key(k):
    for p in ['Sp','W','H','C','N','S','X','E']:
        if k.startswith(p): return p
rows=[]
for k,(raw,hr) in R.items():
    w=tab[key(k)]; raw=np.array(raw); hr=np.array(hr)
    Edet=(w*W).mean(1)-0.5*(w*w).mean(1)
    E=np.where(hr>0, hr/20*TGT, Edet)
    for i in range(51):
        rows.append((k,key(k),i,raw[i]-E[i],np.sqrt((w[i]**2).mean()),np.abs(w[i]).mean(),abs(w[i].mean()),E[i],Edet[i],hr[i]))
r=np.array([x[3] for x in rows]); rms=np.array([x[4] for x in rows]); mabs=np.array([x[5] for x in rows]); amean=np.array([x[6] for x in rows])
grp=np.array([x[1] for x in rows]); runs=np.array([x[0] for x in rows])
print('per group: mean resid, std resid, mean rms(w), std/rms*10 (=sigma per point)')
for g in tab:
    m=grp==g; print(g, round(r[m].mean(),4), round(r[m].std(ddof=1),4), round(rms[m].mean(),3), round((r[m]/rms[m]).std()*10,3), 'n',m.sum())
for name,s in [('sqrt(mean w2)/10',rms/10),('mean|w|',mabs),('|mean w|',amean+1e-9)]:
    z=r/s; sig=np.sqrt((z**2).mean())
    ll=(-0.5*(r/(sig*s))**2-np.log(sig*s*math.sqrt(2*math.pi))).sum(); print(name,'sigma=',round(sig,4),'loglik=',round(ll,1))
z=r/(rms/10)
print('pooled z: mean',z.mean().round(4),'std',z.std(ddof=1).round(4),'skew',stats.skew(z).round(3),'exkurt',stats.kurtosis(z).round(3),'n',len(z))
n=len(z);jb=n/6*(stats.skew(z)**2+stats.kurtosis(z)**2/4);print('JB',round(jb,2),'(chi2_2 5% crit 5.99)','max|z|/std',(np.abs(z).max()/z.std()).round(2),'frac |z|>2sd',(np.abs(z)>2*z.std()).mean().round(4),'>3sd',(np.abs(z)>3*z.std()).mean().round(4))
print('mean z t-stat', (z.mean()/(z.std(ddof=1)/math.sqrt(len(z)))).round(2))
# heteroscedasticity in t for W runs: std per t across 5 W runs
m=grp=='W'; zz=z[m].reshape(-1,51); print('W runs per-t std of z (5 samples each) by t-bands', [round(zz[:,a:b].std(ddof=1),3) for a,b in [(0,10),(10,20),(20,30),(30,40),(40,51)]])
# correlation of residuals between identical runs (same seed?)
for a,b in [('Wa','Wb'),('Wa','Wc'),('Ha','Hb'),('C1','C2'),('S1','S2'),('N1a','N1b'),('X19a','X19b')]:
    print(a,b,'corr',np.corrcoef(r[runs==a],r[runs==b])[0,1].round(3))
# check hr identical in repeated tables
for a,b in [('Wa','Wb'),('Wa','Wc'),('Wa','Wd'),('Wa','We'),('Ha','Hb'),('X19a','X19b')]:
    print('hr identical',a,b,R[a][1]==R[b][1])
print('hr sums', {k:round(sum(v[1]),2) for k,v in R.items()})
# deterministic model check for X19 and H: predicted hr from W (as mu) vs actual
for k in ['Ha','X19a']:
    w=tab[key(k)]; Ed=(w*W).mean(1)-0.5*(w*w).mean(1); hr=np.array(R[k][1])
    print(k,'pred hr sum (W as mu)',round((20*Ed/TGT).sum(),2),'actual',round(hr.sum(),2))
np.save('agents/D_noise/z.npy',z)
print('\nsigma (=std of z) per group per t-band [0-9,10-19,20-29,30-39,40-50]')
bands=[(0,10),(10,20),(20,30),(30,40),(40,51)]
ti=np.array([x[2] for x in rows])
for g in tab:
    m=grp==g
    print(g,[round(float(np.sqrt((z[m&(ti>=a)&(ti<b)]**2).mean())),2) for a,b in bands])
print('\n-- sigma(t) fit --')
tt=ti/50
v=np.array([np.mean(z[ti==i]**2) for i in range(51)])  # 16 samples each
ts=np.arange(51)/50
for name,X in [('sigma=a+b t',np.c_[np.ones(51),ts])]:
    # fit sigma^2 ~ (a+bt)^2 via grid
    best=None
    for a in np.linspace(0.2,1.2,101):
        for b in np.linspace(0,2,201):
            s2=(a+b*ts)**2; nll=(np.log(s2)+v/s2).sum()
            if best is None or nll<best[0]: best=(nll,a,b)
    print(name,'a=%.3f b=%.3f'%best[1:])
best2=None
for a in np.linspace(0.1,2,191):
    for b in np.linspace(-1,3,401):
        s2=a+b*ts
        if (s2<=0).any(): continue
        nll=(np.log(s2)+v/s2).sum()
        if best2 is None or nll<best2[0]: best2=(nll,a,b)
print('sigma^2=a+b t: a=%.3f b=%.3f'%best2[1:], 'nll',round(best2[0],2),'vs linear-sigma nll',round(best[0],2))
const=v.mean(); print('const sigma^2',round(const,3),'nll',round((np.log(const)+v/const).sum(),2))
print('per-t sigma (rms z over 16 runs):',np.round(np.sqrt(v),2).tolist())
sig_t=best[1]+best[2]*tt
zn=z/sig_t
print('normalized: std',zn.std().round(3),'skew',round(float(stats.skew(zn)),3),'exkurt',round(float(stats.kurtosis(zn)),3))
n=len(zn);jb=n/6*(stats.skew(zn)**2+stats.kurtosis(zn)**2/4);print('JB',round(float(jb),2),'frac>2',(np.abs(zn)>2).mean().round(4),'(gauss .0455) >3',(np.abs(zn)>3).mean().round(4),'(.0027) max',np.abs(zn).max().round(2))
np.save('agents/D_noise/sig_ab.npy',np.array(best[1:]))
print('\n-- bias check: mean(raw - E) per group, t-stat --')
for g in tab:
    m=grp==g; print(g,'mean resid %.5f  SE %.5f  t=%.2f  n=%d'%(r[m].mean(), r[m].std(ddof=1)/math.sqrt(m.sum()), r[m].mean()/(r[m].std(ddof=1)/math.sqrt(m.sum())), m.sum()))
print('all: mean z/sigma(t) %.4f t=%.2f'%(zn.mean(), zn.mean()*math.sqrt(len(zn))))
