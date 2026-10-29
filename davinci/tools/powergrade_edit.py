"""Edita um PowerGrade (.drx) existente mantendo a estrutura de que o utilizador gosta.

Uso:
  python3 powergrade_edit.py modelo.drx saida.drx --label "NOME" [opções]
    --cst "NOME DO NÓ:param=VALOR,param=VALOR"   altera parâmetros de um nó CST: texto (ex.: inputColorSpace=REC709_COLORSPACE)
                                                 ou ligado/desligado com 0/1 (ex.: doInvOOTF=1)
    --remove "NOME1,NOME2"                       retira nós (e o que estiver dentro deles, se forem compostos)
    --append-lut "DEPOIS DE:NOVO NOME=Pasta/F.cube"  acrescenta um nó com LUT logo a seguir ao nó indicado;
                                                 se esse nó era a saída do grafo, o novo passa a ser a saída
    --thumb imagem.png                           miniatura da Galeria

Exemplo (estrutura SRM com o look Dourado no fim, para Rec.709):
  python3 powergrade_edit.py SRM_FREE.drx Dourado_SRM_709.drx --label "DOURADO VIVO 709" \
     --cst "CST IN:inputColorSpace=REC709_COLORSPACE,inputGamma=TWOPOINTFOUR_GAMMA" \
     --remove "CINEON,FILM LOOKS" --append-lut "CST OUT:DOURADO VIVO=Dourado/DouradoVivo_LOOK.cube"

Notas:
- Só se mudam valores de texto que já existem no nó (não se acrescentam parâmetros novos).
- Todos os DbId passam a ser novos; os UUID antigos que aparecem dentro do grade (nomes de contexto OFX)
  são trocados pelos novos, para tudo ficar coerente.
"""
import argparse, datetime, html, re, sys, uuid, os
import zstandard
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import powergrade_build as B
from powergrade_build import fields, build, getv, setv, setb, vint, vbytes, iter_nodes, set_lut_path, is_lut

def node_name(n):
    v = getv(n, 6)
    return v.decode(errors="replace") if isinstance(v, bytes) else None

def set_ofx_strings(node, changes):
    """Muda parâmetros OFX de texto: mensagem {1: nome, 2: {5: texto}} em qualquer profundidade do campo 10."""
    done = set()
    def rec(b, depth=0):
        try:
            fs = fields(b)
        except Exception:
            return b
        if build(fs) != b:
            return b
        names = [p for f, w, ks, p in fs if f == 1 and w == 2]
        if len(fs) == 2 and names and names[0].decode(errors="ignore") in changes:
            nm = names[0].decode()
            for x in fs:
                if x[0] == 2 and x[1] == 2:
                    vf = fields(x[3]); val = changes[nm]
                    if any(f == 5 for f, *_ in vf):                    # texto (ex.: REC709_COLORSPACE)
                        setb(vf, 5, val.encode()); x[3] = build(vf); done.add(nm)
                    elif any(f == 3 and w == 0 for f, w, *_ in vf) and val in ("0", "1"):   # ligado/desligado
                        setv(vf, 3, int(val)); x[3] = build(vf); done.add(nm)
            return build(fs)
        if depth > 14:
            return b
        for x in fs:
            if x[1] == 2 and len(x[3]) > 2:
                x[3] = rec(x[3], depth + 1)
        return build(fs)
    nf = fields(node)
    for x in nf:
        if x[0] == 10: x[3] = rec(x[3])
    missing = set(changes) - done
    if missing: sys.exit("parâmetros não encontrados no nó: %s" % ", ".join(sorted(missing)))
    return build(nf)

