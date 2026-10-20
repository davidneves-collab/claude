---
name: davinci-19-free
description: Converter e ajustar ficheiros do DaVinci Resolve para o DaVinci 19 gratuito (Mac) do utilizador — bins .drb e projetos .drp de versões superiores com títulos/animações Fusion → pacote .drfx; PowerGrades .drx com ferramentas Studio (marca de água) → versão FREE; ajustar nós de PowerGrades. Usar sempre que aparecer .drb, .drp, .drx, .drfx, .setting, PowerGrade, "marca de água", "versão free", "nodes/nós" do DaVinci, ou "precisa de versão superior".
---

# DaVinci 19 Free — conversões e ajustes

## Contexto do utilizador
- DaVinci Resolve **19 gratuito**, **Mac**, interface em **português (BR)** (Galeria, Pool de Mídia, Aplicar Grade…).
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
| `powergrade_cst.py entrada.drx saida.drx "CST IN" inputColorSpace=X … [--node "" …] [--replace "a=>b"] [--label …]` | Muda os valores de nós CST (também dentro de compostos) e troca textos exatos (caminho de LUT, nome de nó) |
| `validate_setting.py pasta/` | Verifica sintaxe Lua dos .setting (com `lupa`) |
| `pb.py`, `luaparse.py`, `curves.py`, `drfx_lib.py` | Bibliotecas: protobuf genérico, parser de tabelas Lua/Fusion, curvas de keyframes do Edit, montagem de macros |

Trabalhar sempre em cópias no scratchpad; nunca sobrescrever o ficheiro do utilizador. Entregar com SendUserFile; vários ficheiros → zip.

## O que se sabe dos formatos
- **.drb / .drp**: zip com XML. A composição Fusion de cada clip está em `<CompositionBA>` = 4 bytes de tamanho + zlib → blob Qt com cabeçalho `Composition { … Compressed = true }` seguido de outro zlib (`78 da`) com a tabela de tools em texto Lua.
- Tags XML com `::` (ex. `ListMgt::LmVersion`) → não usar ElementTree; usar regex.
- Num .drp, timeline = `<Sm2Timeline>` com `<Sm2Sequence DbId>` que liga ao `SeqContainer/*.xml` (`<Sequence>`). Cada `<Sm2TiTrack>` é uma pista (índice baixo = camada de baixo).
- Propriedades do clip na página Edit: `<EffectFiltersBA>` = cabeçalho + `0x81` + **zstd** → protobuf. Grupo 4 = Transform (p40 Pos X normalizada pela largura, p41 Pos Y pela altura, p42/p43 Zoom X/Y, p47 Rotação), grupo 2 p1 = Opacidade (0–100), grupo 6 = Crop, grupo 50 = OFX (ex. dropshadow). Curvas: cabeçalho 4 bytes + por keyframe int32 frame, 2 bytes, uint16 flags (bit0 = tem tangentes), double valor, [+6 doubles de tangentes]. Frames ≥ 86400 são tempo absoluto → subtrair o Start do clip. p48 (par de doubles) ignorado de propósito.
- **.drx (PowerGrade)**: XML; o grade está em `<pClipFullVer>…<Body>` = `0x81` + zstd → protobuf. Nós = campo 1 → campo 7 (id em 1, nome em 6). Nós compostos têm o grafo interno no campo 11 (recursivo). Campo 10 do nó = bloco OFX (entradas tipo 3221225545/566/571/607/682; manter só 3221225473). Campo 9 = separadores; id **15 = Noise Reduction** (Studio).
- **CST (colorspacetransformv2)**: no bloco OFX do nó (campo 10) os parâmetros vêm como texto legível: `inputColorSpace`, `inputGamma`, `outputColorSpace`, `outputGamma`, `doFwdOOTF`, `doInvOOTF`. Valores vistos: `REC709_COLORSPACE`, `DWG_COLORSPACE`, `REC709_GAMMA`, `TWOPOINTFOUR_GAMMA`, `DAV_INTER_OETF_GAMMA`, `CINEON_GAMMA`. Para Canon usei `CANON_CINEMA_GAMUT_COLORSPACE` / `CANON_LOG3_GAMMA` **por dedução, sem confirmação** (20-10-2026, "2.2 C-Log3 FREE"): confirmar com o utilizador se o CST IN abre com Canon Cinema Gamut / Canon Log 3.
- Ficheiros vindos do DaVinci 21 (DbPrjVer 17): mudar a 2.ª linha para `<!--DbAppVer="20.1.0.0020" DbPrjVer="15"-->` (feito no itsjohan; confirmar com o utilizador se importou bem).

