/**
 * Agenda de Produção: scripts, filmagens e fotografia.
 *
 * Colar em: Google Sheet > Extensões > Apps Script, guardar e recarregar a folha.
 * Aparece o menu "Produção" com:
 *   1. Configurar folha / aplicar tema: cria separadores, listas e o tema Terrae.
 *   2. Enviar agendamento ao consultor: para a(s) linha(s) selecionada(s), cria o
 *      evento na tua agenda com o consultor como convidado (fica nas duas agendas)
 *      e envia-lhe um email com o link do script, o local e a data.
 *   3. Atualizar evento: se mudares data, hora ou local, atualiza o evento já criado.
 */

const SHEET = 'Agendamentos';
const SHEET_CONSULTORES = 'Consultores';
const SHEET_SERVICOS = 'Servicos';
const LINHAS = 500;
const ESTADOS = ['Iniciado', 'Em tratamento', 'Concluído'];
const SERVICOS = [
  'Total (posicionamento de marca + consultor)',
  'Marca Pessoal',
  'Marca Terrae',
  'Campanhas',
  'Imóvel (tour)',
  'Apenas Drone',
];

// Paleta Terrae (cores oficiais e variações claras)
const COR = {
  ink: '#1D1D1B',
  sand: '#E4DDD3',
  sandLight: '#ECE5DA',
  sandSoft: '#F2EDE5',
  sage: '#8A8E75',
  sageClaro: '#DCDDD5',
  sienna: '#976E53',
  siennaClaro: '#E5DBD4',
};
const FONTE = 'Manrope';

// Email: remetente, assinatura e logótipos (IDs de ficheiros PNG no Google Drive).
// O ID é a parte do link entre /d/ e /view. Sem ID, o email segue sem logótipo.
const EMAIL = {
  remetente: 'David Neves · Produção Terrae',
  assinaturaNome: 'David Neves',
  assinaturaCargo: 'Produção Terrae',
  logoCabecalho: '', // versão clara do logótipo, para o fundo escuro do cabeçalho
  logoAssinatura: '', // versão escura do logótipo, para a assinatura em fundo claro
};

// Colunas da folha Agendamentos (1 = A)
const COL = {
  id: 1, consultor: 2, email: 3, servico: 4, local: 5, data: 6, hora: 7, duracao: 8,
  script: 9, pasta: 10, estado: 11, notas: 12, enviado: 13, evento: 14,
};
const CABECALHO = [
  'ID', 'Consultor', 'Email do consultor', 'Tipo de serviço', 'Local', 'Data', 'Hora',
  'Duração (min)', 'Link do script', 'Link da pasta do produto final', 'Estado', 'Notas',
  'Enviado ao consultor', 'ID evento (não editar)',
];

function onOpen() {
  criarMenu();
}

// Gatilho instalável (configurado em "Configurar folha"): garante o menu mesmo
// quando o onOpen simples não corre (ex.: várias contas Google no browser).
function abrirMenu() {
  criarMenu();
}

function criarMenu() {
  SpreadsheetApp.getUi()
    .createMenu('Produção')
    .addItem('Enviar agendamento ao consultor', 'enviarSelecionados')
    .addItem('Atualizar evento (data/hora/local)', 'atualizarSelecionados')
    .addSeparator()
    .addItem('Configurar folha / aplicar tema', 'configurar')
    .addToUi();
}

/* ---------- Configuração inicial ---------- */

