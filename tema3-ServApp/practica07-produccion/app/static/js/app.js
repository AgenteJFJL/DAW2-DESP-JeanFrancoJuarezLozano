(function () {
  'use strict';
  var modal = document.getElementById('modal');
  var cuerpo = document.getElementById('modal-cuerpo');
  var ultimo = null;

  function cerrar() {
    if (!modal) return;
    modal.hidden = true;
    cuerpo.textContent = '';
    if (ultimo) { ultimo.focus(); ultimo = null; }
  }

  function abrir(url, origen) {
    var sep = url.indexOf('?') === -1 ? '?' : '&';
    fetch(url + sep + 'parcial=1', { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error('no disponible'); return r.text(); })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        cuerpo.textContent = '';
        var ficha = doc.querySelector('.ficha');
        if (ficha) cuerpo.appendChild(document.importNode(ficha, true));
        ultimo = origen;
        modal.hidden = false;
        document.getElementById('modal-cerrar').focus();
      })
      .catch(function () { /* espíritu bloqueado: no se abre nada */ });
  }

  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-ficha]');
    if (btn) { abrir(btn.getAttribute('data-ficha'), btn); return; }
    if (ev.target.id === 'modal' || ev.target.id === 'modal-cerrar') cerrar();
  });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') cerrar(); });
})();
