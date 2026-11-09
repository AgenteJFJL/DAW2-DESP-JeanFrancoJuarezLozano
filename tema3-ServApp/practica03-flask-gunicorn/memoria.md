# Memoria - Práctica 03: Flask + Gunicorn + Nginx

**Alumno:** Jean Franco Juarez Lozano

## 1. Introducción
Esta práctica laharemos en el mismo equipo (Dovker), se aprenderá a cómo funciona cada pieza, Flask, Gunicorn, Nginx y systemd

## 2. Arquitectura
Usuario → Nginx → Gunicorn → Flask

## 3. Análisis de componentes
### Flask
La aplicación flask contiene un html que contiene información tal  como mi nombre y la fecha.

### Gunicorn
Es un servidor WSGI. Flask solo trae un servidor de desarrollo (un proceso, sin robustez). Gunicorn lanza varios workers en paralelo y gestiona reinicios.
en este: ../venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
../venv/bin/gunicorn despliega el entorno gunicorn virtual
--workers -2 Llama dos procesos que atienden peticiones
--bind ....: 8000 escucha solo en local el localhost que es 8000
app:app  Es el app.py que he creado

### Nginx
Es un servidor web y de reverse proxy, en /etc/nginx/sites-available/flask, está la configuracion y está en la carpeta del mismo nombre, destaca el contenido estático, HTTPS, balanceo, oculta el backend.

## 4. Servicio systemd
En su configuracion de service, está siempre activo, así que aunque lo matemos con un kill, y volvemos a ver el estado, estará activo.

## 5. Análisis de logs


## 6. Comparación con Tomcat
En la práctica hecha con Tomcat, Nginx hace de proxy inverso y el backend no se expone directamente, igual pasa aquí, pero aquí vienen las diferencias, El lenguaje usado en la práctica Tomcat es Java, mientras que en esta es Python (WSGI), el Backend en Tomcat es un contenedor de servlets completo, mientras que en esta practica es de Servidor WSGI ligero, el despliegue en la primera practica es de copair el WAR, mientras que aquí es desplegarel código en un entorno virtual. Por último , en Tomcat, el puerto era el 8080, mientra sque aquí era el 8000
## 7. Cuestiones finales
1. ¿Cuál es la función de Flask?
   La funciond e flask es definir rutas y lógica, recibe un mínimo de peticiones y devuelve respuestas, es un framework que permite el desarrollo web de forma rápida. No es un framework pesado como Django.

## 8. Conclusiones