function configurar() {
  const ss = SpreadsheetApp.getActive();
  ss.setSpreadsheetTimeZone('Europe/Lisbon');

  const cons = ss.getSheetByName(SHEET_CONSULTORES) || ss.insertSheet(SHEET_CONSULTORES);
  if (cons.getLastRow() === 0) {
    cons.getRange(1, 1, 2, 2).setValues([['Nome', 'Email'], ['(exemplo) Nome do consultor', 'consultor@exemplo.pt']]);
  }
  aplicarTema(cons, 2, 200);
  cons.setColumnWidths(1, 2, 260);
  cons.setTabColor(COR.sage);

  // A lista de serviços vem do código: atualizar aqui e voltar a correr "Configurar"
  const serv = ss.getSheetByName(SHEET_SERVICOS) || ss.insertSheet(SHEET_SERVICOS);
  serv.getRange(1, 1, Math.max(serv.getMaxRows(), 1), 1).clearContent();
  serv.getRange(1, 1, SERVICOS.length + 1, 1).setValues([['Tipo de serviço']].concat(SERVICOS.map(s => [s])));
  aplicarTema(serv, 1, 50);
  serv.setColumnWidth(1, 320);
  serv.setTabColor(COR.sienna);

  let sh = ss.getSheetByName(SHEET);
  if (!sh) {
    sh = ss.getSheets()[0];
    sh.setName(SHEET);
  }
  sh.getRange(1, 1, 1, CABECALHO.length).setValues([CABECALHO]);
  if (sh.getMaxRows() < LINHAS + 1) sh.insertRowsAfter(sh.getMaxRows(), LINHAS + 1 - sh.getMaxRows());
  aplicarTema(sh, CABECALHO.length, LINHAS);
  sh.setFrozenColumns(2);
  sh.setTabColor(COR.ink);

  const n = LINHAS;
  sh.getRange(2, 1, n, CABECALHO.length).clearDataValidations(); // remove listas fora do sítio
  const lista = (range) => SpreadsheetApp.newDataValidation().requireValueInRange(range, true).setAllowInvalid(false).build();
  sh.getRange(2, COL.consultor, n).setDataValidation(lista(cons.getRange('A2:A200')));
  sh.getRange(2, COL.servico, n).setDataValidation(lista(serv.getRange('A2:A100')));
  sh.getRange(2, COL.estado, n).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(ESTADOS, true).setAllowInvalid(false).build());
  sh.getRange(2, COL.data, n).setDataValidation(
    SpreadsheetApp.newDataValidation().requireDate().setAllowInvalid(false).build()).setNumberFormat('dd/mm/yyyy');
  sh.getRange(2, COL.hora, n).setNumberFormat('hh:mm');
  sh.getRange(2, COL.enviado, n).setNumberFormat('dd/mm/yyyy hh:mm');

  // Email preenchido pelo script (sem fórmulas, para funcionar em qualquer idioma)
  sh.getRange(2, COL.email, n).clearContent();
  preencherEmails();
  instalarGatilhos();

  // Cores do estado
  const est = sh.getRange(2, COL.estado, n);
  const regra = (txt, fundo, letra) => SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo(txt).setBackground(fundo).setFontColor(letra).setRanges([est]).build();
  sh.setConditionalFormatRules([
    regra('Iniciado', COR.siennaClaro, COR.sienna),
    regra('Em tratamento', COR.sageClaro, COR.ink),
    regra('Concluído', COR.sage, COR.sandSoft),
  ]);

  [70, 180, 220, 230, 220, 95, 60, 90, 280, 280, 120, 240, 140, 160]
    .forEach((w, i) => sh.setColumnWidth(i + 1, w));
  sh.getRange(1, COL.email).setNote('Preenchido automaticamente ao escolher o consultor. Para mudar, edita o separador Consultores.');
  sh.getRange(1, COL.evento).setNote('Preenchido pelo script. Não editar.');
  sh.getRange(2, COL.evento, n).setFontColor(COR.sage);
  sh.getRange(2, COL.email, n).setFontColor(COR.sienna);

  SpreadsheetApp.getUi().alert(
    'Folha configurada.\n\n1) Preenche o separador "Consultores" (nome + email).\n' +
    '2) Ajusta os tipos de serviço no separador "Servicos" se quiseres.\n' +
    '3) Para enviar: seleciona a linha e usa Produção > Enviar agendamento ao consultor.');
}

// Tema Terrae: cabeçalho Ink, linhas alternadas em tons de areia, letra Manrope
function aplicarTema(folha, colunas, linhas) {
  const total = folha.getRange(1, 1, linhas + 1, colunas);
  folha.getBandings().forEach(b => b.remove());
  total.setBackground(null); // limpa cores antigas, que se sobrepunham às linhas alternadas
  total.applyRowBanding()
    .setHeaderRowColor(COR.ink)
    .setFirstRowColor(COR.sandSoft)
    .setSecondRowColor(COR.sandLight);
  total.setFontFamily(FONTE).setFontSize(10).setFontColor(COR.ink).setVerticalAlignment('middle');
  folha.getRange(1, 1, 1, colunas)
    .setFontColor(COR.sand).setFontWeight('normal').setFontSize(10).setWrap(true);
  folha.setRowHeight(1, 40);
  folha.setRowHeights(2, linhas, 28);
  folha.setFrozenRows(1);
}

/* ---------- Email do consultor ---------- */

function mapaConsultores() {
  const cons = SpreadsheetApp.getActive().getSheetByName(SHEET_CONSULTORES);
  const mapa = {};
  if (!cons || cons.getLastRow() < 2) return mapa;
  cons.getRange(2, 1, cons.getLastRow() - 1, 2).getValues().forEach(([nome, email]) => {
    if (nome) mapa[String(nome).trim()] = String(email || '').trim();
  });
  return mapa;
}

