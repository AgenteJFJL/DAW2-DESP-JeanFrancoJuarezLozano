from flask import Flask
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def index():
    return f"""
    <h1>Práctica 04: Flask + Gunicorn + Nginx en AWS</h1>
    <p><b>Alumno:</b> Jean Franco Juarez Lozano</p>
    <p><b>Práctica:</b> Despliegue en AWS EC2 con HTTPS</p>
    <p><b>Fecha:</b> {datetime.now():%d/%m/%Y %H:%M:%S}</p>
    """