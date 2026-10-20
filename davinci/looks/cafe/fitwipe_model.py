import numpy as np
from scipy.interpolate import RegularGridInterpolator
_d=np.load("wipefit.npz"); C=_d['C']; corr=_d['corr']; n=corr.shape[0]
g=np.linspace(0,1,n); I=RegularGridInterpolator((g,g,g),corr)
def feats(x):
    r,g_,b=x[...,0],x[...,1],x[...,2]; one=np.ones_like(r)
    return np.stack([one,r,g_,b,r*r,g_*g_,b*b,r*g_,r*b,g_*b,r**3,g_**3,b**3,r*r*g_,r*r*b,g_*g_*r,g_*g_*b,b*b*r,b*b*g_,r*g_*b],-1)
def model(x): return np.clip(feats(x)@C+I(np.clip(x,0,1).reshape(-1,3)).reshape(x.shape),0,1)
