"""Capa gráfica para a miniatura de um PowerGrade (nunca usar fotos de pessoas).

Uso:
  python3 powergrade_cover.py saida.png "CINEKIT" "C-LOG3" "KODAK 5219 + 2383" [clog3|rec709|#rrggbb] ["rodapé"]

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

def draw_icon(d, kind, cx, cy, s, col):
    """Pictogramas simples: 'drone' (4 hélices) ou 'gimbal' (punho + cabeça de câmara)."""
    w = max(4, int(s * 0.05))
    if kind == "drone":
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            ax, ay = cx + dx * s * 0.42, cy + dy * s * 0.42
            d.line((cx, cy, ax, ay), fill=col, width=w)
            d.ellipse((ax - s * 0.2, ay - s * 0.2, ax + s * 0.2, ay + s * 0.2), outline=col, width=w)
        d.rounded_rectangle((cx - s * 0.16, cy - s * 0.12, cx + s * 0.16, cy + s * 0.12), int(s * 0.05), fill=col)
    elif kind == "gimbal":
        d.rounded_rectangle((cx - s * 0.13, cy - s * 0.05, cx + s * 0.13, cy + s * 0.62), int(s * 0.1), outline=col, width=w)
        d.ellipse((cx - s * 0.06, cy + s * 0.18, cx + s * 0.06, cy + s * 0.30), fill=col)
        d.rounded_rectangle((cx - s * 0.2, cy - s * 0.5, cx + s * 0.2, cy - s * 0.12), int(s * 0.08), outline=col, width=w)
        d.ellipse((cx - s * 0.1, cy - s * 0.41, cx + s * 0.1, cy - s * 0.21), outline=col, width=w)

def cover(path, title, big, look, accent, footer="Canon R50 V  ·  DaVinci Resolve",
          title_font="InterDisplay-Bold.otf", title_size=54, icon=None):
    W, H = 1152, 648
    y, x = np.mgrid[0:H, 0:W]
    base = np.zeros((H, W, 3)); base[...] = (14, 15, 18)
    glow = np.exp(-(((x - W * 0.82) / (W * 0.45)) ** 2 + ((y - H * 0.15) / (H * 0.6)) ** 2))[..., None] * np.array(accent)
    glow2 = np.exp(-(((x - W * 0.1) / (W * 0.4)) ** 2 + ((y - H * 1.0) / (H * 0.5)) ** 2))[..., None] * np.array((20, 70, 80))
    im = Image.fromarray(np.clip(base + glow * 0.55 + glow2 * 0.6, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for yy in (18, H - 46):
        for xx in range(20, W, 58): d.rounded_rectangle((xx, yy, xx + 34, yy + 28), 6, fill=(0, 0, 0))
    if icon: draw_icon(d, icon, W - 190, 205, 230, tuple(int(c * 0.9) for c in accent))
    ty = 118 if title_size <= 60 else 118 - (title_size - 54)
    d.text((70, ty), title, font=font(title_font, title_size), fill=(235, 228, 215))
    size = 210
    room = W - 140 - (300 if icon else 0)
    while size > 90 and d.textlength(big, font=font("InterDisplay-Black.otf", size)) > room: size -= 10
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
    footer = sys.argv[6] if len(sys.argv) > 6 else "Canon R50 V  ·  DaVinci Resolve"
    cover(out, title, big, look, accent, footer)
    print("ok:", out)
