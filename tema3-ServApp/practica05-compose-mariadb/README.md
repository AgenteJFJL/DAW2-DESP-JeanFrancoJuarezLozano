# Práctica 05: Docker Compose, MariaDB, Persistencia y Copias de Seguridad

**Alumno:** Jean Franco Juárez Lozano
**Ciclo:** DAW - Despliegue de Aplicaciones Web
**Fecha:** 17/11/2026
**IP pública de la instancia:** «44.204.184.65 IP final de la EC2»

## 1. Introducción
En esta práctica se evoluciona el despliegue de la práctica anterior hacia una arquitectura multi-contenedor coordinada con Docker Compose, reutilizando la misma instancia AWS EC2. La solución está formada por tres contenedores: Nginx (reverse proxy con HTTPS), Flask (aplicación web con Gunicorn) y MariaDB (base de datos con almacenamiento persistente). Además se comprueba la persistencia de los datos y se realizan una copia de seguridad y su restauración tras una pérdida de datos simulada.

## 2. Arquitectura

```text
Usuario
   │  HTTPS (443)  /  HTTP (80) → redirige a HTTPS
   ▼
AWS EC2 (Ubuntu) ── Docker Compose ── red_interna (bridge)
   │
   ├── nginx    (única publicación: 80 y 443, termina SSL)
   │      │  HTTP interno, flask:5000
   │      ▼
   ├── flask    (Gunicorn + Flask, solo expone 5000 a la red interna)
   │      │  SQL, mariadb:3306
   │      ▼
   └── mariadb  (base de datos practica05juarez)
          │
          ▼
   Volumen persistente: mariadb_data → /var/lib/mysql
```

Diagrama: ![Arquitectura](docs/arquitectura-practica05.png)

- Solo **Nginx** publica puertos al exterior (80 y 443).
- **Flask** y **MariaDB** solo son accesibles desde la red Docker interna, por lo que no están expuestos a Internet.
- Los contenedores se encuentran por el nombre del servicio (`flask`, `mariadb`) gracias al DNS interno de Docker.

## 3. Docker Compose
Todo el despliegue se define en `docker-compose.yml`, que se levanta con `docker compose up -d`.

| Elemento | Función |
|---|---|
| Servicio `mariadb` | Imagen `mariadb:11`. Crea la base de datos y el usuario a partir de variables de entorno y ejecuta los scripts SQL de inicialización |
| Servicio `flask` | Se construye desde `./app`. Espera a que MariaDB esté sana (`depends_on` con `service_healthy`) |
| Servicio `nginx` | Imagen `nginx:stable`. Publica los puertos 80 y 443 y monta la configuración y los certificados |
| Red `red_interna` | Red bridge privada que comunica los tres contenedores |
| Volumen `mariadb_data` | Almacenamiento persistente de MariaDB |
| `healthcheck` | Comprueba que MariaDB está lista antes de arrancar Flask |
| `restart: unless-stopped` | Los contenedores se reinician solos tras un fallo o reinicio de la máquina |

Los scripts `schema.sql` y `datos.sql` se montan como `01-schema.sql` y `02-datos.sql` en `/docker-entrypoint-initdb.d/`. MariaDB los ejecuta por orden alfabético y solo cuando el volumen está vacío; con los nombres originales, `datos.sql` se ejecutaría antes que `schema.sql` y fallaría.

Se usa la versión actual de Compose (`docker compose`, con espacio), equivalente a `docker-compose` del enunciado.

> Nota de seguridad: por simplicidad las contraseñas están escritas en el `docker-compose.yml`. En un entorno real irían en un fichero `.env` o en *secrets*.

## 4. Flask
`app/app.py` se conecta a MariaDB con **PyMySQL**, consulta la tabla `tareas` y muestra los registros en una tabla HTML, junto con el nombre del alumno. Los parámetros de conexión (host, usuario, contraseña y base de datos) se leen de variables de entorno definidas en el Compose. Si la base de datos no está disponible, la aplicación muestra un mensaje de error.

Se eligió PyMySQL en lugar del paquete oficial `mariadb` porque es 100 % Python y no requiere compilar librerías C al construir la imagen.

`app/requirements.txt`: `flask`, `gunicorn`, `pymysql`.
`app/Dockerfile`: imagen `python:3.12-slim`, instala las dependencias y arranca Gunicorn con 2 workers en `0.0.0.0:5000`, con el registro de accesos activado (`--access-logfile -`).

