(function () {
  'use strict';
  var buscar = document.getElementById('buscar');
  if (buscar) {
    var items = document.querySelectorAll('#lista-admin li');
    buscar.addEventListener('input', function () {
      var q = buscar.value.trim().toLowerCase();
      items.forEach(function (li) { li.hidden = q !== '' && li.getAttribute('data-texto').indexOf(q) === -1; });
    });
  }

  var selFam = document.getElementById('sel-familia');
  var filaNueva = document.getElementById('fila-familia-nueva');
  if (selFam && filaNueva) {
    var campo = filaNueva.querySelector('input');
    var alternar = function () {
      var nueva = selFam.value === 'nueva';
      filaNueva.hidden = !nueva;
      campo.required = nueva;
    };
    selFam.addEventListener('change', alternar);
    alternar();
  }

  var archivo = document.getElementById('imagen');
  var previa = document.getElementById('previa');
  var aviso = document.getElementById('previa-aviso');
  if (archivo && previa) {
    archivo.addEventListener('change', function () {
      var f = archivo.files[0];
      aviso.hidden = true;
      if (!f) return;
      if (f.size > 3 * 1024 * 1024) {
        aviso.textContent = 'Pesa más de 3 MB: el servidor la rechazará.';
        aviso.hidden = false;
      }
      var url = URL.createObjectURL(f);
      var img = previa.querySelector('img');
      if (!img) { img = document.createElement('img'); img.width = 128; img.height = 128; previa.insertBefore(img, aviso); }
      img.alt = 'Vista previa';
      img.onload = function () {
        if (img.naturalWidth !== 512 || img.naturalHeight !== 512) {
          aviso.textContent = 'Tu imagen es de ' + img.naturalWidth + '×' + img.naturalHeight +
            ' px. Lo ideal es 512×512; se ajustará automáticamente.';
          aviso.hidden = false;
        }
        URL.revokeObjectURL(url);
      };
      img.src = url;
    });
  }
})();
