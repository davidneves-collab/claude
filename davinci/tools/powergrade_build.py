"""Cria um PowerGrade (.drx) novo: uma cadeia de nós com nomes; cada LUT vai num nó próprio.

Uso:
  python3 powergrade_build.py modelo.drx saida.drx --label "NOME" --lut "Pasta/Ficheiro.cube" \
      --nodes "EXPOSURE,BALANCE,CONTRAST,SKIN,LOOK*,SAT" [--thumb imagem.png]
  # várias LUTs, cada uma no seu nó (NOME*=caminho):
  python3 powergrade_build.py modelo.drx saida.drx --label "NOME" \
      --nodes "EXPOSURE,BALANCE,CONTRAST,SKIN,CLOG3 TO 709*=Pasta/Conv.cube,LOOK*=Pasta/Look.cube,SAT"

- modelo.drx: qualquer PowerGrade FREE que já funcione no DaVinci do utilizador (dá o esqueleto XML e
  os protótipos de nó vazio e de nó com LUT). Tem de conter pelo menos um nó com LUT.
- O nó marcado com * recebe a LUT de --lut; "NOME*=caminho" recebe esse caminho. Os outros ficam vazios.
- --lut é o caminho relativo à pasta de LUTs do DaVinci (ex.: "Claude Looks/Look_Canon709.cube").
- Os identificadores (DbId) são todos novos, para não colidir com stills já importados.
- O caminho da galeria (GalleryPath) do modelo é mantido, como nos PowerGrades que já foram testados.
"""
import argparse, datetime, html, io, os, re, sys, uuid
import zstandard
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pb import varint

LUT_PARAM = 2248147105      # parâmetro do separador 1 que guarda o caminho da LUT

def enc_varint(n):
    out = bytearray()
    while True:
        b = n & 0x7f; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); return bytes(out)

def fields(b):
    i = 0; out = []
    while i < len(b):
        st = i; key, i = varint(b, i); f, w = key >> 3, key & 7; ks = b[st:i]
        if w == 0: s = i; _, i = varint(b, i); out.append([f, w, ks, b[s:i]])
        elif w == 1: out.append([f, w, ks, b[i:i + 8]]); i += 8
        elif w == 5: out.append([f, w, ks, b[i:i + 4]]); i += 4
        elif w == 2: l, i = varint(b, i); out.append([f, w, ks, b[i:i + l]]); i += l
        else: raise ValueError("wire type %d" % w)
    return out

def build(fs):
    return b"".join(ks + (enc_varint(len(p)) + p if w == 2 else p) for f, w, ks, p in fs)

def key(f, w): return enc_varint((f << 3) | w)
def vint(f, n): return [f, 0, key(f, 0), enc_varint(n)]
def vbytes(f, b): return [f, 2, key(f, 2), b]
def getv(msg, f):
    for ff, w, ks, p in fields(msg):
        if ff == f: return varint(p, 0)[0] if w == 0 else p
def setv(fs, f, n):
    for x in fs:
        if x[0] == f: x[1], x[2], x[3] = 0, key(f, 0), enc_varint(n); return
    fs.append(vint(f, n))
def setb(fs, f, b):
    for x in fs:
        if x[0] == f: x[1], x[2], x[3] = 2, key(f, 2), b; return
    fs.append(vbytes(f, b))

def iter_nodes(graph):
    """Todos os nós (campo 7), incluindo os de dentro de nós compostos (campo 11)."""
    for f, w, ks, p in fields(graph):
        if f == 7 and w == 2:
            yield p
            sub = getv(p, 11)
            if isinstance(sub, bytes):
                try: yield from iter_nodes(sub)
                except Exception: pass

def tab_ids(node):
    t = getv(node, 9)
    if not isinstance(t, bytes): return []
    return [getv(p, 1) for f, w, ks, p in fields(t) if f == 1]