function emailDe(nome, mapa) {
  if (!nome) return '';
  return (mapa || mapaConsultores())[String(nome).trim()] || '⚠ consultor sem email';
}

// Atualiza a coluna "Email do consultor" de todas as linhas
function preencherEmails() {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET);
  const ultima = sh.getLastRow();
  if (ultima < 2) return;
  const mapa = mapaConsultores();
  const nomes = sh.getRange(2, COL.consultor, ultima - 1).getValues();
  sh.getRange(2, COL.email, ultima - 1).setValues(nomes.map(([nome]) => [emailDe(nome, mapa)]));
}

function onEdit(e) {
  const sh = e.range.getSheet();
  const nome = sh.getName();
  if (nome === SHEET_CONSULTORES) {
    preencherEmails();
  } else if (nome === SHEET && e.range.getLastColumn() >= COL.consultor && e.range.getColumn() <= COL.consultor) {
    const linhas = e.range.getNumRows();
    const primeira = e.range.getRow();
    const mapa = mapaConsultores();
    for (let r = Math.max(2, primeira); r < primeira + linhas; r++) {
      sh.getRange(r, COL.email).setValue(emailDe(sh.getRange(r, COL.consultor).getValue(), mapa));
    }
  }
}

function instalarGatilhos() {
  const ss = SpreadsheetApp.getActive();
  const existe = ScriptApp.getProjectTriggers().some(t => t.getHandlerFunction() === 'abrirMenu');
  if (!existe) ScriptApp.newTrigger('abrirMenu').forSpreadsheet(ss).onOpen().create();
}

/* ---------- Envio ---------- */

function enviarSelecionados() {
  processarSelecao(false);
}

function atualizarSelecionados() {
  processarSelecao(true);
}

function processarSelecao(soAtualizar) {
  const ui = SpreadsheetApp.getUi();
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET);
  const sel = sh.getActiveRange();
  if (!sel || SpreadsheetApp.getActiveSheet().getName() !== SHEET) {
    ui.alert('Seleciona uma ou mais linhas no separador "' + SHEET + '".');
    return;
  }

  const primeira = Math.max(2, sel.getRow());
  const ultima = sel.getLastRow();
  const resultados = [];

  for (let r = primeira; r <= ultima; r++) {
    const v = sh.getRange(r, 1, 1, CABECALHO.length).getValues()[0];
    if (!v[COL.consultor - 1]) continue;
    v[COL.email - 1] = emailDe(v[COL.consultor - 1]);
    v.horaTexto = sh.getRange(r, COL.hora).getDisplayValue();
    sh.getRange(r, COL.email).setValue(v[COL.email - 1]);
    try {
      if (soAtualizar) {
        resultados.push(`Linha ${r}: ${atualizarLinha(sh, r, v)}`);
      } else {
        if (v[COL.enviado - 1]) {
          const resp = ui.alert(`A linha ${r} já foi enviada em ${formatarData(v[COL.enviado - 1], true)}. Enviar novamente?`, ui.ButtonSet.YES_NO);
          if (resp !== ui.Button.YES) { resultados.push(`Linha ${r}: ignorada`); continue; }
        }
        resultados.push(`Linha ${r}: ${enviarLinha(sh, r, v)}`);
      }
    } catch (e) {
      resultados.push(`Linha ${r}: ERRO, ${e.message}`);
    }
  }
  ui.alert(resultados.length ? resultados.join('\n') : 'Nenhuma linha com consultor selecionada.');
}

function validar(v) {
  const falta = [];
  const email = String(v[COL.email - 1] || '');
  if (!email || email.indexOf('@') < 0) falta.push('email do consultor');
  if (!v[COL.servico - 1]) falta.push('tipo de serviço');
  if (!(v[COL.data - 1] instanceof Date)) falta.push('data');
  if (!v[COL.script - 1]) falta.push('link do script');
  if (falta.length) throw new Error('falta ' + falta.join(', '));
}

function horario(v) {
  const data = v[COL.data - 1];
  // A hora é lida como texto ("10:00"): ler a célula como Date dá minutos
  // errados (fuso de Lisboa de 1899).
  const m = String(v.horaTexto || '').match(/(\d{1,2})[:h](\d{2})/);
  if (!m) return { diaInteiro: true, inicio: data };
  const inicio = new Date(data);
  inicio.setHours(Number(m[1]), Number(m[2]), 0, 0);
  const dur = Number(v[COL.duracao - 1]) || 120;
  return { diaInteiro: false, inicio, fim: new Date(inicio.getTime() + dur * 60000) };
}

