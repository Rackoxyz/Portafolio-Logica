import mysql.connector
import tkinter as tk
from tkinter import messagebox, Toplevel, ttk
from decimal import Decimal

# --- CONFIGURACIÓN DE CONEXIÓN (APUNTA AL MASTER) ---
DB_CONFIG = {
    'host': '192.168.56.10', 
    'user': 'root', 
    'password': 'isaac.rick', # <--- ¡REEMPLAZAR!
    'database': 'chinos_cafe'
}

# --- FUNCIÓN DE CONEXIÓN ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        messagebox.showerror("Error de Conexión", f"No se pudo conectar a la base de datos: {err}")
        return None

# --- APLICACIÓN COMPLETA DE PUNTO DE VENTA ---
class POSApp:
    def __init__(self, master):
        self.master = master
        master.title("POS - Chino's Cafe (FINAL)")
        master.geometry("450x350")
        self.carrito = {} # Usamos diccionario para agrupar items por ID
        
        self.conn = get_db_connection()
        if not self.conn:
            master.destroy()
            return
        
        self.setup_ui()

    def setup_ui(self):
        main_frame = tk.Frame(self.master, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)

        tk.Label(main_frame, text="Chino's Cafe - Tareas", font=("Arial", 18, "bold")).pack(pady=10)
        
        # Botones de Funcionalidad
        tk.Button(main_frame, text="1. VER INVENTARIO Y STOCK", command=self.show_products_window, height=2).pack(pady=8, fill='x')
        tk.Button(main_frame, text="2. INICIAR VENTA / FACTURAR", command=self.register_sale_window, height=2).pack(pady=8, fill='x')
        tk.Button(main_frame, text="3. AÑADIR NUEVO PRODUCTO", command=self.add_product_window, height=2).pack(pady=8, fill='x')
        tk.Button(main_frame, text="4. SALIR", command=self.master.quit, height=2).pack(pady=8, fill='x')
        
    # --- VENTANA DE INVENTARIO (PRODUCTOS Y STOCK) ---
    def show_products_window(self):
        """Muestra una ventana con todos los productos y su stock."""
        if not self.conn: return
        
        window = Toplevel(self.master)
        window.title("Inventario Actual")
        window.geometry("600x400")
        
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id_producto, nombre, precio, stock FROM productos ORDER BY id_producto")
            results = cursor.fetchall()
            
            tk.Label(window, text="LISTA DE PRODUCTOS Y STOCK", font=("Arial", 14, "bold")).pack(pady=10)

            # Treeview para la tabla
            tree = ttk.Treeview(window, columns=('ID', 'Nombre', 'Precio', 'Stock'), show='headings')
            tree.heading('ID', text='ID')
            tree.heading('Nombre', text='Nombre del Producto')
            tree.heading('Precio', text='Precio')
            tree.heading('Stock', text='Stock Actual')
            
            # Establecer anchos
            tree.column('ID', width=50, anchor='center')
            tree.column('Nombre', width=250)
            tree.column('Precio', width=100, anchor='e')
            tree.column('Stock', width=100, anchor='center')

            for item in results:
                tree.insert('', 'end', values=(item['id_producto'], item['nombre'], f"${item['precio']:.2f}", item['stock']))

            tree.pack(fill='both', expand=True, padx=10, pady=10)
            
        except mysql.connector.Error as err:
            messagebox.showerror("Error de Consulta", f"Error al obtener productos: {err}")
        finally:
            cursor.close()

    # --- VENTANA PARA AÑADIR PRODUCTO ---
    def add_product_window(self):
        """Permite añadir nuevos productos al inventario."""
        window = Toplevel(self.master)
        window.title("Añadir Nuevo Producto")
        
        # Campos de entrada
        tk.Label(window, text="Nombre:").grid(row=0, column=0, padx=5, pady=5)
        name_entry = tk.Entry(window)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(window, text="Precio:").grid(row=1, column=0, padx=5, pady=5)
        price_entry = tk.Entry(window)
        price_entry.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(window, text="Stock Inicial:").grid(row=2, column=0, padx=5, pady=5)
        stock_entry = tk.Entry(window)
        stock_entry.grid(row=2, column=1, padx=5, pady=5)
        
        def save_product():
            name = name_entry.get()
            try:
                # Usar Decimal para manejo exacto de moneda
                price = Decimal(price_entry.get()) 
                stock = int(stock_entry.get())
            except Exception:
                messagebox.showerror("Error", "Precio y Stock deben ser números válidos.")
                return
            
            cursor = self.conn.cursor()
            sql = "INSERT INTO productos (nombre, precio, stock) VALUES (%s, %s, %s)"
            
            try:
                cursor.execute(sql, (name, price, stock))
                self.conn.commit()
                messagebox.showinfo("Éxito", f"Producto '{name}' añadido con éxito. Stock: {stock}")
                window.destroy()
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error al guardar producto: {err}")
            finally:
                cursor.close()

        tk.Button(window, text="Guardar Producto", command=save_product).grid(row=3, column=0, columnspan=2, pady=10)

    # --- VENTANA DE VENTA INTERACTIVA Y FACTURACIÓN ---
    def register_sale_window(self):
        """Gestiona el proceso de facturación: añadir productos, calcular total y registrar."""
        window = Toplevel(self.master)
        window.title("Caja Registradora")
        window.geometry("850x600")
        
        self.carrito = {} # Limpiar carrito al iniciar nueva venta
        
        # Frames
        left_frame = tk.Frame(window, width=300, padx=10, pady=10)
        left_frame.pack(side='left', fill='y')
        
        right_frame = tk.Frame(window, width=500, padx=10, pady=10)
        right_frame.pack(side='right', fill='both', expand=True)

        # --- PANEL DE AÑADIR PRODUCTO ---
        tk.Label(left_frame, text="Añadir Producto", font=("Arial", 12, "bold")).pack(pady=10)
        
        tk.Label(left_frame, text="ID Producto:").pack(pady=5)
        id_entry = tk.Entry(left_frame)
        id_entry.pack(pady=5)
        
        tk.Label(left_frame, text="Cantidad:").pack(pady=5)
        qty_entry = tk.Entry(left_frame)
        qty_entry.pack(pady=5)

        tk.Button(left_frame, text="AÑADIR A FACTURA", 
                  command=lambda: self._add_item_to_cart(id_entry.get(), qty_entry.get(), tree, total_label)).pack(pady=15, fill='x')

        # --- PANEL DE LA FACTURA (CARRITO) ---
        tk.Label(right_frame, text="FACTURA ACTUAL", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Treeview para la tabla de la factura
        tree = ttk.Treeview(right_frame, columns=('ID', 'Nombre', 'Cantidad', 'Precio_U', 'Subtotal'), show='headings')
        tree.heading('ID', text='ID')
        tree.heading('Nombre', text='Producto')
        tree.heading('Cantidad', text='Cant.')
        tree.heading('Precio_U', text='P. Unit.')
        tree.heading('Subtotal', text='Subtotal')
        
        # Anchos de columna
        tree.column('ID', width=50, anchor='center')
        tree.column('Cantidad', width=80, anchor='center')
        tree.column('Precio_U', width=100, anchor='e')
        tree.column('Subtotal', width=100, anchor='e')
        
        tree.pack(fill='both', expand=True)

        # Total
        self.total_value = Decimal(0)
        total_label = tk.Label(right_frame, text="TOTAL: $0.00", font=("Arial", 18, "bold"), fg="darkred")
        total_label.pack(pady=15)

        # Botón de Finalizar
        tk.Button(right_frame, text="FINALIZAR VENTA", 
                  command=lambda: self._finalize_sale(window)).pack(pady=10, fill='x')

    # --- LÓGICA DEL CARRITO (AÑADIR ITEM) ---
    def _add_item_to_cart(self, id_str, qty_str, tree, total_label):
        """Busca el producto, valida stock y lo añade al carrito/factura."""
        if not self.conn: return

        try:
            id_producto = int(id_str)
            cantidad = int(qty_str)
            if cantidad <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "ID y Cantidad deben ser números enteros positivos.")
            return

        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id_producto = %s", (id_producto,))
            product = cursor.fetchone()
            
            if not product:
                messagebox.showerror("Error", f"Producto ID {id_producto} no encontrado.")
                return
            
            # 1. Validar Stock Total
            # Sumar la cantidad ya en el carrito más la nueva cantidad
            current_cart_qty = self.carrito.get(id_producto, {}).get('cantidad', 0)
            required_stock = current_cart_qty + cantidad

            if required_stock > product['stock']:
                messagebox.showerror("Error de Stock", f"Stock insuficiente. Disponible: {product['stock']}. Ya en carrito: {current_cart_qty}")
                return

            # 2. Agregar o actualizar el carrito (diccionario)
            subtotal = Decimal(product['precio']) * cantidad
            if id_producto in self.carrito:
                self.carrito[id_producto]['cantidad'] += cantidad
                self.carrito[id_producto]['subtotal'] += subtotal
            else:
                self.carrito[id_producto] = {
                    'nombre': product['nombre'],
                    'precio_u': Decimal(product['precio']),
                    'cantidad': cantidad,
                    'subtotal': subtotal
                }
            
            # 3. Actualizar la vista (Treeview y Total)
            self._update_treeview(tree)
            self._update_total(total_label)
            
        except mysql.connector.Error as err:
            messagebox.showerror("Error SQL", f"Error al buscar producto: {err}")
        finally:
            cursor.close()

    # --- LÓGICA DEL CARRITO (ACTUALIZAR VISTA) ---
    def _update_treeview(self, tree):
        """Limpia y reconstruye el Treeview con los items agrupados del carrito."""
        for item in tree.get_children():
            tree.delete(item)
            
        for id_p, data in self.carrito.items():
            tree.insert('', 'end', values=(
                id_p, 
                data['nombre'], 
                data['cantidad'], 
                f"${data['precio_u']:.2f}", 
                f"${data['subtotal']:.2f}"
            ))

    # --- LÓGICA DEL CARRITO (ACTUALIZAR TOTAL) ---
    def _update_total(self, total_label):
        """Calcula y actualiza el total de la factura."""
        self.total_value = sum(item['subtotal'] for item in self.carrito.values())
        total_label.config(text=f"TOTAL: ${self.total_value:.2f}")

    # --- LÓGICA DE TRANSACCIÓN CRÍTICA (FINALIZAR VENTA) ---
    def _finalize_sale(self, window):
        """Registra la venta principal, el detalle y actualiza el stock en una transacción."""
        if not self.carrito:
            messagebox.showwarning("Venta Vacía", "Debes añadir al menos un producto a la factura.")
            return

        cursor = self.conn.cursor()
        
        try:
            # 1. Iniciar la transacción (IMPORTANTE: Esto garantiza la integridad)
            self.conn.start_transaction()
            
            # 2. Registrar la Venta Principal (tabla 'ventas')
            total = self.total_value
            cursor.execute("INSERT INTO ventas (fecha_venta, total) VALUES (NOW(), %s)", (total,))
            id_venta = cursor.lastrowid # Obtener el ID de la venta recién creada

            # 3. Procesar cada item del carrito y actualizar stock
            for id_producto, item in self.carrito.items():
                cantidad = item['cantidad']
                precio_u = item['precio_u']
                
                # Insertar en el detalle de la venta (tabla 'detalle_venta')
                sql_detalle = "INSERT INTO detalle_venta (id_venta, id_producto, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql_detalle, (id_venta, id_producto, cantidad, precio_u))
                
                # Actualizar Stock (Restar la cantidad vendida)
                sql_stock = "UPDATE productos SET stock = stock - %s WHERE id_producto = %s"
                cursor.execute(sql_stock, (cantidad, id_producto))
            
            # 4. Confirmar TODAS las operaciones
            self.conn.commit()
            
            messagebox.showinfo("Venta Finalizada", f"Factura #{id_venta} registrada con éxito. Total: ${total:.2f}")
            window.destroy()
            
        except mysql.connector.Error as err:
            self.conn.rollback() # Revierte si ALGO falla (Ej. error de stock, error DB)
            messagebox.showerror("Error de Venta Crítico", f"Error de transacción: {err}. Venta revertida.")
        finally:
            cursor.close()


# --- EJECUTAR APLICACIÓN ---
if __name__ == "__main__":
    root = tk.Tk()
    app = POSApp(root)
    root.mainloop()