## 5. MariaDB
- Imagen `mariadb:11`.
- Base de datos: `practica05juarez`, con la tabla `tareas` (`id`, `titulo`, `descripcion`, `completada`, `fecha_creacion`), definida en `database/schema.sql`.
- Datos de prueba: 5 registros en `database/datos.sql`.
- Usuario de la aplicación: `flaskuser`, con permisos sobre esa base de datos. La aplicación no usa `root`.
- Acceso al cliente:

```bash
sudo docker exec -it mariadb bash
mariadb -u root -p
USE practica05juarez;
```

## 6. Docker Volume
El volumen con nombre `mariadb_data` está montado en `/var/lib/mysql`, que es donde MariaDB guarda los datos. Lo gestiona Docker y vive fuera del contenedor.

```bash
sudo docker volume ls
```

Aparece como `«practica05_mariadb_data»`. Docker antepone el nombre del proyecto (la carpeta `practica05`) al nombre del volumen.

## 7. Persistencia
Procedimiento seguido para comprobarla:

1. Se insertaron 3 tareas nuevas con `INSERT INTO tareas ...` desde el cliente `mariadb` (en total, 8 registros).
2. Se apagaron los contenedores con `sudo docker compose down` y se volvieron a levantar con `sudo docker compose up -d`.
3. Al recargar la web, las 8 tareas seguían presentes.

Los datos sobreviven porque están en el volumen y no en el sistema de ficheros del contenedor, que es efímero. Los scripts de inicialización no se ejecutaron de nuevo, así que no hubo duplicados.

Se evitó usar `docker compose down -v`, ya que la opción `-v` elimina los volúmenes y destruiría los datos.

## 8. Backup
Se generó con `mariadb-dump` (en `mariadb:11` ya no existe `mysqldump`):

```bash
sudo docker exec mariadb sh -c 'mariadb-dump -u root -p"$MARIADB_ROOT_PASSWORD" --databases practica05juarez' > backups/backup.sql
```

- `--databases` incluye `CREATE DATABASE` y `USE` en el volcado, de modo que se puede restaurar aunque la base de datos ya no exista.
- `"$MARIADB_ROOT_PASSWORD"` es una variable de entorno del contenedor, así que la contraseña no aparece en el comando.
- La redirección `>` la ejecuta el shell de la EC2, por lo que el fichero queda en `/opt/practica05/backups/`. Después se descargó al repositorio con `scp`.

Resultado: `backups/backup.sql`, de «4, con `ls -l backups/`», con las sentencias `CREATE TABLE` e `INSERT INTO`.

## 9. Restore
**Pérdida de datos simulada:**

```sql
DROP DATABASE practica05juarez;
```

Tras ejecutarla, la web mostró «Error de base de datos».

**Restauración:**

```bash
sudo docker exec -i mariadb sh -c 'mariadb -u root -p"$MARIADB_ROOT_PASSWORD"' < backups/backup.sql
```

Se usa `-i` (y no `-it`) porque no hay terminal interactiva: el contenido entra por la redirección `<`.

**Verificación:** se comprobaron las tablas y los registros con `SHOW TABLES; SELECT * FROM tareas;` y la web volvió a mostrar las 8 tareas sin reiniciar ningún contenedor. Los permisos de `flaskuser` se conservaron.

## 10. Evidencias obtenidas

