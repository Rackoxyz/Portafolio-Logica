CREATE DATABASE IF NOT EXISTS sistema_mantenimiento
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE sistema_mantenimiento;

SET FOREIGN_KEY_CHECKS=0;

CREATE TABLE IF NOT EXISTS UBICACIONES (
    ubicacion_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_ubicacion VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS TIPOS_MANTENIMIENTO (
    tipo_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_tipo VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ESTADOS_KANBAN (
    estado_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_estado VARCHAR(50) NOT NULL UNIQUE,
    orden INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS EQUIPOS (
    equipo_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_equipo VARCHAR(255) NOT NULL,
    marca VARCHAR(100) NOT NULL,
    serie VARCHAR(100) NOT NULL,
    ubicacion_id INT NOT NULL,
    tipo_mantenimiento_pred_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY ux_equipo_serie (serie),
    INDEX idx_equipo_ubicacion (ubicacion_id),
    INDEX idx_equipo_marca (marca),
    CONSTRAINT fk_equipos_ubicacion FOREIGN KEY (ubicacion_id)
        REFERENCES UBICACIONES(ubicacion_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_equipos_tipo_pred FOREIGN KEY (tipo_mantenimiento_pred_id)
        REFERENCES TIPOS_MANTENIMIENTO(tipo_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS MANTENIMIENTOS (
    folio_id INT AUTO_INCREMENT PRIMARY KEY,
    equipo_id INT NOT NULL,
    fecha_ingreso DATETIME NOT NULL,
    fecha_programada DATETIME NOT NULL,
    descripcion_servicio VARCHAR(255) NOT NULL,
    avance_porcentaje DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    costo_inicial DECIMAL(10,2) NOT NULL,
    costo_final DECIMAL(10,2) NULL,
    fecha_salida DATETIME NULL,
    observacion TEXT NULL,
    materiales_requeridos TEXT NULL,
    estado_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (avance_porcentaje >= 0 AND avance_porcentaje <= 100),
    CHECK (fecha_programada >= fecha_ingreso),
    INDEX idx_mant_equipo (equipo_id),
    INDEX idx_mant_estado (estado_id),
    CONSTRAINT fk_mant_equipo FOREIGN KEY (equipo_id)
        REFERENCES EQUIPOS(equipo_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_mant_estado FOREIGN KEY (estado_id)
        REFERENCES ESTADOS_KANBAN(estado_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS MANT_HISTORIAL (
    historial_id INT AUTO_INCREMENT PRIMARY KEY,
    folio_id INT NOT NULL,
    accion VARCHAR(100) NOT NULL,
    detalle TEXT NULL,
    usuario VARCHAR(100) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_hist_folio (folio_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS=1;

ALTER TABLE MANT_HISTORIAL
  ADD CONSTRAINT fk_hist_folio FOREIGN KEY (folio_id)
    REFERENCES MANTENIMIENTOS(folio_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE;

INSERT IGNORE INTO TIPOS_MANTENIMIENTO (nombre_tipo) VALUES
('Predictivo'), ('Preventivo'), ('Correctivo');

INSERT IGNORE INTO ESTADOS_KANBAN (nombre_estado, orden) VALUES
('Por Hacer', 10), ('En Revisión', 20), ('En Espera de Material', 30), ('Terminada', 40);

INSERT IGNORE INTO UBICACIONES (nombre_ubicacion) VALUES
('HOTEL CAM / HABITACIÓN 102'),
('HOTEL CAM / HABITACIÓN 201'),
('RESTAURANTE/COCINA'),
('DATACENTER TYGO');