/**
 * Define a assinatura do Gmail (emails novos e respostas) no formato da equipa Terrae.
 * Precisa do serviço "Gmail API" ativo no editor (Serviços > + > Gmail API).
 * Correr uma vez: escolher definirAssinaturaGmail e carregar em Executar.
 */
function definirAssinaturaGmail() {
  const email = Session.getEffectiveUser().getEmail();
  const whatsapp = EMAIL.whatsapp.replace(/\D/g, '');
  const html = `
<table cellpadding="0" cellspacing="0" border="0" style="color:#000000;border-collapse:collapse;font-family:-apple-system,'Segoe UI',Roboto,sans-serif">
  <tbody><tr>
    <td style="vertical-align:middle;padding-right:18px">
      <a href="https://terrae.pt/" style="text-decoration:none;border:0" target="_blank"><img src="${EMAIL.logoAssinatura}" alt="Terrae" width="116" style="display:block;width:116px;height:auto;border:0"></a>
    </td>
    <td style="vertical-align:middle;border-left:1px solid #D3C9BA;padding-left:18px">
      <div style="font-size:15px;font-weight:600;color:#1D1D1B">${EMAIL.nome}</div>
      <div style="font-size:12px;color:#7A746A;padding-bottom:9px">${EMAIL.cargo}</div>
      <div style="font-size:13px;line-height:1.8">
        <a href="https://wa.me/${whatsapp}" style="color:#976E53;text-decoration:none" target="_blank">WhatsApp ${EMAIL.whatsapp}</a><br>
        <a href="mailto:${email}" style="color:#976E53;text-decoration:none" target="_blank">${email}</a>
      </div>
    </td>
  </tr></tbody>
</table>`;
  Gmail.Users.Settings.SendAs.patch({ signature: html }, 'me', email);
  console.log('Assinatura do Gmail atualizada para ' + email);
}
