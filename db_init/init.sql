-- 1. Asegurar que la BBDD existe
CREATE DATABASE IF NOT EXISTS db_agencia;
USE db_agencia;

-- 2. Tabla USUARIOS (Actualizada con nombre_agencia)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    tipo ENUM('cliente', 'admin', 'agencia') NOT NULL DEFAULT 'cliente',
    nombre_agencia VARCHAR(150),
    totp_secret VARCHAR(32)
);

-- 3. Tabla RESERVAS (¡Esta tabla faltaba!)
CREATE TABLE IF NOT EXISTS reservas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    tipo_servicio VARCHAR(50) NOT NULL,
    id_servicio_externo INT NOT NULL,
    detalles_reserva TEXT,
    fecha_reserva DATETIME,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- 4. Usuario de Replicación (Para facilitar la conexión del esclavo)
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED WITH mysql_native_password BY 'password_replica';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';
FLUSH PRIVILEGES;

-- 5. Usuario de la Aplicación
-- Revocamos todo para empezar limpio
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'user_agencia'@'%';
-- Asignamos SOLO CRUD
GRANT SELECT, INSERT, UPDATE, DELETE ON db_agencia.* TO 'user_agencia'@'%';
-- Aplicar cambios
FLUSH PRIVILEGES;