"""Constrói um PowerGrade completo (árvore de nós em série) a partir de uma especificação JSON.

Uso:
  python3 powergrade_tree.py spec.json saida.drx

spec.json:
{
  "template": "SRM_NODE_SETUP_1.9_FREE.drx",     # PowerGrade aprovado: dá o XML, os protótipos e os nós copiados
  "label": "NOME NA GALERIA",
  "thumb": "imagem.png",                          # opcional
  "sources": {"itsjohan": "itsjohan.drx"},        # opcional: outros PowerGrades de onde copiar separadores
  "nodes": [                                       # pela ordem da cadeia
    {"name": "NR", "src": "tpl:52", "enabled": false, "pos": [0, 0]},
    {"name": "CST IN", "src": "tpl:26", "cst": {"inputColorSpace": "REC709_COLORSPACE", ...}},
    {"name": "CONTRAST", "pivot": 0.336},
    {"name": "CURVES", "curve": [[0.16, 0.135], [0.336, 0.336], ...]},          # curva ganged (0..1)
    {"name": "MASK BRILHO", "src": "tpl:51", "circle": {"p05_size": 850, ...}}, # janela circular (pg_windows)
    {"name": "MASK DESFOQUE", "blur": 0.65, "circle": {..., "p09_invert": 2}},  # raio do Blur na escala do UI
    {"name": "MASK VINHETA", "tab1_from": "itsjohan:72", "circle": {...}},      # copia o separador 1 de outro nó
    {"name": "LUT 2383", "lut": "Film Looks/Rec709 Kodak 2383 D65.cube"},
    ...
  ]
}
- "src": "tpl:<id>" copia esse nó do modelo e MANTÉM o id (os CST/OFX continuam coerentes); sem "src" = nó vazio.
- "enabled": false = nó desligado (cinzento), como no DaVinci.
- "pos": [linha, coluna] para arrumar a árvore no ecrã.
Só usa codificações verificadas byte a byte em PowerGrades reais (ver pg_corrector.py e pg_windows.py).
"""
import datetime, html, json, os, re, sys, uuid
import zstandard
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import powergrade_build as B
import pg_corrector as C
import pg_windows as W
from powergrade_edit import set_ofx_strings

def load_graph(path):
    x = open(path, encoding="utf-8").read()
    m, pre, d = B.body_of(x, "pClipFullVer")
    top = B.fields(d); gi = [i for i, f in enumerate(top) if f[0] == 1][0]
    return x, m, pre, top, gi, top[gi][3]

def node_by_id(graph, nid):
    for n in B.iter_nodes(graph):
        if B.getv(n, 1) == nid: return n
    raise KeyError(nid)

