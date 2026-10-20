import numpy as np
from scipy.ndimage import gaussian_filter
d=np.load("wipe.npz"); X=d['X'].astype(np.float64); Y=d['Y'].astype(np.float64)
def feats(x):
    r,g,b=x[...,0],x[...,1],x[...,2]; one=np.ones_like(r)
    cols=[one,r,g,b,r*r,g*g,b*b,r*g,r*b,g*b,r**3,g**3,b**3,r*r*g,r*r*b,g*g*r,g*g*b,b*b*r,b*b*g,r*g*b]
    return np.stack(cols,-1)
# robust poly prior (2 passes, drop worst 10%)
w=np.ones(len(X),bool)
for it in range(2):
    C,*_=np.linalg.lstsq(feats(X[w]),Y[w],rcond=None)
    e=np.abs(feats(X)@C-Y).sum(1); w=e<np.percentile(e,90)
P=feats(X)@C
print("poly rmse",np.sqrt(((P-Y)[w]**2).mean()))
# residual grid in log domain
n=33; res=(Y-P)[w]; Xi=X[w]
idx=np.clip(np.round(Xi*(n-1)).astype(int),0,n-1)
acc=np.zeros((n,n,n,3)); cnt=np.zeros((n,n,n))
np.add.at(acc,(idx[:,0],idx[:,1],idx[:,2]),res); np.add.at(cnt,(idx[:,0],idx[:,1],idx[:,2]),1)
s=1.0
num=np.stack([gaussian_filter(acc[...,k],s) for k in range(3)],-1); den=gaussian_filter(cnt,s)
conf=den/(den+30)
corr=num/np.maximum(den,1e-9)[...,None]*conf[...,None]
np.savez("wipefit.npz",C=C,corr=corr)
from scipy.interpolate import RegularGridInterpolator
g=np.linspace(0,1,n); I=RegularGridInterpolator((g,g,g),corr)
def model(x): return np.clip(feats(x)@C+I(np.clip(x,0,1).reshape(-1,3)).reshape(x.shape),0,1)
M=model(Xi)
print("final rmse",np.sqrt(((M-Y[w])**2).mean()), "cells",int((cnt>0).sum()))
