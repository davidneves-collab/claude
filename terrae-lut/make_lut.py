"""Gera o LUT de look Terrae (Rec.709 / Gamma 2.4 -> Rec.709 / Gamma 2.4).

Aplicar DEPOIS da conversao C-Log3/Cinema Gamut -> Rec.709 (Color Space Transform no DaVinci).
"""
import sys
import numpy as np

SAND = np.array([0xE4, 0xDD, 0xD3]) / 255.0
SIZE = 33


def rgb_to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-8
    rr = m & (mx == r)
    gg = m & (mx == g) & ~rr
    bb = m & ~rr & ~gg
    h[rr] = ((g - b)[rr] / d[rr]) % 6
    h[gg] = (b - r)[gg] / d[gg] + 2
    h[bb] = (r - g)[bb] / d[bb] + 4
    h = h * 60.0
    s = np.where(mx > 1e-8, d / np.maximum(mx, 1e-8), 0)
    return h, s, mx


def hsv_to_rgb(h, s, v):
    h = (h % 360) / 60.0
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    out = np.stack([
        np.choose(i, [v, q, p, p, t, v]),
        np.choose(i, [t, v, v, q, p, p]),
        np.choose(i, [p, p, t, v, v, q]),
    ], -1)
    return out


def bump(h, center, width):
    d = np.abs(((h - center + 180) % 360) - 180)
    return np.where(d < width, 0.5 * (1 + np.cos(np.pi * d / width)), 0.0)


def look(rgb):
    rgb = np.clip(rgb, 0, 1)
    h, s, v = rgb_to_hsv(rgb)

    w_green = bump(h, 105, 75)   # vegetacao
    w_skin = bump(h, 25, 22)     # pele, madeira, terracota
    w_blue = bump(h, 215, 50)    # ceu, agua

    # Verdes puxados para Sage (oliva), menos saturados
    h = h - 20 * w_green
    sat = 0.90 - 0.20 * w_green - 0.08 * w_blue + 0.08 * w_skin
    # Pele protegida: nunca acima de ~0.98 da saturacao original
    s = np.clip(s * sat, 0, 1)
    rgb = hsv_to_rgb(h, s, v)

    # Curva: S suave, pretos levantados (sem esmagar), altas luzes contidas
    x = np.clip(rgb, 0, 1)
    g = 0.82 * x + 0.18 * (3 * x**2 - 2 * x**3)
    black, white = 0.03, 0.955
    rgb = black + (white - black) * g

    # Split tone: altas luzes para Sand, sombras neutras-quentes (Ink)
    y = rgb @ np.array([0.2126, 0.7152, 0.0722])
    sand_tint = SAND / SAND.mean()
    hi = (np.clip((y - 0.45) / 0.55, 0, 1) ** 2)[..., None] * 0.45
    rgb = rgb * (1 - hi + hi * sand_tint)
    lo = ((1 - np.clip(y / 0.35, 0, 1)) ** 2)[..., None]
    rgb = rgb + lo * np.array([0.006, 0.004, 0.0])
    return np.clip(rgb, 0, 1)


def write_cube(path):
    lin = np.linspace(0, 1, SIZE)
    b, g, r = np.meshgrid(lin, lin, lin, indexing="ij")  # R varia mais rapido
    grid = np.stack([r, g, b], -1).reshape(-1, 3)
    out = look(grid)
    with open(path, "w") as f:
        f.write('TITLE "Terrae Look v1 - Rec709 G2.4"\n')
        f.write("# Aplicar apos CST C-Log3/Cinema Gamut -> Rec.709/Gamma 2.4\n")
        f.write(f"LUT_3D_SIZE {SIZE}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n")
        for px in out:
            f.write(f"{px[0]:.6f} {px[1]:.6f} {px[2]:.6f}\n")


if __name__ == "__main__":
    write_cube(sys.argv[1] if len(sys.argv) > 1 else "Terrae_Look_v1.cube")
