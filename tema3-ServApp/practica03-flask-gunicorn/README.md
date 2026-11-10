¿# Práctica 03: Despliegue de Flask con Gunicorn y Nginx

**Alumno:** Jean Franco Juarez Lozano

## 1. Introducción
En esta práctica se despliega una aplicación web desarrollada con Flask, ejecutada mediante Gunicorn (servidor de aplicaciones WSGI) y publicada a través de Nginx, que actúa como reverse proxy. El servicio se gestiona con systemd para que arranque automáticamente y se recupere de fallos. El entorno de trabajo ha sido Ubuntu sobre WSL2.

- **Nginx** es el único componente de cara al cliente (puerto 80).
- **Gunicorn** escucha solo en `127.0.0.1:8000`, por lo que no es accesible directamente desde fuera de la máquina.
- **Flask** contiene la lógica de la aplicación y no se ejecuta con su servidor de desarrollo.

## 2. Arquitectura
Usuario → Nginx (:80) → Gunicorn (:8000) → Flask

Explica en pocas líneas el papel de cada capa y por qué Gunicorn solo escucha en 127.0.0.1.
(Opcional: diagrama en `capturas/arquitectura.png`.)

## 3. Despliegue realizado
Resumen paso a paso de lo que hiciste:
1. Creación de la estructura de carpetas.
2. Aplicación Flask.
3. Ejecución con Gunicorn, se ejecutó el comando (requiere terminal de ubuntu instalado):
sudo apt update && sudo apt install -y python3-venv nginx
sudo mkdir -p /opt/practica03 && sudo chown $USER:$USER /opt/practica03
cp -r tema3-ServApp/practica03-flask-gunicorn/aplicacion /opt/practica03/
cd /opt/practica03
python3 -m venv venv
./venv/bin/pip install -r aplicacion/requirements.txt
cd aplicacion
../venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app

comprobamos con ./venv/bin/gunicorn --version  (sale gunicorn 26.2.0)

con ../venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app  iniciamos, y ahora tenemos que comprobar en otra temrinal de ubuntu: curl http://127.0.0.1:8000


4. Configuración de Nginx como reverse proxy.
5. Verificación del flujo completo.
6. Servicio systemd.
7. Verificación de persistencia.

## 4. Configuración empleada
### 4.1 Aplicación Flask
Fichero: `aplicacion/app.py`. Define la ruta `/`, que muestra una página de bienvenida con el nombre del alumno, el nombre de la práctica y la fecha y hora actuales.

### 4.2 Gunicorn

```bash
gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
```
- `--workers 2`: dos procesos que atienden peticiones en paralelo.
- `--bind 127.0.0.1:8000`: escucha solo en local, puerto 8000.
- `app:app`: módulo `app.py` y la variable Flask `app`.

### 4.3 Nginx

Fichero: `configuracion/nginx-flask` (copia de `/etc/nginx/sites-available/flask`).
- `listen 80`: recibe las peticiones HTTP.
- `proxy_pass http://127.0.0.1:8000`: las reenvía a Gunicorn.
- `proxy_set_header ...`: transmite al backend el host, la IP real del cliente y el protocolo original.

### 4.4 systemd

Fichero: `configuracion/flask-gunicorn.service` (copia de `/etc/systemd/system/`).
- `ExecStart`: comando que lanza Gunicorn con el Python del entorno virtual.
- `Restart=always` y `RestartSec=3`: reinicia el servicio 3 segundos después de cualquier caída.
- `WantedBy=multi-user.target`: permite arrancarlo automáticamente con el sistema (`systemctl enable`).
- `--access-logfile -` y `--error-logfile -`: envían los logs de Gunicorn a `journalctl`.

## 5. Verificaciones realizadas

| Prueba | Comando | Resultado |
|---|---|---|
| Gunicorn local | `curl http://127.0.0.1:8000` | HTML de la aplicación |
| Gunicorn escuchando | `ss -tlnp \| grep 8000` | `127.0.0.1:8000` con gunicorn |
| Flujo por Nginx | `curl -I http://localhost` | `HTTP/1.1 200 OK` |
| Estado del servicio | `systemctl status flask-gunicorn` | `active (running)` |
| Reinicio ante fallo | `sudo pkill -9 -f gunicorn` | El servicio vuelve a estar activo en unos 3 s |
| Persistencia | `wsl --shutdown` y volver a abrir | La aplicación responde sin arranque manual |
| Error 502 | Parar el servicio y pedir la web | `502 Bad Gateway` |

## 6. Capturas
 Se encuentran en la carpeta capturas, son evidencias del funcionamiento y estructura.
## 7. Análisis de logs

### 7.1 Logs de Gunicorn (`journalctl -u flask-gunicorn -f`)

