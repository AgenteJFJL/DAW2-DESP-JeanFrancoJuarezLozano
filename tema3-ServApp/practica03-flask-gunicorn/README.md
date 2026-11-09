¿# Práctica 03: Despliegue de Flask con Gunicorn y Nginx

**Alumno:** Jean Franco Juarez Lozano

## 1. Introducción
Breve descripción de la práctica y de qué se ha desplegado (2-4 líneas).

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
Ruta del fichero y explicación breve de `app.py`.
### 4.2 Gunicorn
Comando usado y significado de `--workers` y `--bind`.
### 4.3 Nginx
Fichero en `configuracion/` y explicación de `proxy_pass` y las cabeceras `proxy_set_header`.
### 4.4 systemd
Fichero `.service` en `configuracion/` y explicación de `ExecStart`, `Restart=always` y `WantedBy`.

## 5. Evidencias
| Evidencia | Captura |
|---|---|
| Flask funcionando | ![](capturas/01-flask.png) |
| Gunicorn ejecutándose | ![](capturas/02-gunicorn.png) |
| Configuración de Nginx | ![](capturas/03-nginx.png) |
| Flujo completo | ![](capturas/04-flujo.png) |
| Servicio systemd | ![](capturas/05-systemd.png) |
| Logs generados | ![](capturas/06-logs.png) |

## 6. Problemas encontrados
## 7. Soluciones aplicadas
| Problema | Causa | Solución |
|---|---|---|
| Ej.: 502 Bad Gateway | Gunicorn parado | `systemctl start flask-gunicorn` |

## 8. Conclusiones
Qué has aprendido y qué mejorarías.