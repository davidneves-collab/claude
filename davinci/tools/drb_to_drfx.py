"""Converte um bin (.drb) do DaVinci 20/21 com títulos Fusion num pacote .drfx para uma versão anterior do DaVinci (ex.: 19).

Uso: python3 drb_to_drfx.py entrada.drb saida.drfx "Nome da Pasta"
Cada título do Media Pool vira um .setting em Edit/Titles/<Nome da Pasta>/.
"""
import sys, os, re, zlib, zipfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drfx_lib import layer_info, macro_text, inputs_for

def comp_tools(cba_hex):
    d = zlib.decompress(bytes.fromhex(cba_hex)[4:])
    i = d.find(b"Composition {"); j = d.find(b"Compressed = true", i); k = d.find(b"x\xda", j)
    return zlib.decompress(d[k:]).decode()

def main(src, dst, vendor):
    z = zipfile.ZipFile(src)
    items = collections.OrderedDict(); seen = set()
    for name in sorted(n for n in z.namelist() if n.startswith("MediaPool/") and n.endswith("MpFolder.xml")):
        txt = z.read(name).decode("utf-8")
        folder = re.sub(r"^\d+_", "", os.path.basename(os.path.dirname(name)))
        for m in re.finditer(r"<CompositionBA>([0-9a-f]+)</CompositionBA>", txt):
            body = comp_tools(m.group(1))
            if body in seen: continue
            seen.add(body); items.setdefault(folder, []).append(body)
    out = {}
    for folder, bodies in items.items():
        for body in bodies:
            keep, names, outop, txt_src, tn, sample = layer_info(body)
            label = folder if len(bodies) == 1 else f"{folder} - {sample}"
            fname = re.sub(r'[\\/:*?"<>|]', "", label).strip(); base = fname; i = 2
            while fname in out: fname = f"{base} {i}"; i += 1
            ins, _ = inputs_for("", txt_src, tn, 1, "Text")
            out[fname] = macro_text("M_" + re.sub(r"\W", "_", fname), ins, outop, [x for _, _, x in keep])
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for fname, s in out.items(): zo.writestr(f"Edit/Titles/{vendor}/{fname}.setting", s)
    print(f"{len(out)} títulos -> {dst}")
    for f in out: print("  ", f)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Titulos Convertidos")