function enviarLinha(sh, r, v) {
  validar(v);
  garantirId(sh, r, v);

  const consultor = v[COL.consultor - 1];
  const email = v[COL.email - 1];
  const servico = v[COL.servico - 1];
  const local = v[COL.local - 1] || '';
  const h = horario(v);
  const titulo = `${servico}: ${consultor}`;
  const descricao = descricaoEvento(v);

  const cal = CalendarApp.getDefaultCalendar();
  let ev = v[COL.evento - 1] ? cal.getEventById(v[COL.evento - 1]) : null;
  if (ev) {
    aplicarHorario(ev, h);
    ev.setTitle(titulo).setLocation(local).setDescription(descricao);
    if (!ev.getGuestByEmail(email)) ev.addGuest(email);
  } else {
    const opts = { location: local, description: descricao, guests: email, sendInvites: true };
    ev = h.diaInteiro
      ? cal.createAllDayEvent(titulo, h.inicio, opts)
      : cal.createEvent(titulo, h.inicio, h.fim, opts);
    sh.getRange(r, COL.evento).setValue(ev.getId());
  }

  const imagens = logotipos();
  MailApp.sendEmail({
    to: email,
    name: EMAIL.remetente,
    subject: `Agendamento: ${servico}, ${formatarData(h.inicio, !h.diaInteiro)}`,
    body: descricaoEvento(v),
    htmlBody: emailHtml(v, h, imagens),
    inlineImages: imagens,
  });

  sh.getRange(r, COL.enviado).setValue(new Date());
  if (!v[COL.estado - 1]) sh.getRange(r, COL.estado).setValue('Iniciado');
  return `enviado a ${email}`;
}

function atualizarLinha(sh, r, v) {
  const id = v[COL.evento - 1];
  if (!id) return 'ainda não foi enviada (usa "Enviar agendamento")';
  validar(v);
  const ev = CalendarApp.getDefaultCalendar().getEventById(id);
  if (!ev) return 'evento não encontrado na agenda (foi apagado?)';
  aplicarHorario(ev, horario(v));
  ev.setLocation(v[COL.local - 1] || '').setDescription(descricaoEvento(v))
    .setTitle(`${v[COL.servico - 1]}: ${v[COL.consultor - 1]}`);
  return 'evento atualizado (o Google avisa o consultor da alteração)';
}

function aplicarHorario(ev, h) {
  if (h.diaInteiro) ev.setAllDayDate(h.inicio);
  else ev.setTime(h.inicio, h.fim);
}

function garantirId(sh, r, v) {
  if (v[COL.id - 1]) return;
  const ids = sh.getRange(2, COL.id, Math.max(1, sh.getLastRow() - 1)).getValues()
    .map(x => Number(String(x[0]).replace(/\D/g, '')) || 0);
  const novo = 'P' + String(Math.max(0, ...ids) + 1).padStart(4, '0');
  sh.getRange(r, COL.id).setValue(novo);
  v[COL.id - 1] = novo;
}

function descricaoEvento(v) {
  return [
    `Serviço: ${v[COL.servico - 1]}`,
    `Consultor: ${v[COL.consultor - 1]}`,
    `Local: ${v[COL.local - 1] || '(a definir)'}`,
    `Script: ${v[COL.script - 1]}`,
    v[COL.pasta - 1] ? `Pasta do produto final: ${v[COL.pasta - 1]}` : '',
    v[COL.notas - 1] ? `Notas: ${v[COL.notas - 1]}` : '',
    `Ref.: ${v[COL.id - 1]}`,
  ].filter(Boolean).join('\n');
}

// Lê os logótipos do Drive para irem embutidos no email (cid:logoCabecalho, cid:logoAssinatura)
function logotipos() {
  const imagens = {};
  ['logoCabecalho', 'logoAssinatura'].forEach(chave => {
    if (!EMAIL[chave]) return;
    try {
      imagens[chave] = DriveApp.getFileById(EMAIL[chave]).getBlob().setName(chave);
    } catch (e) {
      console.warn(`Logótipo ${chave} não encontrado: ${e.message}`);
    }
  });
  return imagens;
}

