/**
 * Aprovação de vídeos.
 *
 * Os vídeos postos na pasta APROVAÇÃO aparecem no separador "Aprovação" da folha.
 * Quando o Sandro ou o Nuno escolhem "Aprovado", o vídeo passa para a pasta PUBLICAR,
 * o consultor ganha acesso e recebe um email, e o David recebe aviso.
 * "A corrigir" envia ao David o comentário escrito na linha.
 *
 * O trabalho com o Drive corre num gatilho de tempo (a cada 5 minutos): os gatilhos
 * de edição não têm acesso ao Drive. "Produção > Processar aprovações agora" faz o mesmo na hora.
 */

const SHEET_APROVACAO = 'Aprovação';
const PASTA_APROVACAO = '18RthU54nwZitm8OuSOPh3yMqcsmrXEVB';
const PASTA_PUBLICAR = '1wSkFpBjSTVFCBGDLKrvVvHncjXrvB1F9';
const DECISOES = ['Pendente', 'Aprovado', 'A corrigir'];
const AP = { video: 1, projeto: 2, consultor: 3, decisao: 4, comentario: 5, por: 6, data: 7, estado: 8, ficheiro: 9 };
const AP_CABECALHO = ['Vídeo', 'Projeto (ID)', 'Consultor', 'Decisão', 'Comentário', 'Decidido por',
  'Data da decisão', 'Estado', 'ID ficheiro (não editar)'];

// Projeto de origem dos vídeos que já estavam nas pastas dos projetos antes da pasta APROVAÇÃO existir
const ORIGEM_INICIAL = {
  '18xPER87y8kaeW0iJ0TWtCa9CqgX2ZuQR': 'P0001', '1dgkeMtZi69gYvlkKqdTe_7DMPl7Dlyln': 'P0001',
  '1RO08SV11egK9ENhBtnZdTWrW_tFuQcCq': 'P0002', '18tDGQFddCv4uif_KSPiX5ar9wufISK6m': 'P0002',
  '1VQa9kTm_p05lKPMbnNp-1GIxEduq3NAh': 'P0003', '116uNluuiROKg8M_BDarmEs3WcMFjYLDW': 'P0004',
  '1dOJlVUqX4FxVEnNjY3dHaydM04oTRtn-': 'P0006', '1Pp8TDmUWeKCuXzUitvl_FtlBF0yO7CFf': 'P0006',
  '1ldgHQB3SE1uC7AHOY574C8QIH_pqe1FF': 'P0007', '1j1rhHp5BH0OP_7iozFKYkcGHPAAt3Dga': 'P0007',
  '1JOSgdtVDp5a51OHy7QIdkmpHR4DGLYjb': 'P0009', '1QxF1BliUGbVAxVoFTkiTLwudUvrPANBs': 'P0009',
  '1sTOlY2GCjiurVVRQUR2yPL8Ed4xKyn1Z': 'P0011',
};

/* ---------- Configuração ---------- */

function configurarAprovacao() {
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName(SHEET_APROVACAO) || ss.insertSheet(SHEET_APROVACAO);
  const n = 300;
  if (sh.getMaxRows() < n + 1) sh.insertRowsAfter(sh.getMaxRows(), n + 1 - sh.getMaxRows());
  if (sh.getMaxColumns() < AP_CABECALHO.length) sh.insertColumnsAfter(sh.getMaxColumns(), AP_CABECALHO.length - sh.getMaxColumns());
  sh.getRange(1, 1, 1, AP_CABECALHO.length).setValues([AP_CABECALHO]);
  aplicarTema(sh, AP_CABECALHO.length, n);
  sh.setTabColor(COR.sienna);
  sh.setFrozenColumns(1);

  const ids = ss.getSheetByName(SHEET).getRange('A2:A501');
  sh.getRange(2, AP.projeto, n).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInRange(ids, true).setAllowInvalid(false).build());
  sh.getRange(2, AP.decisao, n).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(DECISOES, true).setAllowInvalid(false).build());
  sh.getRange(2, AP.data, n).setNumberFormat('dd/mm/yyyy hh:mm');

  const dec = sh.getRange(2, AP.decisao, n);
  const regra = (txt, fundo, letra) => SpreadsheetApp.newConditionalFormatRule()
    .whenTextEqualTo(txt).setBackground(fundo).setFontColor(letra).setRanges([dec]).build();
  sh.setConditionalFormatRules([
    regra('Aprovado', COR.sage, COR.sandSoft),
    regra('A corrigir', COR.siennaClaro, COR.sienna),
  ]);
  [320, 110, 180, 120, 300, 200, 140, 260, 160].forEach((w, i) => sh.setColumnWidth(i + 1, w));
  sh.getRange(2, AP.ficheiro, n).setFontColor(COR.sage);
  sh.getRange(1, AP.decisao).setNote('Sandro ou Nuno: escolher "Aprovado" ou "A corrigir". Em "A corrigir", escrever o comentário ao lado.');

  // Os revisores só devem mexer neste separador: os outros pedem confirmação antes de editar
  [SHEET, SHEET_CONSULTORES, SHEET_SERVICOS].forEach(nome => {
    const folha = ss.getSheetByName(nome);
    if (folha && !folha.getProtections(SpreadsheetApp.ProtectionType.SHEET).length) {
      folha.protect().setDescription('Editado pela Produção').setWarningOnly(true);
    }
  });

  const existentes = ScriptApp.getProjectTriggers().map(t => t.getHandlerFunction());
  if (existentes.indexOf('aprovacoesAutomaticas') < 0) {
    ScriptApp.newTrigger('aprovacoesAutomaticas').timeBased().everyMinutes(5).create();
  }
  aprovacoesAutomaticas();
  avisar('Separador "Aprovação" configurado. Os vídeos da pasta APROVAÇÃO são lidos a cada 5 minutos.');
}

