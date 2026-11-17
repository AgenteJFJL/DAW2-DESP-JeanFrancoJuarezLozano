SET NAMES utf8mb4;
USE practica05juarez;

INSERT INTO tareas (titulo, descripcion, completada) VALUES
('Crear la estructura del proyecto', 'Carpetas y ficheros de la práctica 05', TRUE),
('Escribir el docker-compose.yml', 'Servicios nginx, flask y mariadb', TRUE),
('Desplegar en AWS EC2', 'Transferir el zip y levantar los contenedores', FALSE),
('Comprobar la persistencia', 'Insertar datos y reiniciar los contenedores', FALSE),
('Hacer el backup y restaurarlo', 'Usar mariadb-dump', FALSE);