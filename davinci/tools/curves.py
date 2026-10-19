import sys,re,glob,zstandard,struct,json,os
sys.path.insert(0,os.path.dirname(__file__)); from pb import dec,tryrec
dctx=zstandard.ZstdDecompressor()
def parse_curve(b):
    hdr=b[:4]; i=4; keys=[]
    while i<len(b):
        fr=struct.unpack("<i",b[i:i+4])[0]; flags=struct.unpack("<H",b[i+6:i+8])[0]
        val=struct.unpack("<d",b[i+8:i+16])[0]; i+=16
        tang=None
        if flags&1:
            tang=struct.unpack("<6d",b[i:i+48]); i+=48
        keys.append((fr,flags,val,tang))
    return hdr.hex(),keys
def clip_effects(clip):
    m=re.search(r"<EffectFiltersBA>([0-9a-f]+)",clip)
    if not m: return []
    raw=bytes.fromhex(m.group(1)); k=raw.find(b"\x28\xb5\x2f\xfd")
    if k<0: return []
    d=dctx.decompress(raw[k:],max_output_size=10**7)
    groups=[]
    for f,v in dec(d):
        if f!=1: continue
        g=dec(v); gid=[x for ff,x in g if ff==1][0]; params={}
        ofx=None
        for ff,x in g:
            if ff==9 and x:
                p=dict((a,b) for a,b in dec(x)) if True else None
                pl=dec(x); pid=[b for a,b in pl if a==1]
                if not pid: continue
                pid=pid[0]; ent={}
                for a,b in pl:
                    if a==10: ent['curve']=parse_curve(b)
                    if a==3:
                        try: ent['static']=tryrec(b)
                        except: ent['static']=b
                params[pid]=ent
        groups.append((gid,params))
    return groups
if __name__=="__main__":
    src=sys.argv[1]
    idx=json.load(open(sys.argv[2]))
    t=open(os.path.join(src,"MediaPool/Master/MpFolder.xml")).read()
    for f in sorted(glob.glob(os.path.join(src,"SeqContainer/*.xml"))):
        x=open(f).read()
        for ti,tr in enumerate(re.findall(r"<Sm2TiTrack.*?</Sm2TiTrack>",x,re.S)):
            for c in re.findall(r"<Sm2TiVideoClip.*?</Sm2TiVideoClip>",tr,re.S):
                print("==",os.path.basename(f)[:8],"track",ti,re.search(r"<Name>([^<]*)",c).group(1))
                for gid,params in clip_effects(c):
                    for pid,e in params.items():
                        print("  g",gid,"p",pid, e.get('static',''), e.get('curve',''))
