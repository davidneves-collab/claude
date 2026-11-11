"""Verifica um PowerGrade (.drx) antes de o entregar: estrutura igual à dos ficheiros reais do DaVinci.

Uso:
  python3 powergrade_check.py ficheiro.drx [mais.drx ...]

Confere: XML bem formado; corpo descomprime e reconstrói byte a byte; ids de nó únicos; campo 7 = 1;
a 1.ª entrada do campo 10 é o interruptor do nó (0xC0000001); separadores ordenados e com a lista
compacta 03 04 05 06 12; ligações com 5:64/6:64 e a apontar para nós existentes; cadeia da entrada à
saída sem buracos; contextos OFX "OfxImageEffectContextFilter_<LmVersion>_<id>" coerentes; LUTs com
'/'; miniatura JPEG presente. Mostra um resumo de cada nó (ligado/desligado, CST, LUT, separadores).
"""
import re, sys, os, struct, xml.parsers.expat, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import powergrade_build as B
from pb import varint

ENABLE = 0xC0000001

def ofx_strings(node):
    f10 = B.getv(node, 10) or b""
    return {k.decode(): v.decode() for k, v in re.findall(rb"([a-z][a-zA-Z]*(?:ColorSpace|Gamma))\x12.\*.([A-Z0-9_]+)", f10)}

def check(path):
    errs = []; x = open(path, encoding="utf-8").read()
    try: xml.parsers.expat.ParserCreate().Parse(x, True)
    except Exception as e: errs.append("XML: %s" % e)
    m, pre, d = B.body_of(x, "pClipFullVer")
    top = B.fields(d)
    if B.build(top) != d: errs.append("corpo não reconstrói byte a byte")
    g = [q for q in top if q[0] == 1][0][3]
    nodes = list(B.iter_nodes(g)); ids = [B.getv(n, 1) for n in nodes]
    if len(ids) != len(set(ids)): errs.append("ids de nó repetidos")
    lmv = re.search(r'<pClipFullVer>\s*<ListMgt::LmVersion DbId="([^"]+)"', x).group(1)
    rows = []
    for n in nodes:
        nid = B.getv(n, 1); nm = (B.getv(n, 6) or b"").decode(errors="replace")
        if B.getv(n, 7) != 1: errs.append("nó %s: campo 7 != 1" % nid)
        f10 = B.fields(B.getv(n, 10) or b"")
        if not f10 or B.getv(f10[0][3], 1) != ENABLE: errs.append("nó %s: interruptor não é a 1.ª entrada" % nid)
        on = B.getv(B.getv(f10[0][3], 2), 2) == 2 if f10 else None
        t9 = B.getv(n, 9); tabs = []
        if isinstance(t9, bytes):
            ents = [p for f, w, k, p in B.fields(t9) if f == 1]; tabs = [B.getv(p, 1) for p in ents]
            if tabs != sorted(tabs): errs.append("nó %s: separadores fora de ordem" % nid)
            packed = [p for f, w, k, p in B.fields(t9) if f == 2]
            if B.getv(n, 8) == 44 and packed != [bytes.fromhex("0304050612")]: errs.append("nó %s: lista compacta inesperada" % nid)
        for u, i in re.findall(rb"OfxImageEffectContextFilter_([0-9a-f-]{36})_(\d+)", B.getv(n, 10) or b""):
            if u.decode() != lmv or int(i) != nid: errs.append("nó %s: contexto OFX incoerente (%s_%s)" % (nid, u.decode()[:8], i.decode()))
        luts = [l.decode() for l in re.findall(rb"[\w .-]+(?:/[\w .-]+)+\.cube", n)]
        if any("\\" in l for l in luts): errs.append("nó %s: LUT com '\\'" % nid)
        rows.append((nid, nm, on, ofx_strings(n), luts, tabs))
    links = [(B.getv(q[3], 1), B.getv(q[3], 3), B.getv(q[3], 4) or 0, B.getv(q[3], 5), B.getv(q[3], 6)) for q in B.fields(g) if q[0] == 8]
    top_ids = [B.getv(q[3], 1) for q in B.fields(g) if q[0] == 7]
    for a, b, p, f5, f6 in links:
        if f5 != 64 or f6 != 64: errs.append("ligação %s->%s sem 64/64" % (a, b))
        if a not in top_ids or b not in top_ids: errs.append("ligação %s->%s para nó inexistente" % (a, b))
    gin = B.getv(B.getv(B.getv(g, 9), 3), 4); gout = B.getv(B.getv(B.getv(g, 10), 3), 4)
    nxt = {a: b for a, b, p, *_ in links if p == 0}; cur, seen = gin, set()
    while cur != gout and cur in nxt and cur not in seen: seen.add(cur); cur = nxt[cur]
    if cur != gout: errs.append("a cadeia principal não liga a entrada (%s) à saída (%s)" % (gin, gout))
    th = re.search(r"<BtThumnail\b[^>]*>.*?<Buffer>([0-9a-f]*)</Buffer>", x, re.S)
    if not th or not bytes.fromhex(th.group(1)).startswith(b"\xff\xd8"): errs.append("miniatura JPEG em falta")
    label = re.search(r"<Label>([^<]*)</Label>", x).group(1)
    print("==", os.path.basename(path), "|", label, "|", "OK" if not errs else "%d PROBLEMA(S)" % len(errs))
    for nid, nm, on, cst, luts, tabs in rows:
        extra = []
        if cst: extra.append("CST " + " ".join("%s=%s" % kv for kv in sorted(cst.items())))
        if luts: extra.append("LUT " + ", ".join(luts))
        print("   %3s %-14s %s %s" % (nid, nm, "ON " if on else "OFF", " | ".join(extra)))
    for e in errs: print("   !!", e)
    return not errs

if __name__ == "__main__":
    ok = all([check(p) for p in sys.argv[1:]])
    sys.exit(0 if ok else 1)
