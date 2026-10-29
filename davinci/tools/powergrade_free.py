"""Retira de um PowerGrade (.drx) as ferramentas exclusivas do DaVinci Studio, deixando os nós vazios.

Uso: python3 powergrade_free.py entrada.drx saida.drx
Remove: ResolveFX da lista STUDIO e o separador de Noise Reduction (id 15). Acrescenta ' FREE' à etiqueta.
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
    return out
def build(fs):
    return b"".join(ks+(enc_varint(len(p))+p if w==2 else p) for f,w,ks,p in fs)
def first_varint(msg,fid):
    for f,w,ks,p in fields(msg):
        if f==fid and w==0: return varint(p,0)[0]
removed=[]
STUDIO=[b'resolvefx.glow',b'resolvefx.filmlook',b'resolvefx.colortonediffuser',b'resolvefx.halationplugin',b'resolvefx.filmgrain',b'resolvefx.halation']
def fix_node(node):
    fs=fields(node); nid=first_varint(node,1); out=[]
    name=[p for f,w,ks,p in fs if f==6]
    for f,w,ks,p in fs:
        if f==10 and w==2:
            sub=fields(p); keep=[]
            for e in sub:
                t=first_varint(e[3],1) if e[0]==1 else None
                if t is not None and t!=3221225473:
                    blob=e[3]
                    hit=[x for x in STUDIO if x in p]
                    if hit: removed.append((nid,hit[0].decode(),t)); continue
                keep.append(e)
            p=build(keep)
        if f==9 and w==2:
            sub=fields(p); keep=[]
            for e in sub:
                if e[0]==1 and first_varint(e[3],1)==15: removed.append((nid,"NR")); continue
                keep.append(e)
            p=build(keep)
        if f==11 and w==2:
            try:
                g=[]
                for f2,w2,ks2,p2 in fields(p):
                    if f2==7 and w2==2: p2=fix_node(p2)
                    g.append((f2,w2,ks2,p2))
                p=build(g)
            except Exception: pass
        out.append((f,w,ks,p))
    return build(out)
src,dst=sys.argv[1],sys.argv[2]
t=open(src).read()
m=re.search(r"(<pClipFullVer>.*?<Body>)([0-9a-f]+)(</Body>)",t,re.S)
raw=bytes.fromhex(m.group(2)); k=raw.find(b"\x28\xb5\x2f\xfd"); prefix=raw[:k]
d=zstandard.ZstdDecompressor().decompress(raw[k:],max_output_size=10**8)
top=fields(d); newtop=[]
for f,w,ks,p in top:
    if f==1 and w==2:
        g=[]
        for f2,w2,ks2,p2 in fields(p):
            if f2==7 and w2==2: p2=fix_node(p2)
            g.append((f2,w2,ks2,p2))
        p=build(g)
    newtop.append((f,w,ks,p))
nd=build(newtop)
# caminhos de LUT gravados no Windows ('Film Looks\\x.cube') passam a '/' como nas exportações do Mac (mesmo tamanho: o protobuf continua válido)
nd=re.sub(rb"[ -~]{1,200}?\.cube", lambda m: m.group(0).replace(b"\\", b"/"), nd)
assert build(top)==d, "roundtrip mismatch"
comp=zstandard.ZstdCompressor(level=19,write_content_size=True).compress(nd)
nb=(prefix+comp).hex()
out=t[:m.start(2)]+nb+t[m.end(2):]
out=re.sub(r"<Label>([^<]*)</Label>",lambda m:"<Label>"+m.group(1)+" FREE</Label>",out,count=1)
open(dst,"w").write(out)
print(removed, len(d), len(nd))
print("remaining studio:",[x for x in STUDIO if x in nd]); print("cst:",nd.count(b"colorspacetransformv2"), "cube:", b".cube" in nd)
