from flask import Flask
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def index():
    return f"""
    <h1>Bienvenido a la Práctica 03</h1>
    <p><b>Alumno:</b>Jean Franco Juarez Lozano</p>
    <p><b>Práctica:</b> Flask + Gunicorn + Nginx</p>
    <p><b>Fecha:</b> {datetime.now():%d/%m/%Y %H:%M:%S}</p>
    """