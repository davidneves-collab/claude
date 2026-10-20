# Look Café v1

LUT `Look_Cafe_v1.cube` (33³): entrada e saída em DaVinci Wide Gamut / DaVinci Intermediate.
Vai entre o CST IN e o CST OUT (DWG/DI → Rec.709 Gamma 2.4, sem tone mapping).

Feita a partir de um reel de referência com versão log e versão gradeada (wipe):
1. `pairs.py` — alinha pares de frames log/gradeado do mesmo plano e recolhe píxeis.
2. `fit.py`, `model.py` — curva de luminância + matriz de crominância com desvios por zona de luz.
3. `makelut.py` — gera a v1 (saturação ×1.15). `apply.py`/`colormath.py` — conversões.
4. v2: `refine.py` (correção 3D por cor, `corr.npy`), `tune.py` (curva por quantis, `tone2.json`), `tune2.py` (cor por zona de luz, `tone3.json`), `makelut2.py` → `Look_Cafe_v2.cube` e `comparacao_v1_v2.jpg`.
5. `val_lut.jpg` — validação: resultado (esquerda) vs referência (direita).

Suposição: a referência foi filmada em Sony S-Log3 / S-Gamut3.Cine (não confirmado).
Instalar no Mac em `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/Terrae/`.
6. v3: `meas.py` (croma por zona de luz), `makelut3.py <extra> <saida.cube>` sobre a v2 → `Look_Cafe_v3.cube` (medida) e `Look_Cafe_v3_Forte.cube` (saturação extra ×1.2 nos médios/sombras); `comparacao_v3.jpg`.
7. **v4 (método correto):** `wipepairs.py` usa a cortina do vídeo — o mesmo píxel está em log no frame t e gradeado no t+1
   (1/30 s), dando 1,77 M pares exatos em todos os planos. `fit4.py`/`m4.py`: curva de tons monótona + matriz de cor 3x3 por
   zona de luz (ridge) em espaço descodificado + grelha 3D de correção (`m4corr.npy`). `makelut4.py` → `Look_Cafe_v4.cube`.
   `comparacao_v4_cortina.jpg`: à esquerda da linha amarela o original, à direita a LUT aplicada ao log do mesmo frame.
   As v1–v3 comparavam frames de momentos diferentes e ajustavam por distribuição (confundia a cor dos objetos com o grade).
