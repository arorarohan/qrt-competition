import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"load.py")).read())
# smooth with small gaussian in x and t
def sm(Z, sx, st):
    from numpy import exp
    kx=np.exp(-0.5*(np.arange(-8,9)/sx)**2); kx/=kx.sum()
    kt=np.exp(-0.5*(np.arange(-5,6)/st)**2); kt/=kt.sum()
    Z=np.array([np.convolve(np.pad(r,8,mode='edge'),kx,'valid') for r in Z])
    Z=np.array([np.convolve(np.pad(c,5,mode='edge'),kt,'valid') for c in Z.T]).T
    return Z
for sx,st in [(1,0.7),(2,1),(3,1.5)]:
    Z=sm(W,sx,st)
    utt=(Z[2:,1:-1]-2*Z[1:-1,1:-1]+Z[:-2,1:-1])/0.02**2
    uxx=(Z[1:-1,2:]-2*Z[1:-1,1:-1]+Z[1:-1,:-2])/0.01**2
    ut=(Z[2:,1:-1]-Z[:-2,1:-1])/0.04; ux=(Z[1:-1,2:]-Z[1:-1,:-2])/0.02
    a=utt.ravel(); b=uxx.ravel()
    c2=(a@b)/(b@b); r2=1-((a-c2*b)**2).sum()/(a**2).sum()
    # heat eqn ut = D uxx ; advection ut = -v ux
    a2=ut.ravel(); D=(a2@b)/(b@b); r2h=1-((a2-D*b)**2).sum()/(a2**2).sum()
    v=-(a2@ux.ravel())/(ux.ravel()@ux.ravel()); r2a=1-((a2+v*ux.ravel())**2).sum()/(a2**2).sum()
    print(sx,st,'wave c2=%.3f R2=%.3f | heat D=%.4f R2=%.3f | advect v=%.3f R2=%.3f'%(c2,r2,D,r2h,v,r2a))
