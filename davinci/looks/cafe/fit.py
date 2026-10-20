import numpy as np,sys
sys.path.insert(0,sys.argv[1]); from colormath import *
d=np.load(sys.argv[1]+"/../work/pairs.npz") if False else np.load(sys.argv[2])
A,B,idx=d['A'],d['B'],None
# keep pairs 13,47,58 only (indices by blocks saved in order 1,13,47,58,69)
def neutral(logv):
    lin=slog3_dec(logv)@SG3C_to_DWG.T          # scene linear DWG
    return tm(lin@DWG_to_709.T)                 # neutral 709 display
N=neutral(A); G=B
Ny=N@LW; Gy=G@LW
ok=(Ny>0.01)&(Ny<0.99)
N,G,Ny,Gy=N[ok],G[ok],Ny[ok],Gy[ok]
# luma curve
bins=np.linspace(0,1,41); c=(bins[:-1]+bins[1:])/2; med=np.full(40,np.nan); cnt=np.zeros(40)
for i in range(40):
    m=(Ny>=bins[i])&(Ny<bins[i+1]); cnt[i]=m.sum()
    if m.sum()>200: med[i]=np.median(Gy[m])
print("luma bins (N->G):",[(round(a,2),round(b,3),int(n)) for a,b,n in zip(c,med,cnt) if not np.isnan(b)])
np.savez(sys.argv[2].replace('pairs','fitdata'),N=N,G=G)
