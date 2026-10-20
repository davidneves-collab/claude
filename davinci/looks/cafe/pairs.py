import cv2,numpy as np,sys
S=sys.argv[1]
PAIRS=[(1,12),(13,23),(47,57),(58,68),(69,80)]
def ld(i): return cv2.imread(f"{S}/f/{i:03d}.png")[:,:,::-1].astype(np.float32)/255
allA=[];allB=[]
for a,b in PAIRS:
    A=ld(a);B=ld(b);H,W=A.shape[:2]
    ga=cv2.GaussianBlur(cv2.cvtColor((A*255).astype(np.uint8),cv2.COLOR_RGB2GRAY),(5,5),0)
    gb=cv2.GaussianBlur(cv2.cvtColor((B*255).astype(np.uint8),cv2.COLOR_RGB2GRAY),(5,5),0)
    # normalise contrast for alignment (log vs graded differ): use edges
    ea=cv2.Canny(ga,10,40).astype(np.float32); eb=cv2.Canny(gb,20,80).astype(np.float32)
    ea=cv2.GaussianBlur(ea,(9,9),0); eb=cv2.GaussianBlur(eb,(9,9),0)
    M=np.eye(2,3,dtype=np.float32)
    try:
        _,M=cv2.findTransformECC(ea,eb,M,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,200,1e-5),None,5)
    except cv2.error as e: print("ecc fail",a,b)
    Bw=cv2.warpAffine(B,M,(W,H),flags=cv2.INTER_LINEAR+cv2.WARP_INVERSE_MAP)
    mask=np.zeros((H,W),bool); mask[int(.03*H):int(.97*H),int(.18*W):int(.9*W)]=True
    mask[int(.17*H):int(.33*H),int(.7*W):]=False
    # reject misaligned: local edge mismatch -> use blurred images, drop high-gradient pixels
    gA=np.abs(cv2.Laplacian(cv2.GaussianBlur(A,(0,0),2),cv2.CV_32F)).sum(2)
    mask&=gA<np.percentile(gA,70)
    Ab=cv2.GaussianBlur(A,(0,0),2);Bb=cv2.GaussianBlur(Bw,(0,0),2)
    allA.append(Ab[mask]);allB.append(Bb[mask])
    print(a,b,"M",np.round(M,3).tolist(),"n",mask.sum(),"logpct",np.round(np.percentile(Ab[mask].mean(1),[0.5,5,50,95,99.5]),3))
    cv2.imwrite(f"{S}/work/al_{a}.png",(np.hstack([A,Bw])[:,:,::-1]*255).astype(np.uint8))
np.savez(f"{S}/work/pairs.npz",A=np.concatenate(allA),B=np.concatenate(allB))
