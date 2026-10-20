import numpy as np
def npm(prim,w=(0.3127,0.3290)):
    P=np.array([[x/y,1,(1-x-y)/y] for x,y in prim]).T
    W=np.array([w[0]/w[1],1,(1-w[0]-w[1])/w[1]])
    return P*np.linalg.solve(P,W)
SG3C=npm([(0.766,0.275),(0.225,0.800),(0.089,-0.087)])
DWG=npm([(0.8000,0.3130),(0.1682,0.9877),(0.0790,-0.1155)])
R709=npm([(0.64,0.33),(0.30,0.60),(0.15,0.06)])
SG3C_to_DWG=np.linalg.inv(DWG)@SG3C
DWG_to_709=np.linalg.inv(R709)@DWG
R709_to_DWG=np.linalg.inv(DWG_to_709)
def slog3_dec(x):
    x=np.asarray(x,float)
    return np.where(x>=171.2102946929/1023,10**((x*1023-420)/261.5)*(0.18+0.01)-0.01,(x*1023-95)*0.01125/(171.2102946929-95))
A_,B_,C_,M_,LC=0.0075,7.0,0.07329248,10.44426855,0.00262409
LOGCUT=0.02740668
def di_enc(l): l=np.asarray(l,float); return np.where(l<=LC,l*M_,(np.log2(np.maximum(l,LC)+A_)+B_)*C_)
def di_dec(v): v=np.asarray(v,float); return np.where(v<=LOGCUT,v/M_,2**(v/C_-B_)-A_)
def tm(l):  # neutral display render: soft rolloff then 2.4 encode
    l=np.maximum(l,0); t=l*(1+l/6)/(1+l)
    return np.clip(t,0,1)**(1/2.4)
LW=np.array([0.2126,0.7152,0.0722])
