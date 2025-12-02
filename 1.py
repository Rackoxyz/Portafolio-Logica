import pymysql
import sys
import os
import time

# --- CONFIGURACIÓN DE CONEXIÓN AL MASTER ---
DB_CONFIG = {
    'host': '192.168.56.10',
    'user': 'root',
    'password': 'isaac.rick',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor 
}

# Ruta absoluta del archivo SQL
SQL_FILE_PATH = r'C:\Users\rickr\OneDrive\Desktop\CHINOS CAFE\db_setup.sql'
DATABASE_NAME = 'sistema_mantenimiento'


def validate_sql_file():
    """Valida que el archivo SQL exista y sea legible."""
    if not os.path.exists(SQL_FILE_PATH):
        print(f"❌ ERROR: Archivo '{SQL_FILE_PATH}' no encontrado.")
        print(f"   📍 Directorio actual: {os.getcwd()}")
        sys.exit(1)
    
    if not os.path.isfile(SQL_FILE_PATH):
        print(f"❌ ERROR: '{SQL_FILE_PATH}' no es un archivo válido.")
        sys.exit(1)
    
    file_size = os.path.getsize(SQL_FILE_PATH)
    if file_size == 0:
        print(f"❌ ERROR: '{SQL_FILE_PATH}' está vacío.")
        sys.exit(1)
    
    print(f"✅ Archivo SQL encontrado ({file_size} bytes)")


def parse_sql_commands(sql_content):
    """Parsea el contenido SQL y retorna comandos válidos."""
    commands = []
    for statement in sql_content.split(';'):
        # Remover espacios en blanco y comentarios
        lines = [line.strip() for line in statement.split('\n') 
                 if line.strip() and not line.strip().startswith('--')]
        cleaned = ' '.join(lines).strip()
        
        if cleaned:
            commands.append(cleaned)
    
    return commands


def execute_sql_file():
    """Conecta a la DB, lee el archivo SQL y ejecuta todas las sentencias."""
    try:
        validate_sql_file()
        
        print("📂 Leyendo archivo SQL...")
        with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        sql_commands = parse_sql_commands(sql_content)
        print(f"📋 Se encontraron {len(sql_commands)} comandos SQL.\n")

        print("🔌 Conectando al servidor MariaDB...")
        
        # ⚠️ CRÍTICO: Deshabilitar autocommit para controlar transacciones manualmente
        connection = pymysql.connect(**DB_CONFIG, autocommit=False)
        
        try:
            with connection.cursor() as cursor:
                print(f"✅ Conexión exitosa a {DB_CONFIG['host']}\n")
                
                # ===== FASE 1: CREAR ESTRUCTURA SIN LOG BINARIO =====
                print("FASE 1: Creando estructura de BD (DDL sin replicación)...")
                print("-" * 80)
                
                cursor.execute("SET sql_log_bin=0")
                connection.commit()
                print("⚠️  Log binario desactivado para DDL\n")
                
                # Crear base de datos
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} "
                             f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                print(f"✅ Base de datos '{DATABASE_NAME}' creada.\n")
                
                cursor.execute(f"USE {DATABASE_NAME}")
                
                # Ejecutar solo comandos CREATE TABLE (DDL)
                executed_count = 0
                failed_count = 0
                
                for i, command in enumerate(sql_commands, 1):
                    # Solo ejecutar CREATE TABLE con log binario desactivado
                    if 'CREATE TABLE' in command.upper() or 'CREATE DATABASE' in command.upper():
                        try:
                            cursor.execute(command)
                            executed_count += 1
                            print(f"  ✓ DDL Comando {i} ejecutado")
                        except pymysql.err.ProgrammingError as e:
                            if 'already exists' not in str(e):
                                failed_count += 1
                                print(f"⚠️  DDL Comando {i}: {str(e)[:60]}...")
                            executed_count += 1
                
                connection.commit()
                print(f"\n✅ {executed_count} comandos DDL ejecutados\n")
                
                # ===== FASE 2: REACTIVAR LOG BINARIO Y INSERTAR DATOS =====
                print("FASE 2: Re-activando replicación para datos (DML)...")
                print("-" * 80)
                
                cursor.execute("SET sql_log_bin=1")
                connection.commit()
                print("✅ Log binario re-activado\n")
                
                # Esperar un poco para que el Slave esté listo
                print("⏳ Esperando sincronización del Slave (5 segundos)...")
                time.sleep(5)
                
                # Ahora ejecutar los INSERT (estos SÍ se replicarán)
                print("\nInsertando datos iniciales (estos se REPLICARÁN)...")
                for i, command in enumerate(sql_commands, 1):
                    if 'INSERT' in command.upper():
                        try:
                            cursor.execute(command)
                            print(f"  ✓ INSERT Comando {i}: {cursor.rowcount} filas")
                        except pymysql.err.IntegrityError:
                            print(f"  ℹ️  INSERT Comando {i}: Datos duplicados (ignorado)")
                        except Exception as e:
                            print(f"  ❌ INSERT Comando {i}: {str(e)[:60]}")
                
                connection.commit()
                
                print(f"\n{'=' * 80}")
                print("✅ ¡Base de datos configurada con éxito!")
                print("=" * 80)
                print(f"\n📊 Resumen:")
                print(f"  • Estructura (DDL): ✅ CREADA (sin replicación)")
                print(f"  • Datos iniciales (DML): ✅ INSERTADOS (SÍ replicados)")
                print(f"  • Log binario: ✅ ACTIVO para datos\n")

        finally:
            connection.close()
            
    except pymysql.err.OperationalError as e:
        print("\n❌ ERROR: No se pudo conectar a la base de datos.")
        print("   Verifica:")
        print("   • MV Master esté encendida")
        print("   • IP correcta (192.168.56.10)")
        print("   • Usuario y contraseña válidos")
        print(f"   • Detalle: {e}")
        sys.exit(1)
    except pymysql.err.DatabaseError as e:
        print(f"\n❌ ERROR de base de datos: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ ERROR: No se pudo leer '{SQL_FILE_PATH}'")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR inesperado: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == '__main__':
    execute_sql_file()

