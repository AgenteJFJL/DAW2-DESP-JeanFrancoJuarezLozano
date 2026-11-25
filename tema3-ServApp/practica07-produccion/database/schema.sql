-- Santuario de Espíritus · esquema de la base de datos (MariaDB)
CREATE DATABASE IF NOT EXISTS practica07jfjl04
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE practica07jfjl04;

-- Las 6 rarezas y el peso (%) de cada una. La probabilidad de cada espíritu
-- se calcula en la aplicación: peso de su rareza / nº de espíritus de esa rareza.
CREATE TABLE IF NOT EXISTS rarezas (
  id     TINYINT UNSIGNED PRIMARY KEY,
  nombre VARCHAR(20)  NOT NULL,
  peso   DECIMAL(5,2) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS familias (
  id     INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(40) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS espiritus (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  nombre      VARCHAR(80)  NOT NULL,
  subtitulo   VARCHAR(100) NOT NULL,
  descripcion TEXT         NOT NULL,
  rareza      TINYINT UNSIGNED NOT NULL,
  familia_id  INT          NOT NULL,
  variante_de INT          NULL,
  imagen      VARCHAR(120) NOT NULL,
  creado      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_rareza (rareza),
  CONSTRAINT fk_esp_rareza  FOREIGN KEY (rareza)      REFERENCES rarezas(id),
  CONSTRAINT fk_esp_familia FOREIGN KEY (familia_id)  REFERENCES familias(id),
  CONSTRAINT fk_esp_base    FOREIGN KEY (variante_de) REFERENCES espiritus(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usuarios (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  usuario       VARCHAR(40)  NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  es_admin      BOOLEAN      NOT NULL DEFAULT FALSE,
  invocaciones  INT          NOT NULL DEFAULT 0,
  racha         INT          NOT NULL DEFAULT 0,   -- invocaciones seguidas sin Raro o superior
  creado        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Colección de cada usuario: un registro por espíritu y la cantidad de copias.
CREATE TABLE IF NOT EXISTS colecciones (
  usuario_id  INT NOT NULL,
  espiritu_id INT NOT NULL,
  cantidad    INT NOT NULL DEFAULT 1,
  primera_vez TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (usuario_id, espiritu_id),
  CONSTRAINT fk_col_usuario  FOREIGN KEY (usuario_id)  REFERENCES usuarios(id)  ON DELETE CASCADE,
  CONSTRAINT fk_col_espiritu FOREIGN KEY (espiritu_id) REFERENCES espiritus(id) ON DELETE CASCADE
) ENGINE=InnoDB;
