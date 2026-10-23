"""Converte um projeto (.drp) do DaVinci 20/21 com animações de texto em camadas num .drfx para uma versão anterior do DaVinci (ex.: 19).

Uso: python3 drp_to_drfx.py entrada.drp saida.drfx "Nome da Pasta"
Cada timeline vira um título; as camadas são juntas com Merge, os atrasos com TimeSpeed,
e os keyframes do Inspector (posição, zoom, rotação, opacidade) e o Drop Shadow do clip
são recriados em nós Fusion.
"""
import sys,os,re,json,zipfile,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from luaparse import top_entries
from curves import clip_effects
import drfx_lib as b2
src_in,outzip=sys.argv[1],sys.argv[2]
import tempfile
src=tempfile.mkdtemp()
zipfile.ZipFile(src_in).extractall(src)
VENDOR=sys.argv[3] if len(sys.argv)>3 else "Text Animations"
t=open(os.path.join(src,"MediaPool/Master/MpFolder.xml")).read()
seq2name={m.group(2):m.group(1) for m in re.finditer(r'<Sm2Timeline[^>]*>\s*<FieldsBlob/>\s*<Name>([^<]*)</Name>.*?<Sm2Sequence DbId="([^"]+)"',t,re.S)}
import zlib
def comp_body(c):
    cba=re.search(r"<CompositionBA>([0-9a-f]+)",c)
    if not cba: return None
    d=zlib.decompress(bytes.fromhex(cba.group(1))[4:])
    i=d.find(b"Composition {"); j=d.find(b"Compressed = true",i); k=d.find(b"x\xda",j)
    return zlib.decompress(d[k:]).decode()
def static_val(e):
    s=e.get('static')
    try: return s[0][1][0][1][1]
    except Exception: return None
def param(params,pid,start,default):
    e=params.get(pid)
    if not e: return ('static',default)
    if 'curve' in e:
        keys=[]
        for fr,fl,v,tg in e['curve'][1]:
            if fr>=86000: fr-=start
            keys.append((fr,fl,v,tg))
        if len(keys)==1: return ('static',keys[0][2])
        return ('curve',keys)
    v=static_val(e)
    return ('static', default if v is None else v)
def spline(name, keys, scale=1.0, add=0.0, shift=0):
    parts=[]
    for i,(fr,fl,v,tg) in enumerate(keys):
        F=fr+shift; V=v*scale+add; items=[f"{V!r}"]
        prv=keys[i-1] if i>0 else None; nxt=keys[i+1] if i+1<len(keys) else None
        if fl&1==0:
            items.append("Flags = { Linear = true }")
        else:
            if nxt:
                dx=tg[2] if tg else 0; span=nxt[0]-fr
                if dx<=0: rx,ry=F+span/3, V+((nxt[2]*scale+add)-V)/3
                else: rx,ry=F+min(dx,span), V
                items.append(f"RH = {{ {rx!r}, {ry!r} }}")
            if prv:
                dx=tg[0] if tg else 0; span=fr-prv[0]
                if dx>=0: lx,ly=F-span/3, V-(V-(prv[2]*scale+add))/3
                else: lx,ly=F-min(-dx,span), V
                items.append(f"LH = {{ {lx!r}, {ly!r} }}")
        parts.append(f"[{F}] = {{ " + ", ".join(items) + " }")
    return f'{name} = BezierSpline {{ SplineColor = {{ Red = 220, Green = 160, Blue = 60 }}, KeyFrames = {{ {", ".join(parts)} }}, }}'
def inp(name, p, tools, splname, scale=1.0, add=0.0, shift=0):
    kind,v=p
    if kind=='static': return f"{name} = Input {{ Value = {v*scale+add!r}, }}"
    tools.append(spline(splname,v,scale,add,shift)); return f'{name} = Input {{ SourceOp = "{splname}", Source = "Value", }}'
