import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import pymysql
from datetime import datetime, timedelta
from tkcalendar import Calendar
import csv

# --- CONFIGURACIÓN GLOBAL DE LA BASE DE DATOS ---
DB_CONFIG = {
    'host': '192.168.56.10',
    'user': 'root',
    'password': 'isaac.rick',
    'database': 'sistema_mantenimiento',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


class MantenimientoApp:
    def __init__(self, root):
        self.root = root
        root.title("🔧 SISTEMA DE MANTENIMIENTO ABC SYSTEM - Chiriquí")
        root.geometry("1400x800")
        root.resizable(True, True)
        
        # Configurar estilo profesional
        self.setup_styles()
        
        # Variables
        self.connection = None
        self.catalog_data = {}
        self.equipos_data = []
        self.mantenimientos_data = []
        self.equipo_seleccionado = None
        self.mant_seleccionado = None
        
        # Intentar conexión y cargar catálogos
        if self.db_connect():
            self.load_catalog_data()
            
        # Crear interfaz
        self.create_main_interface()
        
    # --- CONFIGURACIÓN DE ESTILOS ---
    def setup_styles(self):
        """Configura los estilos visuales de la aplicación."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Define colores profesionales
        bg_color = '#f5f5f5'
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#1f4788')
        style.configure('Subtitle.TLabel', font=('Segoe UI', 13, 'bold'), foreground='#2c5aa0')
        style.configure('Normal.TLabel', font=('Segoe UI', 10), background=bg_color)
        style.configure('Success.TLabel', font=('Segoe UI', 10), foreground='#27ae60')
        style.configure('Error.TLabel', font=('Segoe UI', 10), foreground='#e74c3c')
        style.configure('Treeview', font=('Segoe UI', 9), rowheight=28)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), foreground='#2980b9')
        style.configure('Danger.TButton', font=('Segoe UI', 10), foreground='#e74c3c')
        
        # Configurar colores de alternancia en Treeview
        style.configure('Treeview', background='white', foreground='black')
        style.map('Treeview', background=[('selected', '#2c5aa0')])
        
    # --- FUNCIÓN DE CONEXIÓN A BASE DE DATOS ---
    def db_connect(self):
        """Conecta a la base de datos MariaDB."""
        try:
            # ⚠️ autocommit=False para mejor manejo de transacciones
            self.connection = pymysql.connect(**DB_CONFIG, autocommit=False)
            return True
        except pymysql.err.OperationalError as e:
            messagebox.showerror("❌ Error de Conexión", 
                f"No se pudo conectar a la BD Master.\n"
                f"Verifica la MV Master (192.168.56.10).\n"
                f"Error: {e}")
            return False
    
    # --- CARGA DE DATOS INICIALES ---
    def load_catalog_data(self):
        """Carga catálogos desde la BD."""
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT ubicacion_id, nombre_ubicacion FROM UBICACIONES ORDER BY nombre_ubicacion")
                self.catalog_data['ubicaciones'] = cursor.fetchall()
                
                cursor.execute("SELECT tipo_id, nombre_tipo FROM TIPOS_MANTENIMIENTO ORDER BY nombre_tipo")
                self.catalog_data['tipos_mantenimiento'] = cursor.fetchall()
                
                cursor.execute("SELECT estado_id, nombre_estado FROM ESTADOS_KANBAN ORDER BY orden")
                self.catalog_data['estados_kanban'] = cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Error DB", f"No se pudieron cargar los catálogos: {e}")
    
    # --- CREAR INTERFAZ PRINCIPAL ---
    def create_main_interface(self):
        """Crea la interfaz principal con pestañas."""
        # Frame superior con logo/título
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill='x', padx=20, pady=15, ipady=10)
        
        ttk.Label(header_frame, text="🔧 SISTEMA DE MANTENIMIENTO ABC SYSTEM", 
                 style='Title.TLabel').pack(side='left')
        
        status_text = "✅ CONECTADO" if self.connection else "❌ DESCONECTADO"
        status_color = '#27ae60' if self.connection else '#e74c3c'
        status_label = ttk.Label(header_frame, text=f"Estado: {status_text}", 
                                font=('Segoe UI', 11, 'bold'), foreground=status_color)
        status_label.pack(side='right')
        
        # Notebook con pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")
        
        # PESTAÑA 1: EQUIPOS (CRUD)
        self.frame_equipos = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_equipos, text='📊 EQUIPOS (CRUD)')
        self.setup_equipos_tab()
        
        # PESTAÑA 2: CALENDARIO
        self.frame_calendario = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_calendario, text='📅 CALENDARIO')
        self.setup_calendario_tab()
        
        # PESTAÑA 3: MANTENIMIENTOS (Kanban)
        self.frame_mantenimientos = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_mantenimientos, text='✅ MANTENIMIENTOS (Kanban)')
        self.setup_mantenimientos_tab()
        
        # PESTAÑA 4: REPORTES Y EXPORTACIÓN
        self.frame_reportes = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_reportes, text='📈 REPORTES & EXPORTACIÓN')
        self.setup_reportes_tab()
        
        # PESTAÑA 5: CONFIGURACIÓN Y MONITOREO
        self.frame_config = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_config, text='⚙️ CONFIGURACIÓN')
        self.setup_config_tab()
    
    # ========== PESTAÑA 1: EQUIPOS (CRUD COMPLETO) ==========
    def setup_equipos_tab(self):
        """Diseña la pestaña de EQUIPOS con CRUD completo."""
        main_frame = ttk.Frame(self.frame_equipos, padding="15 15 15 15")
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="Gestión Completa de Equipos", style='Subtitle.TLabel').pack(pady=10)
        
        # === FORMULARIO DE CREACIÓN/EDICIÓN ===
        form_frame = ttk.LabelFrame(main_frame, text="📝 Nuevo/Editar Equipo", padding="12 12 12 12")
        form_frame.pack(fill='x', pady=10)
        
        # Fila 1
        ttk.Label(form_frame, text="📍 Ubicación:", style='Normal.TLabel').grid(row=0, column=0, sticky='w', padx=5, pady=7)
        ubicaciones = [d['nombre_ubicacion'] for d in self.catalog_data.get('ubicaciones', [])]
        self.eq_ubicacion = ttk.Combobox(form_frame, values=ubicaciones, state='readonly', width=28)
        self.eq_ubicacion.grid(row=0, column=1, padx=5, pady=7, sticky='ew')
        if ubicaciones:
            self.eq_ubicacion.current(0)
        
        ttk.Label(form_frame, text="🏷️  Marca:", style='Normal.TLabel').grid(row=0, column=2, sticky='w', padx=5, pady=7)
        self.eq_marca = ttk.Entry(form_frame, width=25)
        self.eq_marca.grid(row=0, column=3, padx=5, pady=7, sticky='ew')
        
        # Fila 2
        ttk.Label(form_frame, text="⚙️  Nombre Equipo:", style='Normal.TLabel').grid(row=1, column=0, sticky='w', padx=5, pady=7)
        self.eq_nombre = ttk.Entry(form_frame, width=28)
        self.eq_nombre.grid(row=1, column=1, padx=5, pady=7, sticky='ew')
        
        ttk.Label(form_frame, text="📱 Serie:", style='Normal.TLabel').grid(row=1, column=2, sticky='w', padx=5, pady=7)
        self.eq_serie = ttk.Entry(form_frame, width=25)
        self.eq_serie.grid(row=1, column=3, padx=5, pady=7, sticky='ew')
        
        # Fila 3
        ttk.Label(form_frame, text="🔧 Tipo Mantenimiento:", style='Normal.TLabel').grid(row=2, column=0, sticky='w', padx=5, pady=7)
        tipos = [d['nombre_tipo'] for d in self.catalog_data.get('tipos_mantenimiento', [])]
        self.eq_tipo = ttk.Combobox(form_frame, values=tipos, state='readonly', width=28)
        self.eq_tipo.grid(row=2, column=1, padx=5, pady=7, sticky='ew')
        if tipos:
            self.eq_tipo.current(0)
        
        # Botones de acción
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=15)
        
        ttk.Button(btn_frame, text="✅ Crear Equipo", command=self.crear_equipo).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="✏️  Actualizar", command=self.actualizar_equipo).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔄 Refrescar Tabla", command=self.actualizar_tabla_equipos).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="❌ Eliminar", command=self.eliminar_equipo).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🧹 Limpiar Formulario", command=self.limpiar_form_equipos).pack(side='left', padx=5)
        
        # === BÚSQUEDA Y FILTROS ===
        search_frame = ttk.LabelFrame(main_frame, text="🔍 Búsqueda y Filtros", padding="10 10 10 10")
        search_frame.pack(fill='x', pady=10)
        
        ttk.Label(search_frame, text="Buscar por Nombre/Serie:", style='Normal.TLabel').pack(side='left', padx=5)
        self.eq_search = ttk.Entry(search_frame, width=40)
        self.eq_search.pack(side='left', padx=5)
        self.eq_search.bind('<KeyRelease>', lambda e: self.filtrar_equipos())
        
        ttk.Button(search_frame, text="🔎 Buscar", command=self.filtrar_equipos).pack(side='left', padx=5)
        
        # === TABLA DE EQUIPOS ===
        ttk.Label(main_frame, text="📋 Equipos Registrados", style='Subtitle.TLabel').pack(pady=(20, 10))
        
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill='both', expand=True)
        
        vsb = ttk.Scrollbar(table_frame, orient='vertical')
        hsb = ttk.Scrollbar(table_frame, orient='horizontal')
        
        self.equipos_tree = ttk.Treeview(table_frame, 
            columns=('ID', 'Nombre', 'Marca', 'Serie', 'Ubicación', 'Tipo', 'Creado'),
            height=14, yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=self.equipos_tree.yview)
        hsb.config(command=self.equipos_tree.xview)
        
        self.equipos_tree.column('#0', width=0, stretch='no')
        self.equipos_tree.column('ID', anchor='center', width=45)
        self.equipos_tree.column('Nombre', anchor='w', width=160)
        self.equipos_tree.column('Marca', anchor='w', width=110)
        self.equipos_tree.column('Serie', anchor='w', width=110)
        self.equipos_tree.column('Ubicación', anchor='w', width=170)
        self.equipos_tree.column('Tipo', anchor='w', width=130)
        self.equipos_tree.column('Creado', anchor='center', width=130)
        
        for col in ['ID', 'Nombre', 'Marca', 'Serie', 'Ubicación', 'Tipo', 'Creado']:
            self.equipos_tree.heading(col, text=col, anchor='w')
        
        self.equipos_tree.bind('<Button-1>', self.on_equipos_click)
        self.equipos_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        self.actualizar_tabla_equipos()
    
    # --- MÉTODOS CRUD EQUIPOS ---
    def crear_equipo(self):
        """Crea un nuevo equipo con validación."""
        nombre = self.eq_nombre.get().strip()
        marca = self.eq_marca.get().strip()
        serie = self.eq_serie.get().strip()
        ubicacion = self.eq_ubicacion.get()
        tipo = self.eq_tipo.get()
        
        if not all([nombre, marca, serie, ubicacion, tipo]):
            messagebox.showwarning("⚠️ Campos Incompletos", "Por favor completa todos los campos.")
            return
        
        if len(serie) < 3:
            messagebox.showwarning("⚠️ Validación", "La serie debe tener al menos 3 caracteres.")
            return
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT ubicacion_id FROM UBICACIONES WHERE nombre_ubicacion = %s", (ubicacion,))
                ub_result = cursor.fetchone()
                cursor.execute("SELECT tipo_id FROM TIPOS_MANTENIMIENTO WHERE nombre_tipo = %s", (tipo,))
                tp_result = cursor.fetchone()
                
                if not ub_result or not tp_result:
                    messagebox.showerror("❌ Error", "Ubicación o Tipo no válido.")
                    return
                
                cursor.execute(
                    "INSERT INTO EQUIPOS (nombre_equipo, marca, serie, ubicacion_id, tipo_mantenimiento_pred_id) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (nombre, marca, serie, ub_result['ubicacion_id'], tp_result['tipo_id'])
                )
                self.connection.commit()
                
                messagebox.showinfo("✅ Éxito", f"Equipo '{nombre}' creado correctamente.")
                self.limpiar_form_equipos()
                self.actualizar_tabla_equipos()
        except pymysql.err.IntegrityError:
            messagebox.showerror("❌ Error", "La serie ya existe en la base de datos.")
        except Exception as e:
            messagebox.showerror("❌ Error DB", f"Error al crear equipo: {e}")
    
    def actualizar_equipo(self):
        """Actualiza el equipo seleccionado."""
        if not self.equipo_seleccionado:
            messagebox.showwarning("⚠️ Selección", "Por favor selecciona un equipo de la tabla.")
            return
        
        nombre = self.eq_nombre.get().strip()
        marca = self.eq_marca.get().strip()
        serie = self.eq_serie.get().strip()
        ubicacion = self.eq_ubicacion.get()
        tipo = self.eq_tipo.get()
        
        if not all([nombre, marca, serie, ubicacion, tipo]):
            messagebox.showwarning("⚠️ Campos Incompletos", "Completa todos los campos.")
            return
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT ubicacion_id FROM UBICACIONES WHERE nombre_ubicacion = %s", (ubicacion,))
                ub_result = cursor.fetchone()
                cursor.execute("SELECT tipo_id FROM TIPOS_MANTENIMIENTO WHERE nombre_tipo = %s", (tipo,))
                tp_result = cursor.fetchone()
                
                cursor.execute(
                    "UPDATE EQUIPOS SET nombre_equipo=%s, marca=%s, serie=%s, ubicacion_id=%s, tipo_mantenimiento_pred_id=%s WHERE equipo_id=%s",
                    (nombre, marca, serie, ub_result['ubicacion_id'], tp_result['tipo_id'], self.equipo_seleccionado)
                )
                self.connection.commit()
                
                messagebox.showinfo("✅ Éxito", f"Equipo {self.equipo_seleccionado} actualizado.")
                self.limpiar_form_equipos()
                self.actualizar_tabla_equipos()
        except Exception as e:
            messagebox.showerror("❌ Error DB", f"Error al actualizar: {e}")
    
    def eliminar_equipo(self):
        """Elimina el equipo seleccionado."""
        if not self.equipo_seleccionado:
            messagebox.showwarning("⚠️ Selección", "Por favor selecciona un equipo.")
            return
        
        if messagebox.askyesno("🗑️ Confirmar Eliminación", f"¿Eliminar equipo ID {self.equipo_seleccionado}?"):
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute("DELETE FROM EQUIPOS WHERE equipo_id = %s", (self.equipo_seleccionado,))
                    self.connection.commit()
                    messagebox.showinfo("✅ Éxito", "Equipo eliminado correctamente.")
                    self.limpiar_form_equipos()
                    self.actualizar_tabla_equipos()
            except pymysql.err.IntegrityError:
                messagebox.showerror("❌ Error", "No se puede eliminar: el equipo tiene mantenimientos asociados.")
            except Exception as e:
                messagebox.showerror("❌ Error DB", f"Error al eliminar: {e}")
    
    def on_equipos_click(self, event):
        """Carga datos del equipo seleccionado en el formulario."""
        selected = self.equipos_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        values = self.equipos_tree.item(item)['values']
        
        self.equipo_seleccionado = values[0]
        self.eq_nombre.delete(0, 'end')
        self.eq_nombre.insert(0, values[1])
        self.eq_marca.delete(0, 'end')
        self.eq_marca.insert(0, values[2])
        self.eq_serie.delete(0, 'end')
        self.eq_serie.insert(0, values[3])
        self.eq_ubicacion.set(values[4])
        self.eq_tipo.set(values[5])
    
    def filtrar_equipos(self):
        """Filtra equipos por nombre o serie."""
        if not self.connection:
            return
        
        search_term = self.eq_search.get().strip().lower()
        
        for item in self.equipos_tree.get_children():
            self.equipos_tree.delete(item)
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT e.equipo_id, e.nombre_equipo, e.marca, e.serie, u.nombre_ubicacion, "
                    "tm.nombre_tipo, e.created_at FROM EQUIPOS e "
                    "JOIN UBICACIONES u ON e.ubicacion_id = u.ubicacion_id "
                    "JOIN TIPOS_MANTENIMIENTO tm ON e.tipo_mantenimiento_pred_id = tm.tipo_id "
                    "WHERE LOWER(e.nombre_equipo) LIKE %s OR LOWER(e.serie) LIKE %s "
                    "ORDER BY e.created_at DESC",
                    (f'%{search_term}%', f'%{search_term}%')
                )
                datos = cursor.fetchall()
                
                for row in datos:
                    self.equipos_tree.insert('', 'end', values=(
                        row['equipo_id'], row['nombre_equipo'], row['marca'], row['serie'],
                        row['nombre_ubicacion'], row['nombre_tipo'], row['created_at'].strftime('%Y-%m-%d %H:%M')
                    ))
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error en búsqueda: {e}")
    
    def actualizar_tabla_equipos(self):
        """Actualiza la tabla de equipos."""
        if not self.connection:
            return
        
        for item in self.equipos_tree.get_children():
            self.equipos_tree.delete(item)
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT e.equipo_id, e.nombre_equipo, e.marca, e.serie, u.nombre_ubicacion, "
                    "tm.nombre_tipo, e.created_at FROM EQUIPOS e "
                    "JOIN UBICACIONES u ON e.ubicacion_id = u.ubicacion_id "
                    "JOIN TIPOS_MANTENIMIENTO tm ON e.tipo_mantenimiento_pred_id = tm.tipo_id "
                    "ORDER BY e.created_at DESC"
                )
                self.equipos_data = cursor.fetchall()
                
                for row in self.equipos_data:
                    self.equipos_tree.insert('', 'end', values=(
                        row['equipo_id'], row['nombre_equipo'], row['marca'], row['serie'],
                        row['nombre_ubicacion'], row['nombre_tipo'], row['created_at'].strftime('%Y-%m-%d %H:%M')
                    ))
        except Exception as e:
            messagebox.showerror("❌ Error DB", f"Error al cargar equipos: {e}")
        
        # Actualizar combobox de mantenimientos con la lista recién cargada
        self.populate_mant_equipo()

    # Añadir método para poblar el combobox de equipos
    def populate_mant_equipo(self):
        """Actualiza los valores del Combobox de 'Equipo' en la pestaña de mantenimientos."""
        # ...existing code...
        try:
            values = [e['nombre_equipo'] for e in self.equipos_data] if self.equipos_data else []
            # Si el widget ya existe, actualizamos sus valores
            if hasattr(self, 'mant_equipo') and isinstance(self.mant_equipo, ttk.Combobox):
                self.mant_equipo['values'] = values
                if values:
                    try:
                        self.mant_equipo.current(0)
                    except Exception:
                        pass
        except Exception:
            # no hacemos nada si aún no existe la UI
            pass
    
    def limpiar_form_equipos(self):
        """Limpia el formulario de equipos."""
        self.eq_nombre.delete(0, 'end')
        self.eq_marca.delete(0, 'end')
        self.eq_serie.delete(0, 'end')
        self.eq_search.delete(0, 'end')
        self.equipo_seleccionado = None
        if self.catalog_data.get('ubicaciones'):
            self.eq_ubicacion.current(0)
        if self.catalog_data.get('tipos_mantenimiento'):
            self.eq_tipo.current(0)
    
    # ========== PESTAÑA 2: CALENDARIO ==========
    def setup_calendario_tab(self):
        """Diseña la pestaña de CALENDARIO con tkcalendar profesional."""
        main_frame = ttk.Frame(self.frame_calendario, padding="15 15 15 15")
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="📅 Agenda de Mantenimientos", style='Subtitle.TLabel').pack(pady=10)
        
        # Frame para calendario y lista
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill='both', expand=True, pady=10)
        
        # Lado izquierdo: Calendario interactivo
        left_frame = ttk.LabelFrame(content_frame, text="📆 Selecciona una Fecha", padding="10 10 10 10")
        left_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        self.calendar = Calendar(left_frame, selectmode='day', year=datetime.now().year, 
                                 month=datetime.now().month, day=datetime.now().day,
                                 font=('Arial', 11), headersformatvar='%B %Y')
        self.calendar.pack(fill='both', expand=True, padx=5, pady=5)
        self.calendar.bind('<<CalendarSelected>>', lambda e: self.mostrar_mantenimientos_fecha())
        
        # Lado derecho: Lista de mantenimientos
        right_frame = ttk.LabelFrame(content_frame, text="📋 Mantenimientos Programados", padding="10 10 10 10")
        right_frame.pack(side='right', fill='both', expand=True, padx=5)
        
        # Scrollbar para lista
        scrollbar = ttk.Scrollbar(right_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.mant_listbox = tk.Listbox(right_frame, yscrollcommand=scrollbar.set, font=('Segoe UI', 10))
        self.mant_listbox.pack(fill='both', expand=True)
        scrollbar.config(command=self.mant_listbox.yview)
        
        # Botón para actualizar
        ttk.Button(main_frame, text="🔄 Refrescar Calendario", command=self.mostrar_mantenimientos_fecha).pack(pady=10)
        
        self.mostrar_mantenimientos_fecha()
    
    def mostrar_mantenimientos_fecha(self):
        """Muestra mantenimientos para la fecha seleccionada."""
        selected_date = self.calendar.get_date()
        
        self.mant_listbox.delete(0, 'end')
        
        if not self.connection:
            self.mant_listbox.insert('end', "❌ No hay conexión a BD")
            return
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT m.folio_id, e.nombre_equipo, m.descripcion_servicio, m.fecha_programada, ek.nombre_estado "
                    "FROM MANTENIMIENTOS m "
                    "JOIN EQUIPOS e ON m.equipo_id = e.equipo_id "
                    "JOIN ESTADOS_KANBAN ek ON m.estado_id = ek.estado_id "
                    "WHERE DATE(m.fecha_programada) = %s "
                    "ORDER BY m.fecha_programada",
                    (selected_date,)
                )
                datos = cursor.fetchall()
                
                if not datos:
                    self.mant_listbox.insert('end', f"ℹ️ No hay mantenimientos para {selected_date}")
                else:
                    self.mant_listbox.insert('end', f"📅 Mantenimientos para {selected_date}:\n")
                    self.mant_listbox.insert('end', "─" * 70)
                    for row in datos:
                        item_text = f"\n[ID:{row['folio_id']}] {row['nombre_equipo']}\n  Descripción: {row['descripcion_servicio']}\n  Estado: {row['nombre_estado']}\n"
                        self.mant_listbox.insert('end', item_text)
        except Exception as e:
            self.mant_listbox.insert('end', f"❌ Error: {e}")

    # ========== PESTAÑA 3: MANTENIMIENTOS (KANBAN MEJORADO) ==========
    def setup_mantenimientos_tab(self):
        """Diseña la pestaña de MANTENIMIENTOS con Kanban."""
        main_frame = ttk.Frame(self.frame_mantenimientos, padding="15 15 15 15")
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="✅ Gestión de Mantenimientos (Kanban)", style='Subtitle.TLabel').pack(pady=10)
        
        # === FORMULARIO ===
        form_frame = ttk.LabelFrame(main_frame, text="📝 Nuevo Mantenimiento", padding="10 10 10 10")
        form_frame.pack(fill='x', pady=10)
        
        ttk.Label(form_frame, text="Equipo:", style='Normal.TLabel').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.mant_equipo = ttk.Combobox(form_frame, state='readonly', width=30)
        self.mant_equipo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        # Poblar el combobox de equipos con la lista actual (puede haberse cargado antes)
        self.populate_mant_equipo()
        
        ttk.Label(form_frame, text="Descripción:", style='Normal.TLabel').grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.mant_desc = ttk.Entry(form_frame, width=30)
        self.mant_desc.grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        
        ttk.Label(form_frame, text="Costo Inicial:", style='Normal.TLabel').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.mant_costo = ttk.Entry(form_frame, width=15)
        self.mant_costo.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(form_frame, text="Fecha Programada:", style='Normal.TLabel').grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.mant_fecha = ttk.Entry(form_frame, width=20)
        self.mant_fecha.insert(0, (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
        self.mant_fecha.grid(row=1, column=3, padx=5, pady=5, sticky='ew')
        
        ttk.Button(form_frame, text="✅ Crear", command=self.crear_mantenimiento).grid(row=2, column=3, sticky='e', padx=5, pady=10)
        
        # === VISTA KANBAN ===
        ttk.Label(main_frame, text="📊 Tablero Kanban", style='Subtitle.TLabel').pack(pady=(20, 10))
        
        kanban_frame = ttk.Frame(main_frame)
        kanban_frame.pack(fill='both', expand=True)
        
        self.kanban_frames = {}
        estados = self.catalog_data.get('estados_kanban', [])
        
        for estado in estados:
            self.create_kanban_column(kanban_frame, estado)
        
        self.actualizar_kanban()
    
    def create_kanban_column(self, parent, estado):
        """Crea una columna Kanban."""
        col_frame = ttk.LabelFrame(parent, text=f"{estado['nombre_estado']}", padding="10 10 10 10")
        col_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        scroll_frame = ttk.Frame(col_frame)
        scroll_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(scroll_frame, bg='#f0f0f0', highlightthickness=0, height=500)
        scrollbar = ttk.Scrollbar(scroll_frame, orient='vertical', command=canvas.yview)
        scrollable = ttk.Frame(canvas, padding="5")
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.kanban_frames[estado['estado_id']] = (scrollable, estado)
    
    def crear_mantenimiento(self):
        """Crea un nuevo mantenimiento."""
        equipo = self.mant_equipo.get()
        desc = self.mant_desc.get().strip()
        costo_str = self.mant_costo.get().strip()
        fecha_str = self.mant_fecha.get().strip()
        
        if not all([equipo, desc, costo_str, fecha_str]):
            messagebox.showwarning("⚠️ Campos Incompletos", "Completa todos los campos.")
            return
        
        # Validar costo
        try:
            costo = float(costo_str)
        except ValueError:
            messagebox.showerror("❌ Error", "El costo debe ser un número.")
            return
        
        # Validar formato fecha YYYY-MM-DD
        try:
            fecha_date = datetime.strptime(fecha_str, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("❌ Error", "Formato de fecha inválido. Usa AAAA-MM-DD.")
            return
        
        # Buscar equipo_id en memoria
        equipo_id = None
        for eq in self.equipos_data:
            if eq['nombre_equipo'] == equipo:
                equipo_id = eq['equipo_id']
                break
        
        if not equipo_id:
            messagebox.showerror("❌ Error", "Equipo no válido.")
            return
        
        # construir fecha_programada como string (día seleccionado a las 23:59:59)
        fecha_programada_str = fecha_date.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%d %H:%M:%S')
        
        # Insertar usando GREATEST para asegurar fecha_programada >= NOW()
        try:
            with self.connection.cursor() as cursor:
                try:
                    sql = (
                        "INSERT INTO MANTENIMIENTOS (equipo_id, fecha_ingreso, fecha_programada, "
                        "descripcion_servicio, costo_inicial, estado_id) "
                        "VALUES (%s, NOW(), GREATEST(%s, NOW() + INTERVAL 60 SECOND), %s, %s, 1)"
                    )
                    cursor.execute(sql, (equipo_id, fecha_programada_str, desc, costo))
                    self.connection.commit()
                except pymysql.err.IntegrityError as ie:
                    messagebox.showerror("❌ Error DB", f"Error de integridad: {ie}\nPosible causa: violación de FK o CHECK.")
                    return
                except pymysql.err.OperationalError as oe:
                    # Manejar error 4025 (constraint CHECK) explícitamente
                    code = oe.args[0] if isinstance(oe.args, (list, tuple)) and oe.args else None
                    if code == 4025 or 'CONSTRAINT' in str(oe).upper():
                        messagebox.showerror("❌ Error DB", "Violación de constraint al insertar mantenimiento (fecha_programada < fecha_ingreso). Ajusta la fecha o usa una fecha futura.")
                    else:
                        messagebox.showerror("❌ Error DB", f"Error al insertar mantenimiento: {oe}")
                    return
                except Exception as e:
                    messagebox.showerror("❌ Error DB", f"Error al insertar mantenimiento: {e}")
                    return
        except Exception as e:
            messagebox.showerror("❌ Error DB", f"Error de conexión/ejecución: {e}")
            return
        
        # Éxito
        messagebox.showinfo("✅ Éxito", "Mantenimiento creado correctamente.")
        self.mant_desc.delete(0, 'end')
        self.mant_costo.delete(0, 'end')
        self.mant_fecha.delete(0, 'end')
        self.mant_fecha.insert(0, (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
        self.actualizar_kanban()
    
    def actualizar_kanban(self):
        """Actualiza el tablero Kanban."""
        if not self.connection:
            return
        
        for scrollable, _ in self.kanban_frames.values():
            for widget in scrollable.winfo_children():
                widget.destroy()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT m.folio_id, e.nombre_equipo, m.descripcion_servicio, m.estado_id, "
                    "m.avance_porcentaje, m.costo_inicial, m.observacion FROM MANTENIMIENTOS m "
                    "JOIN EQUIPOS e ON m.equipo_id = e.equipo_id "
                    "ORDER BY m.created_at DESC"
                )
                datos = cursor.fetchall()
                
                for row in datos:
                    estado_id = row['estado_id']
                    if estado_id in self.kanban_frames:
                        scrollable, estado = self.kanban_frames[estado_id]
                        
                        card = ttk.Frame(scrollable, relief='solid', borderwidth=1)
                        card.pack(fill='x', pady=5, padx=2)
                        
                        # Header
                        header = ttk.Frame(card)
                        header.pack(fill='x', padx=5, pady=3)
                        ttk.Label(header, text=f"ID: {row['folio_id']}", 
                                 font=('Segoe UI', 10, 'bold'), foreground='#2c5aa0').pack(anchor='w')
                        ttk.Label(header, text=f"💰 ${row['costo_inicial']:.2f}", 
                                 font=('Segoe UI', 9), foreground='#27ae60').pack(anchor='w')
                        
                        # Body
                        ttk.Label(card, text=f"Equipo: {row['nombre_equipo']}", 
                                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=5)
                        ttk.Label(card, text=f"{row['descripcion_servicio']}", 
                                 font=('Segoe UI', 9), wraplength=150).pack(anchor='w', padx=5, pady=3)
                        
                        # Observación breve
                        if row.get('observacion'):
                            ttk.Label(card, text=f"Obs: {row['observacion'][:80]}", font=('Segoe UI', 8), foreground='#666').pack(anchor='w', padx=5)
                        
                        # Barra de progreso
                        progress = ttk.Progressbar(card, length=150, mode='determinate', 
                                                   value=row['avance_porcentaje'], orient='horizontal')
                        progress.pack(fill='x', padx=5, pady=3)
                        ttk.Label(card, text=f"{row['avance_porcentaje']:.0f}% completado", 
                                 font=('Segoe UI', 8)).pack(anchor='center', pady=2)
                        
                        # Botones: editar y gestionar material / historial
                        btns = ttk.Frame(card)
                        btns.pack(fill='x', padx=5, pady=3)
                        ttk.Button(btns, text="✏️ Editar Progreso", 
                                  command=lambda fid=row['folio_id']: self.editar_progreso_mantenimiento(fid)).pack(side='left', padx=3)
                        
                        # Mostrar botón "Material recibido" solo si columna corresponde a "En Espera de Material"
                        # Detectamos por nombre del estado cargado en self.kanban_frames
                        estado_nombre = estado.get('nombre_estado') if isinstance(estado, dict) else None
                        if estado_nombre and "Espera" in estado_nombre:
                            ttk.Button(btns, text="📦 Material recibido", 
                                       command=lambda fid=row['folio_id']: self.mark_material_received(fid)).pack(side='left', padx=3)
                        
                        # Botón para ver historial
                        ttk.Button(btns, text="🕘 Ver Historial", command=lambda fid=row['folio_id']: self.show_historial_mantenimiento(fid)).pack(side='right', padx=3)
        except Exception as e:
            print(f"Error en Kanban: {e}")
    
    def editar_progreso_mantenimiento(self, folio_id):
        """Abre diálogo para editar progreso de mantenimiento."""
        nuevo_progreso = simpledialog.askinteger("Editar Progreso", 
                                                 "Ingresa el porcentaje de avance (0-100):", 
                                                 minvalue=0, maxvalue=100)
        if nuevo_progreso is None:
            return
        
        try:
            # Determinar estado basado en progreso
            nuevo_estado = 1 if nuevo_progreso == 0 else (2 if nuevo_progreso < 100 else 4)
            
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE MANTENIMIENTOS SET avance_porcentaje=%s, estado_id=%s WHERE folio_id=%s",
                    (nuevo_progreso, nuevo_estado, folio_id)
                )
                self.connection.commit()
            
            messagebox.showinfo("✅ Éxito", f"Progreso actualizado a {nuevo_progreso}%")
            self.actualizar_kanban()
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error: {e}")
    
    # ========== PESTAÑA 4: REPORTES Y EXPORTACIÓN ==========
    def setup_reportes_tab(self):
        """Diseña la pestaña de REPORTES."""
        main_frame = ttk.Frame(self.frame_reportes, padding="15 15 15 15")
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="📈 Reportes y Exportación", style='Subtitle.TLabel').pack(pady=10)
        
        # Botones de reportes
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)
        
        ttk.Button(btn_frame, text="📊 Total Equipos", command=self.reporte_equipos).pack(side='left', padx=8, pady=5)
        ttk.Button(btn_frame, text="🔧 Pendientes", command=self.reporte_pendientes).pack(side='left', padx=8, pady=5)
        ttk.Button(btn_frame, text="💰 Costos", command=self.reporte_costos).pack(side='left', padx=8, pady=5)
        ttk.Button(btn_frame, text="📋 Completo", command=self.reporte_completo).pack(side='left', padx=8, pady=5)
        ttk.Button(btn_frame, text="💾 Exportar CSV", command=self.exportar_csv).pack(side='left', padx=8, pady=5)
        
        # Área de texto
        self.reporte_text = tk.Text(main_frame, height=28, width=130, font=('Courier New', 9))
        self.reporte_text.pack(fill='both', expand=True, pady=10)
    
    def reporte_equipos(self):
        """Reporte de equipos por ubicación."""
        self.reporte_text.delete('1.0', 'end')
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT u.nombre_ubicacion, COUNT(*) as total FROM EQUIPOS e "
                    "JOIN UBICACIONES u ON e.ubicacion_id = u.ubicacion_id "
                    "GROUP BY u.nombre_ubicacion ORDER BY total DESC"
                )
                datos = cursor.fetchall()
                
                self.reporte_text.insert('end', "=" * 100 + "\n")
                self.reporte_text.insert('end', "REPORTE: EQUIPOS POR UBICACIÓN\n")
                self.reporte_text.insert('end', f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.reporte_text.insert('end', "=" * 100 + "\n\n")
                
                total = 0
                for row in datos:
                    self.reporte_text.insert('end', f"📍 {row['nombre_ubicacion']:<50} {row['total']:>5} equipos\n")
                    total += row['total']
                
                self.reporte_text.insert('end', f"\n{'─' * 100}\n")
                self.reporte_text.insert('end', f"TOTAL GENERAL: {total} equipos\n")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error: {e}")
    
    def reporte_pendientes(self):
        """Reporte de mantenimientos pendientes."""
        self.reporte_text.delete('1.0', 'end')
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT m.folio_id, e.nombre_equipo, m.descripcion_servicio, ek.nombre_estado, m.avance_porcentaje, m.fecha_programada "
                    "FROM MANTENIMIENTOS m "
                    "JOIN EQUIPOS e ON m.equipo_id = e.equipo_id "
                    "JOIN ESTADOS_KANBAN ek ON m.estado_id = ek.estado_id "
                    "WHERE m.estado_id != 4 ORDER BY m.fecha_programada"
                )
                datos = cursor.fetchall()
                
                self.reporte_text.insert('end', "=" * 140 + "\n")
                self.reporte_text.insert('end', "REPORTE: MANTENIMIENTOS PENDIENTES\n")
                self.reporte_text.insert('end', f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.reporte_text.insert('end', "=" * 140 + "\n\n")
                self.reporte_text.insert('end', f"{'Folio':<8} {'Equipo':<30} {'Descripción':<30} {'Estado':<20} {'Avance':<10} {'Fecha':<15}\n")
                self.reporte_text.insert('end', f"{'-'*140}\n")
                
                for row in datos:
                    self.reporte_text.insert('end', 
                        f"{row['folio_id']:<8} {row['nombre_equipo']:<30} {row['descripcion_servicio']:<30} {row['nombre_estado']:<20} {row['avance_porcentaje']:<10.0f}% {row['fecha_programada'].strftime('%Y-%m-%d'):<15}\n")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error: {e}")
    
    def reporte_costos(self):
        """Reporte de costos."""
        self.reporte_text.delete('1.0', 'end')
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT SUM(costo_inicial) as costo_total FROM MANTENIMIENTOS")
                total = cursor.fetchone()['costo_total'] or 0
                
                cursor.execute(
                    "SELECT e.nombre_equipo, COUNT(*) as cantidad, SUM(m.costo_inicial) as total FROM MANTENIMIENTOS m "
                    "JOIN EQUIPOS e ON m.equipo_id = e.equipo_id "
                    "GROUP BY e.nombre_equipo ORDER BY total DESC"
                )
                datos = cursor.fetchall()
                
                self.reporte_text.insert('end', "=" * 100 + "\n")
                self.reporte_text.insert('end', "REPORTE: COSTOS DE MANTENIMIENTO\n")
                self.reporte_text.insert('end', f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.reporte_text.insert('end', "=" * 100 + "\n\n")
                self.reporte_text.insert('end', f"{'Equipo':<50} {'Cantidad':<12} {'Costo Total':<20}\n")
                self.reporte_text.insert('end', f"{'-'*100}\n")
                
                for row in datos:
                    self.reporte_text.insert('end', f"{row['nombre_equipo']:<50} {row['cantidad']:<12} ${row['total']:>10,.2f}\n")
                
                self.reporte_text.insert('end', f"\n{'─' * 100}\n")
                self.reporte_text.insert('end', f"💰 COSTO TOTAL GENERAL: ${total:,.2f}\n")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error: {e}")
    
    def reporte_completo(self):
        """Reporte completo del sistema."""
        self.reporte_text.delete('1.0', 'end')
        
        try:
            with self.connection.cursor() as cursor:
                # Estadísticas generales
                cursor.execute("SELECT COUNT(*) as total FROM EQUIPOS")
                total_equipos = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as total FROM MANTENIMIENTOS")
                total_mantenimientos = cursor.fetchone()['total']
                
                cursor.execute("SELECT SUM(costo_inicial) as total FROM MANTENIMIENTOS")
                costo_total = cursor.fetchone()['total'] or 0
                
                self.reporte_text.insert('end', "╔" + "═" * 98 + "╗\n")
                self.reporte_text.insert('end', "║" + " " * 20 + "REPORTE COMPLETO DEL SISTEMA" + " " * 50 + "║\n")
                self.reporte_text.insert('end', "║" + " " * 15 + f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + " " * 50 + "║\n")
                self.reporte_text.insert('end', "╚" + "═" * 98 + "╝\n\n")
                
                self.reporte_text.insert('end', "📊 ESTADÍSTICAS GENERALES:\n")
                self.reporte_text.insert('end', f"  • Total de Equipos: {total_equipos}\n")
                self.reporte_text.insert('end', f"  • Total de Mantenimientos: {total_mantenimientos}\n")
                self.reporte_text.insert('end', f"  • Costo Total Invertido: ${costo_total:,.2f}\n\n")
                
                # Detalles por ubicación
                self.reporte_text.insert('end', "📍 EQUIPOS POR UBICACIÓN:\n")
                cursor.execute(
                    "SELECT u.nombre_ubicacion, COUNT(*) as total FROM EQUIPOS e "
                    "JOIN UBICACIONES u ON e.ubicacion_id = u.ubicacion_id "
                    "GROUP BY u.nombre_ubicacion ORDER BY total DESC"
                )
                for row in cursor.fetchall():
                    self.reporte_text.insert('end', f"  • {row['nombre_ubicacion']}: {row['total']} equipos\n")
                
                self.reporte_text.insert('end', "\n🔧 MANTENIMIENTOS POR ESTADO:\n")
                cursor.execute(
                    "SELECT ek.nombre_estado, COUNT(*) as total FROM MANTENIMIENTOS m "
                    "JOIN ESTADOS_KANBAN ek ON m.estado_id = ek.estado_id "
                    "GROUP BY m.estado_id ORDER BY ek.orden"
                )
                for row in cursor.fetchall():
                    self.reporte_text.insert('end', f"  • {row['nombre_estado']}: {row['total']} mantenimientos\n")
                
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error: {e}")
    
    def exportar_csv(self):
        """Exporta reportes a CSV."""
        try:
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", 
                                                     filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
            if not file_path:
                return
            
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT e.equipo_id, e.nombre_equipo, e.marca, e.serie, u.nombre_ubicacion, "
                    "tm.nombre_tipo, COUNT(m.folio_id) as mantenimientos FROM EQUIPOS e "
                    "LEFT JOIN UBICACIONES u ON e.ubicacion_id = u.ubicacion_id "
                    "LEFT JOIN TIPOS_MANTENIMIENTO tm ON e.tipo_mantenimiento_pred_id = tm.tipo_id "
                    "LEFT JOIN MANTENIMIENTOS m ON e.equipo_id = m.equipo_id "
                    "GROUP BY e.equipo_id"
                )
                datos = cursor.fetchall()
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['ID', 'Nombre', 'Marca', 'Serie', 'Ubicación', 'Tipo', 'Mantenimientos']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in datos:
                    writer.writerow({
                        'ID': row['equipo_id'],
                        'Nombre': row['nombre_equipo'],
                        'Marca': row['marca'],
                        'Serie': row['serie'],
                        'Ubicación': row['nombre_ubicacion'],
                        'Tipo': row['nombre_tipo'],
                        'Mantenimientos': row['mantenimientos']
                    })
            
            messagebox.showinfo("✅ Éxito", f"Datos exportados a:\n{file_path}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al exportar: {e}")
    
    # ========== PESTAÑA 5: CONFIGURACIÓN ==========
    def setup_config_tab(self):
        """Diseña la pestaña de CONFIGURACIÓN."""
        main_frame = ttk.Frame(self.frame_config, padding="15 15 15 15")
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="⚙️ Configuración del Sistema", style='Subtitle.TLabel').pack(pady=10)
        
        # Información de conexión
        info_frame = ttk.LabelFrame(main_frame, text="🔌 Información de Conexión", padding="15 15 15 15")
        info_frame.pack(fill='x', pady=10)
        
        status = "✅ CONECTADO" if self.connection else "❌ DESCONECTADO"
        ttk.Label(info_frame, text=f"Estado: {status}", style='Normal.TLabel').pack(anchor='w', pady=5)
        ttk.Label(info_frame, text=f"Servidor Master: {DB_CONFIG['host']}", style='Normal.TLabel').pack(anchor='w', pady=5)
        ttk.Label(info_frame, text=f"Base de Datos: {DB_CONFIG['database']}", style='Normal.TLabel').pack(anchor='w', pady=5)
        ttk.Label(info_frame, text=f"Usuario: {DB_CONFIG['user']}", style='Normal.TLabel').pack(anchor='w', pady=5)
        
        # Verificación de réplica
        replica_frame = ttk.LabelFrame(main_frame, text="🔄 Estado de Réplica", padding="15 15 15 15")
        replica_frame.pack(fill='x', pady=10)
        
        ttk.Button(replica_frame, text="🔍 Verificar Estado de Réplica", command=self.verificar_replica).pack(pady=10)
        
        self.replica_text = tk.Text(replica_frame, height=10, width=100, font=('Courier', 9))
        self.replica_text.pack(fill='both', expand=True, pady=10)
        
        # Limpieza y mantenimiento
        maint_frame = ttk.LabelFrame(main_frame, text="🧹 Mantenimiento", padding="15 15 15 15")
        maint_frame.pack(fill='x', pady=10)
        
        ttk.Button(maint_frame, text="🔄 Reconectar a BD", command=self.reconectar_bd).pack(side='left', padx=10, pady=10)
        ttk.Button(maint_frame, text="📊 Estadísticas de BD", command=self.mostrar_estadisticas_bd).pack(side='left', padx=10, pady=10)
    
    def verificar_replica(self):
        """Verifica el estado de la réplica."""
        self.replica_text.delete('1.0', 'end')
        self.replica_text.insert('end', "🔍 Verificando estado de réplica...\n\n")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW MASTER STATUS")
                master_status = cursor.fetchone()
                
                self.replica_text.insert('end', "═ MASTER STATUS ═\n")
                if master_status:
                    for key, value in master_status.items():
                        self.replica_text.insert('end', f"  {key}: {value}\n")
                else:
                    self.replica_text.insert('end', "No se pudo obtener información del Master\n")
                
                self.replica_text.insert('end', "\n" + "═" * 50 + "\n\n")
                self.replica_text.insert('end', "✅ Verificación completada.\n")
        except Exception as e:
            self.replica_text.insert('end', f"❌ Error: {e}\n")
    
    def reconectar_bd(self):
        """Reconecta a la base de datos."""
        try:
            if self.connection:
                self.connection.close()
            
            if self.db_connect():
                self.load_catalog_data()
                messagebox.showinfo("✅ Éxito", "Reconexión exitosa a la base de datos.")
            else:
                messagebox.showerror("❌ Error", "No se pudo reconectar a la base de datos.")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error en reconexión: {e}")
    
    def mostrar_estadisticas_bd(self):
        """Muestra estadísticas de la BD."""
        self.replica_text.delete('1.0', 'end')
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT TABLE_NAME, TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s", 
                             (DB_CONFIG['database'],))
                datos = cursor.fetchall()
                
                self.replica_text.insert('end', "═ ESTADÍSTICAS DE TABLAS ═\n\n")
                for row in datos:
                    self.replica_text.insert('end', f"📋 {row['TABLE_NAME']}: {row['TABLE_ROWS']} registros\n")
                
                self.replica_text.insert('end', "\n" + "═" * 50 + "\n")
                total_registros = sum(row['TABLE_ROWS'] for row in datos)
                self.replica_text.insert('end', f"TOTAL: {total_registros} registros en la BD\n")
        except Exception as e:
            self.replica_text.insert('end', f"❌ Error: {e}\n")
    
    # --- Nuevas funciones: marcar material recibido y ver historial ---
    def mark_material_received(self, folio_id):
        """Marca que llegó el material: pide detalle, actualiza mantenimiento y crea entrada historial."""
        material = simpledialog.askstring("Material recibido", "Describe el material recibido (pieza, cantidad, nota):")
        if not material:
            return
        usuario = simpledialog.askstring("Usuario", "Nombre del responsable que confirma recepción:", initialvalue="Técnico")
        try:
            with self.connection.cursor() as cursor:
                # Actualizar mantenimiento: cambiar a 'En Revisión' (estado_id correspondiente)
                # Buscamos el estado_id de 'En Revisión'
                cursor.execute("SELECT estado_id FROM ESTADOS_KANBAN WHERE nombre_estado = %s LIMIT 1", ("En Revisión",))
                row = cursor.fetchone()
                estado_revision_id = row['estado_id'] if row else 2
                # append observacion y asegurar avance mínimo 5%
                cursor.execute("SELECT observacion, avance_porcentaje FROM MANTENIMIENTOS WHERE folio_id=%s", (folio_id,))
                m = cursor.fetchone() or {}
                nueva_obs = (m.get('observacion') or '') + f"\nMaterial recibido: {material} - {usuario} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                nuevo_avance = max(float(m.get('avance_porcentaje', 0)), 5.0)
                cursor.execute(
                    "UPDATE MANTENIMIENTOS SET estado_id=%s, observacion=%s, avance_porcentaje=%s WHERE folio_id=%s",
                    (estado_revision_id, nueva_obs, nuevo_avance, folio_id)
                )
                # Insertar en historial
                cursor.execute(
                    "INSERT INTO MANT_HISTORIAL (folio_id, accion, detalle, usuario) VALUES (%s, %s, %s, %s)",
                    (folio_id, "Material recibido", material, usuario)
                )
                self.connection.commit()
            messagebox.showinfo("✅ Material registrado", "Se registró la recepción del material y se reanudó el mantenimiento.")
            self.actualizar_kanban()
        except Exception as e:
            messagebox.showerror("❌ Error DB", f"No se pudo registrar material: {e}")

    def show_historial_mantenimiento(self, folio_id):
        """Muestra en ventana simple el historial de acciones para un mantenimiento."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT historial_id, accion, detalle, usuario, created_at FROM MANT_HISTORIAL WHERE folio_id=%s ORDER BY created_at DESC", (folio_id,))
                rows = cursor.fetchall()
        except Exception as e:
            messagebox.showerror("❌ Error DB", f"No se pudo consultar historial: {e}")
            return
        # Crear ventana modal
        win = tk.Toplevel(self.root)
        win.title(f"Historial - Folio {folio_id}")
        win.geometry("600x400")
        txt = tk.Text(win, wrap='word', font=('Segoe UI', 10))
        txt.pack(fill='both', expand=True, padx=8, pady=8)
        if not rows:
            txt.insert('end', "No hay historial para este mantenimiento.")
        else:
            for r in rows:
                txt.insert('end', f"[{r['created_at'].strftime('%Y-%m-%d %H:%M')}] {r['accion']} - {r.get('usuario') or ''}\n{r.get('detalle') or ''}\n\n")
        ttk.Button(win, text="Cerrar", command=win.destroy).pack(pady=6)


# --- EJECUTAR LA APLICACIÓN ---
if __name__ == "__main__":
    root = tk.Tk()
    app = MantenimientoApp(root)
    root.mainloop()