## Ferramentas Studio (causam marca de água) — removidas
ResolveFX `glow`, `filmlook` (Film Look Creator), `colortonediffuser`, `halationplugin`, `filmgrain`; Noise Reduction (separador 15).
**Mantidas (gratuitas):** `colorspacetransformv2` (CST), `gaussianblur`, `dropshadow`, LUTs (`Film Looks/*.cube`), Color Warper, curvas, janelas, qualificadores.
Se aparecer uma ResolveFX desconhecida: perguntar ao utilizador antes de a retirar (ou entregar versão sem ela e oferecer uma com ela para testar).

## Substitutos gratuitos (sugestões dadas ao utilizador)
- Glow/Bloom → nó com Blur + modo de composição **Soft Light**, opacidade ~10% (o utilizador faz à mão).
- Grão → página Edit: Effects > Fusion Effects > **Film Grain**.
- Denoise → sem alternativa gratuita.
- Para eu **criar** nós novos dentro de um PowerGrade preciso de um .drx de exemplo exportado do DaVinci 19 free com essa ferramenta configurada (ainda não recebido).

## Histórico (13-10-2026)
- ClashiVFX_Titles.drb (DaVinci 20.2) → 28 títulos .drfx — **funcionou**.
- 20_Text_Animations.drp (DaVinci 21) → 20 títulos .drfx (camadas juntas; falta PlayHead.png no nº 16; easing aproximado).
- PowerGrades FREE: 2383 CB 1.192 (Glow, Film Look, NR), F-01 CineWarm, F-02 CineTone, F-03 CineCool (Bloom, Halation), itsjohan 1.53 (Halation, Glow, Film Grain; cabeçalho 21→20.1), SRM Node Setup 1.9 (Glow, NR).
- 20-10-2026: Rec709 2.2.1 (DbAppVer 20.0) → "2.2 FREE" (Halation, Glow, Film Grain). CST IN = Rec.709/Rec.709 → DWG/DaVinci Intermediate; CST OUT = DWG/DI → Rec.709/Gamma 2.4; composto LUTS com CST Rec.709/2.4 → Cineon antes das LUTs 2383 e 3513DI. Miniatura: .dpx com o mesmo nome do .drx.
- Câmara: **Canon EOS R50 V** (C-Log3; espaço de cor Cinema Gamut, BT.2020 ou BT.709 — confirmar qual usa).
- O utilizador passou para o **DaVinci 21 free** num MacBook Pro M1 16 GB (20-10-2026). Capta em Canon **C-Log3** e em **Rec.709** direto da câmara: quer duas versões de cada PowerGrade (CST IN diferente).
- 20-10-2026: **Look Café** a partir de um reel com log/gradeado (wipe): LUT `davinci/looks/cafe/Look_Cafe_v1.cube` (DWG/DI → DWG/DI) metida no nó 2383 do composto LUTS do 2.2 FREE (CST interno passou a identidade DWG/DI). Caminho da LUT no .drx: `Terrae/Look_Cafe_v1.cube` (relativo à pasta LUT do DaVinci) — **por confirmar** se o DaVinci a encontra. Nós desligados parecem ter a entrada 3221225473 do campo 10 com valor 0 (ligados = 2) — por confirmar.
- Os ficheiros originais e convertidos são packs comprados pelo utilizador: **não** os guardar no repositório.
