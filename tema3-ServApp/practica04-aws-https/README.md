# Práctica 04: Despliegue en AWS EC2 con HTTPS de una aplicación Flask con Gunicorn y Nginx

**Alumno:** Jean Franco Juárez Lozano
**Ciclo:** DAW - Despliegue de Aplicaciones Web
**Fecha:** 17/11/2026
**IP pública de la instancia:** «3.87.201.82»

## 1. Introducción
En esta práctica se despliega en Internet una aplicación web Flask utilizando una instancia AWS EC2 con Ubuntu. La preparación inicial del servidor se automatiza con AWS User Data (`user-data.sh`). Flask se ejecuta con Gunicorn dentro de un contenedor Docker y se publica a través de Nginx, que actúa como reverse proxy y gestiona HTTPS con un certificado SSL/TLS autofirmado.

## 2. Objetivos
- Crear una instancia EC2 y configurar su grupo de seguridad.
- Automatizar la preparación del servidor con User Data.
- Conectarse mediante SSH y transferir ficheros con `scp`.
- Empaquetar y ejecutar Flask con Gunicorn en un contenedor Docker.
- Configurar Nginx como reverse proxy.
- Implementar HTTPS con SSL/TLS y redirigir HTTP a HTTPS.
- Analizar los logs de Nginx y Gunicorn.
- Documentar el despliegue.

## 3. Arquitectura utilizada

```text
Internet
   │  HTTPS (443)  /  HTTP (80) → redirige a HTTPS
   ▼
Nginx (instalado en la EC2, reverse proxy, termina SSL)
   │  HTTP interno, localhost:5000
   ▼
Contenedor Docker "flask-app"
   └─ Gunicorn (2 workers) → Flask (app.py)
```

Diagrama: ![Arquitectura](docs/arquitectura.png)

- **Nginx** es el punto de entrada: recibe las conexiones, descifra TLS y reenvía el tráfico en HTTP a Gunicorn.
- **Gunicorn + Flask** se ejecutan en un contenedor Docker que publica el puerto 5000.
- El Security Group solo permite los puertos 22, 80 y 443, por lo que el puerto 5000 no es accesible desde Internet.

## 4. AWS EC2

| Parámetro | Valor |
|---|---|
| Nombre | `practica04-flask` |
| Sistema operativo | Ubuntu Server 24.04 LTS |
| Tipo de instancia | `t2.micro` |
| Par de claves | `practica04.pem` |
| IP pública | «COMPLETAR» |

**Security Group (reglas de entrada):**

| Tipo | Puerto | Origen | Motivo |
|---|---|---|---|
| SSH | 22 | Mi IP | Administración restringida a mi IP |
| HTTP | 80 | 0.0.0.0/0 | Web pública (redirige a HTTPS) |
| HTTPS | 443 | 0.0.0.0/0 | Web pública cifrada |

Se abrió temporalmente el puerto 5000 (origen: Mi IP) únicamente para comprobar el acceso directo a Flask (Tarea 11). Después se eliminó la regla, ya que en producción solo Nginx debe ser accesible.

La instancia es la máquina virtual donde se ejecuta todo el sistema: aporta recursos, IP pública y control total del sistema operativo.

## 5. User Data
AWS ejecuta este script como root durante el primer arranque de la instancia (`configuracion/user-data.sh`):

```bash
#!/bin/bash
apt update -y
apt install -y docker.io git curl
systemctl enable docker
systemctl start docker
mkdir -p /opt/practica04
```

| Comando | Función |
|---|---|
| `apt update -y` | Actualiza el índice de paquetes |
| `apt install -y docker.io git curl` | Instala el motor de contenedores, Git y curl |
| `systemctl enable docker` | Docker arranca automáticamente con el sistema |
| `systemctl start docker` | Inicia Docker ahora |
| `mkdir -p /opt/practica04` | Crea la carpeta de trabajo |

**Ventajas de la automatización:** el servidor queda listo sin intervención manual, el proceso es reproducible, se reducen los errores humanos y se ahorra tiempo al crear nuevas instancias. La explicación detallada está en `configuracion/instrucciones.txt`.