def is_blank(node):
    f10 = getv(node, 10)
    base_only = isinstance(f10, bytes) and all(getv(p, 1) == 3221225473 for f, w, ks, p in fields(f10) if f == 1)
    return getv(node, 8) == 44 and set(tab_ids(node)) <= {2, 3, 4, 5, 6, 18} and base_only

def is_lut(node):
    return getv(node, 8) == 44 and b".cube" in node and getv(node, 11) is None and \
        set(tab_ids(node)) <= {1, 2, 3, 4, 5, 6, 18} and 1 in tab_ids(node)

def set_lut_path(node, path):
    """Troca o caminho da LUT: nó.9 -> entrada(tab 1).6 -> .2 -> parâmetro(LUT_PARAM).2 -> .5"""
    nf = fields(node)
    for x in nf:
        if x[0] != 9: continue
        tabs = fields(x[3])
        for t in tabs:
            if t[0] != 1 or getv(t[3], 1) != 1: continue
            tf = fields(t[3])
            for a in tf:
                if a[0] != 6: continue
                af = fields(a[3])
                for b in af:
                    if b[0] != 2: continue
                    bf = fields(b[3])
                    for c in bf:
                        if c[0] == 3 and getv(c[3], 1) == LUT_PARAM:
                            cf = fields(c[3])
                            for d in cf:
                                if d[0] == 2:
                                    df = fields(d[3]); setb(df, 5, path.encode()); d[3] = build(df)
                            c[3] = build(cf)
                    b[3] = build(bf)
                a[3] = build(af)
            t[3] = build(tf)
        x[3] = build(tabs)
    return build(nf)

def make_node(proto, nid, num, x, y, name):
    nf = fields(proto)
    setv(nf, 1, nid); setv(nf, 2, num); setv(nf, 4, x); setv(nf, 5, y); setb(nf, 6, name.encode())
    nf = [f for f in nf if f[0] != 11]
    order = [1, 2, 4, 5, 6, 7, 8, 9, 10, 12]
    nf.sort(key=lambda f: order.index(f[0]) if f[0] in order else 99)
    return build(nf)

def body_of(xml, tag):
    m = re.search(r"(<%s>.*?<Body>)([0-9a-f]*)(</Body>)" % tag, xml, re.S)
    raw = bytes.fromhex(m.group(2)); k = raw.find(b"\x28\xb5\x2f\xfd")
    return m, raw[:k], zstandard.ZstdDecompressor().decompress(raw[k:], max_output_size=10 ** 8)

