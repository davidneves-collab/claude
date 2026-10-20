import numpy as np,json,sys
sys.path.insert(0,".")
from colormath import *
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter
d=np.load("wipe.npz"); X=d['X'].astype(np.float64); Y=d['Y'].astype(np.float64)
def neutral(v): return tm((slog3_dec(v)@SG3C_to_DWG.T)@DWG_to_709.T)
N=neutral(X); Ny=N@LW; Gy=Y@LW
# tone
e=np.quantile(Ny,np.linspace(0,1,51)); xs=[];ys=[]
for a,b in zip(e[:-1],e[1:]):
    m=(Ny>=a)&(Ny<b)
    if m.sum()>300: xs.append(np.median(Ny[m])); ys.append(np.median(Gy[m]))
xs=np.array(xs); ys=np.maximum.accumulate(np.array(ys))
X_=np.concatenate([[0],xs,[min(1,xs[-1]+0.1),1]]); Y_=np.concatenate([[0],ys,[min(1,ys[-1]+0.6*(1-ys[-1])),1]])
X_,iu=np.unique(X_,return_index=True); Y_=np.maximum.accumulate(Y_[iu]); curve=PchipInterpolator(X_,Y_)
# chroma per bin, ridge toward s*I
cN=N-Ny[:,None]; cG=Y-Gy[:,None]
nb=10; eb=np.quantile(Ny,np.linspace(0,1,nb+1)); cen=[];Ms=[];Os=[]
lam=2e3
for k in range(nb):
    m=(Ny>=eb[k])&(Ny<=eb[k+1]); A=cN[m]; B=cG[m]
    s=(A*B).sum()/max((A*A).sum(),1e-9)
    for it in range(2):
        Am=np.c_[A,np.ones(len(A))]
        R=np.zeros((4,4)); R[:3,:3]=np.eye(3)*lam
        T=np.zeros((4,3)); T[:3,:3]=np.eye(3)*s*lam
        sol=np.linalg.solve(Am.T@Am+R,Am.T@B+T)
        r=np.abs(Am@sol-B).sum(1); keep=r<np.percentile(r,90); A,B=A[keep],B[keep]
    cen.append(float(np.median(Ny[m]))); Ms.append(sol[:3].T.tolist()); Os.append(sol[3].tolist())
    print(round(cen[-1],3),"s",round(s,2),np.round(sol[:3].T,2).tolist(),np.round(sol[3],3).tolist())
json.dump({"X":X_.tolist(),"Y":Y_.tolist(),"cen":cen,"M":Ms,"O":Os},open("fit4.json","w"))
