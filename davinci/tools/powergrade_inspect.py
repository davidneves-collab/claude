"""Lista os nós de um PowerGrade (.drx): nome, ResolveFX, LUTs e separadores usados.

Uso: python3 powergrade_inspect.py ficheiro.drx
"""
import sys,re,zstandard
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from pb import dec,varint
t=open(sys.argv[1]).read()
print("ver:",re.search(r"DbAppVer=\"([^\"]+)",t).group(1), "label:",re.search(r"<Label>([^<]*)",t).group(1))
bodies=re.findall(r"<(pClipFullVer|pTrackVer)>.*?<Body>([0-9a-f]*)</Body>",t,re.S)
for kind,h in bodies:
    if not h: continue
    raw=bytes.fromhex(h); k=raw.find(b"\x28\xb5\x2f\xfd")
    d=zstandard.ZstdDecompressor().decompress(raw[k:],max_output_size=10**8)
    print("==",kind,len(d))
    def first(m,fid):
        for f,v in dec(m):
            if f==fid: return v
    def nodes(msg,depth=0):
        for f,v in dec(msg):
            if f==7 and isinstance(v,bytes):
                try: n=dec(v)
                except: continue
                nid=first(v,1); nm=first(v,6); nm=nm if isinstance(nm,bytes) else b''
                ofx=sorted(set(re.findall(rb"com\.blackmagicdesign\.resolvefx\.\w+|com\.[a-z]+\.[\w.]+",v)))
                luts=sorted(set(re.findall(rb"[\w /.-]+\.cube",v)))
                f9=first(v,9); ids=[]
                if isinstance(f9,bytes):
                    for a,b in dec(f9):
                        if a==1: ids.append(first(b,1))
                print("  "*depth+f"  node {nid} {nm.decode(errors='replace')!r} ofx={[o.decode() for o in ofx]} luts={[l.decode() for l in luts]} tabs={ids}")
                sub=first(v,11)
                if isinstance(sub,bytes): nodes(sub,depth+1)
    for f,v in dec(d):
        if f==1: nodes(v)
