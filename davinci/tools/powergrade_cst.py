"""Muda parâmetros do Color Space Transform (CST) de um nó de um PowerGrade (.drx).

Uso: python3 powergrade_cst.py entrada.drx saida.drx "CST IN" inputColorSpace=X inputGamma=Y [--label "2.2 C-Log3 FREE"]
Só altera parâmetros que já existem no nó (valores em texto, ex. REC709_COLORSPACE).
"""
import sys,re,zstandard
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from pb import varint
def enc_varint(n):
    out=bytearray()
    while True:
        b=n&0x7f; n>>=7
        if n: out.append(b|0x80)
        else: out.append(b); return bytes(out)
def fields(b):
    i=0; out=[]
    while i<len(b):
        st=i; key,i=varint(b,i); f,w=key>>3,key&7; ks=b[st:i]
        if w==0: s=i; _,i=varint(b,i); out.append((f,w,ks,b[s:i]))
        elif w==1: out.append((f,w,ks,b[i:i+8])); i+=8
        elif w==5: out.append((f,w,ks,b[i:i+4])); i+=4
        elif w==2: l,i=varint(b,i); out.append((f,w,ks,b[i:i+l])); i+=l
        else: raise ValueError("wire type")
    if i!=len(b): raise ValueError("tamanho")
    return out
def build(fs):
    return b"".join(ks+(enc_varint(len(p))+p if w==2 else p) for f,w,ks,p in fs)

def set_param(buf,name,value):
    """Procura recursivamente a entrada {1: name, 2: {5: valor}} e troca o valor."""
    if name not in buf: return buf,0
    try: fs=fields(buf)
    except Exception: return buf,0
    if build(fs)!=buf: return buf,0
    n=0; out=[]
    for f,w,ks,p in fs:
        if w==2 and name in p:
            sub=None
            try: sub=fields(p)
            except Exception: pass
            if sub and build(sub)==p and any(e[0]==1 and e[3]==name for e in sub):
                g=[]
                for e in sub:
                    if e[0]==2:
                        inner=fields(e[3])
                        inner=[(5,2,b'\x2a',value.encode()) if x[0]==5 else x for x in inner]
                        e=(e[0],e[1],e[2],build(inner)); n+=1
                    g.append(e)
                p=build(g)
            else:
                p,k=set_param(p,name,value); n+=k
        out.append((f,w,ks,p))
    return build(out),n

def main():
    a=sys.argv[1:]; label=None
    if "--label" in a: i=a.index("--label"); label=a[i+1]; del a[i:i+2]
    src,dst,node_name=a[0],a[1],a[2].encode()
    params=[x.split("=",1) for x in a[3:]]
    t=open(src).read()
    m=re.search(r"(<pClipFullVer>.*?<Body>)([0-9a-f]+)(</Body>)",t,re.S)
    raw=bytes.fromhex(m.group(2)); k=raw.find(b"\x28\xb5\x2f\xfd"); prefix=raw[:k]
    d=zstandard.ZstdDecompressor().decompress(raw[k:],max_output_size=10**8)
    hits=0
    def fix(node):
        nonlocal hits
        if not any(f==6 and p==node_name for f,w,ks,p in fields(node)): return node
        for pname,val in params:
            node,n=set_param(node,pname.encode(),val)
            if n==0: sys.exit(f"parâmetro {pname} não encontrado no nó {node_name.decode()}")
            hits+=n
        return node
    newtop=[]
    for f,w,ks,p in fields(d):
        if f==1 and w==2:
            p=build([(f2,w2,ks2,fix(p2) if f2==7 and w2==2 else p2) for f2,w2,ks2,p2 in fields(p)])
        newtop.append((f,w,ks,p))
    if not hits: sys.exit(f"nó {node_name.decode()} não encontrado")
    comp=zstandard.ZstdCompressor(level=19,write_content_size=True).compress(build(newtop))
    out=t[:m.start(2)]+(prefix+comp).hex()+t[m.end(2):]
    if label: out=re.sub(r"<Label>[^<]*</Label>","<Label>"+label+"</Label>",out,count=1)
    open(dst,"w").write(out)
    print("alterados:",hits)

if __name__=="__main__": main()
