"""Terrae · render de legendas para vídeo vertical 1080x1920.

Segue legendas/NORMA_LEGENDAS_TERRAE.md: abertura com o símbolo desenhado,
blocos de legenda (filete + contexto Manrope + destaque Arya) com entrada
palavra a palavra, e fecho com lockup sobre Ink.

Uso:
  python3 terrae_legendas.py blocos.json video.mp4 saida.mp4 --fonts DIR --assets DIR
"""
import argparse, json, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 25
SAND, SAND_LIGHT, SIENNA, INK = (0xE4, 0xDD, 0xD3), (0xEC, 0xE5, 0xDA), (0x97, 0x6E, 0x53), (0x1D, 0x1D, 0x1B)
SCHEMES = {  # caixa, texto, opacidade da caixa
    "ctx": (INK, SAND, 217),
    "sand": (SAND_LIGHT, INK, 255),
    "sienna": (SIENNA, SAND, 255),
    "ink": (INK, SAND, 255),
}
X0, BASE_Y, GAP = 72, 1480, 10
CTX = dict(size=46, h=83, base=57, pad=28)
EMPH = dict(size=96, h=134, base=99, pad=28)
INTRO, XFADE = 1.4, 0.4          # segundos de abertura antes da imagem; dissolve
OUTRO_FADE, OUTRO_HOLD = 0.8, 4.0


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ramp(t, a, d):
    return ease((t - a) / d) if d > 0 else float(t >= a)


# ---------- tempos das palavras ----------
def voiced_mask(wav_path):
    w = wave.open(wav_path)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    hop = w.getframerate() // 100
    rms = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) + 1 for i in range(0, len(a) - hop, hop)])
    db = 20 * np.log10(rms)
    return db > np.percentile(db, 35)  # 10 ms por posição


def word_times(block, mask):
    """Distribui as palavras do bloco pelo tempo com voz, proporcional ao n.º de letras."""
    words = [w for ln in block["lines"] for w in ln["text"].split()]
    s, e = int(block["start"] * 100), int(block["end"] * 100)
    seg = mask[s:e]
    idx = np.where(seg)[0] if seg.any() else np.arange(len(seg))
    weights = np.array([len(w) + 1 for w in words], float)
    cum = np.concatenate([[0], np.cumsum(weights)]) / weights.sum()
    return [block["start"] + idx[min(int(c * len(idx)), len(idx) - 1)] / 100 for c in cum[:-1]]


# ---------- desenho ----------
class Fonts:
    def __init__(self, d):
        self.cache, self.d = {}, d

    def get(self, kind, size):
        k = (kind, size)
        if k not in self.cache:
            f = "Manrope-Medium.ttf" if kind == "ctx" else "Arya-400.ttf"
            self.cache[k] = ImageFont.truetype(f"{self.d}/{f}", size)
        return self.cache[k]


def layout_block(block, fonts):
    """Calcula caixas e posições das palavras (de baixo para cima a partir de BASE_Y)."""
    centered = block.get("closing", False)
    lines, y = [], BASE_Y
    specs = []
    for ln in block["lines"]:
        if ln["style"] == "ctx":
            spec = dict(CTX)
        else:
            spec = dict(EMPH)
            if centered:
                spec.update(size=block.get("size", 132), h=int(block.get("size", 132) * 1.34),
                            base=int(block.get("size", 132) * 1.0), pad=46)
        specs.append(spec)
    for ln, spec in reversed(list(zip(block["lines"], specs))):
        font = fonts.get("ctx" if ln["style"] == "ctx" else "emph", spec["size"])
        words = ln["text"].split()
        text_w = font.getlength(ln["text"])
        bw = int(text_w + 2 * spec["pad"])
        bx = (W - bw) // 2 if centered else X0
        top = y - spec["h"]
        xs, cur = [], 0.0
        for i, w in enumerate(words):
            xs.append(bx + spec["pad"] + cur)
            cur += font.getlength(w + " ")
        lines.insert(0, dict(style=ln["style"], font=font, words=words, xs=xs,
                             box=(bx, top, bx + bw, y), baseline=top + spec["base"]))
        y = top - GAP
    fil_w = 84 if not centered else 84
    fil_x = X0 if not centered else W // 2 - fil_w // 2
    top_box = lines[0]["box"][1]
    filete = (fil_x, top_box - 24, fil_x + fil_w, top_box - 20)
    return lines, filete


