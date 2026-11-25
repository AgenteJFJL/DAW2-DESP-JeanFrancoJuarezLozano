"""CONTROLADOR (MVC): rutas Flask. Recibe la petición, llama al modelo
(models.py) y devuelve una vista (templates/) o JSON."""
import functools
import os
import secrets
import time
from datetime import timedelta

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

import imagenes
import models

BASE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.environ.get("MEDIA_DIR", "/data/media")
ADMIN_SESION = 2 * 60 * 60            # el modo administrador caduca a las 2 h

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)
# Detrás de Nginx Proxy Manager + Nginx interno: 2 saltos para la IP real, 1 para el esquema.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1)
app.teardown_appcontext(models.cerrar)


# ------------------------------------------------------------------ arranque
def _arranque():
    models.sembrar_media(os.path.join(BASE, "seed_pictures"), MEDIA)
    admin = models.normalizar_usuario(os.environ.get("ADMIN_USER", ""))
    clave = os.environ.get("ADMIN_PASSWORD", "")
    if not admin or len(clave) < 8:
        raise SystemExit("ADMIN_USER / ADMIN_PASSWORD no válidos (mínimo 8 caracteres)")
    for intento in range(1, 31):
        try:
            models.asegurar_admin(admin, clave)
            return
        except Exception as exc:                      # la BD aún arranca
            print(f"[arranque] esperando a MariaDB ({intento}/30): {exc}", flush=True)
            time.sleep(2)
    raise SystemExit("No se pudo conectar con la base de datos")


_arranque()


# ------------------------------------------------------------- seguridad
_fallos = {}


def _bloqueado():
    ahora = time.time()
    lista = [t for t in _fallos.get(request.remote_addr, []) if ahora - t < 600]
    _fallos[request.remote_addr] = lista
    return len(lista) >= 8


def _fallo():
    _fallos.setdefault(request.remote_addr, []).append(time.time())


@app.before_request
def _antes():
    if request.endpoint in ("static", "media"):
        return
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    if request.method == "POST":
        recibido = request.form.get("csrf") or request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(recibido, session["csrf"]):
            abort(400)
    g.usuario = models.usuario_por_id(session["uid"]) if "uid" in session else None


@app.after_request
def _cabeceras(resp):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; "
        "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.is_secure:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    if request.endpoint not in ("static", "media"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def _admin_activo():
    u = getattr(g, "usuario", None)
    return bool(u and u["es_admin"] and session.get("admin_hasta", 0) > time.time())


@app.context_processor
def _contexto():
    return {"yo": getattr(g, "usuario", None), "admin_activo": _admin_activo(),
            "csrf": session.get("csrf", ""), "PITY": models.PITY}


def login_requerido(f):
    @functools.wraps(f)
    def interior(*a, **k):
        if not g.usuario:
            return redirect(url_for("login"))
        return f(*a, **k)
    return interior


def admin_requerido(f):
    @functools.wraps(f)
    def interior(*a, **k):
        if not g.usuario:
            return redirect(url_for("login"))
        if not _admin_activo():
            flash("Entra por «Acceso de administrador» para usar el panel.", "error")
            return redirect(url_for("login"))
        return f(*a, **k)
    return interior


def _entrar(u, admin=False):
    session.clear()
    session.permanent = True
    session["uid"] = u["id"]
    session["csrf"] = secrets.token_urlsafe(32)
    if admin:
        session["admin_hasta"] = time.time() + ADMIN_SESION


# ------------------------------------------------------------ errores
def _error(codigo, titulo, texto):
    return render_template("error.html", codigo=codigo, titulo=titulo, texto=texto), codigo


@app.errorhandler(400)
def _e400(_):
    return _error(400, "Petición no válida", "Recarga la página e inténtalo de nuevo.")


@app.errorhandler(404)
def _e404(_):
    return _error(404, "Aquí no hay nada…", "Este rincón del santuario está vacío (o aún no lo has desbloqueado).")


@app.errorhandler(413)
def _e413(_):
    return _error(413, "Fichero demasiado grande", "El límite es de 3 MB por imagen.")


@app.errorhandler(500)
def _e500(_):
    return _error(500, "El santuario tiembla", "Algo ha fallado en el servidor. Inténtalo de nuevo en unos segundos.")


# ------------------------------------------------------------ acceso
@app.get("/")
def inicio():
    return redirect(url_for("invocar" if g.usuario else "login"))


@app.get("/login")
def login():
    if g.usuario:
        return redirect(url_for("invocar"))
    return render_template("login.html")


@app.post("/login")
def login_post():
    if _bloqueado():
        flash("Demasiados intentos fallidos. Espera unos minutos.", "error")
        return redirect(url_for("login"))
    nombre = models.normalizar_usuario(request.form.get("usuario"))
    u = models.autenticar(nombre, request.form.get("password")) if nombre else None
    if not u:
        _fallo()
        flash("Usuario o contraseña incorrectos.", "error")
        return redirect(url_for("login"))
    _entrar(u)
    return redirect(url_for("invocar"))