| Nº | Descripción | Captura |
|---|---|---|
| 01 | Estructura del proyecto | ![](capturas/01-estructura-proyecto.png) |
| 02 | `schema.sql` | ![](capturas/02-schema-sql.png) |
| 03 | `datos.sql` | ![](capturas/03-datos-sql.png) |
| 04 | `requirements.txt` | ![](capturas/04-requirements.png) |
| 05 | `app.py` | ![](capturas/05-app-py.png) |
| 06 | `Dockerfile` | ![](capturas/06-dockerfile.png) |
| 07 | `nginx.conf` | ![](capturas/07-nginx.png) |
| 08 | `docker-compose.yml` | ![](capturas/08-compose-yml.png) |
| 09 | Transferencia a la EC2 con `scp` | ![](capturas/09-transferencia-ec2.png) |
| 10 | ZIP transferido | ![](capturas/10-zip-transferido.png) |
| 11 | Transferencia verificada (descompresión) | ![](capturas/11-transferencia-verificada.png) |
| 12 | Construcción de las imágenes | ![](capturas/12-compose-up.png) |
| 13 | `docker compose ps` | ![](capturas/13-compose-ps.png) |
| 14 | Aplicación funcionando | ![](capturas/14-aplicacion-funcionando.png) |
| 15 | Acceso a MariaDB | ![](capturas/15-acceso-mariadb.png) |
| 16 | Inserción de registros | ![](capturas/16-insert-mariadb.png) |
| 17 | Volúmenes | ![](capturas/17-volumenes.png) |
| 18 | Backup generado | ![](capturas/18-backup-generado.png) |
| 19 | Borrado de datos | ![](capturas/19-borrar-datos.png) |
| 20 | Restauración | ![](capturas/20-restaurar.png) |
| 21 | Datos restaurados | ![](capturas/21-datos-restaurados.png) |

## 11. Análisis de la arquitectura (Tarea 14)

### Docker Compose: ¿qué problema resuelve?
Resuelve la gestión de aplicaciones formadas por varios contenedores. Sin Compose habría que lanzar cada contenedor con un `docker run` largo y crear a mano las redes, los volúmenes y el orden de arranque. Con un único `docker-compose.yml` todo queda definido de forma declarativa y reproducible, y se levanta con `up` y se apaga con `down`.

### Flask: ¿qué función desempeña?
Contiene la lógica de la aplicación: se conecta a MariaDB, consulta la tabla `tareas` y genera la página HTML que ve el usuario. Se ejecuta con Gunicorn, que es el servidor adecuado para producción.

### MariaDB: ¿qué función desempeña?
Es el sistema gestor de bases de datos relacionales. Almacena los datos de forma estructurada y permite consultarlos y modificarlos con SQL. Es el backend de datos de Flask.

### Docker Network: ¿por qué es necesaria?
Permite que los contenedores se comuniquen entre sí de forma privada y se localicen por el nombre del servicio (`flask`, `mariadb`) sin conocer sus IP. También aísla a Flask y MariaDB de Internet, ya que solo Nginx publica puertos.

### Docker Volume: ¿por qué es necesario?
El sistema de ficheros de un contenedor es efímero: se pierde al eliminarlo. El volumen guarda `/var/lib/mysql` fuera del contenedor, de modo que los datos sobreviven a `down`, a reinicios y a actualizaciones de la imagen.

### Backup: ¿por qué es importante?
Protege frente a borrados accidentales, errores de la aplicación, corrupción de datos o fallos del servidor. El volumen aporta persistencia, pero **no es una copia de seguridad**: si se borra la base de datos o el volumen, la información desaparece.

### Restore: ¿por qué es importante?
Una copia que nunca se ha restaurado no garantiza nada. Restaurar permite recuperar el servicio tras una pérdida de datos y comprobar que el backup es válido y completo.

## 12. Problemas encontrados

1. Al crear los ficheros a mano en el repositorio, se pegó la palabra `EOF` dentro de ellos y dio errores.
2. A veces me olvidaba de usar el sudo para los comandos, y tenía que volver a hacerlos.

## 13. Soluciones aplicadas

| Problema | Causa | Solución |
|---|---|---|
| Error al pegar el contenido en los ficheros | `EOF` es solo el marcador del comando `cat > fichero <<'EOF'` de la terminal, no parte del contenido | Pegar únicamente el contenido entre el comando y el marcador final, y comprobar con `grep -rn "EOF" .` que no quedaba ninguno |

## 14. Conclusiones
Esta práctica me ha permitido pasar de un contenedor aislado a una arquitectura completa de tres capas coordinada con Docker Compose. He comprobado que la red interna permite comunicar los servicios sin exponerlos a Internet, que el volumen garantiza la persistencia de MariaDB y que, aun así, la persistencia no sustituye a las copias de seguridad: simulé una pérdida total de la base de datos y la recuperé con `backup.sql`.

**Mejoras posibles:** guardar las contraseñas en un `.env` o en *secrets*, automatizar los backups con `cron` y almacenarlos fuera de la EC2 (por ejemplo, en S3), usar un dominio con Let's Encrypt, añadir una Elastic IP y definir límites de recursos en el Compose.