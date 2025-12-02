import pymysql
import time
import csv
import os
from datetime import datetime, timedelta

# Configs (ajusta si es necesario)
MASTER = {'host': '192.168.56.10', 'user': 'root', 'password': 'isaac.rick',
          'database': 'sistema_mantenimiento', 'charset': 'utf8mb4',
          'cursorclass': pymysql.cursors.DictCursor, 'autocommit': True}
SLAVE  = {'host': '192.168.56.20', 'user': 'root', 'password': 'isaac.rick',
          'database': 'sistema_mantenimiento', 'charset': 'utf8mb4',
          'cursorclass': pymysql.cursors.DictCursor, 'autocommit': True}

POLL_INTERVAL = 1.0
POLL_TIMEOUT = 30

def connect(cfg):
    return pymysql.connect(**cfg)

def fetchone(conn, sql, params=None):
    with conn.cursor() as c:
        c.execute(sql, params or ())
        return c.fetchone()

def fetchall(conn, sql, params=None):
    with conn.cursor() as c:
        c.execute(sql, params or ())
        return c.fetchall()

def execute(conn, sql, params=None):
    with conn.cursor() as c:
        c.execute(sql, params or ())
        return c.lastrowid if hasattr(c, 'lastrowid') else None

def poll_for_slave_row(check_fn, timeout=POLL_TIMEOUT):
    start = time.time()
    while time.time() - start < timeout:
        if check_fn():
            return True
        time.sleep(POLL_INTERVAL)
    return False

def ensure_catalogs(master_conn):
    # return a pair of ubicacion_id, tipo_id (create if none)
    row = fetchone(master_conn, "SELECT ubicacion_id FROM UBICACIONES LIMIT 1")
    if row:
        ubicacion_id = row['ubicacion_id']
    else:
        execute(master_conn, "INSERT INTO UBICACIONES (nombre_ubicacion) VALUES (%s)",
                (f'TEST_UB_{int(time.time())}',))
        ubicacion_id = fetchone(master_conn, "SELECT LAST_INSERT_ID() as id")['id']
    row = fetchone(master_conn, "SELECT tipo_id FROM TIPOS_MANTENIMIENTO LIMIT 1")
    if row:
        tipo_id = row['tipo_id']
    else:
        execute(master_conn, "INSERT INTO TIPOS_MANTENIMIENTO (nombre_tipo) VALUES (%s)",
                (f'TEST_TIPO_{int(time.time())}',))
        tipo_id = fetchone(master_conn, "SELECT LAST_INSERT_ID() as id")['id']
    return ubicacion_id, tipo_id

def test_create_equipo(master_conn, slave_conn):
    print("TEST: Crear equipo en Master y verificar réplica en Slave")
    ubic_id, tipo_id = ensure_catalogs(master_conn)
    serie = f"TEST-SERIE-{int(time.time())}"
    nombre = f"Equipo Prueba {int(time.time())}"
    marca = "TEST-MARCA"
    execute(master_conn,
            "INSERT INTO EQUIPOS (nombre_equipo, marca, serie, ubicacion_id, tipo_mantenimiento_pred_id) VALUES (%s,%s,%s,%s,%s)",
            (nombre, marca, serie, ubic_id, tipo_id))
    # poll slave
    def check():
        r = fetchone(slave_conn, "SELECT * FROM EQUIPOS WHERE serie = %s", (serie,))
        return bool(r)
    ok = poll_for_slave_row(check)
    print("  RESULT:", "PASS" if ok else "FAIL")
    return {'serie': serie, 'nombre': nombre, 'ubic_id': ubic_id, 'tipo_id': tipo_id, 'ok': ok}

def test_update_ubicacion(master_conn, slave_conn, serie):
    print("TEST: Actualizar ubicación del equipo en Master y verificar réplica")
    # create new ubicacion on master
    new_name = f"TEST-UB-NEW-{int(time.time())}"
    execute(master_conn, "INSERT INTO UBICACIONES (nombre_ubicacion) VALUES (%s)", (new_name,))
    new_ubic = fetchone(master_conn, "SELECT ubicacion_id FROM UBICACIONES WHERE nombre_ubicacion=%s", (new_name,))['ubicacion_id']
    # update equipo
    execute(master_conn, "UPDATE EQUIPOS SET ubicacion_id=%s WHERE serie=%s", (new_ubic, serie))
    def check():
        r = fetchone(slave_conn, "SELECT u.ubicacion_id FROM EQUIPOS e JOIN UBICACIONES u ON e.ubicacion_id=u.ubicacion_id WHERE e.serie=%s", (serie,))
        return r and r.get('ubicacion_id') == new_ubic
    ok = poll_for_slave_row(check)
    print("  RESULT:", "PASS" if ok else "FAIL")
    return ok

