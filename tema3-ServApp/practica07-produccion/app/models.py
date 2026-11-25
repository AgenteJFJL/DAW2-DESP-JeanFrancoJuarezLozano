"""MODELO (MVC): acceso a MariaDB y reglas del juego.

Aquí no hay HTML ni rutas: solo datos y lógica. El controlador (app.py) llama
a estas funciones y las vistas (templates/) muestran el resultado.
"""
import os
import re
import secrets
import shutil
import unicodedata

import pymysql
from flask import g
from werkzeug.security import check_password_hash, generate_password_hash

# Cada PITY invocaciones, al menos una es de rareza RAREZA_GARANTIA o superior.
PITY = int(os.environ.get("PITY", "5"))
RAREZA_GARANTIA = 2          # 2 = Raro
RAREZAS_NOMBRES = ["Común", "Poco común", "Raro", "Súper raro", "Épico", "Legendario"]
DOMINIO = "@educa.madrid.org"
USUARIO_RE = re.compile(r"^[a-z0-9._-]{3,40}$")
RNG = secrets.SystemRandom()  # aleatoriedad del sistema, no predecible


# ---------------------------------------------------------------- conexión
def conectar():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "mariadb"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "flaskuser"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "practica07jfjl04"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=5,
        read_timeout=15,
        write_timeout=15,
    )


def db():
    """Una conexión por petición, guardada en flask.g."""
    if "db" not in g:
        g.db = conectar()
    return g.db


