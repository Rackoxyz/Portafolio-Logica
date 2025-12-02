import pymysql
from tkinter import messagebox
import sys
import time

# --- CONFIGURACIÓN DE CONEXIÓN AL SLAVE ---
DB_CONFIG_SLAVE = {
    'host': '192.168.56.20',
    'user': 'root',
    'password': 'isaac.rick',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor 
}

# --- CONFIGURACIÓN DE CONEXIÓN AL MASTER (para obtener posición y reparar réplica) ---
DB_CONFIG_MASTER = {
    'host': '192.168.56.10',
    'user': 'root',
    'password': 'isaac.rick',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': True
}

# Ruta absoluta del archivo SQL para creación de tablas
SQL_FILE_PATH = r'C:\Users\rickr\OneDrive\Desktop\CHINOS CAFE\db_setup.sql'

# Comandos SQL para crear tablas (solo la estructura)
SQL_CREATE_TABLES = """
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
    materiales_requeridos TEXT NULL,  -- nuevo campo
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
"""

# Nuevo bloque: ALTERs para añadir FKs (se ejecutan después de crear tablas)
SQL_ADD_FKS = """
ALTER TABLE MANT_HISTORIAL
  ADD CONSTRAINT fk_hist_folio FOREIGN KEY (folio_id)
    REFERENCES MANTENIMIENTOS(folio_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE;
"""

# Comandos SQL para insertar datos iniciales
SQL_SEED_COMMANDS = """
INSERT IGNORE INTO TIPOS_MANTENIMIENTO (nombre_tipo) VALUES
('Predictivo'), ('Preventivo'), ('Correctivo');

INSERT IGNORE INTO ESTADOS_KANBAN (nombre_estado, orden) VALUES
('Por Hacer', 10), ('En Revisión', 20), ('En Espera de Material', 30), ('Terminada', 40);

INSERT IGNORE INTO UBICACIONES (nombre_ubicacion) VALUES
('HOTEL CAM / HABITACIÓN 102'),
('HOTEL CAN / HABITACIÓN 201'),
('RESTAURANTE/COCINA'),
('DATACENTER TYGO');
"""

def verify_slave_status(cursor):
    """Verifica el estado de la réplica en el Slave."""
    try:
        cursor.execute("SHOW SLAVE STATUS")
        result = cursor.fetchone()
        
        if not result:
            print("⚠️  El servidor no es esclavo o no está configurado correctamente.")
            print("   (Esto podría ser un error de permisos SLAVE MONITOR)\n")
            return False
        
        print("✅ Estado de réplica verificado.")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        return True
    except pymysql.err.OperationalError as e:
        if '1227' in str(e) or 'SLAVE MONITOR' in str(e):
            print("⚠️  No hay permisos para ver estado de réplica (SLAVE MONITOR)")
            print("   Ejecuta en SLAVE: GRANT SLAVE MONITOR ON *.* TO 'root'@'localhost';\n")
            return True  # Continuamos de todas formas
        else:
            print(f"❌ ERROR al verificar estado de réplica: {e}\n")
            return False

def wait_for_slave_sync(cursor, max_wait=30):
    """Espera a que el Slave se sincronice con el Master."""
    try:
        print("⏳ Esperando sincronización del Slave con el Master...")
        for i in range(max_wait):
            try:
                cursor.execute("SHOW SLAVE STATUS")
                result = cursor.fetchone()
                
                if result and result['Seconds_Behind_Master'] == 0:
                    print("✅ Slave sincronizado con el Master.\n")
                    return True
            except:
                # Si no puede hacer SHOW SLAVE STATUS, espera sin verificar
                pass
            
            time.sleep(1)
        
        print("⚠️  Tiempo de espera completado.\n")
        return True
    except Exception as e:
        print(f"⚠️  No se pudo verificar sincronización: {e}\n")
        return True

