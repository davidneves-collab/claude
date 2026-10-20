import numpy as np,cv2,sys,json
sys.path.insert(0,".")
import apply2
from apply2 import *
R=".."
def st(x):
    hsv=cv2.cvtColor(x.astype(np.float32),cv2.COLOR_RGB2HSV); y=x@LW
    return np.round([np.percentile(y,5),np.percentile(y,50),np.percentile(y,95),np.percentile(y,99),hsv[...,1].mean()],3)
PA=[(13,23),(47,57),(58,68),(1,12),(69,80)]
def frames():
    for a,b in PA:
        A=cv2.imread(f"{R}/f/{a:03d}.png")[:,:,::-1]/255.; B=cv2.imread(f"{R}/f/{b:03d}.png")[:,:,::-1]/255.
        H,W=A.shape[:2]; sl=(slice(int(.05*H),int(.95*H)),slice(int(.2*W),int(.9*W)))
        yield a,A[sl],B[sl]
def sat(G,s):
    Gy=G@LW; return np.clip(Gy[...,None]+(G-Gy[...,None])*s,0,1)
ym=[];yr=[]
apply2.SAT=1.0
for a,A,B in frames():
    o=look2(neutral_from_slog(A),True); ym.append((o@LW).ravel()); yr.append((B@LW).ravel())
ym=np.concatenate(ym); yr=np.concatenate(yr)
q=np.linspace(0,1,101); xm=np.quantile(ym,q); xr=np.quantile(yr,q)
xm=np.maximum.accumulate(xm+np.arange(101)*1e-6)
X=np.concatenate([[0],xm,[1]]); Y=np.concatenate([[0],xr,[min(1,xr[-1]+0.05)]])
X,iu=np.unique(X,return_index=True); Y=np.maximum.accumulate(Y[iu])
json.dump({"X":X.tolist(),"Y":Y.tolist()},open("tone2.json","w"))
def tone2(G):
    y=G@LW; y2=np.interp(y,X,Y); return np.clip(G*(y2/np.maximum(y,1e-4))[...,None],0,1)
S2=float(sys.argv[1]) if len(sys.argv)>1 else 1.0
rows=[]
for a,A,B in frames():
    o=sat(tone2(look2(neutral_from_slog(A),True)),S2)
    print(a,"mine",st(o),"ref",st(B))
    rows.append(cv2.resize(np.hstack([o,B]),(300,270)))
cv2.imwrite("val3.jpg",(np.hstack(rows)[:,:,::-1]*255).astype(np.uint8))
