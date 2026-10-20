import numpy as np,sys
sys.path.insert(0,".")
from colormath import *
import m4; m4.load_corr()
def slog3_enc(l):
    l=np.asarray(l,float)
    return np.where(l>=0.01125,(420+np.log10((np.maximum(l,0.01125)+0.01)/0.19)*261.5)/1023,(l*(171.2102946929-95)/0.01125+95)/1023)
n=33; g=np.linspace(0,1,n); b,gg,r=np.meshgrid(g,g,g,indexing='ij')
di=np.stack([r,gg,b],-1).reshape(-1,3)
lin_sg=di_dec(di)@np.linalg.inv(SG3C_to_DWG).T
G=m4.model(np.clip(slog3_enc(lin_sg),0,1))
out=di_enc(np.maximum((G**2.4)@R709_to_DWG.T,0))
with open("Look_Cafe_v4.cube","w") as f:
    f.write('TITLE "Look Cafe v4 (DWG/DaVinci Intermediate in, DWG/DaVinci Intermediate out)"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
    for v in out: f.write("%.6f %.6f %.6f\n"%tuple(v))
# end-to-end check through the baked LUT on the wipe frames
from scipy.interpolate import RegularGridInterpolator
import cv2
L=np.loadtxt("Look_Cafe_v4.cube",skiprows=4).reshape(33,33,33,3); I=RegularGridInterpolator((g,g,g),np.transpose(L,(2,1,0,3)))
def viaLUT(A):
    d=di_enc(slog3_dec(A)@SG3C_to_DWG.T); return np.clip(di_dec(I(np.clip(d,0,1).reshape(-1,3)).reshape(d.shape))@DWG_to_709.T,0,1)**(1/2.4)
d=np.load("wipe.npz"); X=d['X'].astype(np.float64)[::20]; Y=d['Y'].astype(np.float64)[::20]
print("rmse via LUT",np.sqrt(((viaLUT(X)-Y)**2).mean()).round(4),"model",np.sqrt(((m4.model(X)-Y)**2).mean()).round(4))
rows=[]
for t in (13,22,46,151,190,220):
    A=cv2.imread(f"../f30/{t:03d}.png")[:,:,::-1].astype(np.float64)/255; B=cv2.imread(f"../f30/{t+1:03d}.png")[:,:,::-1].astype(np.float64)/255
    dd=np.abs(B-A).mean(2)[20:-20].mean(0); k=int(dd.argmax())
    o=A.copy(); o[:,k:]=viaLUT(A[:,k:]); o[:,k-1:k+1]=[1,1,0]
    rows.append(o)
img=(np.hstack(rows)[:,:,::-1]*255).astype(np.uint8)
cv2.imwrite("comparacao_v4_cortina.jpg",img,[cv2.IMWRITE_JPEG_QUALITY,90])