def cerrar(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        try:
            conn.rollback()          # si no hubo commit, no queda nada a medias
        finally:
            conn.close()


def _todos(sql, args=()):
    with db().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def _uno(sql, args=()):
    with db().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()


def confirmar():
    db().commit()


# ---------------------------------------------------------------- arranque
def asegurar_admin(usuario, password):
    """Crea (o actualiza) la cuenta de administrador a partir del .env."""
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash, es_admin FROM usuarios WHERE usuario=%s", (usuario,))
            u = cur.fetchone()
            if u is None:
                cur.execute(
                    "INSERT INTO usuarios (usuario, password_hash, es_admin) VALUES (%s, %s, 1)",
                    (usuario, generate_password_hash(password)),
                )
            elif not u["es_admin"] or not check_password_hash(u["password_hash"], password):
                cur.execute(
                    "UPDATE usuarios SET es_admin=1, password_hash=%s WHERE id=%s",
                    (generate_password_hash(password), u["id"]),
                )
        conn.commit()
    finally:
        conn.close()


def sembrar_media(origen, destino):
    """Copia las imágenes iniciales al volumen (sin pisar las que ya existan)."""
    os.makedirs(destino, exist_ok=True)
    for nombre in os.listdir(origen):
        if not os.path.exists(os.path.join(destino, nombre)):
            shutil.copy2(os.path.join(origen, nombre), os.path.join(destino, nombre))


# ---------------------------------------------------------------- usuarios
def normalizar_usuario(texto):
    t = (texto or "").strip().lower()
    if t.endswith(DOMINIO):
        t = t[: -len(DOMINIO)]
    return t if USUARIO_RE.match(t) else None


def usuario_por_id(uid):
    return _uno("SELECT id, usuario, es_admin, invocaciones, racha FROM usuarios WHERE id=%s", (uid,))


def usuario_por_nombre(nombre):
    return _uno("SELECT id, usuario, password_hash, es_admin, invocaciones, racha FROM usuarios WHERE usuario=%s", (nombre,))


_HASH_FALSO = generate_password_hash("contraseña-de-relleno")


def autenticar(usuario, password):
    u = usuario_por_nombre(usuario)
    ok = check_password_hash(u["password_hash"] if u else _HASH_FALSO, password or "")
    return u if (u and ok) else None


def crear_usuario(usuario, password):
    try:
        with db().cursor() as cur:
            cur.execute(
                "INSERT INTO usuarios (usuario, password_hash) VALUES (%s, %s)",
                (usuario, generate_password_hash(password)),
            )
        confirmar()
    except pymysql.err.IntegrityError:
        db().rollback()
        return None
    return usuario_por_nombre(usuario)


def listar_usuarios():
    return _todos(
        """SELECT u.id, u.usuario, u.es_admin, u.invocaciones, COUNT(c.espiritu_id) AS distintos
           FROM usuarios u LEFT JOIN colecciones c ON c.usuario_id = u.id
           GROUP BY u.id ORDER BY u.usuario"""
    )


# ---------------------------------------------------------------- catálogo
_SQL_CATALOGO = """
    SELECT e.id, e.nombre, e.subtitulo, e.descripcion, e.rareza, e.familia_id,
           f.nombre AS familia, e.variante_de, b.nombre AS variante_nombre,
           e.imagen, r.nombre AS rareza_nombre
    FROM espiritus e
    JOIN familias f  ON f.id = e.familia_id
    JOIN rarezas r   ON r.id = e.rareza
    LEFT JOIN espiritus b ON b.id = e.variante_de
"""


def catalogo():
    return _todos(_SQL_CATALOGO + " ORDER BY e.rareza, e.id")


def espiritu(espiritu_id):
    return _uno(_SQL_CATALOGO + " WHERE e.id = %s", (espiritu_id,))


def familias():
    return _todos("SELECT id, nombre FROM familias ORDER BY nombre")


def familias_con_progreso(usuario_id):
    return _todos(
        """SELECT f.id, f.nombre, COUNT(DISTINCT e.id) AS total, COUNT(DISTINCT c.espiritu_id) AS tengo
           FROM familias f
           LEFT JOIN espiritus e ON e.familia_id = f.id
           LEFT JOIN colecciones c ON c.espiritu_id = e.id AND c.usuario_id = %s
           GROUP BY f.id HAVING total > 0 ORDER BY f.id""",
        (usuario_id,),
    )


def coleccion_de(usuario_id):
    filas = _todos("SELECT espiritu_id, cantidad FROM colecciones WHERE usuario_id=%s", (usuario_id,))
    return {f["espiritu_id"]: f["cantidad"] for f in filas}


# ------------------------------------------------------------ probabilidades
def tabla_probabilidades():
    """Probabilidad por rareza y por espíritu, calculada en cada consulta.

    El peso de cada rareza es fijo; lo que se reparte entre los espíritus de
    una rareza depende de cuántos haya. Si cambias un espíritu de rareza,
    las cifras se recalculan solas. Una rareza sin espíritus no cuenta y su
    peso se reparte entre las demás.
    """
    rarezas = _todos("SELECT id, nombre, peso FROM rarezas ORDER BY id")
    cuentas = {f["rareza"]: f["n"] for f in _todos("SELECT rareza, COUNT(*) AS n FROM espiritus GROUP BY rareza")}
    peso_activo = sum(float(r["peso"]) for r in rarezas if cuentas.get(r["id"], 0) > 0)
    filas = []
    for r in rarezas:
        n = cuentas.get(r["id"], 0)
        pct = float(r["peso"]) / peso_activo * 100 if n and peso_activo else 0.0
        filas.append({
            "id": r["id"], "nombre": r["nombre"], "peso": float(r["peso"]), "cantidad": n,
            "porcentaje": pct, "por_espiritu": pct / n if n else 0.0,
        })
    return filas


# ---------------------------------------------------------------- invocar
def invocar(usuario_id):
    """Una invocación completa y atómica. El sorteo se hace aquí, en el servidor."""
    with db().cursor() as cur:
        cur.execute("SELECT invocaciones, racha FROM usuarios WHERE id=%s FOR UPDATE", (usuario_id,))
        u = cur.fetchone()

    por_rareza = {}
    for e in _todos("SELECT id, rareza FROM espiritus"):
        por_rareza.setdefault(e["rareza"], []).append(e["id"])
    if not por_rareza:
        raise RuntimeError("No hay espíritus en el catálogo")

    probs = [p for p in tabla_probabilidades() if p["cantidad"] > 0]
    garantizada = u["racha"] >= PITY - 1
    candidatas = [p for p in probs if not garantizada or p["id"] >= RAREZA_GARANTIA] or probs
    x = RNG.random() * sum(p["porcentaje"] for p in candidatas)
    elegida = candidatas[-1]
    acumulado = 0.0
    for p in candidatas:
        acumulado += p["porcentaje"]
        if x < acumulado:
            elegida = p
            break

    espiritu_id = RNG.choice(por_rareza[elegida["id"]])
    racha = 0 if elegida["id"] >= RAREZA_GARANTIA else u["racha"] + 1

    with db().cursor() as cur:
        cur.execute(
            "INSERT INTO colecciones (usuario_id, espiritu_id, cantidad) VALUES (%s, %s, 1) "
            "ON DUPLICATE KEY UPDATE cantidad = cantidad + 1",
            (usuario_id, espiritu_id),
        )
        cur.execute("UPDATE usuarios SET invocaciones = invocaciones + 1, racha = %s WHERE id=%s", (racha, usuario_id))
        cur.execute("SELECT cantidad FROM colecciones WHERE usuario_id=%s AND espiritu_id=%s", (usuario_id, espiritu_id))
        copias = cur.fetchone()["cantidad"]
        cur.execute("SELECT COUNT(*) AS n FROM colecciones WHERE usuario_id=%s", (usuario_id,))
        distintos = cur.fetchone()["n"]
    confirmar()
    return {
        "espiritu": espiritu(espiritu_id), "nuevo": copias == 1, "copias": copias,
        "racha": min(racha, PITY - 1), "invocaciones": u["invocaciones"] + 1, "distintos": distintos,
        "probabilidad": next(p["por_espiritu"] for p in probs if p["id"] == elegida["id"]),
    }


# ---------------------------------------------------------------- jugadores
def ranking():
    filas = _todos(
        """SELECT u.id, u.usuario, u.es_admin, u.invocaciones,
                  COUNT(c.espiritu_id) AS distintos,
                  (SELECT e2.id FROM colecciones c2 JOIN espiritus e2 ON e2.id = c2.espiritu_id
                    WHERE c2.usuario_id = u.id ORDER BY e2.rareza DESC, e2.id DESC LIMIT 1) AS mejor_id
           FROM usuarios u LEFT JOIN colecciones c ON c.usuario_id = u.id
           GROUP BY u.id ORDER BY distintos DESC, u.invocaciones DESC, u.usuario"""
    )
    por_id = {e["id"]: e for e in catalogo()}
    for f in filas:
        f["mejor"] = por_id.get(f["mejor_id"])
    return filas


# ------------------------------------------------------- administración
def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40] or "espiritu"