def main(spec_path, out):
    spec = json.load(open(spec_path)); base = os.path.dirname(os.path.abspath(spec_path))
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    xml, m, prefix, top, gi, graph = load_graph(rel(spec["template"]))
    srcs = {k: load_graph(rel(v))[5] for k, v in spec.get("sources", {}).items()}
    blank = next(n for n in B.iter_nodes(graph) if B.is_blank(n))
    tpl_ids = {int(n["src"].split(":")[1]) for n in spec["nodes"] if n.get("src", "").startswith("tpl:")}
    next_id = max(B.getv(n, 1) for n in B.iter_nodes(graph)) + 1
    built, ids = [], []
    for i, ns in enumerate(spec["nodes"]):
        if ns.get("src", "").startswith("tpl:"):
            nid = int(ns["src"].split(":")[1]); proto = node_by_id(graph, nid)
        else:
            nid = next_id; next_id += 1; proto = blank
        r, c = ns.get("pos", [0, i])
        node = B.make_node(proto, nid, i + 1, 120 + 250 * c, 260 + 230 * r, ns["name"])
        if "cst" in ns: node = set_ofx_strings(node, ns["cst"])
        tab1 = {}
        if "pivot" in ns: tab1.update(C.primaries_params(pivot=ns["pivot"]))
        if "curve" in ns: tab1.update(C.curve_params(ganged=[tuple(p) for p in ns["curve"]]))
        if "blur" in ns: tab1.update({pid: C.v_float(ns["blur"] - 0.5) for pid in C.P["BLUR_RADIUS_RGB"]})
        if "lut" in ns: tab1.update(C.lut_params(ns["lut"]))
        if "tab1_from" in ns:
            k, sid = ns["tab1_from"].split(":")
            node = C.set_tab(node, C.get_tab(node_by_id(srcs[k], int(sid)), 1))
        if tab1:
            node = C.set_tab(node, C.make_tab(1, tab1))
        if "circle" in ns:
            node = C.set_tab(node, W.make_circle_tab(mat=W.matrix(), style="v20", **ns["circle"]))
        if "strength" in ns:
            node = C.set_tab(node, C.make_key_tab(ns["strength"]))
        node = W.set_enabled(node, ns.get("enabled", True))
        built.append(node); ids.append(nid)
    if len(set(ids)) != len(ids): sys.exit("ids repetidos")
    # grafo: nós e ligações novos, entrada/saída apontadas para o 1.º/último
    out_g = []
    for f in B.fields(graph):
        if f[0] == 1: out_g.append(B.vint(1, ids[0])); continue
        if f[0] in (7, 8): continue
        if f[0] in (9, 10):
            inner = B.fields(f[3])
            for x in inner:
                if x[0] == 3:
                    xf = B.fields(x[3]); B.setv(xf, 4, ids[0] if f[0] == 9 else ids[-1]); x[3] = B.build(xf)
            f[3] = B.build(inner)
            if f[0] == 9:
                out_g += [B.vbytes(7, n) for n in built]
                for k in range(len(ids) - 1):
                    out_g.append(B.vbytes(8, B.build([B.vint(1, ids[k]), B.vint(3, ids[k + 1]), B.vint(5, 64), B.vint(6, 64), B.vint(7, k + 1)])))
        out_g.append(f)
    top[gi][3] = B.build(out_g)
    nd = B.build(top)
    mapping = {old: str(uuid.uuid4()) for old in set(re.findall(r'DbId="([0-9a-f-]{36})"', xml))}
    for old, new in mapping.items(): nd = nd.replace(old.encode(), new.encode())
    comp = zstandard.ZstdCompressor(level=19, write_content_size=True).compress(nd)
    xml = xml[:m.start(2)] + (prefix + comp).hex() + xml[m.end(2):]
    for old, new in mapping.items(): xml = xml.replace(old, new)
    label = html.escape(spec["label"], quote=False)
    xml = re.sub(r"<Label>[^<]*</Label>", lambda mm: "<Label>%s</Label>" % label, xml, count=1)
    xml = re.sub(r"<SrcHint>[^<]*</SrcHint>", lambda mm: "<SrcHint>%s</SrcHint>" % label, xml, count=1)
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000")
    xml = re.sub(r"<CreateTime>[^<]*</CreateTime>", lambda mm: "<CreateTime>%s</CreateTime>" % now, xml, count=1)
    if spec.get("thumb"):
        j = B.jpeg_thumb(rel(spec["thumb"])).hex()
        xml, n = re.subn(r"(<BtThumnail\b[^>]*>.*?<Buffer>)[0-9a-f]*(</Buffer>)", lambda mm: mm.group(1) + j + mm.group(2), xml, count=1, flags=re.S)
        if n != 1: sys.exit("miniatura não encontrada")
    thumbs = B.build([B.vbytes(1, B.build([B.vint(1, 2 * nid), B.vbytes(2, B.build([B.vint(1, 0xffffffff), B.vint(2, 0xffffffff)]))])) for nid in ids]).hex()
    xml, n = re.subn(r"<ClipThumbnails>[0-9a-f]*</ClipThumbnails>|<ClipThumbnails/>", lambda mm: "<ClipThumbnails>%s</ClipThumbnails>" % thumbs, xml, count=1)
    open(out, "w", encoding="utf-8").write(xml)
    print("ok:", out, "|", " > ".join(n["name"] + ("" if n.get("enabled", True) else " (off)") for n in spec["nodes"]))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
