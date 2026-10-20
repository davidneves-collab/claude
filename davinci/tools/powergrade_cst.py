"""Muda parâmetros do Color Space Transform (CST) de um nó de um PowerGrade (.drx).

Uso: python3 powergrade_cst.py entrada.drx saida.drx "CST IN" inputColorSpace=X inputGamma=Y [--label "2.2 C-Log3 FREE"]
     [--node "OUTRO NÓ" param=valor ...] [--replace "texto antigo=>texto novo"]
Só altera parâmetros que já existem no nó (valores em texto, ex. REC709_COLORSPACE).
Procura também dentro de nós compostos. Um nó sem nome escreve-se "". --replace troca um texto exato
(ex. caminho de uma LUT ou nome de um nó) em todo o grade.
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

def replace_str(buf,old,new):
    """Troca recursivamente um campo de texto cujo conteúdo é exatamente old."""
    if old not in buf: return buf,0
    try: fs=fields(buf)
    except Exception: return buf,0
    if build(fs)!=buf: return buf,0
    n=0; out=[]
    for f,w,ks,p in fs:
        if w==2 and p==old: p=new; n+=1
        elif w==2: p,k=replace_str(p,old,new); n+=k
        out.append((f,w,ks,p))
    return build(out),n

def main():
    a=sys.argv[1:]; label=None; reps=[]
    while "--label" in a: i=a.index("--label"); label=a[i+1]; del a[i:i+2]
    while "--replace" in a: i=a.index("--replace"); reps.append([x.encode() for x in a[i+1].split("=>",1)]); del a[i:i+2]
    src,dst=a[0],a[1]; jobs=[]; cur=None
    for x in a[2:]:
        if x=="--node": continue
        if "=" in x and cur is not None: cur[1].append(x.split("=",1))
        else: cur=[x.encode(),[]]; jobs.append(cur)
    t=open(src).read()
    m=re.search(r"(<pClipFullVer>.*?<Body>)([0-9a-f]+)(</Body>)",t,re.S)
    raw=bytes.fromhex(m.group(2)); k=raw.find(b"\x28\xb5\x2f\xfd"); prefix=raw[:k]
    d=zstandard.ZstdDecompressor().decompress(raw[k:],max_output_size=10**8)
    found=set(); hits=0
    def fix(node):
        nonlocal hits
        nfs=fields(node); name=b"".join(p for f,w,ks,p in nfs if f==6)
        for jname,params in jobs:
            if name!=jname or not params: continue
            if b"colorspacetransform" not in node: continue
            for pname,val in params:
                node,n=set_param(node,pname.encode(),val)
                if n==0: sys.exit(f"parâmetro {pname} não encontrado no nó {jname.decode()!r}")
                hits+=n
            found.add(jname)
        out=[]
        for f,w,ks,p in fields(node):
            if f==11 and w==2:
                try: p=graph(p)
                except Exception: pass
            out.append((f,w,ks,p))
        return build(out)
    def graph(g):
        return build([(f,w,ks,fix(p) if f==7 and w==2 else p) for f,w,ks,p in fields(g)])
    newtop=[(f,w,ks,graph(p) if f==1 and w==2 else p) for f,w,ks,p in fields(d)]
    for jname,params in jobs:
        if params and jname not in found: sys.exit(f"nó {jname.decode()!r} com CST não encontrado")
    body=build(newtop)
    for old,new in reps:
        body,n=replace_str(body,old,new)
        if n==0: sys.exit(f"texto {old.decode()!r} não encontrado")
        hits+=n
    comp=zstandard.ZstdCompressor(level=19,write_content_size=True).compress(body)
    out=t[:m.start(2)]+(prefix+comp).hex()+t[m.end(2):]
    if label: out=re.sub(r"<Label>[^<]*</Label>","<Label>"+label+"</Label>",out,count=1)
    open(dst,"w").write(out)
    print("alterados:",hits)

if __name__=="__main__": main()
