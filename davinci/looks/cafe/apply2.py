import numpy as np,sys
sys.path.insert(0,"/tmp/claude-0/-home-user-claude/9a1b4659-5c67-5fe1-8bf2-e9f9e4d7a521/scratchpad/ref/work")
from apply import *
from scipy.interpolate import RegularGridInterpolator
corr=np.load("/tmp/claude-0/-home-user-claude/9a1b4659-5c67-5fe1-8bf2-e9f9e4d7a521/scratchpad/ref/work/corr.npy")
n=corr.shape[0]; g=np.linspace(0,1,n)
I=RegularGridInterpolator((g,g,g),corr)
SAT=1.15
def look2(N,use_corr=True):
    G=look_from_neutral(N); Gy=G@LW; G=np.clip(Gy[...,None]+(G-Gy[...,None])*SAT,0,1)
    if use_corr: G=np.clip(G+I(np.clip(N,0,1).reshape(-1,3)).reshape(N.shape),0,1)
    return G