def all_ids(graph):
    ids = []
    for n in iter_nodes(graph): ids.append(getv(n, 1))
    return ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template"); ap.add_argument("out"); ap.add_argument("--label", required=True)
    ap.add_argument("--cst", action="append", default=[]); ap.add_argument("--remove", default="")
    ap.add_argument("--append-lut", action="append", default=[]); ap.add_argument("--thumb")
    a = ap.parse_args()
    xml = open(a.template, encoding="utf-8").read()
    m, prefix, d = B.body_of(xml, "pClipFullVer")
    top = fields(d); gi = [i for i, f in enumerate(top) if f[0] == 1][0]; graph = top[gi][3]
    gf = fields(graph)
    byname = {}
    for x in gf:
        if x[0] == 7: byname[node_name(x[3])] = x
    lut_proto = next((n for n in iter_nodes(graph) if is_lut(n)), None)
    # 1) CST
    for spec in a.cst:
        nm, kv = spec.split(":", 1)
        if nm not in byname: sys.exit("nó não encontrado: %s" % nm)
        ch = dict(p.split("=", 1) for p in kv.split(","))
        byname[nm][3] = set_ofx_strings(byname[nm][3], ch)
    # 2) retirar nós
    rem_names = [s.strip() for s in a.remove.split(",") if s.strip()]
    rem_ids = set()
    for nm in rem_names:
        if nm not in byname: sys.exit("nó não encontrado: %s" % nm)
        rem_ids.add(getv(byname[nm][3], 1))
    out_id = None; in_id = None
    for x in gf:
        if x[0] == 10: out_id = getv(getv(x[3], 3), 4)
        if x[0] == 9: in_id = getv(getv(x[3], 3), 4)
    links = [x for x in gf if x[0] == 8]
    preds = {getv(l[3], 3): getv(l[3], 1) for l in links if not getv(l[3], 4)}
    # se a saída do grafo é um nó retirado, recua até ao primeiro nó que fica
    while out_id in rem_ids: out_id = preds[out_id]
    gf = [x for x in gf if not (x[0] == 7 and getv(x[3], 1) in rem_ids)]
    gf = [x for x in gf if not (x[0] == 8 and (getv(x[3], 1) in rem_ids or getv(x[3], 3) in rem_ids))]
    # 3) acrescentar nós com LUT
    used = set(all_ids(graph)); next_id = max(used) + 1
    link_ids = [getv(x[3], 7) for x in gf if x[0] == 8]; next_link = max(link_ids + [0]) + 1
    for spec in a.append_lut:
        after, rest = spec.split(":", 1); new_name, path = rest.split("=", 1)
        anchor = next((x for x in gf if x[0] == 7 and node_name(x[3]) == after), None)
        if anchor is None: sys.exit("nó não encontrado: %s" % after)
        aid = getv(anchor[3], 1); ax = getv(anchor[3], 4); ay = getv(anchor[3], 5)
        nid = next_id; next_id += 1
        num = max(getv(x[3], 2) for x in gf if x[0] == 7) + 1
        node = B.make_node(set_lut_path(lut_proto, path), nid, num, ax + 260, ay, new_name)
        # liga: anchor -> novo; o que saía do anchor (porta 0) passa a sair do novo
        for x in gf:
            if x[0] == 8 and getv(x[3], 1) == aid:
                lf = fields(x[3]); setv(lf, 1, nid); x[3] = build(lf)
        if out_id == aid: out_id = nid
        pos = max(i for i, x in enumerate(gf) if x[0] == 7) + 1
        gf.insert(pos, vbytes(7, node))
        lpos = max(i for i, x in enumerate(gf) if x[0] in (7, 8)) + 1
        gf.insert(lpos, vbytes(8, build([vint(1, aid), vint(3, nid), vint(5, 64), vint(6, 64), vint(7, next_link)])))
        next_link += 1
    for x in gf:
        if x[0] == 10:
            inner = fields(x[3])
            for y in inner:
                if y[0] == 3:
                    yf = fields(y[3]); setv(yf, 4, out_id); y[3] = build(yf)
            x[3] = build(inner)
    top[gi][3] = build(gf)
    nd = build(top)
    # identificadores novos (XML e dentro do grade)
    mapping = {old: str(uuid.uuid4()) for old in set(re.findall(r'DbId="([0-9a-f-]{36})"', xml))}
    for old, new in mapping.items(): nd = nd.replace(old.encode(), new.encode())
    comp = zstandard.ZstdCompressor(level=19, write_content_size=True).compress(nd)
    xml = xml[:m.start(2)] + (prefix + comp).hex() + xml[m.end(2):]
    for old, new in mapping.items(): xml = xml.replace(old, new)
    label = html.escape(a.label, quote=False)
    xml = re.sub(r"<Label>[^<]*</Label>", lambda mm: "<Label>%s</Label>" % label, xml, count=1)
    xml = re.sub(r"<SrcHint>[^<]*</SrcHint>", lambda mm: "<SrcHint>%s</SrcHint>" % label, xml, count=1)
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000")
    xml = re.sub(r"<CreateTime>[^<]*</CreateTime>", lambda mm: "<CreateTime>%s</CreateTime>" % now, xml, count=1)
    if a.thumb:
        j = B.jpeg_thumb(a.thumb).hex()
        xml, n = re.subn(r"(<BtThumnail\b[^>]*>.*?<Buffer>)[0-9a-f]*(</Buffer>)", lambda mm: mm.group(1) + j + mm.group(2), xml, count=1, flags=re.S)
        if n != 1: sys.exit("miniatura não encontrada")
    new_graph = top[gi][3]
    thumbs = build([vbytes(1, build([vint(1, 2 * nid), vbytes(2, build([vint(1, 0xffffffff), vint(2, 0xffffffff)]))]))
                    for nid in all_ids(new_graph)]).hex()
    xml, n = re.subn(r"<ClipThumbnails>[0-9a-f]*</ClipThumbnails>|<ClipThumbnails/>",
                     lambda mm: "<ClipThumbnails>%s</ClipThumbnails>" % thumbs, xml, count=1)
    open(a.out, "w", encoding="utf-8").write(xml)
    print("ok:", a.out)

if __name__ == "__main__":
    main()