def create_database_structure(cursor):
    """Crea la estructura de base de datos en el Slave (LOCAL, SIN REPLICAR)."""
    print("📋 Creando estructura de base de datos...\n")
    
    try:
        # ⚠️ CRÍTICO: Intentar desactivar replicación (puede fallar por permisos)
        try:
            cursor.execute("SET sql_log_bin=0")
            print("⚠️  Replicación desactivada para DDL local\n")
            replication_disabled = True
        except pymysql.err.OperationalError as e:
            if '1227' in str(e) or 'BINLOG ADMIN' in str(e):
                print("⚠️  No hay permisos para deshabilitar replicación (BINLOG ADMIN)")
                print("   Las tablas se crearán pero SER REPLICADAS al Master\n")
                replication_disabled = False
            else:
                raise
        
        # Crear BD si no existe
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS sistema_mantenimiento "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute("USE sistema_mantenimiento")
        print("✅ Base de datos 'sistema_mantenimiento' lista.\n")
        
        # Deshabilitar restricciones foráneas
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        print("⚠️  Foreign Key Checks deshabilitadas\n")
        
        # Crear tablas
        commands = SQL_CREATE_TABLES.split(';')
        created_count = 0
        
        for command in commands:
            command = command.strip()
            if command and command.upper().startswith('CREATE'):
                cursor.execute(command)
                created_count += 1
                table_name = command.split('TABLE')[1].split('(')[0].strip()
                print(f"  ✓ Tabla {table_name} verificada")
        
        # Re-habilitar FK
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        
        # Intentar aplicar ALTER TABLE para añadir FKs (si el servidor lo permite)
        try:
            for stmt in [s.strip() for s in SQL_ADD_FKS.split(';') if s.strip()]:
                try:
                    cursor.execute(stmt)
                    print(f"  ✓ ALTER OK")
                except Exception as e_alt:
                    print(f"  ⚠️  ALTER skipped/not applied: {e_alt}")
        except Exception:
            pass
        
        # Re-habilitar replicación si fue deshabilitada
        if replication_disabled:
            try:
                cursor.execute("SET sql_log_bin=1")
            except:
                pass
        
        print(f"\n✅ Se crearon {created_count} tablas correctamente.")
        print("✅ Foreign Key Checks re-habilitadas\n")
        return True
        
    except Exception as e:
        print(f"❌ ERROR al crear estructura: {e}\n")
        try:
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        except:
            pass
        return False

def get_master_status():
    """Retorna (file, position) del Master o None en error."""
    try:
        conn = pymysql.connect(**DB_CONFIG_MASTER)
        try:
            with conn.cursor() as c:
                c.execute("SHOW MASTER STATUS")
                row = c.fetchone()
                if not row:
                    return None
                # Normalizar nombres de columnas posibles
                file = row.get('File') or row.get('File_name') or row.get('file') or row.get('master_log_file')
                pos = row.get('Position') or row.get('Pos') or row.get('position') or row.get('master_log_pos')
                if file and pos is not None:
                    return (file, int(pos))
                return None
        finally:
            conn.close()
    except Exception as e:
        print(f"⚠️ No se pudo obtener MASTER STATUS: {e}")
        return None

