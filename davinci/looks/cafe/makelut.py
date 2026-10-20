import numpy as np,sys
sys.path.insert(0,sys.argv[1]); from apply import *
SAT=1.15; n=33
g=np.linspace(0,1,n)
b,gg,r=np.meshgrid(g,g,g,indexing='ij')   # .cube order: R fastest
di=np.stack([r,gg,b],-1).reshape(-1,3)
N=neutral_from_di(di@np.eye(3))
G=look_from_neutral(N)
Gy=G@LW; G=np.clip(Gy[:,None]+(G-Gy[:,None])*SAT,0,1)
lin709=G**2.4
out=di_enc(np.maximum(lin709@R709_to_DWG.T,0))
with open(sys.argv[2],"w") as f:
    f.write('TITLE "Look Cafe v1 (DWG/DaVinci Intermediate in, DWG/DaVinci Intermediate out)"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
    for v in out: f.write("%.6f %.6f %.6f\n"%tuple(v))
print("range",out.min(0),out.max(0))