def familia_por_nombre_o_crear(nombre):
    """Devuelve el id de la familia (la crea si no existe; sin distinguir mayúsculas)."""
    f = _uno("SELECT id FROM familias WHERE nombre=%s", (nombre,))
    if f:
        return f["id"]
    with db().cursor() as cur:
        cur.execute("INSERT INTO familias (nombre) VALUES (%s)", (nombre,))
        return cur.lastrowid


def crear_espiritu(d):
    with db().cursor() as cur:
        cur.execute(
            "INSERT INTO espiritus (nombre, subtitulo, descripcion, rareza, familia_id, variante_de, imagen) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (d["nombre"], d["subtitulo"], d["descripcion"], d["rareza"], d["familia_id"], d["variante_de"], d["imagen"]),
        )
        nuevo_id = cur.lastrowid
    confirmar()
    return nuevo_id


def actualizar_espiritu(espiritu_id, d):
    with db().cursor() as cur:
        cur.execute(
            "UPDATE espiritus SET nombre=%s, subtitulo=%s, descripcion=%s, rareza=%s, familia_id=%s, "
            "variante_de=%s, imagen=COALESCE(%s, imagen) WHERE id=%s",
            (d["nombre"], d["subtitulo"], d["descripcion"], d["rareza"], d["familia_id"],
             d["variante_de"], d.get("imagen"), espiritu_id),
        )
    confirmar()


def regalar(usuario_id, espiritu_id, cantidad):
    """Añade copias de un espíritu a un usuario (el admin puede regalárselas a sí mismo)."""
    with db().cursor() as cur:
        cur.execute("SELECT id FROM usuarios WHERE id=%s FOR UPDATE", (usuario_id,))
        if cur.fetchone() is None:
            return False
        cur.execute("SELECT id FROM espiritus WHERE id=%s", (espiritu_id,))
        if cur.fetchone() is None:
            return False
        cur.execute(
            "INSERT INTO colecciones (usuario_id, espiritu_id, cantidad) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE cantidad = cantidad + VALUES(cantidad)",
            (usuario_id, espiritu_id, cantidad),
        )
    confirmar()
    return True
