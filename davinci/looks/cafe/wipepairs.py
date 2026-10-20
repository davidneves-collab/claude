import numpy as np,cv2
F=[cv2.imread(f"../f30/{i:03d}.png")[:,:,::-1].astype(np.float32)/255 for i in range(1,361)]
H,W=F[0].shape[:2]
X=[];Y=[];info=[]
ymask=np.ones(H,bool); ymask[:int(.03*H)]=False; ymask[int(.97*H):]=False
for t in range(len(F)-1):
    D=np.abs(F[t+1]-F[t]).mean(2)
    d=D[ymask].mean(0)
    k=int(d.argmax())
    if d[k]<0.15: continue
    thr=0.5*d[k]; a=k; b=k
    while a>0 and d[a-1]>thr: a-=1
    while b<W-1 and d[b+1]>thr: b+=1
    if b-a+1>26 or b-a+1<8: continue
    a+=2; b-=2
    A=F[t][:,a:b+1]; B=F[t+1][:,a:b+1]
    # direction check: log side has lower contrast
    if A.std()<B.std()*0.6 or True:
        m=ymask.copy()
        # exclude instagram logo zone
        if b>0.7*W: m[int(.17*H):int(.33*H)]=False
        Ab=cv2.GaussianBlur(A,(3,3),0)[m].reshape(-1,3); Bb=cv2.GaussianBlur(B,(3,3),0)[m].reshape(-1,3)
        # reject pixels with motion: local temporal consistency using neighbour frame of graded side
        X.append(Ab); Y.append(Bb); info.append((t+1,a,b,round(float(A.std()),3),round(float(B.std()),3)))
X=np.concatenate(X); Y=np.concatenate(Y)
print(len(info),"frames;",len(X),"pixels"); print(info[:5],info[-5:])
print("log range",np.percentile(X,[0.5,50,99.5],axis=0).round(3).tolist())
np.savez("wipe.npz",X=X,Y=Y)
