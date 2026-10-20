import numpy as np,sys,json
sys.path.insert(0,sys.argv[1]); from colormath import *
from scipy.interpolate import PchipInterpolator
d=np.load(sys.argv[1]+"/fitdata.npz"); N,G=d['N'],d['G']
Ny=N@LW; Gy=G@LW
# --- luma curve: binned medians, smoothed, monotone
bins=np.linspace(0.18,0.86,18); xs=[];ys=[]
for a,b in zip(bins[:-1],bins[1:]):
    m=(Ny>=a)&(Ny<b)
    if m.sum()>500: xs.append(np.median(Ny[m])); ys.append(np.median(Gy[m]))
xs=np.array(xs); ys=np.maximum.accumulate(np.array(ys))
ys=np.convolve(np.pad(ys,1,mode='edge'),[.25,.5,.25],'valid')
X=np.concatenate([[0],xs,[1.0]]); Y=np.concatenate([[0],ys,[max(ys[-1]+0.04,0.95)]])
curve=PchipInterpolator(X,Y)
# --- chroma model: cG = s(bin)*(Mc @ cN) + o(bin)
cN=N-Ny[:,None]; cG=G-curve(Ny)[:,None]*0-Gy[:,None]
nb=6; e=np.linspace(0,1,nb+1); bi=np.clip(np.digitize(Ny,e)-1,0,nb-1)
# global 3x3 + per-bin offsets via lstsq
Xd=np.hstack([cN]+[ (bi==k)[:,None].astype(float) for k in range(nb)])
coef,*_=np.linalg.lstsq(Xd,cG,rcond=None)
Mc=coef[:3].T; off=coef[3:]
res=cG-Xd@coef
print("Mc",np.round(Mc,3).tolist()); print("offsets per luma bin",np.round(off,3).tolist())
print("rmse chroma",np.sqrt((res**2).mean()), "rmse luma",np.sqrt(((curve(Ny)-Gy)**2).mean()))
json.dump({"X":X.tolist(),"Y":Y.tolist(),"Mc":Mc.tolist(),"off":off.tolist(),"edges":e.tolist()},open(sys.argv[1]+"/model.json","w"))
print("curve pts",np.round(np.c_[X,Y],3).tolist())
