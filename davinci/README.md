# DaVinci 19 Free — ferramentas

Scripts para adaptar ficheiros do DaVinci Resolve à versão 19 gratuita:

- `tools/drb_to_drfx.py` — bin `.drb` (DaVinci 20/21) com títulos Fusion → pacote `.drfx`
- `tools/drp_to_drfx.py` — projeto `.drp` com animações de texto em camadas → pacote `.drfx`
- `tools/powergrade_inspect.py` — mostra os nós de um PowerGrade `.drx`
- `tools/powergrade_free.py` — retira de um PowerGrade as ferramentas exclusivas do Studio (marca de água)
- `tools/validate_setting.py` — valida a sintaxe dos `.setting`

Dependências: `pip install zstandard lupa`

O guia completo (formatos, lista de ferramentas Studio, histórico) está em `.claude/skills/davinci-19-free/SKILL.md`.
