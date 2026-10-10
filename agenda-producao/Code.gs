/**
 * Agenda de Produção: scripts, filmagens e fotografia.
 *
 * Colar em: Google Sheet > Extensões > Apps Script, guardar e recarregar a folha.
 * Aparece o menu "Produção" com:
 *   1. Configurar folha (só na 1.ª vez): cria separadores, listas e formatação.
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
  'Filmagem — Imóvel (tour)',
  'Filmagem — Apresentação do consultor',
  'Filmagem — Reel / redes sociais',
  'Filmagem — Testemunho de cliente',
  'Filmagem — Drone',
  'Fotografia — Imóvel',
  'Fotografia — Retrato do consultor',
  'Fotografia + Filmagem — Imóvel',
];

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
    .addItem('Configurar folha (1.ª vez)', 'configurar')
    .addToUi();
}

/* ---------- Configuração inicial ---------- */

function configurar() {
  const ss = SpreadsheetApp.getActive();
  const azul = '#1F3A4D';
  ss.setSpreadsheetTimeZone('Europe/Lisbon');

  const cons = ss.getSheetByName(SHEET_CONSULTORES) || ss.insertSheet(SHEET_CONSULTORES);
  if (cons.getLastRow() === 0) {
    cons.getRange(1, 1, 2, 2).setValues([['Nome', 'Email'], ['(exemplo) Nome do consultor', 'consultor@exemplo.pt']]);
  }
  formatarCabecalho(cons.getRange(1, 1, 1, 2), azul);
  cons.setColumnWidths(1, 2, 260);
  cons.setFrozenRows(1);

  const serv = ss.getSheetByName(SHEET_SERVICOS) || ss.insertSheet(SHEET_SERVICOS);
  if (serv.getLastRow() === 0) {
    serv.getRange(1, 1, SERVICOS.length + 1, 1).setValues([['Tipo de serviço']].concat(SERVICOS.map(s => [s])));
  }
  formatarCabecalho(serv.getRange(1, 1, 1, 1), azul);
  serv.setColumnWidth(1, 300);
  serv.setFrozenRows(1);

  let sh = ss.getSheetByName(SHEET);
  if (!sh) {
    sh = ss.getSheets()[0];
    sh.setName(SHEET);
  }
  sh.getRange(1, 1, 1, CABECALHO.length).setValues([CABECALHO]);
  formatarCabecalho(sh.getRange(1, 1, 1, CABECALHO.length), azul);
  sh.setFrozenRows(1);
  sh.setFrozenColumns(2);
  if (sh.getMaxRows() < LINHAS + 1) sh.insertRowsAfter(sh.getMaxRows(), LINHAS + 1 - sh.getMaxRows());

  const n = LINHAS;
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
  const regra = (txt, cor) => SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo(txt).setBackground(cor).setRanges([est]).build();
  sh.setConditionalFormatRules([
    regra('Iniciado', '#FFF2CC'),
    regra('Em tratamento', '#DDEBF7'),
    regra('Concluído', '#D9EAD3'),
  ]);

  [70, 180, 220, 230, 220, 95, 60, 90, 280, 280, 120, 240, 140, 160]
    .forEach((w, i) => sh.setColumnWidth(i + 1, w));
  sh.getRange(1, COL.email).setNote('Preenchido automaticamente ao escolher o consultor. Para mudar, edita o separador Consultores.');
  sh.getRange(1, COL.evento).setNote('Preenchido pelo script. Não editar.');
  sh.getRange(2, COL.evento, n).setFontColor('#999999');
  sh.getRange(2, COL.email, n).setFontColor('#555555');

  SpreadsheetApp.getUi().alert(
    'Folha configurada.\n\n1) Preenche o separador "Consultores" (nome + email).\n' +
    '2) Ajusta os tipos de serviço no separador "Servicos" se quiseres.\n' +
    '3) Para enviar: seleciona a linha e usa Produção > Enviar agendamento ao consultor.');
}

function formatarCabecalho(range, cor) {
  range.setFontWeight('bold').setFontColor('#FFFFFF').setBackground(cor).setVerticalAlignment('middle').setWrap(true);
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

  MailApp.sendEmail({
    to: email,
    subject: `Agendamento: ${servico}, ${formatarData(h.inicio, !h.diaInteiro)}`,
    htmlBody: emailHtml(v, h),
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

function emailHtml(v, h) {
  const esc = s => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const link = (url, txt) => `<a href="${esc(url)}">${esc(txt)}</a>`;
  const linha = (k, val) => `<tr><td style="padding:4px 12px 4px 0;color:#666">${k}</td><td style="padding:4px 0"><b>${val}</b></td></tr>`;
  return `
  <div style="font-family:Arial,sans-serif;font-size:14px;color:#222">
    <p>Olá ${esc(v[COL.consultor - 1])},</p>
    <p>O script foi aprovado e o serviço ficou agendado. Os detalhes estão abaixo.
       O evento já está na tua agenda Google.</p>
    <table style="border-collapse:collapse">
      ${linha('Serviço', esc(v[COL.servico - 1]))}
      ${linha('Data', esc(formatarData(h.inicio, !h.diaInteiro)))}
      ${linha('Local', esc(v[COL.local - 1] || 'a definir'))}
      ${linha('Script', link(v[COL.script - 1], 'Abrir script / roteiro'))}
      ${v[COL.pasta - 1] ? linha('Produto final', link(v[COL.pasta - 1], 'Pasta do produto final')) : ''}
      ${v[COL.notas - 1] ? linha('Notas', esc(v[COL.notas - 1])) : ''}
      ${linha('Ref.', esc(v[COL.id - 1]))}
    </table>
    <p>Lê o script antes do dia. Qualquer dúvida, responde a este email.</p>
  </div>`;
}

function formatarData(d, comHora) {
  const tz = Session.getScriptTimeZone() || 'Europe/Lisbon';
  return Utilities.formatDate(new Date(d), tz, comHora ? "dd/MM/yyyy 'às' HH:mm" : 'dd/MM/yyyy');
}
