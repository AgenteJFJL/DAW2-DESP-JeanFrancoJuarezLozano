(function () {
  'use strict';
  var btn = document.getElementById('btn-invocar');
  if (!btn) return;
  var esc = document.getElementById('escenario');
  var lienzo = document.getElementById('lienzo');
  var ctx = lienzo.getContext('2d');
  var destello = document.getElementById('destello');
  var banner = document.getElementById('banner');
  var resultado = document.getElementById('resultado');
  var plantilla = document.getElementById('plantilla-resultado');
  var PITY = parseInt(btn.dataset.pity, 10);
  var COLORES = ['#9aa3b5', '#6bd48a', '#5db6ff', '#b27bff', '#ff8fd0', '#ffc83d'];
  var NOMBRES = ['Común', 'Poco común', 'Raro', 'Súper raro', 'Épico', 'Legendario'];
  var CARGA = [800, 1000, 1250, 1550, 1850, 2400];
  var parts = [], corre = false, color = '#b69cff', intensidad = 1;

  function medir() {
    var r = esc.getBoundingClientRect();
    lienzo.width = Math.max(1, Math.floor(r.width));
    lienzo.height = Math.max(1, Math.floor(r.height));
  }
  window.addEventListener('resize', medir);
  medir();

  function bucle() {
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);
    var cx = lienzo.width / 2, cy = lienzo.height / 2;
    for (var i = parts.length - 1; i >= 0; i--) {
      var p = parts[i];
      p.a += p.v; p.r *= p.s; p.vida -= 1;
      var x = cx + Math.cos(p.a) * p.r, y = cy + Math.sin(p.a) * p.r;
      ctx.globalAlpha = Math.max(0, Math.min(1, p.vida / 40));
      ctx.fillStyle = p.c;
      ctx.beginPath(); ctx.arc(x, y, p.t, 0, 6.283); ctx.fill();
      if (p.vida <= 0 || p.r < 3) parts.splice(i, 1);
    }
    ctx.globalAlpha = 1;
    if (corre || parts.length) requestAnimationFrame(bucle);
  }

  function emitir(n, c, radio, spiral) {
    for (var i = 0; i < n; i++) {
      parts.push({ a: Math.random() * 6.283, r: radio * (0.6 + Math.random() * 0.6), v: 0.05 + Math.random() * 0.05,
        s: spiral ? 0.975 : 1.03, t: 1 + Math.random() * 2.2, c: c, vida: 60 + Math.random() * 40 });
    }
  }

  var pausa = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };

  function rellenar(d) {
    var nodo = plantilla.content.firstElementChild.cloneNode(true);
    var e = d.espiritu;
    nodo.classList.add('r' + e.rareza);
    var f = function (c) { return nodo.querySelector('[data-campo="' + c + '"]'); };
    f('nuevo').hidden = !d.nuevo;
    f('imagen').src = '/media/' + encodeURIComponent(e.imagen);
    f('imagen').alt = e.nombre;
    f('rareza').textContent = e.rareza_nombre + ' · ' + d.probabilidad.toFixed(2) + ' %';
    f('nombre').textContent = e.nombre;
    f('subtitulo').textContent = e.subtitulo;
    f('familia').textContent = 'Familia: ' + e.familia + (e.variante_nombre ? ' · Variante de ' + e.variante_nombre : '');
    f('descripcion').textContent = e.descripcion;
    f('copias').textContent = d.nuevo ? 'Primera copia' : 'Ya tienes ×' + d.copias;
    return nodo;
  }

  function actualizarGarantia(racha) {
    var restantes = PITY - racha;
    document.getElementById('garantia-texto').textContent =
      'Raro o superior garantizado en ' + restantes + ' invocación' + (restantes === 1 ? '' : 'es');
    document.getElementById('garantia-barra').value = PITY - restantes;
  }

  btn.addEventListener('click', function () {
    btn.disabled = true;
    resultado.textContent = '';
    esc.classList.remove('mostrando', 'tiembla');
    esc.classList.add('cargando');
    banner.hidden = true; destello.hidden = true;
    color = '#b69cff'; corre = true;
    var t0 = Date.now();
    medir(); requestAnimationFrame(bucle);
    var iv = setInterval(function () { emitir(4, color, Math.min(lienzo.width, lienzo.height) * 0.48, true); }, 40);

    fetch(btn.dataset.url, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRF-Token': btn.dataset.csrf } })
      .then(function (r) { if (!r.ok) throw new Error('error ' + r.status); return r.json(); })
      .then(function (d) {
        var rz = d.espiritu.rareza;
        color = COLORES[rz];
        return pausa(Math.max(0, CARGA[rz] - (Date.now() - t0))).then(function () { return d; });
      })
      .then(function (d) {
        var rz = d.espiritu.rareza;
        clearInterval(iv);
        emitir(30 + rz * 25, COLORES[rz], 10, false);
        destello.hidden = false; destello.style.background = rz >= 3 ? COLORES[rz] : '#fff';
        destello.style.animation = 'none'; void destello.offsetWidth; destello.style.animation = '';
        if (rz >= 2) {
          banner.textContent = NOMBRES[rz];
          banner.style.color = COLORES[rz];
          banner.hidden = false;
        }
        if (rz >= 4) { esc.classList.add('tiembla'); }
        esc.classList.remove('cargando'); esc.classList.add('mostrando');
        resultado.appendChild(rellenar(d));
        document.getElementById('n-invocaciones').textContent = d.invocaciones;
        actualizarGarantia(d.racha);
        corre = false; btn.disabled = false;
      })
      .catch(function () {
        clearInterval(iv); corre = false;
        esc.classList.remove('cargando');
        resultado.textContent = 'No se pudo invocar. Recarga la página e inténtalo de nuevo.';
        btn.disabled = false;
      });
  });
})();
