import numpy as np,cv2,sys,json
sys.path.insert(0,".")
from colormath import *
from meas import lutf,render,prof,e
L2=lutf("Look_Cafe_v2.cube")
PA=[(13,23),(47,57),(58,68),(1,12),(69,80)]
def load():
    out=[]
    for a,b in PA:
        A=cv2.imread(f"../f/{a:03d}.png")[:,:,::-1]/255.; B=cv2.imread(f"../f/{b:03d}.png")[:,:,::-1]/255.
        H,W=A.shape[:2]; sl=(slice(int(.05*H),int(.95*H)),slice(int(.2*W),int(.9*W)))
        out.append((A[sl],B[sl]))
    return out
data=load()
EXTRA=float(sys.argv[1]) if len(sys.argv)>1 else 1.0
stages=[]   # list of (X,Y,ec,fac)
def post(G):
    for X,Y,ec,fac in stages:
        y=G@LW; y2=np.interp(y,X,Y); G=np.clip(G*(y2/np.maximum(y,1e-4))[...,None],0,1)
        y=G@LW; f=np.interp(y,ec,fac); G=np.clip(y[...,None]+(G-y[...,None])*f[...,None],0,1)
    return G
for it in range(3):
    mine=[post(render(L2,A)) for A,B in data]; ref=[B for A,B in data]
    ym=np.concatenate([(m@LW).ravel() for m in mine]); yr=np.concatenate([(r@LW).ravel() for r in ref])
    q=np.linspace(0,1,201); xm=np.quantile(ym,q); xr=np.quantile(yr,q)
    X=np.concatenate([[0],xm,[1]]); Y=np.concatenate([[0],xr,[1]])
    X,iu=np.unique(X,return_index=True); Y=np.maximum.accumulate(Y[iu])
    Y=np.convolve(np.pad(Y,3,mode='edge'),np.ones(7)/7,'valid')
    # chroma after tone
    tmp=[]
    for m in mine:
        y=m@LW; y2=np.interp(y,X,Y); tmp.append(np.clip(m*(y2/np.maximum(y,1e-4))[...,None],0,1))
    cm,_,_,_=prof(tmp); cr,_,_,_=prof(ref)
    ec=(e[:-1]+e[1:])/2; fac=np.clip(cr/np.maximum(cm,1e-4),0.8,1.6)
    fac=np.convolve(np.pad(fac,1,mode='edge'),[.25,.5,.25],'valid')
    stages.append((X,Y,ec,fac)); print("iter",it,"fac",np.round(fac,2))
# extra perceptual saturation in mids/darks (user preference)
if EXTRA!=1.0:
    ec=(e[:-1]+e[1:])/2; w=np.interp(ec,[0,.05,.15,.5,.7,1],[0,1,1,1,.3,0])
    stages.append((np.array([0,1.]),np.array([0,1.]),ec,1+(EXTRA-1)*w))
mine=[post(render(L2,A)) for A,B in data]; ref=[B for A,B in data]
cm,nm,_,_=prof(mine); cr,nr,_,_=prof(ref)
print("final croma ratio",np.round(cr/np.maximum(cm,1e-4),2)); print("px dark mine/ref",int(nm[0]),int(nr[0]))
# bake LUT v3: v2 then post (in display), back to DWG/DI
n=33; g=np.linspace(0,1,n); b,gg,r=np.meshgrid(g,g,g,indexing='ij')
di=np.stack([r,gg,b],-1).reshape(-1,3)
G=np.clip(di_dec(L2(di))@DWG_to_709.T,0,1)**(1/2.4)
G=post(G)
out=di_enc(np.maximum((G**2.4)@R709_to_DWG.T,0))
name=sys.argv[2]
with open(name,"w") as f:
    f.write(f'TITLE "{name[:-5]} (DWG/DaVinci Intermediate in, DWG/DaVinci Intermediate out)"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
    for v in out: f.write("%.6f %.6f %.6f\n"%tuple(v))