def test_create_mantenimiento(master_conn, slave_conn, serie):
    print("TEST: Crear mantenimiento en Master y verificar réplica")
    eq = fetchone(master_conn, "SELECT equipo_id FROM EQUIPOS WHERE serie=%s", (serie,))
    if not eq:
        print("  SKIP: equipo no encontrado en master")
        return False
    equipo_id = eq['equipo_id']
    # Asegurar fecha_programada >= fecha_ingreso: usar ahora + 1 día
    fecha_prog = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        execute(master_conn,
                "INSERT INTO MANTENIMIENTOS (equipo_id, fecha_ingreso, fecha_programada, descripcion_servicio, costo_inicial, estado_id) VALUES (%s, NOW(), %s, %s, %s, 1)",
                (equipo_id, fecha_prog, 'Prueba mantenimiento', 10.0))
    except Exception as e:
        # Capturar y explicar errores de constraint (CHECK / FK)
        print(f"  ❌ ERROR al crear mantenimiento: {e}")
        print("  → Posible causa: violation of CHECK (fecha_programada >= fecha_ingreso) o FK faltante.")
        return False
    # poll slave
    def check():
        r = fetchone(slave_conn, "SELECT m.* FROM MANTENIMIENTOS m JOIN EQUIPOS e ON m.equipo_id=e.equipo_id WHERE e.serie=%s ORDER BY m.created_at DESC LIMIT 1", (serie,))
        return bool(r)
    ok = poll_for_slave_row(check)
    print("  RESULT:", "PASS" if ok else "FAIL")
    return ok

def test_update_mant_progress(master_conn, slave_conn, serie):
    print("TEST: Actualizar progreso del mantenimiento en Master y verificar réplica")
    # get latest maintenance id for equipo
    r = fetchone(master_conn, "SELECT m.folio_id FROM MANTENIMIENTOS m JOIN EQUIPOS e ON m.equipo_id=e.equipo_id WHERE e.serie=%s ORDER BY m.created_at DESC LIMIT 1", (serie,))
    if not r:
        print("  SKIP: no hay mantenimiento")
        return False
    folio = r['folio_id']
    execute(master_conn, "UPDATE MANTENIMIENTOS SET avance_porcentaje=%s, estado_id=%s WHERE folio_id=%s", (75, 2, folio))
    def check():
        s = fetchone(slave_conn, "SELECT avance_porcentaje, estado_id FROM MANTENIMIENTOS WHERE folio_id=%s", (folio,))
        return s and int(s.get('avance_porcentaje',0)) == 75
    ok = poll_for_slave_row(check)
    print("  RESULT:", "PASS" if ok else "FAIL")
    return ok

def compare_counts(master_conn, slave_conn):
    print("TEST: Comparar conteos (equipos/mantenimientos) entre Master y Slave")
    m_e = fetchone(master_conn, "SELECT COUNT(*) AS c FROM EQUIPOS")['c']
    s_e = fetchone(slave_conn,  "SELECT COUNT(*) AS c FROM EQUIPOS")['c']
    m_m = fetchone(master_conn, "SELECT COUNT(*) AS c FROM MANTENIMIENTOS")['c']
    s_m = fetchone(slave_conn,  "SELECT COUNT(*) AS c FROM MANTENIMIENTOS")['c']
    ok = (m_e == s_e) and (m_m == s_m)
    print(f"  Equipos: master={m_e} slave={s_e}")
    print(f"  Mantenim.: master={m_m} slave={s_m}")
    print("  RESULT:", "PASS" if ok else "FAIL")
    return ok

def export_csv_master(master_conn, path='verify_export.csv'):
    print("TEST: Exportar CSV desde Master")
    rows = fetchall(master_conn,
                    "SELECT e.equipo_id, e.nombre_equipo, e.marca, e.serie, u.nombre_ubicacion, tm.nombre_tipo FROM EQUIPOS e LEFT JOIN UBICACIONES u ON e.ubicacion_id=u.ubicacion_id LEFT JOIN TIPOS_MANTENIMIENTO tm ON e.tipo_mantenimiento_pred_id=tm.tipo_id")
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID','Nombre','Marca','Serie','Ubicacion','Tipo'])
        for r in rows:
            writer.writerow([r['equipo_id'], r['nombre_equipo'], r['marca'], r['serie'], r.get('nombre_ubicacion'), r.get('nombre_tipo')])
    exists = os.path.exists(path) and os.path.getsize(path) > 0
    print("  RESULT:", "PASS" if exists else "FAIL", f"-> {path}")
    return exists

def cleanup(master_conn, serie):
    print("CLEANUP: eliminando datos de prueba en Master")
    execute(master_conn, "DELETE FROM MANTENIMIENTOS WHERE equipo_id IN (SELECT equipo_id FROM EQUIPOS WHERE serie=%s)", (serie,))
    execute(master_conn, "DELETE FROM EQUIPOS WHERE serie=%s", (serie,))
    print("  CLEANUP done")

def main():
    m = connect(MASTER)
    s = connect(SLAVE)
    summary = {}
    try:
        r = test_create_equipo(m, s)
        summary['create_equipo'] = r['ok']
        if not r['ok']:
            print("ERROR: equipo no replicó. Abortando tests siguientes.")
        else:
            summary['update_ubic'] = test_update_ubicacion(m, s, r['serie'])
            summary['create_mant'] = test_create_mantenimiento(m, s, r['serie'])
            summary['update_mant'] = test_update_mant_progress(m, s, r['serie'])
            summary['counts_equal'] = compare_counts(m, s)
            summary['export_csv'] = export_csv_master(m)
            cleanup(m, r['serie'])
    finally:
        m.close(); s.close()
    print("\nSUMMARY:")
    for k,v in summary.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    all_ok = all(summary.values()) if summary else False
    print("\nOVERALL:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1

if __name__ == '__main__':
    exit(main())
