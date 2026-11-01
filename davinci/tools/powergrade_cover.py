"""Capa gráfica para a miniatura de um PowerGrade (nunca usar fotos de pessoas).

Uso:
  python3 powergrade_cover.py saida.png "CINEKIT" "C-LOG3" "KODAK 5219 + 2383" [clog3|rec709|#rrggbb]

Fundo escuro com perfurações de película, título pequeno, modo em grande (laranja para C-LOG3,
azul-petróleo para REC709) e o look por baixo. 1152x648 (o construtor reduz para 576x324).
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = "/usr/share/fonts/opentype/inter/"
ACCENTS = {"clog3": (232, 140, 58), "rec709": (80, 170, 190)}

def font(name, size):
    for nm in (name, "InterDisplay-Bold.otf", "Inter-Bold.otf"):
        try: return ImageFont.truetype(FONTS + nm, size)
        except Exception: pass
    return ImageFont.load_default()

def cover(path, title, big, look, accent, footer="Canon R50 V  ·  DaVinci Resolve"):
    W, H = 1152, 648
    y, x = np.mgrid[0:H, 0:W]
    base = np.zeros((H, W, 3)); base[...] = (14, 15, 18)
    glow = np.exp(-(((x - W * 0.82) / (W * 0.45)) ** 2 + ((y - H * 0.15) / (H * 0.6)) ** 2))[..., None] * np.array(accent)
    glow2 = np.exp(-(((x - W * 0.1) / (W * 0.4)) ** 2 + ((y - H * 1.0) / (H * 0.5)) ** 2))[..., None] * np.array((20, 70, 80))
    im = Image.fromarray(np.clip(base + glow * 0.55 + glow2 * 0.6, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for yy in (18, H - 46):
        for xx in range(20, W, 58): d.rounded_rectangle((xx, yy, xx + 34, yy + 28), 6, fill=(0, 0, 0))
    d.text((70, 118), title, font=font("InterDisplay-Bold.otf", 54), fill=(235, 228, 215))
    size = 210
    while size > 90 and d.textlength(big, font=font("InterDisplay-Black.otf", size)) > W - 140: size -= 10
    d.text((66, 178), big, font=font("InterDisplay-Black.otf", size), fill=tuple(int(c) for c in accent))
    d.line((72, 438, W - 72, 438), fill=(235, 228, 215), width=3)
    lsize = 64
    while lsize > 30 and d.textlength(look, font=font("InterDisplay-Bold.otf", lsize)) > W - 144: lsize -= 4
    d.text((72, 458), look, font=font("InterDisplay-Bold.otf", lsize), fill=(235, 228, 215))
    d.text((72, 540), footer, font=font("Inter-Medium.otf", 34), fill=(170, 165, 155))
    im.save(path)

if __name__ == "__main__":
    out, title, big, look = sys.argv[1:5]
    acc = sys.argv[5] if len(sys.argv) > 5 else ("clog3" if "LOG" in big.upper() else "rec709")
    accent = ACCENTS.get(acc) or tuple(int(acc.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    cover(out, title, big, look, accent)
    print("ok:", out)
