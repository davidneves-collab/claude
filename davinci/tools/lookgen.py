"""Gera LUTs .cube de um look para câmaras Canon (Canon 709 e Canon Log 3 / Cinema Gamut).

Uso:
  python3 lookgen.py look.json pasta_saida [frame1.png frame2.png ...]

Gera em pasta_saida:
  <nome>_Canon709.cube          entrada Canon 709 / BT.709 (já em Rec.709)  -> look -> Rec.709 gama 2.4
  <nome>_CLog3_CinemaGamut.cube entrada Canon Log 3 + Cinema Gamut          -> Rec.709 -> look
  preview_<frame>.png           antes/depois (look aplicado ao frame, tratado como Canon 709)

O look é sempre aplicado em espaço de visualização Rec.709 (gama 2.4). A versão C-Log3 faz primeiro a
conversão de cena (C-Log3 -> linear -> Cinema Gamut -> Rec.709 -> curva de tons), para que as duas
versões tenham exatamente o mesmo look.

Níveis: o DaVinci normaliza os clips "Video level" para 0-1 antes dos nós (código 64 -> 0, 940 -> 1),
por isso a entrada C-Log3 é interpretada nessa escala (cinzento 18% = 0.328).
"""
import json, os, sys
import numpy as np

# ---------------------------------------------------------------- utilidades
def pchip(xk, yk):
    """Interpolação cúbica monótona (Fritsch-Carlson). Devolve f(x) com extrapolação linear."""
    xk = np.asarray(xk, float); yk = np.asarray(yk, float)
    h = np.diff(xk); d = np.diff(yk) / h
    m = np.zeros_like(yk)
    for i in range(1, len(xk) - 1):
        if d[i - 1] * d[i] > 0:
            w1 = 2 * h[i] + h[i - 1]; w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0] = d[0]; m[-1] = d[-1]
    def f(x):
        x = np.asarray(x, float); out = np.empty_like(x)
        lo = x < xk[0]; hi = x > xk[-1]; mid = ~(lo | hi)
        out[lo] = yk[0] + m[0] * (x[lo] - xk[0])
        out[hi] = yk[-1] + m[-1] * (x[hi] - xk[-1])
        xm = x[mid]; i = np.clip(np.searchsorted(xk, xm) - 1, 0, len(xk) - 2)
        t = (xm - xk[i]) / h[i]
        h00 = (1 + 2 * t) * (1 - t) ** 2; h10 = t * (1 - t) ** 2; h01 = t * t * (3 - 2 * t); h11 = t * t * (t - 1)
        out[mid] = h00 * yk[i] + h10 * h[i] * m[i] + h01 * yk[i + 1] + h11 * h[i] * m[i + 1]
        return out
    return f

LUMA = np.array([0.2126, 0.7152, 0.0722])

def soft_clip01(u, k=0.12):
    """Identidade entre k e 1-k; aproxima-se de 0 e 1 suavemente (sem cortes duros)."""
    u = np.asarray(u, float)
    hi = (1 - k) + k * np.tanh((u - (1 - k)) / k)
    lo = k - k * np.tanh((k - u) / k)
    return np.where(u > 1 - k, hi, np.where(u < k, lo, u))

# ---------------------------------------------------------------- Canon Log 3 / Cinema Gamut
def clog3_decode(v):
    """Valor no DaVinci (níveis vídeo normalizados) -> reflectância linear (cinzento 18% = 0.18)."""
    raw = (np.asarray(v, float) * 876.0 + 64.0) / 1023.0          # código normalizado (fórmula da Canon)
    x = np.where(raw < 0.097465473,
                 -(10 ** ((0.12783901 - raw) / 0.36726845) - 1) / 14.98325,
                 np.where(raw <= 0.15277891,
                          (raw - 0.12512219) / 1.9754798,
                          (10 ** ((raw - 0.12240537) / 0.36726845) - 1) / 14.98325))
    return x * 0.9

def clog3_encode(x):
    """Inverso de clog3_decode (para testes)."""
    x = np.asarray(x, float) / 0.9
    raw = np.where(x < -0.014, -0.36726845 * np.log10(np.maximum(-x * 14.98325 + 1, 1e-10)) + 0.12783901,
                   np.where(x <= 0.014, 1.9754798 * x + 0.12512219,
                            0.36726845 * np.log10(np.maximum(x * 14.98325 + 1, 1e-10)) + 0.12240537))
    return (raw * 1023.0 - 64.0) / 876.0