// Email no visual Terrae: fundo areia, cabeçalho Ink, Manrope, sem negrito
function emailHtml(v, h, imagens) {
  const esc = s => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const fonte = "'Manrope', 'Helvetica Neue', Helvetica, Arial, sans-serif";
  const titulo = "'Arya', Georgia, 'Times New Roman', serif";
  const caps = `font-family:${fonte};font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:${COR.sage};font-weight:500;`;

  const linha = (k, val) => `
    <tr>
      <td style="padding:14px 0;border-top:1px solid ${COR.sand};${caps}width:130px;vertical-align:top;">${k}</td>
      <td style="padding:14px 0;border-top:1px solid ${COR.sand};font-family:${fonte};font-size:15px;color:${COR.ink};font-weight:400;">${val}</td>
    </tr>`;

  const botao = (url, txt, principal) => `
    <td style="padding:0 12px 12px 0;">
      <a href="${esc(url)}" style="display:inline-block;padding:14px 26px;font-family:${fonte};font-size:13px;letter-spacing:0.08em;
        text-decoration:none;font-weight:500;border:1px solid ${COR.ink};
        ${principal ? `background:${COR.ink};color:${COR.sandSoft};` : `background:transparent;color:${COR.ink};`}">${esc(txt)}</a>
    </td>`;

  const cabecalho = imagens.logoCabecalho
    ? `<img src="cid:logoCabecalho" alt="Terrae" height="40" style="display:block;height:40px;border:0;">`
    : `<span style="${caps}color:${COR.sand};">Terrae</span>`;

  const logoAssinatura = imagens.logoAssinatura
    ? `<td style="padding-right:18px;vertical-align:middle;"><img src="cid:logoAssinatura" alt="Terrae" height="44" style="display:block;height:44px;border:0;"></td>`
    : '';

  return `
<!doctype html>
<html lang="pt-PT"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Arya&family=Manrope:wght@400;500&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:${COR.sand};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${COR.sand};">
  <tr><td align="center" style="padding:32px 16px;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:${COR.sandSoft};">

      <tr><td style="background:${COR.ink};padding:28px 40px;">${cabecalho}</td></tr>

      <tr><td style="padding:44px 40px 8px 40px;">
        <div style="${caps}">Agendamento de produção · ${esc(v[COL.id - 1])}</div>
        <div style="font-family:${titulo};font-size:30px;line-height:1.2;color:${COR.ink};font-weight:400;padding:14px 0 22px 0;">${esc(v[COL.servico - 1])}</div>
        <p style="font-family:${fonte};font-size:15px;line-height:1.6;color:${COR.ink};margin:0 0 12px 0;">Olá ${esc(v[COL.consultor - 1])},</p>
        <p style="font-family:${fonte};font-size:15px;line-height:1.6;color:${COR.ink};margin:0 0 28px 0;">
          O script foi aprovado e a produção ficou agendada. O evento já está na tua agenda Google.</p>
      </td></tr>

      <tr><td style="padding:0 40px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          ${linha('Data', esc(formatarData(h.inicio, !h.diaInteiro)))}
          ${linha('Local', esc(v[COL.local - 1] || 'A definir'))}
          ${v[COL.notas - 1] ? linha('Notas', esc(v[COL.notas - 1])) : ''}
          <tr><td colspan="2" style="border-top:1px solid ${COR.sand};font-size:0;line-height:0;">&nbsp;</td></tr>
        </table>
      </td></tr>

      <tr><td style="padding:24px 40px 12px 40px;">
        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
          ${botao(v[COL.script - 1], 'Abrir script', true)}
          ${v[COL.pasta - 1] ? botao(v[COL.pasta - 1], 'Pasta do produto final', false) : ''}
        </tr></table>
      </td></tr>

      <tr><td style="padding:12px 40px 36px 40px;">
        <p style="font-family:${fonte};font-size:15px;line-height:1.6;color:${COR.ink};margin:0;">
          Lê o script antes do dia. Qualquer dúvida, responde a este email.</p>
      </td></tr>

      <tr><td style="padding:28px 40px 40px 40px;border-top:1px solid ${COR.sand};">
        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
          ${logoAssinatura}
          <td style="vertical-align:middle;">
            <div style="font-family:${fonte};font-size:15px;color:${COR.ink};font-weight:500;">${esc(EMAIL.assinaturaNome)}</div>
            <div style="${caps}padding-top:4px;">${esc(EMAIL.assinaturaCargo)}</div>
          </td>
        </tr></table>
      </td></tr>

    </table>
  </td></tr>
</table>
</body></html>`;
}

function formatarData(d, comHora) {
  const tz = Session.getScriptTimeZone() || 'Europe/Lisbon';
  return Utilities.formatDate(new Date(d), tz, comHora ? "dd/MM/yyyy 'às' HH:mm" : 'dd/MM/yyyy');
}