SQL_CREATE_TABLES = """
-- 1. Asegúrate de estar en la BD correcta
CREATE DATABASE IF NOT EXISTS sistema_mantenimiento
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE sistema_mantenimiento;

-- ⚠️ CRÍTICO: Deshabilitar FK checks para evitar conflictos
SET FOREIGN_KEY_CHECKS=0;

-- 2. TABLAS DE CATÁLOGO
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

-- 3. TABLAS PRINCIPALES
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
    materiales_requeridos TEXT NULL,  -- <-- nuevo campo para listar materiales pendientes/solicitados
    estado_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (avance_porcentaje >= 0 AND avance_porcentaje <= 100),
    CHECK (fecha_programada >= fecha_ingreso),
    INDEX idx_mant_equipo (equipo_id),
    INDEX idx_mant_estado (estado_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- tabla historial SIN FK (se agregará con ALTER TABLE después)
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

# Nuevo: comandos ALTER para añadir FKs después de crear tablas
SQL_ADD_FKS = """
ALTER TABLE MANT_HISTORIAL
  ADD CONSTRAINT fk_hist_folio FOREIGN KEY (folio_id)
    REFERENCES MANTENIMIENTOS(folio_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE;
"""

def create_database_structure(cursor):
    """Crea la estructura de base de datos en el Slave (LOCAL, SIN REPLICAR)."""
    print("📋 Creando estructura de base de datos...\n")
    
    try:
        # Deshabilitar FK checks temporalmente
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        
        commands = [s.strip() for s in SQL_CREATE_TABLES.split(';') if s.strip()]
        created_count = 0
        failed_count = 0
        
        # Crear todas las tablas
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
                    print("  ✓ ALTER OK:", stmt.split()[2] if len(stmt.split())>2 else stmt[:40])
                except Exception as e_alt:
                    # No abortar: puede fallar por permisos o por orden; mostrar aviso
                    print(f"  ⚠️  ALTER skipped/not applied: {e_alt}")
        except Exception:
            pass

        print(f"\n✅ Estructura de base de datos creada: {created_count} tablas")
        return True
    except Exception as e:
        print(f"❌ Error al crear estructura: {e}")
        return False

# --- EJECUTAR LA APLICACIÓN ---
if __name__ == "__main__":
    root = tk.Tk()
    app = MantenimientoApp(root)
    root.mainloop()