def _rgb_to_xyz(prim, white):
    P = np.array([[x / y, 1.0, (1 - x - y) / y] for x, y in prim]).T
    W = np.array([white[0] / white[1], 1.0, (1 - white[0] - white[1]) / white[1]])
    return P * np.linalg.solve(P, W)

D65 = (0.3127, 0.3290)
CINEMA_GAMUT = [(0.74, 0.27), (0.17, 1.14), (0.08, -0.10)]
REC709 = [(0.64, 0.33), (0.30, 0.60), (0.15, 0.06)]
M_CG_TO_709 = np.linalg.solve(_rgb_to_xyz(REC709, D65), _rgb_to_xyz(CINEMA_GAMUT, D65))

# Curva de tons (cena -> Rec.709 gama 2.4). Pontos: (stops relativos a 18%, valor codificado)
DRT_POINTS = [(-12, 0.0), (-7, 0.012), (-5, 0.045), (-3, 0.14), (-1.5, 0.27), (0, 0.415),
              (1, 0.53), (2.32, 0.80), (3.5, 0.915), (5, 0.975), (7, 0.997), (10, 1.0)]

def make_drt(points=DRT_POINTS):
    f = pchip([p[0] for p in points], [p[1] for p in points])
    def drt(lin):
        ev = np.log2(np.maximum(lin, 1e-6) / 0.18)
        return np.clip(f(ev), 0, 1)
    return drt

def gamut_soft_clip(rgb, thr=0.8):
    """Comprime suavemente valores negativos (cores fora do Rec.709) em vez de os cortar."""
    y = np.maximum((rgb * LUMA).sum(-1, keepdims=True), 1e-6)
    d = (y - rgb) / y                                      # distância ao eixo neutro (1 = no limite)
    dc = np.where(d > thr, thr + (1 - thr) * np.tanh((d - thr) / (1 - thr)), d)
    return y - dc * y

def clog3_to_709(v, drt=None):
    drt = drt or make_drt()
    lin = clog3_decode(v) @ M_CG_TO_709.T
    lin = gamut_soft_clip(lin)
    return drt(np.maximum(lin, 0))

# ---------------------------------------------------------------- look (espaço Rec.709 gama 2.4)
def hue_deg(rgb):
    y = (rgb * LUMA).sum(-1)
    cb = (rgb[..., 2] - y) / 1.8556; cr = (rgb[..., 0] - y) / 1.5748
    return np.degrees(np.arctan2(cr, cb)) % 360, y, cb, cr

def band_weight(h, center, width):
    d = np.abs(((h - center + 180) % 360) - 180)
    return np.where(d < width, 0.5 * (1 + np.cos(np.pi * d / width)), 0.0)

def apply_look(rgb, P):
    x = np.clip(np.asarray(rgb, float), 0, 1)
    # 1) temperatura/tinta em linear de ecrã
    lin = x ** 2.4
    t = P.get("temperature", 0.0); tint = P.get("tint", 0.0)
    gains = np.array([1 + 0.10 * t, 1 + 0.04 * tint * -1, 1 - 0.10 * t])
    gains = gains / (gains * LUMA).sum()
    lin = lin * gains * 2 ** P.get("exposure", 0.0)
    x = np.clip(lin, 0, None) ** (1 / 2.4)
    # 2) contraste em torno do pivot (com joelho suave) e curva mestra opcional
    c = P.get("contrast", 1.0); pv = P.get("pivot", 0.42)
    if c != 1.0:
        x = soft_clip01(pv + (x - pv) * c)
    if P.get("curve"):
        pts = P["curve"]; f = pchip([p[0] for p in pts], [p[1] for p in pts]); x = f(x)
    x = np.clip(x, 0, 1)
    # 3) cor por zonas (sombras / médios / altas luzes), tipo lift-gamma-gain
    y = (x * LUMA).sum(-1, keepdims=True)
    ws = np.clip(1 - y / 0.5, 0, 1) ** 2; wh = np.clip((y - 0.5) / 0.5, 0, 1) ** 2; wm = 1 - ws - wh
    for w, key in ((ws, "shadows_rgb"), (wm, "midtones_rgb"), (wh, "highlights_rgb")):
        off = np.array(P.get(key, [0, 0, 0]), float)
        off = off - (off * LUMA).sum()                     # só cor, sem mudar a luminância
        x = x + w * off
    # 4) saturação global, por luminância e por bandas de matiz
    h, y1, cb, cr = hue_deg(np.clip(x, 0, 1))
    y1 = y1[..., None]
    sat = P.get("saturation", 1.0) * np.interp(y1[..., 0], [0, 0.25, 0.75, 1],
                                               [P.get("sat_shadows", 1.0), 1, 1, P.get("sat_highlights", 1.0)])
    hshift = np.zeros_like(h); lum = np.zeros_like(h)
    skin = band_weight(h, P.get("skin_hue", 55.0), 30.0) * P.get("skin_protect", 0.0)
    for b in P.get("hue_bands", []):
        w = band_weight(h, b["center"], b.get("width", 40.0)) * (1 - skin)
        sat = sat * (1 + w * (b.get("sat", 1.0) - 1))
        hshift = hshift + w * b.get("hue_shift", 0.0)
        lum = lum + w * b.get("lum", 0.0)
    ang = np.radians(hshift); cb2 = cb * np.cos(ang) - cr * np.sin(ang); cr2 = cb * np.sin(ang) + cr * np.cos(ang)
    cb2 *= sat; cr2 *= sat
    yy = y1[..., 0] + lum
    r = yy + 1.5748 * cr2; b_ = yy + 1.8556 * cb2; g = (yy - LUMA[0] * r - LUMA[2] * b_) / LUMA[1]
    x = np.stack([r, g, b_], -1)
    # 5) pretos levantados / brancos rebaixados (look "fade")
    bl = np.array(P.get("black_rgb", [P.get("black_lift", 0.0)] * 3), float)
    wp = np.array(P.get("white_rgb", [P.get("white_point", 1.0)] * 3), float)
    x = bl + np.clip(x, 0, 1) * (wp - bl)
    return np.clip(x, 0, 1)

