import pymysql
import sys
import time

# --- CONFIGURACIÓN ---
DB_CONFIG_MASTER = {
    'host': '192.168.56.10',
    'user': 'root',
    'password': 'isaac.rick',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

DB_CONFIG_SLAVE = {
    'host': '192.168.56.20',
    'user': 'root',
    'password': 'isaac.rick',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

DATABASE_NAME = 'sistema_mantenimiento'

def get_master_status():
    """Obtiene el estado actual del Master (FILE y POSITION)."""
    print("\n" + "=" * 80)
    print("PASO 0: OBTENER ESTADO DEL MASTER")
    print("=" * 80)
    
    try:
        connection = pymysql.connect(**DB_CONFIG_MASTER, autocommit=True)
        
        with connection.cursor() as cursor:
            print("\n📊 Obteniendo MASTER STATUS...")
            cursor.execute("SHOW MASTER STATUS")
            master_status = cursor.fetchone()
            
            if not master_status:
                print("❌ No se pudo obtener el estado del Master")
                return None
            
            log_file = master_status.get('File')
            log_pos = master_status.get('Position')
            
            print(f"\n✅ Estado del Master obtenido:")
            print(f"  • File: {log_file}")
            print(f"  • Position: {log_pos}\n")
            
            connection.close()
            return (log_file, log_pos)
        
    except Exception as e:
        print(f"❌ ERROR al obtener estado del Master: {e}")
        return None


def reset_slave():
    """PASO 1: Reset completo del Slave."""
    print("\n" + "=" * 80)
    print("PASO 1: RESETEAR SLAVE (192.168.56.20)")
    print("=" * 80)
    
    try:
        connection = pymysql.connect(**DB_CONFIG_SLAVE, autocommit=True)
        
        with connection.cursor() as cursor:
            print("\n🛑 Deteniendo replicación en Slave...")
            cursor.execute("STOP SLAVE")
            print("✅ Slave detenido\n")
            
            print("🗑️  Reseteando replicación...")
            cursor.execute("RESET SLAVE ALL")
            print("✅ Replicación reseteada\n")
            
            print("🗑️  Eliminando base de datos...")
            cursor.execute(f"DROP DATABASE IF EXISTS {DATABASE_NAME}")
            print(f"✅ Base de datos '{DATABASE_NAME}' eliminada\n")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ ERROR en Slave: {e}")
        return False


def reset_master():
    """PASO 2: Reset del Master."""
    print("\n" + "=" * 80)
    print("PASO 2: RESETEAR MASTER (192.168.56.10)")
    print("=" * 80)
    
    try:
        connection = pymysql.connect(**DB_CONFIG_MASTER, autocommit=True)
        
        with connection.cursor() as cursor:
            print("\n🗑️  Eliminando base de datos en Master...")
            cursor.execute(f"DROP DATABASE IF EXISTS {DATABASE_NAME}")
            print(f"✅ Base de datos '{DATABASE_NAME}' eliminada\n")
            
            print("🗑️  Eliminando binlogs antiguos...")
            cursor.execute("RESET MASTER")
            print("✅ Binlogs reseteados\n")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ ERROR en Master: {e}")
        return False


def configure_slave_replication(log_file, log_pos):
    """PASO 3: Configurar automáticamente la replicación en el Slave."""
    print("\n" + "=" * 80)
    print("PASO 3: CONFIGURAR REPLICACIÓN EN SLAVE")
    print("=" * 80)
    
    try:
        connection = pymysql.connect(**DB_CONFIG_SLAVE, autocommit=True)
        
        with connection.cursor() as cursor:
            print("\n⚙️  Configurando CHANGE MASTER TO...")
            
            # Comando CHANGE MASTER con valores reales del Master
            change_master_cmd = f"""
            CHANGE MASTER TO
              MASTER_HOST='{DB_CONFIG_MASTER['host']}',
              MASTER_USER='{DB_CONFIG_MASTER['user']}',
              MASTER_PASSWORD='{DB_CONFIG_MASTER['password']}',
              MASTER_LOG_FILE='{log_file}',
              MASTER_LOG_POS={log_pos}
            """
            
            cursor.execute(change_master_cmd)
            print("✅ CHANGE MASTER configurado\n")
            
            print("🚀 Iniciando replicación (START SLAVE)...")
            cursor.execute("START SLAVE")
            print("✅ Slave iniciado\n")
            
            # Esperar un poco para que la replicación se establezca
            time.sleep(2)
            
            print("📊 Verificando estado de replicación...")
            cursor.execute("SHOW SLAVE STATUS")
            slave_status = cursor.fetchone()
            
            if slave_status:
                io_running = slave_status.get('Slave_IO_Running', 'No')
                sql_running = slave_status.get('Slave_SQL_Running', 'No')
                seconds_behind = slave_status.get('Seconds_Behind_Master', 'NULL')
                
                print(f"  • Slave_IO_Running: {io_running}")
                print(f"  • Slave_SQL_Running: {sql_running}")
                print(f"  • Seconds_Behind_Master: {seconds_behind}")
                
                if io_running == 'Yes' and sql_running == 'Yes':
                    print("\n✅ ¡Replicación configurada correctamente!\n")
                    return True
                else:
                    print("\n⚠️  La replicación no está completamente activa")
                    print("   Verifica el log de errores del Slave\n")
                    return False
            else:
                print("❌ No se pudo obtener el estado de la replicación\n")
                return False
        
        connection.close()
        
    except Exception as e:
        print(f"❌ ERROR al configurar replicación: {e}\n")
        return False


def verify_reset():
    """PASO 4: Verificar que todo fue eliminado."""
    print("\n" + "=" * 80)
    print("PASO 4: VERIFICAR ELIMINACIÓN")
    print("=" * 80)
    
    try:
        # Verificar Master
        print("\n📋 Verificando Master...")
        conn_master = pymysql.connect(**DB_CONFIG_MASTER, autocommit=True)
        with conn_master.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE %s", (DATABASE_NAME,))
            result = cursor.fetchone()
            if result:
                print(f"❌ Base de datos aún existe en Master")
                return False
            else:
                print(f"✅ Base de datos eliminada en Master")
        conn_master.close()
        
        # Verificar Slave
        print("\n📋 Verificando Slave...")
        conn_slave = pymysql.connect(**DB_CONFIG_SLAVE, autocommit=True)
        with conn_slave.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE %s", (DATABASE_NAME,))
            result = cursor.fetchone()
            if result:
                print(f"❌ Base de datos aún existe en Slave")
                return False
            else:
                print(f"✅ Base de datos eliminada en Slave")
        conn_slave.close()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR en verificación: {e}")
        return False


def show_instructions():
    """Muestra instrucciones finales."""
    print("\n" + "=" * 80)
    print("✅ RESET Y CONFIGURACIÓN COMPLETADOS")
    print("=" * 80)
    
    print("""
📋 ORDEN DE EJECUCIÓN (después de este script):

1️⃣ EN SLAVE - Ejecutar en Python (después de 3 segundos):
   python seed_slave_db.py
   ✅ Espera: "✅ ¡INICIALIZACIÓN COMPLETADA!"

2️⃣ EN MASTER - Ejecutar en Python (después de 5 segundos):
   python setup_db.py
   ✅ Espera: "✅ ¡Base de datos configurada con éxito!"

3️⃣ EN SLAVE - Verificar (Ejecutar en MySQL):
   SHOW SLAVE STATUS\G
   Debe mostrar:
   - Slave_IO_Running: Yes
   - Slave_SQL_Running: Yes
   - Seconds_Behind_Master: 0

4️⃣ EN MASTER - Verificar que está replicando:
   SHOW MASTER STATUS;

✨ ¡Replicación lista para usar!
    """)


if __name__ == '__main__':
    print("\n" + "🔴 * " * 20)
    print("⚠️  ADVERTENCIA: Este script ELIMINARÁ toda la base de datos")
    print("🔴 * " * 20)
    
    confirmacion = input("\n¿Deseas continuar? (escribe 'SI' para confirmar): ").strip().upper()
    
    if confirmacion != 'SI':
        print("❌ Operación cancelada.")
        sys.exit(1)
    
    print("\n🚀 Iniciando RESET COMPLETO Y AUTO-CONFIGURACIÓN...\n")
    
    # Paso 0: Obtener estado del Master
    master_info = get_master_status()
    if not master_info:
        print("❌ No se pudo obtener el estado del Master. Abortando.")
        sys.exit(1)
    
    log_file, log_pos = master_info
    time.sleep(1)
    
    # Paso 1: Reset Slave
    if not reset_slave():
        print("\n❌ Error en reset del Slave. Abortando.")
        sys.exit(1)
    
    time.sleep(2)
    
    # Paso 2: Reset Master
    if not reset_master():
        print("\n❌ Error en reset del Master. Abortando.")
        sys.exit(1)
    
    time.sleep(2)
    
    # Paso 3: Verificar eliminación
    if not verify_reset():
        print("\n❌ Verificación falló. Revisa manualmente.")
        sys.exit(1)
    
    time.sleep(1)
    
    # Paso 4: Configurar replicación automáticamente
    if not configure_slave_replication(log_file, log_pos):
        print("\n⚠️  La replicación se configuró pero puede no estar completamente activa")
        print("   Verifica manualmente con: SHOW SLAVE STATUS\\G en el Slave")
    
    # Mostrar instrucciones finales
    show_instructions()
    
    print("\n✅ Reset y auto-configuración completados exitosamente.\n")