/* ---------- Gatilhos ---------- */

// Gatilho de tempo (5 min): junta vídeos novos e trata as decisões
function aprovacoesAutomaticas() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return;
  try {
    sincronizarAprovacao();
    processarDecisoes();
  } finally {
    lock.releaseLock();
  }
}

function processarAprovacoesAgora() {
  aprovacoesAutomaticas();
  avisar('Aprovações processadas.');
}

// Chamado pelo onEdit: regista quem decidiu e quando, e preenche o consultor do projeto
function aprovacaoEditada(e) {
  const sh = e.range.getSheet();
  if (sh.getName() !== SHEET_APROVACAO || e.range.getRow() < 2) return;
  for (let r = e.range.getRow(); r <= e.range.getLastRow(); r++) {
    if (e.range.getColumn() <= AP.decisao && e.range.getLastColumn() >= AP.decisao) {
      const quem = (e.user && e.user.getEmail && e.user.getEmail()) || Session.getActiveUser().getEmail();
      sh.getRange(r, AP.por).setValue(quem || '');
      sh.getRange(r, AP.data).setValue(new Date());
    }
    if (e.range.getColumn() <= AP.projeto && e.range.getLastColumn() >= AP.projeto) {
      sh.getRange(r, AP.consultor).setValue(dadosProjeto(sh.getRange(r, AP.projeto).getValue()).consultor || '');
    }
  }
}

/* ---------- Pasta APROVAÇÃO -> folha ---------- */

function sincronizarAprovacao() {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_APROVACAO);
  if (!sh) return;
  const ultima = Math.max(sh.getLastRow(), 1);
  const conhecidos = ultima > 1
    ? sh.getRange(2, AP.ficheiro, ultima - 1).getValues().map(([id]) => String(id))
    : [];
  const ficheiros = DriveApp.getFolderById(PASTA_APROVACAO).getFiles();
  const novos = [];
  while (ficheiros.hasNext()) {
    const f = ficheiros.next();
    if (conhecidos.indexOf(f.getId()) >= 0) continue;
    const projeto = ORIGEM_INICIAL[f.getId()] || (f.getName().match(/P\d{4}/) || [''])[0];
    novos.push([f.getName(), f.getUrl(), f.getId(), projeto]);
  }
  novos.forEach(([nome, url, id, projeto]) => {
    const r = sh.getLastRow() + 1;
    sh.getRange(r, AP.video).setRichTextValue(
      SpreadsheetApp.newRichTextValue().setText(nome).setLinkUrl(url).build());
    sh.getRange(r, AP.projeto).setValue(projeto);
    sh.getRange(r, AP.consultor).setValue(projeto ? dadosProjeto(projeto).consultor || '' : '');
    sh.getRange(r, AP.decisao).setValue('Pendente');
    sh.getRange(r, AP.ficheiro).setValue(id);
  });
}

/* ---------- Decisões ---------- */

function processarDecisoes() {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_APROVACAO);
  if (!sh || sh.getLastRow() < 2) return;
  const linhas = sh.getRange(2, 1, sh.getLastRow() - 1, AP_CABECALHO.length).getValues();
  linhas.forEach((v, i) => {
    const r = i + 2;
    const decisao = v[AP.decisao - 1];
    const estado = String(v[AP.estado - 1] || '');
    if (decisao !== 'Aprovado' && decisao !== 'A corrigir') return;
    if (estado.indexOf(decisao) === 0) return; // esta decisão já foi tratada
    try {
      const texto = decisao === 'Aprovado' ? aprovar(v) : pedirCorrecao(v);
      sh.getRange(r, AP.estado).setValue(`${decisao} · ${texto} · ${formatarData(new Date(), true)}`);
    } catch (err) {
      sh.getRange(r, AP.estado).setValue('ERRO: ' + err.message);
    }
  });
}