# ---------------------------------------------------------------- .cube
def grid(n):
    v = np.linspace(0, 1, n)
    b, g, r = np.meshgrid(v, v, v, indexing="ij")             # R varia mais depressa (ordem .cube)
    return np.stack([r, g, b], -1).reshape(-1, 3)

def write_cube(path, n, data, title):
    with open(path, "w") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
        np.savetxt(f, np.clip(data, 0, 1), fmt="%.6f")

def read_cube(path):
    n = None; rows = []
    for line in open(path):
        s = line.strip()
        if s.startswith("LUT_3D_SIZE"): n = int(s.split()[1])
        elif s and (s[0].isdigit() or s[0] in "-."): rows.append([float(t) for t in s.split()])
    return n, np.array(rows).reshape(n, n, n, 3)                 # [b][g][r]

def apply_cube(img, n, lut):
    """Interpolação trilinear de uma imagem float (H,W,3) 0-1."""
    p = np.clip(img, 0, 1) * (n - 1); i0 = np.floor(p).astype(int); i0 = np.minimum(i0, n - 2); f = p - i0
    out = 0
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (f[..., 0] if dr else 1 - f[..., 0]) * (f[..., 1] if dg else 1 - f[..., 1]) * (f[..., 2] if db else 1 - f[..., 2])
                out = out + w[..., None] * lut[i0[..., 2] + db, i0[..., 1] + dg, i0[..., 0] + dr]
    return out

def build(look_path, outdir, frames=(), n709=33, nlog=65):
    P = json.load(open(look_path)); name = P.get("name", "Look")
    os.makedirs(outdir, exist_ok=True)
    g = grid(n709)
    p709 = os.path.join(outdir, f"{name}_Canon709.cube")
    write_cube(p709, n709, apply_look(g, P), f"{name} - Canon 709 / BT.709 -> Rec.709")
    gl = grid(nlog)
    pl = os.path.join(outdir, f"{name}_CLog3_CinemaGamut.cube")
    write_cube(pl, nlog, apply_look(clog3_to_709(gl), P), f"{name} - Canon Log 3 Cinema Gamut -> Rec.709")
    outs = [p709, pl]
    if frames:
        from PIL import Image
        n, lut = read_cube(p709)
        for fr in frames:
            im = np.asarray(Image.open(fr).convert("RGB"), float) / 255
            after = apply_cube(im, n, lut)
            both = np.concatenate([im, np.ones((im.shape[0], 8, 3)), after], 1)
            po = os.path.join(outdir, "preview_" + os.path.splitext(os.path.basename(fr))[0] + ".png")
            Image.fromarray((both * 255 + 0.5).astype(np.uint8)).save(po); outs.append(po)
    return outs

if __name__ == "__main__":
    for p in build(sys.argv[1], sys.argv[2], sys.argv[3:]): print(p)
