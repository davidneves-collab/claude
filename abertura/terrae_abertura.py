"""Terrae · abertura/fecho em sequência PNG com alfa (9:16, 1080x1920, 25 fps).

Sequência:
  1. As letras T E R R A E entram uma a uma, da esquerda para a direita (branco com opacidade).
  2. Pausa curta com a palavra completa.
  3. As letras deslizam para a posição do lockup e o símbolo monta-se à esquerda:
     o telhado desce, a base sobe, e encaixam.
  4. O lockup fica parado até ao fim.

Fundo transparente: pôr por cima do vídeo no DaVinci (entrada ou saída).
Lettering e símbolo vêm do SVG oficial (terrae_logo_neg_horizontal.svg). Cada letra
e cada peça do símbolo é animada em separado, sem redesenhar nada.

Uso:
  python3 terrae_abertura.py                      # abertura, ≈2,5 s
  python3 terrae_abertura.py --nome fecho --hold 2.5
  python3 terrae_abertura.py --fundo sand            # fundo sólido Sand, letras Ink
  opções: --opacidade 0.85  --largura 860  --saida DIR
"""
import argparse, io, os, re, shutil, subprocess
import cairosvg
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 25
WHITE = (255, 255, 255)
FUNDOS = {  # cor de fundo, cor das letras e do símbolo
    "transparente": (None, WHITE),
    "sand": ((0xE4, 0xDD, 0xD3), (0x1D, 0x1D, 0x1B)),
    "ink": ((0x1D, 0x1D, 0x1B), WHITE),
    "sienna": ((0x97, 0x6E, 0x53), (0xE4, 0xDD, 0xD3)),
    "sage": ((0x8A, 0x8E, 0x75), (0xE4, 0xDD, 0xD3)),
}

# tempos (s)
# Afinado para retenção em Reels: a primeira letra aparece logo no 1.º frame e o lockup
# fica completo antes dos 2,1 s. Total ≈ 2,5 s como abertura; para fecho, usar --hold maior.
T_LETRA0 = 0.0       # primeira letra
STAGGER = 0.13       # intervalo entre letras
D_LETRA = 0.40       # duração da entrada de cada letra
PAUSA = 0.40         # pausa com a palavra completa, antes do logo
D_LOGO = 0.65        # deslize das letras + montagem do símbolo
HOLD = 0.40          # lockup parado no fim (abertura)
N_LETRAS = 6
T_PALAVRA = T_LETRA0 + STAGGER * (N_LETRAS - 1) + D_LETRA
T_LOGO = T_PALAVRA + PAUSA


def clamp(t):
    return min(max(t, 0.0), 1.0)


def out_expo(t):
    t = clamp(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def out_cubic(t):
    return 1 - (1 - clamp(t)) ** 3


def in_out(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def prog(t, a, d, curve=out_cubic):
    return curve((t - a) / d)


class Lockup:
    VB = (722.93, 205.56)
    LETRAS_X0 = 295.35        # início do T no SVG (x mínimo das letras)

    def __init__(self, width, color):
        svg = open(f"{AQUI}/assets/terrae_logo_neg_horizontal.svg").read()
        els = re.findall(r"<(?:path|polygon)[^>]*/>", svg)
        hexc = "#%02x%02x%02x" % color
        self.w = width
        self.h = int(round(width * self.VB[1] / self.VB[0]))
        self.k = width / self.VB[0]

        def render(el):
            el = el.replace('class="cls-1"', f'fill="{hexc}"')
            doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.VB[0]} {self.VB[1]}">{el}</svg>')
            png = cairosvg.svg2png(bytestring=doc.encode(), output_width=self.w, output_height=self.h)
            return Image.open(io.BytesIO(png)).convert("RGBA")

        self.letras = [render(e) for e in els[:6]]
        self.base, self.telhado = render(els[6]), render(els[7])


def com_alfa(img, a):
    if a >= 1:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(round(v * a))))
    return img


