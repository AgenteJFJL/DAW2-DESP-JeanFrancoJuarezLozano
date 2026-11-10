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

## 5. Comparación con Tomcat
En la práctica hecha con Tomcat, Nginx hace de proxy inverso y el backend no se expone directamente, igual pasa aquí, pero aquí vienen las diferencias, El lenguaje usado en la práctica Tomcat es Java, mientras que en esta es Python (WSGI), el Backend en Tomcat es un contenedor de servlets completo, mientras que en esta practica es de Servidor WSGI ligero, el despliegue en la primera practica es de copair el WAR, mientras que aquí es desplegarel código en un entorno virtual. Por último , en Tomcat, el puerto era el 8080, mientra sque aquí era el 8000


## 7. Preguntas finales:
1. ¿Cuál es la función de Flask?

Flask es un framework web de Python que permite definir la lógica de la aplicación: rutas (@app.route("/")), qué respuesta devuelve cada una y cómo se genera el HTML. En mi práctica, Flask es el que construye la página con mi nombre, la información de la práctica y la fecha.

2. ¿Cuál es la función de Gunicorn?

Gunicorn es un servidor de aplicaciones WSGI. Se encarga de ejecutar la aplicación Flask, recibir las peticiones HTTP, pasárselas a Flask y devolver la respuesta. Lo lancé con gunicorn --workers 2 --bind 127.0.0.1:8000 app:app.

3. ¿Por qué no se utiliza Flask directamente en producción?

Porque el servidor que incluye Flask es solo de desarrollo, atiende pocas peticiones a la vez, no gestiona bien la carga, no se recupera de fallos y no está pensado para recibir tráfico de Internet ni para ser seguro. Para producción se usa un servidor WSGI como Gunicorn.

4. ¿Qué ventajas proporciona Gunicorn?
Ejecuta varios workers en paralelo, atendiendo varias peticiones a la vez (en la práctica usé 2).
Es más estable y robusto que el servidor de desarrollo.
Reinicia automáticamente a los workers que fallan.
Es configurable (puerto, workers, logs de acceso y de error).
Se integra bien con Nginx y con systemd.

5. ¿Qué función realiza Nginx?

Nginx es el servidor web frontal. Recibe las peticiones de los clientes en el puerto 80 y las reenvía a Gunicorn (proxy_pass). Además puede servir contenido estático, gestionar HTTPS, equilibrar la carga y ocultar el backend. En mi práctica fue la única puerta de entrada.

6. ¿Qué es un Reverse Proxy?

Es un servidor intermedio que recibe las peticiones de los usuarios y las reenvía a uno o varios servidores internos, devolviendo luego la respuesta al cliente. El usuario solo conoce al proxy y nunca accede directamente a la aplicación. Aquí, Nginx es el reverse proxy y Gunicorn el backend.

7. ¿Qué ventajas aporta systemd?
Arranque automático de Gunicorn al iniciar el sistema (systemctl enable).
Reinicio ante fallos (Restart=always): comprobé que, al matar el proceso con pkill, volvía a levantarse solo.
Gestión uniforme del ciclo de vida: start, stop, restart, status.
Registro centralizado de logs con journalctl.
Permite ejecutarlo con un usuario concreto y en segundo plano, sin depender de una .terminal abierta.

8. Diferencias entre Tomcat y Gunicorn
Tomcat es de Lenguaje Java, usa Servlets/JSP, es un contenedor de servlets completo, su despliegue es copiar un fichero WAR, su puerti tipico es 8080, y es más pesado.
Gunicor es de lenguaje Python, su estándar es WSGI, es un servidor WSGI ligero, su despliegue es código y entorno virtual, su puerto típico es 8000, además que es más ligero y simple.
9. ¿Qué similitudes existen entre Nginx + Tomcat y Nginx + Gunicorn?
En ambos, Nginx es el frontal y reenvía con proxy_pass al backend.
El backend no se expone directamente a Internet.
Nginx puede encargarse de HTTPS y de los ficheros estáticos en ambos casos.
Los dos siguen la misma arquitectura multicapa: Cliente → Nginx → servidor de aplicaciones → aplicación.
Solo cambia el backend (puerto y tecnología), no la configuración básica del proxy.
10. ¿Qué mejoras podrían realizarse sobre la arquitectura implementada?
Activar HTTPS con certificados (es lo que se hace en la Práctica 04).
Usar Docker/Compose para empaquetar y reproducir el despliegue.
Aumentar workers o usar balanceo de carga con varias instancias.
Servir los ficheros estáticos directamente desde Nginx.
Configurar rotación y centralización de logs.
Añadir monitorización y límites de peticiones (rate limiting).
Ejecutar el servicio con un usuario sin privilegios y reforzar el firewall.
Automatizar el despliegue con scripts o CI/CD.