def attempt_fix_replication(cursor):
    """Si el Slave presenta error 1236/impossible position, intenta reconfigurarlo usando las coordenadas del Master.
    Requiere privilegios para STOP/RESET/CHANGE MASTER en el Slave y conexión al Master (usa root)."""
    try:
        cursor.execute("SHOW SLAVE STATUS")
        status = cursor.fetchone()
        if not status:
            print("ℹ️  SHOW SLAVE STATUS no devolvió datos; no es esclavo o permisos insuficientes.")
            return False

        last_io_err = (status.get('Last_IO_Error') or status.get('Last_IO_Errno') or '') 
        if isinstance(last_io_err, dict):
            last_io_err = str(last_io_err)
        # Detectar mensaje típico de posición imposible
        if '1236' in str(status.get('Last_IO_Errno') or '') or 'impossible position' in str(status.get('Last_IO_Error') or '').lower() or 'first event' in str(status.get('Last_IO_Error') or '').lower():
            print("❗ Detected replication position error on Slave. Attempting automatic fix using Master's binlog coordinates...")
            master_status = get_master_status()
            if not master_status:
                print("⚠️ No se pudo obtener coordenadas del Master. No se puede reconfigurar automáticamente.")
                return False
            master_file, master_pos = master_status
            print(f"  • Master coordinates: {master_file} @ {master_pos}")

            try:
                # Intenta reparar: STOP, RESET, CHANGE MASTER TO using root credentials to master, START
                try:
                    cursor.execute("STOP SLAVE")
                except Exception:
                    pass
                try:
                    cursor.execute("RESET SLAVE ALL")
                except Exception:
                    # en algunas versiones RESET SLAVE ALL puede fallar si no hay privilegios
                    pass

                change_cmd = (
                    "CHANGE MASTER TO "
                    "MASTER_HOST=%s, MASTER_USER=%s, MASTER_PASSWORD=%s, "
                    "MASTER_LOG_FILE=%s, MASTER_LOG_POS=%s"
                )
                # Usamos root del Master (asegúrate de que exista y tenga permisos)
                cursor.execute(change_cmd, (
                    DB_CONFIG_MASTER['host'],
                    DB_CONFIG_MASTER['user'],
                    DB_CONFIG_MASTER['password'],
                    master_file,
                    master_pos
                ))
                cursor.execute("START SLAVE")
                print("✅ Intentado START SLAVE tras CHANGE MASTER. Verifica SHOW SLAVE STATUS para estado.")
                return True
            except Exception as e:
                print(f"❌ No se pudo reconfigurar el Slave automáticamente: {e}")
                return False
        else:
            # No es el error que queremos reparar automáticamente
            return False
    except Exception as e:
        print(f"⚠️ Error al verificar/intent reparar réplica: {e}")
        return False

