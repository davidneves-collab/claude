---
name: davinci-free
description: Ajustar ficheiros do DaVinci Resolve para a versão gratuita do utilizador (DaVinci 21 free, Mac; antes 19 free) — PowerGrades .drx com ferramentas Studio (marca de água) → versão FREE; ajustar nós de PowerGrades; criar looks novos (LUT .cube para Canon 709 e Canon C-Log3 + PowerGrade) a partir de uma referência; converter bins .drb / projetos .drp de versões superiores com títulos Fusion → .drfx; legendar vídeos com estilos de títulos Fusion. Usar sempre que aparecer .drb, .drp, .drx, .drfx, .setting, .cube, LUT, look, color grading, PowerGrade, "marca de água", "versão free", "nodes/nós" do DaVinci, C-Log3, ou "precisa de versão superior".
---

# DaVinci Free — conversões e ajustes

## Contexto do utilizador
- DaVinci Resolve **21 gratuito** (instalado por volta de 23-10-2026; antes usava o 19 gratuito), **Mac**, interface em **português (BR)** (Galeria, Pool de Mídia, Aplicar Grade…).
- O que isto implica no 21 free:
  - Ficheiros feitos no 20/21 (.drb, .drp, .drx) **abrem diretamente** — já não é preciso converter bins/projetos para .drfx nem mexer no cabeçalho de versão. As conversões para .drfx só fazem falta se o ficheiro vier de uma versão **mais recente** que a instalada.
  - Ferramentas Studio (Glow, Halation, Film Grain, Film Look Creator, Color Tone Diffuser, Noise Reduction…) continuam a dar **marca de água** → continuar a usar/fazer versões FREE dos PowerGrades.
  - **Create Subtitles from Audio** (transcrição automática) é Studio → para legendar, transcrever aqui (faster-whisper + ffmpeg, ambos disponíveis na sessão cloud) e entregar um título Fusion com as legendas no estilo pedido + .srt. Primeiro um teste curto (20–30 s); se o vídeo for pesado, pedir só o áudio (Deliver → só áudio WAV/M4A).
  - **Sem MCP nem scripting**: o servidor MCP nativo (21.1) é só Studio e no 21.1 o scripting Python passou a ser só Studio. Não propor ligação direta ao DaVinci.
- Responder em **PT-PT**, curto e prático.
- Os PowerGrades ficam no álbum **"PowerGrade 1"** da Galeria (página Color) — aparecem em todos os projetos.
- Títulos .drfx: instalam-se com duplo clique / arrastar para a página Fusion; ficam em Effects > Titles.
- Esta sessão (cloud) **não** consegue ligar ao DaVinci local. MCP oficial só existe no Resolve 21.1 **Studio**; na versão free não há ligação. Não insistir nisso.

## Ferramentas (pasta `davinci/tools/`)
Todas em Python 3; precisam de `pip install zstandard` (PowerGrades e .drp) e, para validar, `pip install lupa`.

| Script | Para quê |
|---|---|
| `drb_to_drfx.py entrada.drb saida.drfx "Pasta"` | Bin com títulos Fusion (Media Pool) → .drfx |
| `drp_to_drfx.py entrada.drp saida.drfx "Pasta"` | Projeto com animações em camadas (1 timeline = 1 título) → .drfx, recria keyframes do Inspector e Drop Shadow do clip |
| `powergrade_inspect.py ficheiro.drx` | Lista nós, ResolveFX, LUTs e separadores de um PowerGrade |
| `powergrade_free.py entrada.drx saida.drx` | Retira ferramentas Studio (nós ficam vazios), etiqueta + " FREE" |
| `validate_setting.py pasta/` | Verifica sintaxe Lua dos .setting (com `lupa`) |
| `lookgen.py look.json pasta [frames.png…]` | Look → LUTs `<Nome>_Canon709.cube` (33³), `<Nome>_CLog3_CinemaGamut.cube` (65³, níveis Full) e `…_VideoLevels.cube`, + pré-visualizações antes/depois (tetraédrica) |
| `powergrade_build.py modelo.drx saida.drx --label X --lut "Pasta/F.cube" [--nodes …] [--thumb img]` | PowerGrade novo: cadeia de nós vazios + nó LOOK com a LUT; DbIds novos; miniatura própria. Modelo = um FREE já testado (ex. SRM_NODE_SETUP_1.9_FREE.drx, que tem nó vazio e nó LUT) |
| `pb.py`, `luaparse.py`, `curves.py`, `drfx_lib.py` | Bibliotecas: protobuf genérico, parser de tabelas Lua/Fusion, curvas de keyframes do Edit, montagem de macros |