@app.post("/registro")
def registro():
    if _bloqueado():
        flash("Demasiados intentos. Espera unos minutos.", "error")
        return redirect(url_for("login"))
    nombre = models.normalizar_usuario(request.form.get("usuario"))
    clave = request.form.get("password") or ""
    if not nombre:
        flash("Usuario no válido: 3-40 caracteres (letras minúsculas, números, punto, guion). "
              "Puedes escribir tu correo @educa.madrid.org.", "error")
    elif len(clave) < 8 or len(clave) > 200:
        flash("La contraseña debe tener al menos 8 caracteres.", "error")
    elif clave != request.form.get("password2"):
        flash("Las contraseñas no coinciden.", "error")
    else:
        u = models.crear_usuario(nombre, clave)
        if u:
            _entrar(u)
            return redirect(url_for("invocar"))
        _fallo()
        flash("Ese usuario ya existe.", "error")
    return redirect(url_for("login"))


@app.post("/admin/acceso")
def admin_acceso():
    if _bloqueado():
        flash("Demasiados intentos fallidos. Espera unos minutos.", "error")
        return redirect(url_for("login"))
    nombre = models.normalizar_usuario(request.form.get("usuario"))
    u = models.autenticar(nombre, request.form.get("password")) if nombre else None
    if not u or not u["es_admin"]:
        _fallo()
        flash("Credenciales de administrador incorrectas.", "error")
        return redirect(url_for("login"))
    _entrar(u, admin=True)
    return redirect(url_for("admin"))


@app.post("/salir")
def salir():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------ juego
@app.get("/invocar")
@login_requerido
def invocar():
    return render_template("invocar.html", probs=models.tabla_probabilidades(),
                           restantes=models.PITY - g.usuario["racha"])


@app.post("/api/invocar")
@login_requerido
def api_invocar():
    return jsonify(models.invocar(g.usuario["id"]))


@app.get("/coleccion")
@app.get("/coleccion/<usuario>")
@login_requerido
def coleccion(usuario=None):
    dueno = g.usuario if usuario is None else models.usuario_por_nombre(usuario)
    if not dueno:
        abort(404)
    tiene = models.coleccion_de(dueno["id"])
    familia = request.args.get("familia", type=int)
    cat = models.catalogo()
    visibles = [e for e in cat if not familia or e["familia_id"] == familia]
    items = [dict(e, cantidad=tiene[e["id"]]) if e["id"] in tiene else {"bloqueado": True, "id": e["id"]}
             for e in visibles]
    return render_template(
        "coleccion.html", dueno=dueno, propia=dueno["id"] == g.usuario["id"], items=items,
        familias=models.familias_con_progreso(dueno["id"]), familia_sel=familia,
        tengo=len(tiene), total=len(cat), copias=sum(tiene.values()))


@app.get("/espiritu/<int:espiritu_id>")
@login_requerido
def ficha(espiritu_id):
    e = models.espiritu(espiritu_id)
    if not e:
        abort(404)
    mias = models.coleccion_de(g.usuario["id"])
    copias = mias.get(espiritu_id, 0)
    autorizado = copias > 0 or _admin_activo()
    if not autorizado and request.args.get("de"):          # viendo la colección de otro jugador
        otro = models.usuario_por_nombre(request.args["de"])
        autorizado = bool(otro and espiritu_id in models.coleccion_de(otro["id"]))
    if not autorizado:
        abort(404)                                          # bloqueado = inaccesible
    plantilla = "_ficha.html" if request.args.get("parcial") else "ficha.html"
    return render_template(plantilla, e=e, copias=copias)


@app.get("/jugadores")
@login_requerido
def jugadores():
    return render_template("jugadores.html", filas=models.ranking(), total=len(models.catalogo()))


@app.get("/media/<path:nombre>")
def media(nombre):
    return send_from_directory(MEDIA, nombre, max_age=86400)


# ------------------------------------------------------------ administración
@app.get("/admin")
@admin_requerido
def admin():
    return render_template("admin/panel.html", cat=models.catalogo(), probs=models.tabla_probabilidades(),
                           usuarios=models.listar_usuarios(), nombres=models.RAREZAS_NOMBRES)


