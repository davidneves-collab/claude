import numpy as np,json,os,sys
_h=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,_h)
from colormath import *
from scipy.interpolate import PchipInterpolator,RegularGridInterpolator
_m=json.load(open(os.path.join(_h,"fit4.json")))
curve=PchipInterpolator(_m["X"],_m["Y"]); cen=np.array(_m["cen"]); M=np.array(_m["M"]); O=np.array(_m["O"])
_corr=None
def neutral(v): return tm((slog3_dec(v)@SG3C_to_DWG.T)@DWG_to_709.T)
def base(N):
    Ny=N@LW; c=N-Ny[...,None]; Lc=np.clip(Ny,cen[0],cen[-1])
    Mi=np.stack([np.interp(Lc,cen,M[:,i,j]) for i in range(3) for j in range(3)],-1).reshape(Ny.shape+(3,3))
    Oi=np.stack([np.interp(Lc,cen,O[:,i]) for i in range(3)],-1)
    co=np.einsum('...ij,...j->...i',Mi,c)+Oi
    y=curve(np.clip(Ny,0,1)); out=y[...,None]+co
    out=out+(y-out@LW)[...,None]
    return np.clip(out,0,1)
def model_N(N):
    b=base(N)
    if _corr is not None: b=np.clip(b+_corr(np.clip(N,0,1).reshape(-1,3)).reshape(N.shape),0,1)
    return b
def model(v): return model_N(neutral(v))
def load_corr():
    global _corr
    c=np.load(os.path.join(_h,"m4corr.npy")); n=c.shape[0]; g=np.linspace(0,1,n); _corr=RegularGridInterpolator((g,g,g),c)