files={}; report=[]
for f in glob.glob(os.path.join(src,"SeqContainer/*.xml")):
    x=open(f).read(); name=seq2name[re.search(r"<Sequence>([^<]*)",x).group(1)]; num=int(name.split()[-1])
    layers=[]
    for ti,tr in enumerate(re.findall(r"<Sm2TiTrack.*?</Sm2TiTrack>",x,re.S)):
        for c in re.findall(r"<Sm2TiVideoClip.*?</Sm2TiVideoClip>",tr,re.S):
            layers.append(dict(track=ti,start=int(re.search(r"<Start>(\d+)",c).group(1)),name=re.search(r"<Name>([^<]*)",c).group(1),body=comp_body(c),fx=clip_effects(c)))
    t0=min(l['start'] for l in layers)
    skipped=[l['name'] for l in layers if not l['body']]
    layers=[l for l in sorted(layers,key=lambda l:l['track']) if l['body']]
    tools=['Base = Background { Inputs = { GlobalOut = Input { Value = 1000, }, UseFrameFormatSettings = Input { Value = 1, }, Width = Input { Value = 1920, }, Height = Input { Value = 1080, }, TopLeftAlpha = Input { Value = 0, }, }, }']
    acc="Base"; ins=[]; k=1; samples=[]
    for li,l in enumerate(layers):
        p=f"L{li+1}_"; off=l['start']-t0
        keep,names,out,txt_src,tn,sample=b2.layer_info(l['body']); samples.append((off,sample))
        tools+=b2.prefix(keep,names,p); cur=p+out
        g={gid:pr for gid,pr in l['fx']}
        # drop shadow
        for gid,pr in l['fx']:
            if gid==50 and 109 in pr:
                st=pr[109].get('static'); raw=repr(st)
                vals={}
                for pn in ("ShadowDistance","shadowAngle","shadowBlur","shadowStrength"):
                    m=re.search(r"b'"+pn+r"'\), \(2, \[\(2, \('d', ([-0-9.e]+)\)",raw)
                    if m: vals[pn]=float(m.group(1))
                if 'dropshadow' in raw:
                    vs="".join(f"{kk} = Input {{ Value = {vv!r}, }}, " for kk,vv in vals.items())
                    tools.append(f'{p}ClipShadow = ofx.com.blackmagicdesign.resolvefx.DropShadow {{ Inputs = {{ Source = Input {{ SourceOp = "{cur}", Source = "Output", }}, {vs}srcProcessingAlphaMode = Input {{ Value = 4, }}, dstProcessingAlphaMode = Input {{ Value = 4, }}, resolvefxVersion = Input {{ Value = "2.0", }}, }}, }}')
                    cur=p+"ClipShadow"
        tr=g.get(4,{})
        if tr:
            px=param(tr,40,l['start'],0.0); py=param(tr,41,l['start'],0.0)
            zx=param(tr,42,l['start'],1.0); zy=param(tr,43,l['start'],1.0); rot=param(tr,47,l['start'],0.0)
            xin=[]
            xin.append(inp("XSize",zx,tools,p+"ZoomX")); xin.append(inp("YSize",zy,tools,p+"ZoomY"))
            xin.append(inp("Angle",rot,tools,p+"Rot"))
            if px[0]=='static' and py[0]=='static':
                xin.append(f"Center = Input {{ Value = {{ {0.5+px[1]!r}, {0.5+py[1]!r} }}, }}")
            else:
                xi=inp("X",px,tools,p+"PosX",add=0.5); yi=inp("Y",py,tools,p+"PosY",add=0.5)
                tools.append(f'{p}Path = XYPath {{ ShowKeyPoints = false, DrawMode = "ModifyOnly", Inputs = {{ {xi}, {yi}, }}, }}')
                xin.append(f'Center = Input {{ SourceOp = "{p}Path", Source = "Value", }}')
            tools.append(f'{p}ClipXf = Transform {{ Inputs = {{ UseSizeAndAspect = Input {{ Value = 0, }}, {", ".join(xin)}, Input = Input {{ SourceOp = "{cur}", Source = "Output", }}, }}, }}')
            cur=p+"ClipXf"
        if off>0:
            tools.append(f'{p}Delay = TimeSpeed {{ Inputs = {{ Speed = Input {{ Value = 1, }}, Delay = Input {{ Value = {off}, }}, InterpolateBetweenFrames = Input {{ Value = 0, }}, Input = Input {{ SourceOp = "{cur}", Source = "Output", }}, }}, }}')
            cur=p+"Delay"
        op=param(g.get(2,{}),1,l['start'],100.0)
        if op[0]=='curve':
            blend=inp("Blend",op,tools,p+"Opacity",scale=0.01,shift=off)
            if off>0 and op[1][0][2]!=0:
                blend=f'Blend = Input {{ Expression = "iif(time < {off}, 0, {p}Opacity.Value)", }}'
        elif off>0:
            blend=f'Blend = Input {{ Expression = "iif(time < {off}, 0, {op[1]/100!r})", }}'
        else:
            blend=f"Blend = Input {{ Value = {op[1]/100!r}, }}"
        tools.append(f'{p}Merge = Merge {{ Inputs = {{ {blend}, Background = Input {{ SourceOp = "{acc}", Source = "Output", }}, Foreground = Input {{ SourceOp = "{cur}", Source = "Output", }}, PerformDepthMerge = Input {{ Value = 0, }}, }}, }}')
        acc=p+"Merge"
        i2,k=b2.inputs_for(p,txt_src,tn,k,f"Text {li+1}"); ins+=i2
    title=" ".join(s.replace("\\n"," ") for _,s in sorted(samples,key=lambda z:z[0]) if s)[:40].strip()
    fname=re.sub(r'[\\/:*?"<>|]',"",f"{num:02d} - {title}")
    files[f"Edit/Titles/{VENDOR}/{fname}.setting"]=b2.macro_text(f"TA_{num:02d}",ins,acc,tools)
    report.append((fname,skipped))
with zipfile.ZipFile(outzip,"w",zipfile.ZIP_DEFLATED) as z:
    for pth,c in sorted(files.items()): z.writestr(pth,c)
for r in sorted(report): print(r)
