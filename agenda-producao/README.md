# Agenda de Produção: scripts, filmagens e fotografia

Folha Google partilhada com a equipa, ligada ao Gmail e ao Google Calendar.

**Folha:** https://docs.google.com/spreadsheets/d/1WaY7ebq02xcUqtcI0Vv3LE4Ct5MSVn8bx4q-TKzktaI/edit

## Fluxo

1. O script ou roteiro é escrito e aprovado no Drive.
2. Acrescentas uma linha em **Agendamentos** com: consultor, tipo de serviço, local, data, hora, link do script e link da pasta do produto final.
3. Selecionas a linha e escolhes **Produção > Enviar agendamento ao consultor**.
   - O evento é criado na tua agenda com o consultor como convidado, por isso fica nas duas agendas.
   - O consultor recebe um email com o link do script, a data, o local e a pasta.
   - A coluna "Enviado ao consultor" fica com a data e hora do envio. O estado passa a **Iniciado**.
4. Vais atualizando o **Estado**: Iniciado, Em tratamento, Concluído.
5. Se mudares a data, a hora ou o local, escolhes **Produção > Atualizar evento** e o consultor é avisado.

## Instalação (uma vez, cerca de 3 minutos)

1. Abre a folha e vai a **Extensões > Apps Script**.
2. Apaga o conteúdo e cola o ficheiro [`Code.gs`](Code.gs). Guarda.
3. Em **Definições do projeto** (ícone da roda dentada), põe o fuso horário em `Europe/Lisbon`.
4. Volta à folha e recarrega a página. Aparece o menu **Produção**.
5. Escolhe **Produção > Configurar folha (1.ª vez)** e autoriza o acesso ao Gmail e ao Calendar.
6. Preenche o separador **Consultores** com o nome e o email de cada consultor.

## Separadores

| Separador | Para que serve |
|---|---|
| Agendamentos | Um serviço por linha. O email do consultor é preenchido automaticamente. |
| Consultores | Nome e email de cada consultor. Alimenta a lista da coluna Consultor. |
| Servicos | Tipos de serviço. Alimenta a lista da coluna Tipo de serviço e pode ser editado. |

## Notas

- Se a hora ficar vazia, o evento é criado como evento de dia inteiro. Se a duração ficar vazia, assume 2 horas.
- O email é enviado a partir da conta de quem carrega no menu. A quota do Gmail é de cerca de 100 emails por dia em contas gratuitas e 1500 em Google Workspace.
- Para exportar para Excel: **Ficheiro > Transferir > Microsoft Excel (.xlsx)**.
