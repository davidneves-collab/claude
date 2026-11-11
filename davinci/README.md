# DaVinci Free — ferramentas

Scripts para adaptar ficheiros do DaVinci Resolve à versão gratuita (DaVinci 19/21 free):

- `tools/drb_to_drfx.py` — bin `.drb` (DaVinci 20/21) com títulos Fusion → pacote `.drfx`
- `tools/drp_to_drfx.py` — projeto `.drp` com animações de texto em camadas → pacote `.drfx`
- `tools/powergrade_inspect.py` — mostra os nós de um PowerGrade `.drx`
- `tools/powergrade_free.py` — retira de um PowerGrade as ferramentas exclusivas do Studio (marca de água)
- `tools/validate_setting.py` — valida a sintaxe dos `.setting`
- `tools/lookgen.py` — gera LUTs `.cube` de um look (Canon 709 e Canon C-Log3) e pré-visualizações
- `tools/powergrade_build.py` — cria um PowerGrade novo (cadeia de nós + nó LOOK com a LUT)
- `tools/powergrade_edit.py` — edita um PowerGrade existente: CSTs, retirar nós, acrescentar nós de LUT
- `tools/powergrade_tree.py` — constrói uma árvore de nós completa a partir de um JSON (`specs/`)
- `tools/powergrade_check.py` — verifica um .drx antes de entregar (estrutura, ligações, contextos OFX, miniatura)
- `tools/powergrade_cover.py` — capa gráfica para a miniatura (título, modo C-LOG3/REC709, look)
- `tools/pg_corrector.py`, `tools/pg_windows.py` — escrever curvas, LUT, blur, pivot, máscaras circulares, ligar/desligar nós
- `looks/` — parâmetros dos looks criados (ex.: `dourado.json`)

Dependências: `pip install zstandard lupa numpy pillow` (e `colour-science` para verificar a matemática de cor)

O guia completo (formatos, lista de ferramentas Studio, histórico) está em `.claude/skills/davinci-free/SKILL.md`.