def frame(L, t, opac, fundo=None):
    img = Image.new("RGBA", (W, H), (fundo + (255,)) if fundo else (0, 0, 0, 0))
    x_lock = (W - L.w) / 2                       # lockup final centrado
    y_lock = (H - L.h) / 2
    # na fase das letras, a palavra está centrada sozinha
    letras_w = (L.VB[0] - L.LETRAS_X0) * L.k
    x_palavra = (W - letras_w) / 2 - L.LETRAS_X0 * L.k
    g = prog(t, T_LOGO, D_LOGO, in_out)
    x_letras = x_palavra + (x_lock - x_palavra) * g

    camada = Image.new("RGBA", (L.w, L.h), (0, 0, 0, 0))
    for i, letra in enumerate(L.letras):
        t0 = T_LETRA0 + i * STAGGER
        p = prog(t + 1 / FPS, t0, D_LETRA)   # a 1.ª letra já se vê no frame 0
        if p <= 0:
            continue
        # entra a deslizar ligeiramente da esquerda, com fade
        dx = -int(round((1 - out_expo((t - t0) / D_LETRA)) * 26))
        camada.alpha_composite(com_alfa(letra, p), (dx, 0))
    img.alpha_composite(com_alfa(camada, opac), (int(round(x_letras)), int(round(y_lock))))

    # símbolo: telhado desce, base sobe, com fade, já em sincronia com o deslize das letras
    q = prog(t, T_LOGO + 0.10, D_LOGO - 0.05)
    if q > 0:
        off = int(round((1 - q) * 70))
        simb = Image.new("RGBA", (L.w, L.h + 2 * 70), (0, 0, 0, 0))
        simb.alpha_composite(L.telhado, (0, 70 - off))
        simb.alpha_composite(L.base, (0, 70 + off))
        img.alpha_composite(com_alfa(simb, q * opac), (int(round(x_lock)), int(round(y_lock)) - 70))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=f"{AQUI}/saida")
    ap.add_argument("--opacidade", type=float, default=0.85)
    ap.add_argument("--hold", type=float, default=HOLD, help="segundos com o lockup parado no fim (fecho: 2 a 3)")
    ap.add_argument("--nome", default="abertura", help="abertura ou fecho (só muda os nomes dos ficheiros)")
    ap.add_argument("--fundo", default="transparente", choices=list(FUNDOS),
                    help="transparente (para pôr sobre o vídeo) ou fundo sólido Terrae")
    ap.add_argument("--largura", type=int, default=860, help="largura do lockup final em px")
    a = ap.parse_args()

    DUR = T_LOGO + D_LOGO + a.hold
    fundo, cor = FUNDOS[a.fundo]
    base = f"Terrae_{a.nome}_9x16" + (f"_{a.fundo}" if fundo else "")
    pasta = f"{a.saida}/{base}_PNG"
    shutil.rmtree(pasta, ignore_errors=True)
    os.makedirs(pasta)
    L = Lockup(a.largura, cor)
    n = int(round(DUR * FPS))
    for k in range(n):
        frame(L, k / FPS, a.opacidade, fundo).convert("RGB" if fundo else "RGBA").save(f"{pasta}/terrae_{a.nome}_{k:04d}.png", optimize=True)

    # pré-visualização em MP4 sobre Ink (só para ver; a peça de trabalho é a sequência PNG)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x1D1D1B:s={W}x{H}:r={FPS}",
                    "-framerate", str(FPS), "-i", f"{pasta}/terrae_{a.nome}_%04d.png",
                    "-filter_complex", "[0:v][1:v]overlay=shortest=1,format=yuv420p",
                    "-c:v", "libx264", "-crf", "16", "-movflags", "+faststart",
                    f"{a.saida}/{base}_preview.mp4"], check=True)
    shutil.make_archive(f"{a.saida}/{base}_PNG", "zip", pasta)
    print(f"ok: {n} frames, {DUR:.2f} s, {FPS} fps · palavra completa em {T_PALAVRA:.2f} s, logo em {T_LOGO:.2f} s")


if __name__ == "__main__":
    main()