def draw_block(img, block, lay, wt, t):
    lines, filete = lay
    out = 1 - ramp(t, block["hide"] - 0.16, 0.16)
    if out <= 0:
        return
    t0 = block["show"]
    d = ImageDraw.Draw(img)
    # filete
    p = ramp(t, t0, 0.25)
    if p > 0:
        x0, y0, x1, y1 = filete
        if block.get("closing"):
            c = (x0 + x1) / 2; half = (x1 - x0) / 2 * p
            d.rectangle((c - half, y0, c + half, y1), fill=SIENNA + (int(255 * out),))
        else:
            d.rectangle((x0, y0, x0 + (x1 - x0) * p, y1), fill=SIENNA + (int(255 * out),))
    wi = 0
    for ln in lines:
        box_c, txt_c, box_a = SCHEMES[ln["style"]]
        first = wt[wi]
        appear = max(t0, first - 0.18) if ln is not lines[0] else t0
        bx0, by0, bx1, by1 = ln["box"]
        layer = Image.new("RGBA", (bx1 - bx0 + 2, by1 - by0 + 2 + 80), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        if block.get("closing"):
            p = ramp(t, appear, 0.35)
            dy = int(-40 * (1 - p))
            if p > 0:
                ld.rectangle((0, 40 + dy, bx1 - bx0, 40 + dy + by1 - by0), fill=box_c + (int(box_a * p * out),))
        else:
            p = ramp(t, appear, 0.3)
            dy = 0
            if p > 0:
                ld.rectangle((0, 40, (bx1 - bx0) * p, 40 + by1 - by0), fill=box_c + (int(box_a * out),))
        for w, x in zip(ln["words"], ln["xs"]):
            a = ramp(t, max(wt[wi], appear + 0.12), 0.2)
            if a > 0:
                ld.text((x - bx0, ln["baseline"] - by0 + 40 + dy), w, font=ln["font"], anchor="ls",
                        fill=txt_c + (int(255 * a * out),))
            wi += 1
        img.alpha_composite(layer, (bx0, by0 - 40))


def mark_polys(scale, ox, oy):
    p1 = [289.01, 217.47, 150.78, 217.47, 12.55, 217.47, 12.55, 177.63, 0, 177.63, 0, 282.9, 12.55, 282.9, 12.55, 242.56,
          150.78, 242.56, 289.01, 242.56, 289.01, 282.9, 301.55, 282.9, 301.55, 177.63, 289.01, 177.63]
    p2 = [0, 68.12, 0, 137.29, 12.55, 137.29, 12.55, 90.37, 289.01, 27.92, 289.01, 137.29, 301.55, 137.29, 301.55, 0]
    return [[(ox + p[i] * scale, oy + p[i + 1] * scale) for i in range(0, len(p), 2)] for p in (p1, p2)]


def draw_intro(img, t):
    """Sand + símbolo desenhado a traço, depois preenchido. Dissolve para a imagem."""
    a = 1 - ramp(t, INTRO, XFADE)
    if a <= 0:
        return
    layer = Image.new("RGBA", (W, H), SAND + (255,))
    d = ImageDraw.Draw(layer)
    s = 290 / 301.55
    polys = mark_polys(s, (W - 290) / 2, 731)
    draw_p = ramp(t, 0.15, 0.85)
    for poly in polys:
        pts = poly + [poly[0]]
        segs = [np.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
        left = sum(segs) * draw_p
        for i, L in enumerate(segs):
            if left <= 0:
                break
            f = min(1, left / L)
            (xa, ya), (xb, yb) = pts[i], pts[i + 1]
            d.line((xa, ya, xa + (xb - xa) * f, ya + (yb - ya) * f), fill=INK + (255,), width=2)
            left -= L
    fill = ramp(t, 0.95, 0.3)
    if fill > 0:
        fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fl)
        for poly in polys:
            fd.polygon(poly, fill=INK + (int(255 * fill),))
        layer.alpha_composite(fl)
    if a < 1:
        layer.putalpha(Image.eval(layer.getchannel("A"), lambda v: int(v * a)))
    img.alpha_composite(layer)


class Outro:
    def __init__(self, start, fonts, assets):
        import cairosvg, io
        png = cairosvg.svg2png(url=f"{assets}/terrae_logo_neg.svg", output_width=485)
        self.logo = Image.open(io.BytesIO(png)).convert("RGBA")
        self.start = start
        man = lambda s: fonts.get("ctx", s)
        self.texts = [  # texto, fonte, y topo, atraso, cor, tracking
            ("Avaliação institucional. Mediação rigorosa.", man(42), 1067, 0.6, SAND, 0),
            ("terrae.pt", man(40), 1188, 1.0, SAND, 0),
            ("+351 925 348 020", man(40), 1254, 1.2, SAND, 0),
            ("AMI 27242", man(20), 1349, 1.4, (0xB4, 0xAF, 0xA9), 0.24),
        ]

    def draw(self, img, t):
        if t < self.start:
            return
        bg = ramp(t, self.start, OUTRO_FADE)
        layer = Image.new("RGBA", (W, H), INK + (int(255 * bg),))
        la = ramp(t, self.start + 0.3, 0.7)
        if la > 0:
            logo = self.logo.copy()
            logo.putalpha(Image.eval(logo.getchannel("A"), lambda v: int(v * la)))
            layer.alpha_composite(logo, ((W - logo.width) // 2, 480))
        d = ImageDraw.Draw(layer)
        fp = ramp(t, self.start + 0.5, 0.4)
        if fp > 0:
            d.rectangle((540 - 81 * fp, 1000, 540 + 81 * fp, 1002), fill=SIENNA + (255,))
        for txt, font, y, delay, col, track in self.texts:
            a = ramp(t, self.start + delay, 0.5)
            if a <= 0:
                continue
            if track:
                sp = font.size * track
                widths = [font.getlength(c) for c in txt]
                total = sum(widths) + sp * (len(txt) - 1)
                x = W / 2 - total / 2
                for c, wdt in zip(txt, widths):
                    d.text((x, y), c, font=font, anchor="lt", fill=col + (int(255 * a),))
                    x += wdt + sp
            else:
                d.text((W / 2, y), txt, font=font, anchor="mt", fill=col + (int(255 * a),))
        img.alpha_composite(layer)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks"); ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--fonts", required=True); ap.add_argument("--assets", required=True)
    ap.add_argument("--wav", required=True, help="áudio mono 16 kHz do vídeo")
    ap.add_argument("--video-end", type=float, required=True, help="fim útil da imagem (s, tempo do vídeo)")
    args = ap.parse_args()

    cfg = json.load(open(args.blocks))
    blocks = cfg["blocks"]
    fonts = Fonts(args.fonts)
    mask = voiced_mask(args.wav)
    for i, b in enumerate(blocks):
        b["wt"] = [INTRO + x for x in word_times(b, mask)]
        b["show"] = INTRO + b["start"] - 0.05
        nxt = blocks[i + 1]["start"] if i + 1 < len(blocks) else None
        end = b["end"] + 0.7
        if nxt is not None:
            end = min(end, nxt - 0.02) if nxt - b["end"] < 1.2 else end
        b["hide"] = INTRO + end
        b["lay"] = layout_block(b, fonts)

    outro_start = INTRO + cfg["outro_start"]
    total = outro_start + OUTRO_FADE + OUTRO_HOLD
    outro = Outro(outro_start, fonts, args.assets)
    n = int(round(total * FPS))

    pad_stop = total - INTRO - args.video_end + 0.5
    fc = (f"[0:v]trim=0:{args.video_end},setpts=PTS-STARTPTS,"
          f"tpad=start_duration={INTRO}:start_mode=clone:stop_duration={pad_stop}:stop_mode=clone[base];"
          f"[base][1:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[v];"
          f"[0:a]adelay={int(INTRO * 1000)}:all=1,apad,atrim=0:{total}[a]")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", args.video,
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:",
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-r", str(FPS),
           "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-t", f"{total:.3f}", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        t = k / FPS
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for b in blocks:
            if b["show"] <= t <= b["hide"]:
                draw_block(img, b, b["lay"], b["wt"], t)
        draw_intro(img, t)
        outro.draw(img, t)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"ok: {args.out} ({total:.2f} s, {n} frames)")


if __name__ == "__main__":
    main()
