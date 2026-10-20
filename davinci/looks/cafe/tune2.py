import numpy as np,cv2,sys,json
sys.path.insert(0,".")
import apply2
from apply2 import *
apply2.SAT=1.0
R=".."
t=json.load(open("tone2.json")); X,Y=np.array(t["X"]),np.array(t["Y"])
def tone2(G):
    y=G@LW; y2=np.interp(y,X,Y); return np.clip(G*(y2/np.maximum(y,1e-4))[...,None],0,1)
def sat(G,s):
    Gy=G@LW; return np.clip(Gy[...,None]+(G-Gy[...,None])*s,0,1)
PA=[(13,23),(47,57),(58,68),(1,12),(69,80)]
def frames():
    for a,b in PA:
        A=cv2.imread(f"{R}/f/{a:03d}.png")[:,:,::-1]/255.; B=cv2.imread(f"{R}/f/{b:03d}.png")[:,:,::-1]/255.
        H,W=A.shape[:2]; sl=(slice(int(.05*H),int(.95*H)),slice(int(.2*W),int(.9*W)))
        yield a,A[sl],B[sl]
S2=0.95
def stage(A): return sat(tone2(look2(neutral_from_slog(A),True)),S2)
# chroma offset per luma bin: distribution-level (quantile-aligned in luma)
e=np.linspace(0,1,11); c=(e[:-1]+e[1:])/2
om=np.zeros((10,3)); orf=np.zeros((10,3)); nm=np.zeros(10); nr=np.zeros(10)
for a,A,B in frames():
    o=stage(A).reshape(-1,3); b=B.reshape(-1,3)
    for arr,acc,cnt in ((o,om,nm),(b,orf,nr)):
        y=arr@LW; bi=np.clip(np.digitize(y,e)-1,0,9)
        for k in range(10):
            m=bi==k; acc[k]+=(arr[m]-y[m,None]).sum(0); cnt[k]+=m.sum()
off=orf/np.maximum(nr,1)[:,None]-om/np.maximum(nm,1)[:,None]
off[(nm<500)|(nr<500)]=0
print("chroma offsets by luma",np.round(off,3).tolist())
json.dump({"c":c.tolist(),"off":off.tolist(),"sat":S2},open("tone3.json","w"))
def final(A):
    G=stage(A); y=G@LW
    o=np.stack([np.interp(y,c,off[:,k]) for k in range(3)],-1)
    return np.clip(G+o,0,1)
def st(x):
    hsv=cv2.cvtColor(x.astype(np.float32),cv2.COLOR_RGB2HSV); y=x@LW
    return np.round([np.percentile(y,5),np.percentile(y,50),np.percentile(y,95),hsv[...,1].mean(),*(x.reshape(-1,3).mean(0))],3)
rows=[]
for a,A,B in frames():
    o=final(A); print(a,"mine",st(o),"ref",st(B))
    rows.append(cv2.resize(np.hstack([o,B]),(300,270)))
cv2.imwrite("val4.jpg",(np.hstack(rows)[:,:,::-1]*255).astype(np.uint8))
