# Terrae · abertura e fecho (9:16, PNG com alfa)

Sequência PNG 1080×1920, 25 fps, fundo transparente, para pôr por cima do vídeo no DaVinci.

| Tempo | O que acontece |
|---|---|
| 0,00–1,05 s | T E R R A E entram letra a letra, da esquerda para a direita (branco a 85%) |
| 1,05–1,45 s | Pausa com a palavra completa |
| 1,45–2,10 s | As letras deslizam para a posição do lockup e o símbolo monta-se: o telhado desce e a base sobe |
| 2,10 s → fim | Lockup parado (0,4 s na abertura, 2,5 s no fecho) |

Os tempos estão afinados para a retenção. A primeira letra já se vê no frame 0, o lockup fica completo aos 2,1 s e a abertura dura 2,5 s no total.

## Ficheiros (`saida/`)

- `Terrae_abertura_9x16_PNG/` (e `.zip`): 62 frames, 2,5 s
- `Terrae_fecho_9x16_PNG/` (e `.zip`): 115 frames, 4,6 s
- `*_preview.mp4`: pré-visualização sobre Ink, só para ver

No DaVinci: Media Pool → importar a pasta como sequência de imagens (aparece como um clip), a 25 fps.

## Gerar de novo

```bash
pip install cairosvg
python3 terrae_abertura.py                       # abertura
python3 terrae_abertura.py --nome fecho --hold 2.5
```

Opções: `--opacidade` (0,85), `--largura` do lockup em px (860), `--hold`.
Tempos no topo de `terrae_abertura.py` (`STAGGER`, `PAUSA`, …).

Lettering e símbolo vêm do SVG oficial (`assets/terrae_logo_neg_horizontal.svg`). Cada letra e cada peça é animada em separado, sem redesenho.