def _leer_formulario(editando=None):
    f = request.form
    d = {
        "nombre": f.get("nombre", "").strip(),
        "subtitulo": f.get("subtitulo", "").strip(),
        "descripcion": f.get("descripcion", "").strip(),
        "rareza": f.get("rareza", type=int),
        "familia_sel": f.get("familia", ""),
        "familia_nueva": f.get("familia_nueva", "").strip(),
        "variante_de": f.get("variante_de", type=int) or None,
    }
    errores = []
    if not d["nombre"] or len(d["nombre"]) > 80:
        errores.append("El nombre es obligatorio (máximo 80 caracteres).")
    if not d["subtitulo"] or len(d["subtitulo"]) > 100:
        errores.append("El subtítulo es obligatorio (máximo 100 caracteres).")
    if not d["descripcion"] or len(d["descripcion"]) > 1000:
        errores.append("La descripción es obligatoria (máximo 1000 caracteres).")
    if d["rareza"] is None or not 0 <= d["rareza"] <= 5:
        errores.append("Elige una rareza.")
    if d["variante_de"]:
        base = models.espiritu(d["variante_de"])
        if not base or d["variante_de"] == editando:
            errores.append("El espíritu base de la variante no es válido.")
        d["rareza"] = 5                                      # las variantes siempre son Legendarias
    if d["familia_sel"] == "nueva":
        if not d["familia_nueva"] or len(d["familia_nueva"]) > 40:
            errores.append("Escribe el nombre de la nueva familia (máximo 40 caracteres).")
    elif not d["familia_sel"].isdigit() or not any(str(x["id"]) == d["familia_sel"] for x in models.familias()):
        errores.append("Elige una familia o crea una nueva.")
    return d, errores


def _guardar_imagen(d, obligatoria):
    fichero = request.files.get("imagen")
    if not fichero or not fichero.filename:
        if obligatoria:
            return ["La imagen es obligatoria."]
        return []
    try:
        png, aviso = imagenes.procesar(fichero.stream)
    except ValueError as exc:
        return [str(exc)]
    d["imagen"] = imagenes.guardar(png, models.slug(d["nombre"]), MEDIA)
    if aviso:
        flash(aviso, "info")
    return []


def _resolver_familia(d):
    if d["familia_sel"] == "nueva":
        d["familia_id"] = models.familia_por_nombre_o_crear(d["familia_nueva"])
    else:
        d["familia_id"] = int(d["familia_sel"])


@app.route("/admin/espiritu/nuevo", methods=["GET", "POST"])
@admin_requerido
def admin_nuevo():
    if request.method == "POST":
        d, errores = _leer_formulario()
        errores += _guardar_imagen(d, obligatoria=True)
        if not errores:
            _resolver_familia(d)
            nuevo = models.crear_espiritu(d)
            flash(f"«{d['nombre']}» añadido al catálogo. Las probabilidades se han recalculado.", "ok")
            return redirect(url_for("admin") + f"#e{nuevo}")
        for e in errores:
            flash(e, "error")
        return render_template("admin/form.html", e=None, v=d, familias=models.familias(),
                               bases=models.catalogo(), nombres=models.RAREZAS_NOMBRES)
    return render_template("admin/form.html", e=None, v={}, familias=models.familias(),
                           bases=models.catalogo(), nombres=models.RAREZAS_NOMBRES)


@app.route("/admin/espiritu/<int:espiritu_id>/editar", methods=["GET", "POST"])
@admin_requerido
def admin_editar(espiritu_id):
    e = models.espiritu(espiritu_id)
    if not e:
        abort(404)
    if request.method == "POST":
        d, errores = _leer_formulario(editando=espiritu_id)
        errores += _guardar_imagen(d, obligatoria=False)
        if not errores:
            _resolver_familia(d)
            models.actualizar_espiritu(espiritu_id, d)
            flash(f"«{d['nombre']}» guardado. Las probabilidades se han recalculado.", "ok")
            return redirect(url_for("admin") + f"#e{espiritu_id}")
        for er in errores:
            flash(er, "error")
        return render_template("admin/form.html", e=e, v=d, familias=models.familias(),
                               bases=models.catalogo(), nombres=models.RAREZAS_NOMBRES)
    v = {"nombre": e["nombre"], "subtitulo": e["subtitulo"], "descripcion": e["descripcion"],
         "rareza": e["rareza"], "familia_sel": str(e["familia_id"]), "variante_de": e["variante_de"]}
    return render_template("admin/form.html", e=e, v=v, familias=models.familias(),
                           bases=models.catalogo(), nombres=models.RAREZAS_NOMBRES)


@app.post("/admin/regalar")
@admin_requerido
def admin_regalar():
    uid = request.form.get("usuario_id", type=int)
    eid = request.form.get("espiritu_id", type=int)
    n = request.form.get("cantidad", type=int) or 1
    if not uid or not eid or not 1 <= n <= 50:
        flash("Elige usuario, espíritu y una cantidad entre 1 y 50.", "error")
    elif models.regalar(uid, eid, n):
        destino = models.usuario_por_id(uid)["usuario"]
        flash(f"Regalo entregado: {n} × {models.espiritu(eid)['nombre']} para {destino}.", "ok")
    else:
        flash("Usuario o espíritu inexistente.", "error")
    return redirect(url_for("admin") + "#regalo")