## 6. Flask
`aplicacion/app.py` define la ruta `/`, que muestra una página con el nombre del alumno, el nombre de la práctica y la fecha y hora actuales.

Se empaqueta con este `Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app:app"]
```

Los ficheros se copiaron a `/opt/practica04` con `scp`. La imagen se construyó con `sudo docker build -t flask-app .` y el contenedor se lanzó con:

```bash
sudo docker run -d -p 5000:5000 --name flask-app flask-app
```

## 7. Gunicorn
Gunicorn es un servidor de aplicaciones WSGI. Ejecuta Flask con 2 workers (`--workers 2`), escuchando en `0.0.0.0:5000` dentro del contenedor (`--bind`). Es necesario usar `0.0.0.0` y no `127.0.0.1` porque, de lo contrario, no sería alcanzable desde fuera del contenedor.

Sustituye al servidor de desarrollo de Flask, que no es adecuado para producción. Con `sudo docker logs flask-app` se comprobó el arranque: `Starting gunicorn`, `Listening at: http://0.0.0.0:5000` y los `Booting worker`.

## 8. Nginx
Se instaló con `sudo apt install nginx -y` y se configuró como reverse proxy en `/etc/nginx/sites-available/default` (copia en `configuracion/nginx.conf`).

Versión inicial en HTTP (Tarea 13):

```nginx
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

| Directiva | Función |
|---|---|
| `listen 80 default_server` | Escucha en el puerto 80 |
| `server_name _` | Acepta cualquier host (por ejemplo, la IP) |
| `proxy_pass http://localhost:5000` | Reenvía las peticiones a Gunicorn |
| `proxy_set_header ...` | Transmite al backend el host, la IP real del cliente y el protocolo original |

Tras validar con `sudo nginx -t` y reiniciar el servicio, la aplicación quedó accesible en `http://IP_PUBLICA` sin indicar el puerto.

## 9. HTTPS

**Certificado autofirmado** (generado en la EC2):

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout clave.key -out certificado.crt \
  -subj "/C=ES/O=Practica04/CN=IP_PUBLICA" \
  -addext "subjectAltName=IP:IP_PUBLICA"
