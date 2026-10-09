# Terrae · Norma de legendas para vídeo vertical

Base definida a partir de `TESTE_TERRAE2_marca_v02.mp4` (1080×1920, 25 fps, 15,85 s).
Medidas em px sobre o quadro 1080×1920. Aplica-se a todos os vídeos Terrae.

## 1. Estrutura do vídeo

| Bloco | Tempo (ref.) | Descrição |
|---|---|---|
| Abertura | 0,0–1,8 s | Fundo Sand `#E4DDD3`. Símbolo centrado (≈290 px de largura, y 731–1001) desenhado a traço fino Ink, depois preenchido a Ink. |
| Transição | 1,6–2,0 s | Dissolve do Sand para a imagem. |
| Corpo | 2,0 s em diante | Imagem com legendas (secções 2 a 5). |
| Transição | ≈12,0–12,8 s | Dissolve da imagem para Ink, com o lockup a surgir. |
| Fecho | até ao fim | Fundo Ink `#1D1D1B`. Elementos centrados (secção 6). |

## 2. Bloco de legenda (estrutura)

Cada frase falada é um bloco empilhado, alinhado à esquerda, com a base fixa:

1. **Filete**: Sienna `#976E53`, 84 × 4 px, x 72. Fica 20 px acima da primeira caixa.
2. **Linha de contexto** (Manrope): o texto corrido da fala.
3. **Linhas de destaque** (Arya): uma ou duas linhas com a palavra-chave da frase (local, tipologia, ideia central).

- Margem esquerda: **x = 72**.
- Base do bloco: **y = 1480** (440 px acima do fundo). O bloco cresce para cima.
- Intervalo entre caixas: **10 px**.

## 3. Linha de contexto

| Propriedade | Valor |
|---|---|
| Fonte | Manrope 500, ≈46 px |
| Texto | Sand `#E4DDD3`, minúsculas e maiúsculas normais |
| Caixa | Ink `#1D1D1B` a ≈85% de opacidade, altura 83 px |
| Padding | 28 px à esquerda e à direita |

## 4. Linhas de destaque

| Propriedade | Valor |
|---|---|
| Fonte | Arya 400, ≈96 px (sem bold) |
| Caixa | 100% opaca, altura 134 px, padding 30 px à esquerda e à direita |

Três combinações de cor, alternadas ao longo do vídeo:

| Caixa | Texto | Exemplo |
|---|---|---|
| Sand Light `#ECE5DA` | Ink `#1D1D1B` | "Alto de / Santa Catarina" |
| Sienna `#976E53` | Sand `#E4DDD3` | "bela moradia T5" |
| Ink `#1D1D1B` | Sand `#E4DDD3` | "no mercado" |

Quando há duas linhas de destaque, podem ter cores diferentes (ex.: Ink + Sand Light).

## 5. Animação

- **Palavra a palavra**: cada palavra aparece em fade (≈200 ms) sincronizada com a fala.
- **Caixas**: a caixa abre em wipe da esquerda para a direita, um pouco antes do texto. A caixa de destaque aparece vazia e o texto entra a seguir.
- **Saída**: o bloco inteiro sai num corte seco ou num fade de ≤200 ms quando a frase acaba. Fica tudo limpo antes do bloco seguinte.
- **Frase de fecho** (ex.: "Até breve!"): bloco centrado, com o filete também centrado. Caixa Sienna de 713 × 196 px (y 1284–1480), Arya ≈146 px em Sand. Entra a deslizar de cima para baixo.

## 6. Fecho (end card)

Fundo Ink `#1D1D1B`, tudo centrado em x = 540:

| Elemento | Posição (y) | Especificação |
|---|---|---|
| Lockup vertical negativo (`terrae_logo_neg.svg`) | 480–869 | ≈485 px de largura |
| Filete | 1000 | Sienna, 162 × 2 px |
| Assinatura | 1067 | "Avaliação institucional. Mediação rigorosa.", Manrope ≈40 px, Sand |
| Site | 1188 | "terrae.pt", Manrope ≈34 px |
| Telefone | 1254 | "+351 925 348 020", Manrope ≈34 px |
| Licença | 1349 | "AMI 27242", Manrope em maiúsculas, tracking 0,18 em+, ≈20 px, Sand a ≈70% de opacidade |

Os elementos entram em fade escalonado: lockup, depois assinatura, depois site, depois telefone e AMI.

## 7. Regras de texto

- Português europeu e sem travessões. As palavras transcrevem o que é dito.
- Só a frase de fecho leva pontuação final ("muito tempo.", "Até breve!"). No resto, a pontuação é mínima.
- O destaque é a palavra-chave da frase. No máximo uma ideia por bloco.