| Línea del log | Qué significa |
|---|---|
| `Started flask-gunicorn.service - Gunicorn - Flask Practica03.` | systemd ha arrancado el servicio. |
| `Starting gunicorn 26.2.0` | Inicio de la aplicación: arranca el proceso maestro de Gunicorn. |
| `Listening at: http://127.0.0.1:8000` | Gunicorn escucha solo en local, puerto 8000, por lo que no es accesible desde fuera. |
| `Using worker: sync` | Tipo de worker usado (síncrono, el predeterminado). |
| `Booting worker with pid: 316` y `pid: 318` | Se inician los 2 workers configurados con `--workers 2`. |
| `Control socket listening at /home/juarez/.gunicorn/gunicorn.ctl` | Socket de control de Gunicorn, que permite administrarlo en ejecución. |
| `127.0.0.1 - - [09/Nov/2026:17:00:42 -0500] "HEAD / HTTP/1.0" 200 0 "-" "curl/8.18.0"` | Petición procesada: procede de 127.0.0.1, es un `HEAD /`, devolvió `200` y la hizo `curl`. |
| `worker ... was sent SIGTERM` (líneas anteriores) | Aviso de parada de un worker al reiniciar o parar el servicio con systemctl. |

Además, la petición figura como `HTTP/1.0` porque Nginx se comunica con el backend en HTTP/1.0 por defecto, y la IP es `127.0.0.1` porque la petición llega desde Nginx, no desde el cliente final. No aparecen errores durante el arranque.

### 7.2 Logs de Nginx

**Accesos** (`/var/log/nginx/access.log`): cada línea recoge la IP del cliente, la fecha, la petición, el código de respuesta, los bytes enviados, el origen (referer) y el navegador (user agent).

| Petición | Código | Interpretación |
|---|---|---|
| `HEAD / HTTP/1.1` (curl, 16:35:53 y 17:00:42) | 200 | Nginx reenvió la petición a Gunicorn y la aplicación respondió. |
| `GET / HTTP/1.1` (Chrome, 16:36:02 y 16:36:17) | 200 | La página se sirvió correctamente en el navegador. |
| `GET /favicon.ico` (16:36:02) | 404 | El navegador pide el icono de la pestaña y la aplicación no lo tiene. No es un fallo. |
| `HEAD /` y `GET /` (07:40:59 y 07:41:17) | **502** | Prueba con Gunicorn parado: Nginx no pudo contactar con el backend. |

Todas las peticiones muestran la IP `127.0.0.1` porque las hice desde la propia máquina. Se identifican los clientes `curl/8.18.0` y Chrome sobre Windows.

**Errores** (`/var/log/nginx/error.log`):

```text
connect() failed (111: Connection refused) while connecting to upstream,
upstream: "http://127.0.0.1:8000/"
```

Este error aparece junto a los 502 del access.log. Indica que Nginx funcionaba, pero nadie escuchaba en el puerto 8000. Esto demuestra que Nginx es solo un intermediario: si el servidor de aplicaciones cae, el usuario recibe un 502 Bad Gateway.

### 7.3 Relación entre los tres logs
Una misma petición deja rastro en ambos lados: la `HEAD /` de las 17:00:42 aparece en el access.log de Nginx con un 200 y en el log de Gunicorn con la petición procesada por el worker 316. Esto confirma que el flujo completo Usuario → Nginx → Gunicorn → Flask funciona.

## 8. Problemas encontrados y soluciones aplicadas

| Problema | Causa | Solución |
|---|---|---|
| `cp: cannot stat 'E:\jf\...'` | Usé una ruta de Windows dentro de WSL (Linux), que no entiende `E:\` ni las barras invertidas. | En WSL las unidades de Windows se montan en `/mnt/`, así que `E:\` es `/mnt/e/`. Usé barras `/` y rutas entre comillas por los espacios y la `ñ`. |
| `nano` abría `app.py` y `requirements.txt` vacíos | Los ficheros se habían creado vacíos y nadie les había añadido contenido. | Pegué el código en el repositorio con `nano`, lo comprobé con `cat` y volví a copiar los ficheros a `/opt/practica03/aplicacion/`. |
| 502 Bad Gateway al acceder por Nginx | Gunicorn estaba parado (provocado a propósito en la Tarea 9 para analizar los logs). El `error.log` mostraba `connect() failed (111: Connection refused) while connecting to upstream`. | Arrancar el servicio con `sudo systemctl start flask-gunicorn` y comprobar con `systemctl status flask-gunicorn` que estaba `active (running)`. |
| `404` en `/favicon.ico` en el access.log de Nginx | El navegador pide automáticamente el icono de la pestaña y la aplicación no tiene ninguno. | No es un fallo real. Se puede ignorar, o añadir un favicon a la aplicación si se quiere evitar el 404. |