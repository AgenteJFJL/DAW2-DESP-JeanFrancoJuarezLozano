import os
import pymysql
from flask import Flask
from markupsafe import escape

app = Flask(__name__)


def get_connection():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "mariadb"),
        user=os.environ.get("DB_USER", "flaskuser"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "practica05juarez"),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


@app.route("/")
def index():
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, titulo, descripcion, completada, fecha_creacion "
                "FROM tareas ORDER BY id"
            )
            tareas = cur.fetchall()
        conn.close()
    except Exception as e:
        return f"<h1>Error de base de datos</h1><p>{escape(str(e))}</p>", 500

    filas = ""
    for t in tareas:
        estado = "Hecha" if t["completada"] else "Pendiente"
        filas += (
            f"<tr><td>{t['id']}</td><td>{escape(t['titulo'])}</td>"
            f"<td>{escape(t['descripcion'] or '')}</td><td>{estado}</td>"
            f"<td>{t['fecha_creacion']}</td></tr>"
        )

    return f"""
    <html><head><meta charset="utf-8"><title>Práctica 05</title>
    <style>
      body {{ font-family: sans-serif; margin: 40px; }}
      table {{ border-collapse: collapse; }}
      td, th {{ border: 1px solid #999; padding: 6px 12px; }}
      th {{ background: #eee; }}
    </style></head>
    <body>
      <h1>Práctica 05: Flask + MariaDB con Docker Compose</h1>
      <p><b>Alumno:</b> Jean Franco Juárez Lozano</p>
      <h2>Tareas ({len(tareas)} registros)</h2>
      <table>
        <tr><th>ID</th><th>Título</th><th>Descripción</th><th>Estado</th><th>Creada</th></tr>
        {filas}
      </table>
    </body></html>
    """