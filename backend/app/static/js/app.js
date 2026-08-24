// Controle de Treinamentos — utilitários de compartilhamento
function copiarLink(url) {
  function copiarFallback() {
    var tmp = document.createElement("textarea");
    tmp.value = url;
    document.body.appendChild(tmp);
    tmp.select();
    document.execCommand("copy");
    document.body.removeChild(tmp);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(
      function () { alert("Link copiado para a área de transferência."); },
      function () { copiarFallback(); alert("Link copiado para a área de transferência."); }
    );
  } else {
    copiarFallback();
    alert("Link copiado para a área de transferência.");
  }
}

function compartilhar(url, titulo) {
  if (navigator.share) {
    navigator.share({ title: titulo, text: titulo, url: url }).catch(function () {});
  } else {
    copiarLink(url);
  }
}

function imprimirQR(urlQr, nome) {
  var w = window.open("", "_blank", "width=420,height=520");
  if (!w) { alert("Permita pop-ups para imprimir o QR Code."); return; }
  var data = new Date().toLocaleDateString("pt-BR");
  var nomeEscapado = (nome || "").replace(/[<>&"]/g, function (c) {
    return { "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c];
  });
  w.document.write(
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>QR Code</title>' +
    '<style>body{font-family:Segoe UI,system-ui,sans-serif;text-align:center;padding:24px;color:#111}' +
    'h2{font-size:18px;margin:0 0 4px}' +
    'p{font-size:14px;margin:4px 0}' +
    'p.meta{color:#666;font-size:12px}' +
    'img{width:280px;height:280px;display:block;margin:20px auto}</style></head><body>' +
    '<h2>QR Code — Cartão de treinamentos</h2>' +
    '<p><strong>' + nomeEscapado + '</strong></p>' +
    '<img src="' + urlQr + '" alt="QR Code">' +
    '<p class="meta">Impresso em ' + data + '</p>' +
    '<script>window.onload = function () { window.print(); };<' + '/script>' +
    '</body></html>'
  );
  w.document.close();
}

// Botões com data-* (evita injetar nomes de usuários em strings JS inline).
document.addEventListener("click", function (e) {
  var alvo = e.target.closest("[data-compartilhar],[data-copiar],[data-imprimir-qr]");
  if (!alvo) return;
  if (alvo.dataset.compartilhar) {
    compartilhar(alvo.dataset.compartilhar, alvo.dataset.titulo || "");
  } else if (alvo.dataset.copiar) {
    copiarLink(alvo.dataset.copiar);
  } else if (alvo.dataset.imprimirQr) {
    imprimirQR(alvo.dataset.imprimirQr, alvo.dataset.nome || "");
  }
});

// Modal centralizado de confirmação para formulários com data-confirmar.
var _modalEl = null;
function fecharModal() {
  if (_modalEl) { _modalEl.remove(); _modalEl = null; }
}
function mostrarConfirmacao(mensagem, aoConfirmar, perigoso) {
  fecharModal();
  _modalEl = document.createElement("div");
  _modalEl.className = "modal-overlay";
  _modalEl.innerHTML =
    '<div class="modal-caixa" role="dialog" aria-modal="true" aria-labelledby="modal-titulo">' +
    '<h3 id="modal-titulo">Confirmação</h3>' +
    '<p class="modal-mensagem"></p>' +
    '<div class="modal-acoes">' +
    '<button type="button" class="btn btn-secondary" data-modal-cancelar>Cancelar</button>' +
    '<button type="button" class="' + (perigoso ? "btn btn-danger" : "btn btn-primary") + '" data-modal-ok>Confirmar</button>' +
    "</div></div>";
  _modalEl.querySelector(".modal-mensagem").textContent = mensagem;
  document.body.appendChild(_modalEl);
  var ok = _modalEl.querySelector("[data-modal-ok]");
  var cancelar = _modalEl.querySelector("[data-modal-cancelar]");
  _modalEl.addEventListener("click", function (e) {
    if (e.target === _modalEl || e.target === cancelar) fecharModal();
    else if (e.target === ok) { var cb = aoConfirmar; fecharModal(); cb(); }
  });
  document.addEventListener("keydown", function aoTeclar(e) {
    if (!_modalEl) { document.removeEventListener("keydown", aoTeclar); return; }
    if (e.key === "Escape") { fecharModal(); document.removeEventListener("keydown", aoTeclar); }
  });
  ok.focus();
}

document.addEventListener("submit", function (e) {
  var f = e.target.closest("form[data-confirmar]");
  if (!f) return;
  e.preventDefault();
  mostrarConfirmacao(
    f.getAttribute("data-confirmar"),
    function () { f.removeAttribute("data-confirmar"); f.submit(); },
    f.hasAttribute("data-perigo")
  );
});