```

Los ficheros se copiaron a `/etc/nginx/ssl/` (con la clave con permisos `600`) y a la carpeta `configuracion/` del repositorio. Al ser un certificado de prueba y un repositorio privado, subir la clave es aceptable; con un certificado real nunca se haría.

**Configuración final de Nginx:**

```nginx
server {
    listen 80 default_server;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl default_server;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/certificado.crt;
    ssl_certificate_key /etc/nginx/ssl/clave.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

| Directiva | Función |
|---|---|
| `return 301 https://...` | Redirige todo el tráfico HTTP a HTTPS |
| `listen 443 ssl` | Activa TLS en el puerto 443 |
| `ssl_certificate` / `ssl_certificate_key` | Certificado público y clave privada |
| `ssl_protocols TLSv1.2 TLSv1.3` | Deshabilita TLS 1.0 y 1.1 |
| `proxy_pass` | Tras descifrar, reenvía en HTTP plano a Flask (*terminación SSL*) |

**Ventajas de SSL/TLS:** confidencialidad (cifra la comunicación), integridad (los datos no se alteran en tránsito) y autenticación del servidor. Como el certificado es autofirmado, el navegador muestra una advertencia de seguridad; con un dominio y una entidad como Let's Encrypt sería de confianza.

**Comprobaciones realizadas:**
- `https://IP_PUBLICA` muestra la aplicación (tras aceptar la advertencia del certificado).
- `http://IP_PUBLICA` redirige automáticamente a `https://`.

## 10. Evidencias obtenidas

| Nº | Descripción | Captura |
|---|---|---|
| 01 | Laboratorio iniciado | ![](capturas/01-lab-iniciado.png) |
| 02 | Panel de EC2 | ![](capturas/02-panel-ec2.png) |
| 03 | Par de claves | ![](capturas/03-keypair.png) |
| 04 | User Data configurado | ![](capturas/04-user-data-configurado.png) |
| 05 | Instancia en estado Running | ![](capturas/05-instancia-running.png) |
| 06 | Security Group | ![](capturas/06-security-group.png) |
| 07 | IP pública | ![](capturas/07-ip-publica.png) |
| 08 | Conexión SSH | ![](capturas/08-ssh-conectado.png) |
| 09 | Docker instalado automáticamente | ![](capturas/09-docker-instalado-automaticamente.png) |
| 10 | Aplicación subida | ![](capturas/10-aplicacion-subida.png) |
| 11 | Build de la imagen Docker | ![](capturas/11-build-docker.png) |
| 12 | Contenedor Flask en ejecución | ![](capturas/12-contenedor-flask.png) |
| 13 | Gunicorn operativo | ![](capturas/13-gunicorn-operativo.png) |
| 14 | Flask accedido directamente (:5000) | ![](capturas/14-flask-directo.png) |
| 15 | Nginx instalado | ![](capturas/15-nginx-instalado.png) |
| 16 | Reverse proxy configurado | ![](capturas/16-reverse-proxy.png) |
| 17 | Flask a través de Nginx | ![](capturas/17-nginx-flask.png) |
| 18 | Certificados generados | ![](capturas/18-certificados-generados.png) |
| 19 | Configuración HTTPS | ![](capturas/19-configuracion-https.png) |
| 20 | HTTPS funcionando | ![](capturas/20-https-funcionando.png) |
| 21 | Logs de Nginx | ![](capturas/21-logs-nginx.png) |
| 22 | Logs de Gunicorn | ![](capturas/22-logs-gunicorn.png) |

### Análisis de logs
- **Nginx** (`/var/log/nginx/access.log`): cada línea registra la IP del cliente, la fecha, la petición, el código de respuesta (`301` en las peticiones HTTP redirigidas, `200` en las servidas por HTTPS), los bytes enviados y el navegador o herramienta (`curl`, Chrome...).
- **Gunicorn** (`sudo docker logs flask-app`): muestra el inicio (`Starting gunicorn`, `Listening at`) y los dos `Booting worker`. 

## 11. Problemas encontrados

1. **`http://IP:5000` no cargaba en el navegador del ordenador del centro**, aunque `curl localhost:5000` desde la EC2 sí devolvía la página.
2. **`scp` fallaba** con `Identity file ... not accessible` y `Permission denied (publickey)` al copiar los certificados.

## 12. Soluciones aplicadas

| Problema | Causa | Solución |
|---|---|---|
| El puerto 5000 no cargaba desde el PC del centro | La red del centro educativo bloquea el tráfico saliente a puertos no estándar. El despliegue era correcto, ya que `curl localhost:5000` funcionaba | Se comprobó el acceso desde otra red (móvil con datos), donde sí funcionó, y se verificó el Security Group |
| `scp`: `Identity file not accessible` y `Permission denied (publickey)` | Ruta relativa errónea al `.pem` (apuntaba a una carpeta inexistente) y destino mal indicado | Usar la ruta correcta `~/Escritorio/pem-flask04/practica04.pem` y `.` como destino, copiando cada fichero por separado |
| La IP pública cambia en AWS Academy | Se asigna una IP dinámica al reiniciar el laboratorio | Anotar la IP de cada sesión y regenerar el certificado si cambia |

## 13. Conclusiones
Esta práctica me ha permitido desplegar de extremo a extremo una aplicación web en la nube: desde la creación de la instancia y su grupo de seguridad, hasta la automatización con User Data, el uso de contenedores Docker, la configuración de Nginx como reverse proxy y la protección de las comunicaciones con HTTPS. He comprendido por qué Flask no se expone directamente: Gunicorn lo ejecuta de forma robusta y Nginx lo protege y gestiona el cifrado, de modo que el backend no es accesible desde Internet.

**Mejoras posibles:** usar un dominio con un certificado válido de Let's Encrypt, definir los servicios con Docker Compose, asignar una Elastic IP para que la dirección no cambie, publicar Flask solo en local (`-p 127.0.0.1:5000:5000`) y activar el registro de accesos de Gunicorn.