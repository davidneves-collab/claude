import numpy as np,sys,json
sys.path.insert(0,sys.argv[1]); from colormath import *
from scipy.interpolate import PchipInterpolator
m=json.load(open(sys.argv[1]+"/model.json"))
curve=PchipInterpolator(m['X'],m['Y']); Mc=np.array(m['Mc']); off=np.array(m['off']); e=np.array(m['edges'])
def look_from_neutral(N,strength=1.0):
    Ny=N@LW; cN=N-Ny[...,None]
    # smooth per-luma offsets
    cen=(e[:-1]+e[1:])/2
    o=np.stack([np.interp(Ny,cen,off[:,k]) for k in range(3)],-1)
    cG=cN@Mc.T+o
    G=curve(np.clip(Ny,0,1))[...,None]+cG
    G=np.clip(G,0,1)
    return N*(1-strength)+G*strength
def neutral_from_di(di):
    lin=di_dec(di); return tm(lin@DWG_to_709.T)
def neutral_from_slog(v):
    return tm((slog3_dec(v)@SG3C_to_DWG.T)@DWG_to_709.T)
