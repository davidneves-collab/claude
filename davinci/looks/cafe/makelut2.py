import numpy as np,sys,json,cv2
sys.path.insert(0,".")
import apply2
from apply2 import *
apply2.SAT=1.0
t=json.load(open("tone2.json")); X,Y=np.array(t["X"]),np.array(t["Y"])
t3=json.load(open("tone3.json")); c,off,S2=np.array(t3["c"]),np.array(t3["off"]),t3["sat"]
def look_v2(N):
    G=look2(N,True); y=G@LW; y2=np.interp(y,X,Y); G=np.clip(G*(y2/np.maximum(y,1e-4))[...,None],0,1)
    Gy=G@LW; G=np.clip(Gy[...,None]+(G-Gy[...,None])*S2,0,1); y=G@LW
    return np.clip(G+np.stack([np.interp(y,c,off[:,k]) for k in range(3)],-1),0,1)
n=33; g=np.linspace(0,1,n); b,gg,r=np.meshgrid(g,g,g,indexing='ij')
di=np.stack([r,gg,b],-1).reshape(-1,3)
G=look_v2(neutral_from_di(di))
out=di_enc(np.maximum((G**2.4)@R709_to_DWG.T,0))
with open("Look_Cafe_v2.cube","w") as f:
    f.write('TITLE "Look Cafe v2 (DWG/DaVinci Intermediate in, DWG/DaVinci Intermediate out)"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
    for v in out: f.write("%.6f %.6f %.6f\n"%tuple(v))
# full-pipeline check through both LUTs
from scipy.interpolate import RegularGridInterpolator
def lutf(path):
    L=np.loadtxt(path,skiprows=4).reshape(33,33,33,3); I=RegularGridInterpolator((g,g,g),np.transpose(L,(2,1,0,3)))
    return lambda d: I(np.clip(d,0,1).reshape(-1,3)).reshape(d.shape)
L1,L2=lutf("Look_Cafe_v1.cube"),lutf("Look_Cafe_v2.cube")
rows=[]
for a,bb in [(13,23),(47,57),(58,68),(1,12),(69,80)]:
    A=cv2.imread(f"../f/{a:03d}.png")[:,:,::-1]/255.; B=cv2.imread(f"../f/{bb:03d}.png")[:,:,::-1]/255.
    d=di_enc(slog3_dec(A)@SG3C_to_DWG.T)
    r1=np.clip(di_dec(L1(d))@DWG_to_709.T,0,1)**(1/2.4); r2=np.clip(di_dec(L2(d))@DWG_to_709.T,0,1)**(1/2.4)
    rows.append(np.hstack([r1,r2,B]))
img=np.vstack([cv2.resize(r,(1392,832)) for r in rows])
img=cv2.resize(img,(1044,int(img.shape[0]*1044/1392)))
img=(img[:,:,::-1]*255).astype(np.uint8)
for i,t in enumerate(["v1","v2","referencia"]):
    cv2.putText(img,t,(10+i*348,30),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,255,255),2)
cv2.imwrite("comparacao_v1_v2.jpg",img,[cv2.IMWRITE_JPEG_QUALITY,88])
print(img.shape)
