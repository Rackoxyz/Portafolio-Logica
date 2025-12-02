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
    """Parsea el contenido SQL y retorna comandos válidos. Normaliza NBSP y CR."""
    # Normalizar espacios problemáticos
    sql_content = sql_content.replace('\u00A0', ' ').replace('\r', '')
    commands = []
    for statement in sql_content.split(';'):
        lines = [line.strip() for line in statement.split('\n') 
                 if line.strip() and not line.strip().startswith('--')]
        cleaned = ' '.join(lines).strip()
        if cleaned:
            commands.append(cleaned)
    return commands


def show_innodb_status(cursor):
    """Consulta y muestra la sección relevante de SHOW ENGINE INNODB STATUS para ayudar a diagnosticar errores de FK."""
    try:
        cursor.execute("SHOW ENGINE INNODB STATUS")
        status = cursor.fetchone()
        if not status:
            print("ℹ️  No se pudo obtener InnoDB STATUS")
            return
        # status es un dict; el campo con texto suele estar en la primera/única clave
        txt = next(iter(status.values()))
        # Buscar la sección de latest foreign key error
        marker = "LATEST FOREIGN KEY ERROR"
        if marker in txt:
            idx = txt.find(marker)
            excerpt = txt[idx: idx + 2000]  # recortar un bloque razonable
        else:
            excerpt = txt[:2000]
        print("\n" + "═" * 50)
        print("InnoDB STATUS (extracto):\n")
        print(excerpt)
        print("═" * 50 + "\n")
    except Exception as e:
        print(f"⚠️ No se pudo consultar InnoDB STATUS: {e}")


def execute_sql_file():
    """Conecta a la DB, lee el archivo SQL y ejecuta las sentencias en orden lógico."""
    try:
        validate_sql_file()
        print("📂 Leyendo archivo SQL...")
        with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f:
            raw = f.read()
        # Normalizar NBSP y CR para evitar "No database selected"
        raw = raw.replace('\u00A0', ' ').replace('\r', '')
        sql_commands = parse_sql_commands(raw)
        print(f"📋 Se encontraron {len(sql_commands)} comandos SQL.\n")

        alter_cmds = []
        insert_cmds = []

        print("🔌 Conectando al servidor MariaDB...")
        connection = pymysql.connect(**DB_CONFIG, autocommit=False)

        try:
            with connection.cursor() as cursor:
                # Intentar desactivar binlog para DDL (si es posible)
                try:
                    cursor.execute("SET sql_log_bin=0")
                    connection.commit()
                    print("⚠️  Log binario desactivado para DDL")
                except Exception:
                    print("⚠️  No fue posible cambiar sql_log_bin (continuando)")

                # Ejecutar en orden original pero posponer ALTER/INSERT
                for i, cmd in enumerate(sql_commands, 1):
                    up = cmd.strip().upper()
                    if up.startswith('ALTER TABLE'):
                        alter_cmds.append((i, cmd))
                        continue
                    if up.startswith('INSERT'):
                        insert_cmds.append((i, cmd))
                        continue

                    # Ejecutar USE/SET/CREATE etc. en el mismo orden del archivo
                    try:
                        cursor.execute(cmd)
                        head = up.split()[0]
                        print(f"  ✓ Comando {i}: {head}")
                    except Exception as e:
                        print(f"  ⚠️ Comando {i} falló: {e}")
                        if 'No database selected' in str(e):
                            print("    → 'USE sistema_mantenimiento;' no se ejecutó correctamente antes de CREATE TABLE.")
                    # commit en CREATE/SET para evitar transacciones largas
                    if up.startswith('CREATE DATABASE') or up.startswith('CREATE TABLE') or up.startswith('SET '):
                        try:
                            connection.commit()
                        except Exception:
                            pass

                # Ejecutar ALTERs en segunda pasada
                if alter_cmds:
                    print("\n🔧 Ejecutando ALTER TABLE (FKs) en segunda pasada...")
                    for idx, cmd in alter_cmds:
                        try:
                            cursor.execute(cmd)
                            print(f"  ✓ ALTER {idx}")
                        except Exception as e:
                            print(f"  ⚠️ ALTER {idx} falló: {e}")
                            try:
                                show_innodb_status(cursor)
                            except Exception:
                                pass
                    try:
                        connection.commit()
                    except Exception:
                        pass

                # Reactivar binlog para DML
                try:
                    cursor.execute("SET sql_log_bin=1")
                    connection.commit()
                    print("\n✅ Log binario re-activado")
                except Exception:
                    print("\n⚠️ No se pudo reactivar sql_log_bin (continuando)")

                # Ejecutar INSERTs
                if insert_cmds:
                    print("\n📥 Ejecutando INSERTs...")
                    for idx, cmd in insert_cmds:
                        try:
                            cursor.execute(cmd)
                            print(f"  ✓ INSERT {idx} ({cursor.rowcount} filas afectadas)")
                        except pymysql.err.IntegrityError:
                            print(f"  ℹ️ INSERT {idx}: duplicado/ignorado")
                        except Exception as e:
                            print(f"  ❌ INSERT {idx} falló: {e}")
                    try:
                        connection.commit()
                    except Exception:
                        pass

                print("\n✅ Operación completada.")
        finally:
            try:
                connection.close()
            except Exception:
                pass

    except Exception as e:
        print(f"❌ ERROR inesperado: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == '__main__':
    execute_sql_file()