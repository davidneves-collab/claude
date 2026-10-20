import numpy as np,cv2,sys
sys.path.insert(0,".")
from colormath import *
from scipy.interpolate import RegularGridInterpolator
g=np.linspace(0,1,33)
def lutf(path):
    L=np.loadtxt(path,skiprows=4).reshape(33,33,33,3); I=RegularGridInterpolator((g,g,g),np.transpose(L,(2,1,0,3)))
    return lambda d: I(np.clip(d,0,1).reshape(-1,3)).reshape(d.shape)
def render(L,A):
    d=di_enc(slog3_dec(A)@SG3C_to_DWG.T); return np.clip(di_dec(L(d))@DWG_to_709.T,0,1)**(1/2.4)
P=np.array([[1,-1,0],[0.5,0.5,-1]])
e=np.array([0,.03,.06,.1,.15,.22,.3,.4,.55,.7,1.01])
def prof(imgs):
    ch=np.zeros(10); ys=np.zeros(10); n=np.zeros(10); hue=np.zeros((10,2))
    for x in imgs:
        x=x.reshape(-1,3); y=x@LW; c=x@P.T; m=np.hypot(*c.T); bi=np.clip(np.digitize(y,e)-1,0,9)
        for k in range(10):
            s=bi==k; ch[k]+=m[s].sum(); n[k]+=s.sum(); hue[k]+=c[s].sum(0); ys[k]+=y[s].sum()
    n=np.maximum(n,1); return ch/n, n, hue/n[:,None], ys/n
if __name__=="__main__":
    L=lutf(sys.argv[1]); mine=[];ref=[]
    for a,b in [(13,23),(47,57),(58,68),(1,12),(69,80)]:
        A=cv2.imread(f"../f/{a:03d}.png")[:,:,::-1]/255.; B=cv2.imread(f"../f/{b:03d}.png")[:,:,::-1]/255.
        H,W=A.shape[:2]; sl=(slice(int(.05*H),int(.95*H)),slice(int(.2*W),int(.9*W)))
        mine.append(render(L,A)[sl]); ref.append(B[sl])
    cm,nm,hm,_=prof(mine); cr,nr,hr,_=prof(ref)
    for k in range(10): print(f"luma {e[k]:.2f}-{e[k+1]:.2f}  croma mine {cm[k]:.3f} ref {cr[k]:.3f} ratio {cr[k]/max(cm[k],1e-4):.2f}  px mine {int(nm[k])} ref {int(nr[k])}  hue mine {np.round(hm[k],3)} ref {np.round(hr[k],3)}")