function aprovar(v) {
  const id = v[AP.ficheiro - 1];
  const ficheiro = DriveApp.getFileById(id);
  ficheiro.moveTo(DriveApp.getFolderById(PASTA_PUBLICAR));
  const p = dadosProjeto(v[AP.projeto - 1]);
  const partes = ['movido para PUBLICAR'];
  const imagens = logotipos();
  const linhas = [['Vídeo', ficheiro.getName()]]
    .concat(p.id ? [['Projeto', `${p.id} · ${p.servico}`]] : [])
    .concat(v[AP.por - 1] ? [['Aprovado por', v[AP.por - 1]]] : []);

  if (p.email && p.email.indexOf('@') > 0) {
    partilhar(id, p.email);
    MailApp.sendEmail({
      to: p.email,
      name: EMAIL.remetente,
      subject: `Vídeo aprovado: ${ficheiro.getName()}`,
      body: `O vídeo ${ficheiro.getName()} foi aprovado e está pronto a publicar.\n${ficheiro.getUrl()}`,
      htmlBody: modeloEmail({
        eyebrow: `Vídeo aprovado${p.id ? ' · ' + p.id : ''}`,
        titulo: 'Pronto a publicar',
        consultor: p.consultor,
        texto: 'O teu vídeo foi aprovado e está pronto a publicar.',
        linhas: linhas,
        botoes: [[ficheiro.getUrl(), 'Ver vídeo', true]],
        fecho: 'Qualquer dúvida, responde a este email.',
      }, imagens),
      inlineImages: imagens,
    });
    partes.push(`consultor avisado (${p.email})`);
  } else {
    partes.push('sem consultor associado');
  }

  avisarDavid(`Vídeo aprovado: ${ficheiro.getName()}`, 'Vídeo aprovado',
    'O vídeo foi aprovado e já está na pasta PUBLICAR.', linhas,
    [[ficheiro.getUrl(), 'Ver vídeo', true], [DriveApp.getFolderById(PASTA_PUBLICAR).getUrl(), 'Pasta PUBLICAR', false]]);
  return partes.join(', ');
}

function pedirCorrecao(v) {
  const ficheiro = DriveApp.getFileById(v[AP.ficheiro - 1]);
  const p = dadosProjeto(v[AP.projeto - 1]);
  const linhas = [['Vídeo', ficheiro.getName()]]
    .concat(p.id ? [['Projeto', `${p.id} · ${p.consultor} · ${p.servico}`]] : [])
    .concat([['Comentário', v[AP.comentario - 1] || '(sem comentário)']])
    .concat(v[AP.por - 1] ? [['Pedido por', v[AP.por - 1]]] : []);
  avisarDavid(`Correção pedida: ${ficheiro.getName()}`, 'Correção pedida',
    'Este vídeo precisa de correções antes de ser publicado.', linhas, [[ficheiro.getUrl(), 'Ver vídeo', true]]);
  return 'David avisado';
}

function avisarDavid(assunto, titulo, texto, linhas, botoes) {
  const imagens = logotipos();
  MailApp.sendEmail({
    to: Session.getEffectiveUser().getEmail(),
    name: EMAIL.remetente,
    subject: assunto,
    body: `${texto}\n\n${linhas.map(([k, val]) => `${k}: ${val}`).join('\n')}`,
    htmlBody: modeloEmail({
      eyebrow: 'Aprovação de vídeos', titulo: titulo, consultor: EMAIL.nome.split(' ')[0],
      texto: texto, linhas: linhas, botoes: botoes, fecho: 'Mensagem automática da Agenda de Produção.',
    }, imagens),
    inlineImages: imagens,
  });
}

// Consultor, email e serviço de um ID (P0001) a partir do separador Agendamentos
function dadosProjeto(id) {
  if (!id) return {};
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET);
  const ultima = sh.getLastRow();
  if (ultima < 2) return {};
  const linha = sh.getRange(2, 1, ultima - 1, COL.servico).getValues()
    .find(v => String(v[COL.id - 1]).trim() === String(id).trim());
  if (!linha) return { id: id };
  const consultor = linha[COL.consultor - 1];
  return { id: id, consultor: consultor, email: emailDe(consultor), servico: linha[COL.servico - 1] };
}