Trabalhar sempre em cópias no scratchpad; nunca sobrescrever o ficheiro do utilizador. Entregar com SendUserFile; vários ficheiros → zip.

## O que se sabe dos formatos
- **.drb / .drp**: zip com XML. A composição Fusion de cada clip está em `<CompositionBA>` = 4 bytes de tamanho + zlib → blob Qt com cabeçalho `Composition { … Compressed = true }` seguido de outro zlib (`78 da`) com a tabela de tools em texto Lua.
- Tags XML com `::` (ex. `ListMgt::LmVersion`) → não usar ElementTree; usar regex.
- Num .drp, timeline = `<Sm2Timeline>` com `<Sm2Sequence DbId>` que liga ao `SeqContainer/*.xml` (`<Sequence>`). Cada `<Sm2TiTrack>` é uma pista (índice baixo = camada de baixo).
- Propriedades do clip na página Edit: `<EffectFiltersBA>` = cabeçalho + `0x81` + **zstd** → protobuf. Grupo 4 = Transform (p40 Pos X normalizada pela largura, p41 Pos Y pela altura, p42/p43 Zoom X/Y, p47 Rotação), grupo 2 p1 = Opacidade (0–100), grupo 6 = Crop, grupo 50 = OFX (ex. dropshadow). Curvas: cabeçalho 4 bytes + por keyframe int32 frame, 2 bytes, uint16 flags (bit0 = tem tangentes), double valor, [+6 doubles de tangentes]. Frames ≥ 86400 são tempo absoluto → subtrair o Start do clip. p48 (par de doubles) ignorado de propósito.
- **.drx (PowerGrade)**: XML; o grade está em `<pClipFullVer>…<Body>` = `0x81` + zstd → protobuf. Nós = campo 1 → campo 7 (id em 1, nome em 6). Nós compostos têm o grafo interno no campo 11 (recursivo). Campo 10 do nó = bloco OFX (entradas tipo 3221225545/566/571/607/682; manter só 3221225473). Campo 9 = separadores; id **15 = Noise Reduction** (Studio).
- Grafo do PowerGrade: campo 1 do grafo = nó selecionado; ligações = campo 8 `{1: origem, 3: destino, 4: porta de entrada (omitida se 0), 5: 64, 6: 64, 7: id da ligação}`; campo 9 = entrada do grafo (3.4 = primeiro nó), campo 10 = saída (3.4 = último nó). Nó: `[1 id, 2 número no ecrã, 4 x, 5 y, 6 nome, 7, 8 (44 normal / 126 composto), 9 separadores, 10 base OFX, 12]`.
- Nó de LUT: separador 1 com parâmetro 2248147104 = 6 e **2248147105 = caminho relativo à pasta de LUTs** (ex. `Film Looks/Rec709 Kodak 2383 D60.cube`). Os packs F-01/02/03 vinham com `\` (Windows); `powergrade_free.py` agora converte para `/`.
- `<ClipThumbnails>` = protobuf com uma entrada por nó `{1: 2*id, 2: {1: 184, 2: 92, 3: 1, 4: JPEG}}` (sem imagem: `{1: 0xffffffff, 2: 0xffffffff}`). `<BtThumnail DbId=…>` tem atributos (atenção nas regex).
- Ficheiros vindos do DaVinci 21 (DbPrjVer 17) só precisavam de cabeçalho alterado para o DaVinci 19: `<!--DbAppVer="20.1.0.0020" DbPrjVer="15"-->` (feito no itsjohan). Com o 21 instalado já não é necessário.

## Ferramentas Studio (causam marca de água) — removidas
ResolveFX `glow`, `filmlook` (Film Look Creator), `colortonediffuser`, `halationplugin`, `filmgrain`; Noise Reduction (separador 15).
**Mantidas (gratuitas):** `colorspacetransformv2` (CST), `gaussianblur`, `dropshadow`, LUTs (`Film Looks/*.cube`), Color Warper, curvas, janelas, qualificadores.
Se aparecer uma ResolveFX desconhecida: perguntar ao utilizador antes de a retirar (ou entregar versão sem ela e oferecer uma com ela para testar).

## Looks próprios (lookgen)
- O look aplica-se em espaço Rec.709 gama 2.4; a versão C-Log3 faz antes C-Log3 → linear → Cinema Gamut → Rec.709 → curva de tons (DRT), por isso as duas versões têm o mesmo look.
- **Níveis do C-Log3:** as Canon gravam Canon Log em **Full range** no cartão e o DaVinci (Data Levels Auto) lê como Full → o nó recebe código/1023 (cinzento 18% = 0.343, preto = 0.125). Por isso a LUT principal é Full e há uma `_VideoLevels` alternativa. Teste: preto com tampa ≈ 128 (Full) ou ≈ 75 (Video) no waveform de 10 bits.
- C-Log3 assume **Cinema Gamut** (definição da câmara; BT.709/BT.2020 precisam de outra matriz).
- Convenção de matiz das bandas: atan2(Cr, Cb) em graus — magenta ~50, vermelho ~103, pele ~120-140, amarelo ~175, verde ~230, ciano ~283, azul ~355. As bandas só atuam com croma > ~0.02 (cinzentos protegidos).
- Pasta das LUTs no Mac: Definições do Projeto > Gestão de Cor > Tabelas de Consulta > Abrir Pasta de LUTs → copiar a subpasta (ex. `Dourado`) → Atualizar Listas. Interpolação 3D: Tetraédrica. Projeto em DaVinci YRGB, timeline Rec.709 Gamma 2.4.
- Instagram não é acessível desta sessão: pedir o vídeo/capturas da referência. Análise da referência: `refstats` (percentis de luma, tom dos neutros por zona, ocupação de matizes) e calibração dos desvios por zona num degradê cinzento.
- Afinação feita com 3 especialistas (tons, tom de cor, saturação/matiz) + juiz, a partir de frames neutralizados (balanço de brancos global). Pedir frames sem correção da câmara para afinar melhor.

## Substitutos gratuitos (sugestões dadas ao utilizador)
- Glow/Bloom → nó com Blur + modo de composição **Soft Light**, opacidade ~10% (o utilizador faz à mão).
- Grão → página Edit: Effects > Fusion Effects > **Film Grain**.
- Denoise → sem alternativa gratuita.
- Para eu **criar** nós novos dentro de um PowerGrade preciso de um .drx de exemplo exportado do DaVinci free do utilizador com essa ferramenta configurada (ainda não recebido).

## Histórico (13-10-2026)
- ClashiVFX_Titles.drb (DaVinci 20.2) → 28 títulos .drfx — **funcionou**.
- 20_Text_Animations.drp (DaVinci 21) → 20 títulos .drfx (camadas juntas; falta PlayHead.png no nº 16; easing aproximado).
- PowerGrades FREE: 2383 CB 1.192 (Glow, Film Look, NR), F-01 CineWarm, F-02 CineTone, F-03 CineCool (Bloom, Halation), itsjohan 1.53 (Halation, Glow, Film Grain; cabeçalho 21→20.1), SRM Node Setup 1.9 (Glow, NR).
- 23-10-2026: o utilizador passou para o **DaVinci 21 free**. Originais .drb/.drp passam a abrir diretamente (preferir os originais aos .drfx convertidos, sobretudo as Text Animations, cujo easing era aproximado). PowerGrades: continuar com as versões FREE.
- 29-10-2026: look **Dourado** (e **Dourado Forte**) criado a partir de um reel de cozinha/comida (quente, brancos creme ~Cb -0.03/Cr +0.013, pretos limpos, brilho alto, teto de brancos ~0.93). Parâmetros em `davinci/looks/dourado.json` e `dourado_forte.json`; LUTs na subpasta `Dourado`; PowerGrades DOURADO 709 / CLOG3 e DOURADO FORTE 709 / CLOG3 (nós EXPOSURE, BALANCE, CONTRAST, SKIN, LOOK, SAT). Ainda por confirmar pelo utilizador: import no DaVinci, níveis do C-Log3, Cinema Gamut, modelo da câmara.
- Os ficheiros originais e convertidos são packs comprados pelo utilizador: **não** os guardar no repositório.
