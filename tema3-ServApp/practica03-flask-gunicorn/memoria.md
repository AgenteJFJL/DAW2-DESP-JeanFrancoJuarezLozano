# Memoria - Práctica 03: Flask + Gunicorn + Nginx

**Alumno:** Jean Franco Juarez Lozano

## 1. Introducción


## 2. Arquitectura
Usuario → Nginx → Gunicorn → Flask


## 3. Análisis de componentes
### Flask
### Gunicorn
Es un servidor WSGI. Flask solo trae un servidor de desarrollo (un proceso, sin robustez). Gunicorn lanza varios workers en paralelo y gestiona reinicios.
en este: ../venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
../venv/bin/gunicorn despliega el entorno gunicorn virtual
--workers -2 Llama dos procesos que atienden peticiones
--bind ....: 8000 escucha solo en local el localhost que es 8000
app:app  Es el app.py que he creado

### Nginx

## 4. Servicio systemd


## 5. Análisis de logs


## 6. Comparación con Tomcat


## 7. Cuestiones finales
1. ¿Cuál es la función de Flask?
   

## 8. Conclusiones
