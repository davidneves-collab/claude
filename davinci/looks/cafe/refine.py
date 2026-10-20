import numpy as np,sys,cv2,json
sys.path.insert(0,sys.argv[1]); from apply import *
R="/tmp/claude-0/-home-user-claude/9a1b4659-5c67-5fe1-8bf2-e9f9e4d7a521/scratchpad/ref"
SAT=1.15
def base(N):
    G=look_from_neutral(N); Gy=G@LW; return np.clip(Gy[...,None]+(G-Gy[...,None])*SAT,0,1)
# rebuild pairs with per-pair stats, motion-robust
PAIRS=[(13,23),(47,57),(58,68),(1,12),(69,80)]
Xs=[];Ys=[]
for a,b in PAIRS:
    A=cv2.imread(f"{R}/f/{a:03d}.png")[:,:,::-1].astype(np.float32)/255; B=cv2.imread(f"{R}/f/{b:03d}.png")[:,:,::-1].astype(np.float32)/255
    H,W=A.shape[:2]
    ga=cv2.Canny(cv2.cvtColor((A*255).astype(np.uint8),cv2.COLOR_RGB2GRAY),10,40).astype(np.float32)
    gb=cv2.Canny(cv2.cvtColor((B*255).astype(np.uint8),cv2.COLOR_RGB2GRAY),20,80).astype(np.float32)
    ga=cv2.GaussianBlur(ga,(9,9),0); gb=cv2.GaussianBlur(gb,(9,9),0)
    M=np.eye(2,3,dtype=np.float32)
    try: _,M=cv2.findTransformECC(ga,gb,M,cv2.MOTION_AFFINE,(3,200,1e-5),None,5)
    except cv2.error: pass
    Bw=cv2.warpAffine(B,M,(W,H),flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP)
    Ab=cv2.GaussianBlur(A,(0,0),3);Bb=cv2.GaussianBlur(Bw,(0,0),3)
    mask=np.zeros((H,W),bool); mask[int(.03*H):int(.97*H),int(.18*W):int(.9*W)]=True
    mask[int(.17*H):int(.33*H),int(.7*W):]=False
    N=neutral_from_slog(Ab); P=base(N)
    err=np.abs(P-Bb).sum(2)
    print(a,b,"rmse antes",round(float(np.sqrt(((P-Bb)[mask]**2).mean())),4))
    mask&=err<np.percentile(err[mask],85)       # drop motion outliers
    Xs.append(N[mask]); Ys.append(Bb[mask])
X=np.concatenate(Xs); Y=np.concatenate(Ys)
# residual 3D grid regression (kernel smoothing) in neutral space
n=17; res=Y-base(X)
idx=np.clip(np.round(X*(n-1)).astype(int),0,n-1)
acc=np.zeros((n,n,n,3)); cnt=np.zeros((n,n,n))
np.add.at(acc,(idx[:,0],idx[:,1],idx[:,2]),res); np.add.at(cnt,(idx[:,0],idx[:,1],idx[:,2]),1)
from scipy.ndimage import gaussian_filter
s=1.2
num=np.stack([gaussian_filter(acc[...,k],s) for k in range(3)],-1); den=gaussian_filter(cnt,s)
w=den/(den+20.0)                                  # confidence: fades to 0 where no data
corr=num/np.maximum(den,1e-9)[...,None]*w[...,None]
np.save(sys.argv[1]+"/corr.npy",corr)
print("cells with data",(cnt>0).sum(),"max corr",np.abs(corr).max())
