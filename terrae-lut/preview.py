import numpy as np
from PIL import Image, ImageDraw
W, H = 960, 540
img = np.zeros((H, W, 3))
# rampa de cinzentos
img[:90] = np.linspace(0, 1, W)[None, :, None]
# varrimento de matiz
import colorsys
for x in range(W):
    img[90:180, x] = colorsys.hsv_to_rgb(x / W, 0.7, 0.85)
patches = {
    "pele clara": (0.86, 0.66, 0.55), "pele media": (0.68, 0.48, 0.37),
    "vegetacao": (0.30, 0.52, 0.22), "relva": (0.42, 0.65, 0.28),
    "ceu": (0.45, 0.65, 0.88), "terracota": (0.72, 0.38, 0.25),
    "madeira": (0.55, 0.38, 0.24), "parede branca": (0.93, 0.93, 0.92),
    "sombra": (0.12, 0.12, 0.13), "betao": (0.55, 0.55, 0.53),
}
pw = W // 5
for i, (name, c) in enumerate(patches.items()):
    x0, y0 = (i % 5) * pw, 180 + (i // 5) * 180
    img[y0:y0 + 180, x0:x0 + pw] = c
im = Image.fromarray((img * 255).astype(np.uint8))
d = ImageDraw.Draw(im)
for i, name in enumerate(patches):
    d.text(((i % 5) * pw + 8, 180 + (i // 5) * 180 + 8), name, fill=(0, 0, 0) if sum(list(patches.values())[i]) > 1.2 else (255, 255, 255))
im.save("test_before.png")