def jpeg_thumb(img_path, w=576, h=324):
    from PIL import Image
    im = Image.open(img_path).convert("RGB")
    s = max(w / im.width, h / im.height); im = im.resize((round(im.width * s), round(im.height * s)))
    l = (im.width - w) // 2; t = (im.height - h) // 2; im = im.crop((l, t, l + w, t + h))
    b = io.BytesIO(); im.save(b, "JPEG", quality=88); return b.getvalue()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template"); ap.add_argument("out")
    ap.add_argument("--label", required=True); ap.add_argument("--lut")
    ap.add_argument("--nodes", default="EXPOSURE,BALANCE,CONTRAST,SKIN,LOOK*,SAT")
    ap.add_argument("--thumb")
    a = ap.parse_args()
    xml = open(a.template, encoding="utf-8").read()
    m, prefix, d = body_of(xml, "pClipFullVer")
    top = fields(d); gi = [i for i, f in enumerate(top) if f[0] == 1][0]; graph = top[gi][3]
    nodes = list(iter_nodes(graph))
    blank = next((n for n in nodes if is_blank(n)), None)
    lutp = next((n for n in nodes if is_lut(n)), None)
    if blank is None or lutp is None: sys.exit("o modelo precisa de um nó vazio e de um nó com LUT")
    names = [s.strip() for s in a.nodes.split(",") if s.strip()]
    new_nodes = []
    luts = []
    for i, nm in enumerate(names):
        nid = i + 2; path = None
        if "*=" in nm: nm, path = [t.strip() for t in nm.split("*=", 1)]
        elif nm.endswith("*"):
            nm = nm.rstrip("*").strip(); path = a.lut
            if not path: sys.exit("nó %s marcado com * mas falta --lut" % nm)
        if path: luts.append(path)
        proto = set_lut_path(lutp, path) if path else blank
        new_nodes.append(make_node(proto, nid, i + 1, 120 + 260 * i, 300, nm))
    ids = [i + 2 for i in range(len(names))]
    gf = fields(graph); out = []
    for f in gf:
        if f[0] == 1: out.append(vint(1, ids[0])); continue
        if f[0] in (7, 8): continue
        if f[0] == 9 or f[0] == 10:
            inner = fields(f[3])
            for x in inner:
                if x[0] == 3:
                    xf = fields(x[3]); setv(xf, 4, ids[0] if f[0] == 9 else ids[-1]); x[3] = build(xf)
            f[3] = build(inner)
            if f[0] == 9:          # nós e ligações entram antes da entrada do grafo
                out += [vbytes(7, n) for n in new_nodes]
                for k in range(len(ids) - 1):
                    out.append(vbytes(8, build([vint(1, ids[k]), vint(3, ids[k + 1]), vint(5, 64), vint(6, 64), vint(7, k + 1)])))
        out.append(f)
    top[gi][3] = build(out)
    nd = build(top)
    comp = zstandard.ZstdCompressor(level=19, write_content_size=True).compress(nd)
    xml = xml[:m.start(2)] + (prefix + comp).hex() + xml[m.end(2):]
    # identificadores novos
    for old in set(re.findall(r'DbId="([0-9a-f-]{36})"', xml)):
        xml = xml.replace(old, str(uuid.uuid4()))
    label = html.escape(a.label, quote=False)
    xml = re.sub(r"<Label>[^<]*</Label>", lambda mm: "<Label>%s</Label>" % label, xml, count=1)
    xml = re.sub(r"<SrcHint>[^<]*</SrcHint>", lambda mm: "<SrcHint>%s</SrcHint>" % label, xml, count=1)
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000")
    xml = re.sub(r"<CreateTime>[^<]*</CreateTime>", lambda mm: "<CreateTime>%s</CreateTime>" % now, xml, count=1)
    if a.thumb:
        j = jpeg_thumb(a.thumb).hex()
        xml, n = re.subn(r"(<BtThumnail\b[^>]*>.*?<Buffer>)[0-9a-f]*(</Buffer>)",
                         lambda mm: mm.group(1) + j + mm.group(2), xml, count=1, flags=re.S)
        if n != 1: sys.exit("não encontrei a miniatura (<BtThumnail>...<Buffer>) no modelo")
        xml = re.sub(r"<ImgWidth>\d+</ImgWidth>", "<ImgWidth>576</ImgWidth>", xml, count=1)
        xml = re.sub(r"<ImgHeight>\d+</ImgHeight>", "<ImgHeight>324</ImgHeight>", xml, count=1)
    # miniaturas dos nós: uma entrada "sem imagem" por nó, no formato que o próprio DaVinci escreve
    thumbs = build([vbytes(1, build([vint(1, 2 * nid), vbytes(2, build([vint(1, 0xffffffff), vint(2, 0xffffffff)]))]))
                    for nid in ids]).hex()
    xml, n = re.subn(r"<ClipThumbnails>[0-9a-f]*</ClipThumbnails>|<ClipThumbnails/>",
                     lambda mm: "<ClipThumbnails>%s</ClipThumbnails>" % thumbs, xml, count=1)
    if n != 1: sys.exit("não encontrei <ClipThumbnails> no modelo")
    open(a.out, "w", encoding="utf-8").write(xml)
    print("ok:", a.out, "| nós:", ", ".join(names), "| LUTs:", ", ".join(luts))

if __name__ == "__main__":
    main()