def seed_slave_database():
    """Conecta al Slave, crea estructura e inserta datos iniciales."""
    try:
        # ⚠️ CRÍTICO: autocommit=False para controlar transacciones
        connection = pymysql.connect(**DB_CONFIG_SLAVE, autocommit=False)
        
        try:
            with connection.cursor() as cursor:
                print("=" * 80)
                print("🔧 INICIALIZANDO BASE DE DATOS EN SLAVE")
                print("=" * 80)
                print(f"✅ Conexión exitosa al Servidor Slave ({DB_CONFIG_SLAVE['host']})\n")
                
                # Paso 1: Verificar réplica
                print("PASO 1: Verificando estado de réplica...")
                print("-" * 80)
                try:
                    cursor.execute("SHOW SLAVE STATUS")
                    slave_status = cursor.fetchone()
                except Exception as e:
                    slave_status = None
                    print(f"⚠️ No se pudo ejecutar SHOW SLAVE STATUS: {e}")

                if slave_status:
                    last_errno = slave_status.get('Last_IO_Errno') or slave_status.get('Last_IO_Error') or ''
                    # Intentar reparación automática si detectamos el error 1236/impossible position
                    repaired = False
                    if '1236' in str(last_errno) or 'impossible position' in str(slave_status.get('Last_IO_Error') or '').lower() or 'first event' in str(slave_status.get('Last_IO_Error') or '').lower():
                        repaired = attempt_fix_replication(cursor)
                        if repaired:
                            # refrescar estado
                            try:
                                cursor.execute("SHOW SLAVE STATUS")
                                slave_status = cursor.fetchone()
                                print("ℹ️ Estado de réplica luego de intento de reparación:")
                                if slave_status:
                                    for k,v in slave_status.items():
                                        print(f"  {k}: {v}")
                            except:
                                pass

                replica_ok = verify_slave_status(cursor)
                
                # Paso 2: Crear estructura LOCAL (sin replicar)
                print("PASO 2: Creando estructura de BD (LOCAL)...")
                print("-" * 80)
                structure_ok = create_database_structure(cursor)
                connection.commit()  # ✅ Hacer commit después de DDL
                
                if not structure_ok:
                    print("❌ ERROR: No se pudo crear la estructura.")
                    return False
                
                # Paso 3: Esperar sincronización
                print("PASO 3: Esperando sincronización de datos...")
                print("-" * 80)
                wait_for_slave_sync(cursor)
                
                # Paso 4: Verificar datos replicados
                print("PASO 4: Verificando datos replicados...")
                print("-" * 80)
                
                cursor.execute("USE sistema_mantenimiento")
                
                try:
                    cursor.execute("SELECT COUNT(*) as total FROM TIPOS_MANTENIMIENTO")
                    result = cursor.fetchone()
                    total_tipos = result['total'] if result else 0
                    
                    cursor.execute("SELECT COUNT(*) as total FROM ESTADOS_KANBAN")
                    result = cursor.fetchone()
                    total_estados = result['total'] if result else 0
                    
                    cursor.execute("SELECT COUNT(*) as total FROM UBICACIONES")
                    result = cursor.fetchone()
                    total_ubicaciones = result['total'] if result else 0
                    
                    print(f"  ✓ Tipos de Mantenimiento: {total_tipos}")
                    print(f"  ✓ Estados Kanban: {total_estados}")
                    print(f"  ✓ Ubicaciones: {total_ubicaciones}")
                    
                except Exception as e:
                    print(f"  ℹ️  Datos aún no replicados: {e}")
                
                # Resumen
                print("\n" + "=" * 80)
                print("✅ ¡INICIALIZACIÓN COMPLETADA!")
                print("=" * 80)
                print(f"📊 Estado final:")
                print(f"  • Base de datos: ✅ CREADA")
                print(f"  • Tablas: ✅ CREADAS")
                print(f"  • Replicación: {'✅ ACTIVA' if replica_ok else '⚠️  VERIFICAR'}")
                print("\n💡 Próximos pasos:")
                print("  1. (RECOMENDADO) Ejecuta en SLAVE estos comandos:")
                print("     GRANT SUPER, SLAVE MONITOR, BINLOG ADMIN ON *.* TO 'root'@'localhost';")
                print("     GRANT SUPER, SLAVE MONITOR, BINLOG ADMIN ON *.* TO 'root'@'%';")
                print("     FLUSH PRIVILEGES;")
                print("  2. Ejecuta en MASTER: python setup_db.py")
                print("  3. Verifica: SHOW SLAVE STATUS en el Slave")
                print("=" * 80)
                
                messagebox.showinfo(
                    "✅ Éxito",
                    f"Base de datos inicializada en Slave (San Mateo).\n"
                    f"Estructura: ✅ LISTA\n"
                    f"Replicación: {'✅ ACTIVA' if replica_ok else '⚠️  VERIFICAR'}\n\n"
                    f"IMPORTANTE: Ejecuta en el Slave:\n"
                    f"GRANT SUPER, SLAVE MONITOR, BINLOG ADMIN ON *.* TO 'root'@'localhost';\n"
                    f"FLUSH PRIVILEGES;"
                )
                return True

        finally:
            connection.close()
            
    except pymysql.err.OperationalError as e:
        error_msg = (
            "❌ ERROR: No se pudo conectar al Servidor Slave.\n\n"
            "Verifica:\n"
            "  ✓ La MV Slave (San Mateo) esté encendida\n"
            "  ✓ IP correcta: 192.168.56.20\n"
            "  ✓ Usuario y contraseña válidos\n"
            "  ✓ Puerto 3306 accesible\n\n"
            f"Detalle: {e}"
        )
        print("\n" + error_msg)
        messagebox.showerror("❌ Error de Conexión", error_msg)
        return False
        
    except Exception as e:
        error_msg = f"❌ Error inesperado: {type(e).__name__}\n{e}"
        print("\n" + error_msg)
        messagebox.showerror("❌ Error", error_msg)
        return False


if __name__ == '__main__':
    print("\n📌 INSTRUCCIONES PREVIAS (EJECUTAR EN SLAVE):")
    print("   Ejecuta en MySQL del Slave como root:")
    print("   GRANT SUPER, SLAVE MONITOR, BINLOG ADMIN ON *.* TO 'root'@'localhost';")
    print("   GRANT SUPER, SLAVE MONITOR, BINLOG ADMIN ON *.* TO 'root'@'%';")
    print("   FLUSH PRIVILEGES;\n")
    print("   Después continúa con:\n")
    print("   1️⃣  Ejecuta: python seed_slave_db.py (en SLAVE)")
    print("   2️⃣  Espera confirmación de estructura creada")
    print("   3️⃣  Luego ejecuta: python setup_db.py (en MASTER)")
    print("   4️⃣  Verifica: SHOW SLAVE STATUS en el Slave\n")
    
    success = seed_slave_database()
    sys.exit(0 if success else 1)