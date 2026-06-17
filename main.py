"""
main.py
=======
Aplicación GUI Tkinter — TP5 Autómatas y Gramáticas
Sistema de seguimiento de usuarios conectados a un Access Point.

Flujo de la aplicación:
  1. El usuario selecciona el archivo CSV
  2. Se carga y valida en un hilo de fondo (progress bar reactiva)
  3. El combo de APs se pobla dinámicamente con los datos válidos
  4. El usuario elige un AP y un rango de fechas → Buscar
  5. Se muestra la tabla de resultados con estadísticas
  6. Botones para exportar a Excel y ver registros descartados
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
import sys
from datetime import datetime

# Asegurar que el directorio raíz esté en sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.lector import procesar_csv
from src.filtrador import obtener_aps, filtrar, estadisticas
from src.exportador import exportar_excel, exportar_invalidos_excel

# ---------------------------------------------------------------------------
# Paleta de colores y constantes visuales
# ---------------------------------------------------------------------------

C = {
    "bg":           "#F0F4F8",   # Fondo general (gris azulado claro)
    "panel":        "#FFFFFF",   # Fondo de paneles/cards
    "header_bg":    "#1E3A5F",   # Azul marino oscuro (barra superior)
    "header_fg":    "#FFFFFF",   # Texto en header
    "accent":       "#2563EB",   # Azul primario (botones principales)
    "accent_h":     "#1D4ED8",   # Hover del botón principal
    "success":      "#059669",   # Verde (botón exportar)
    "success_h":    "#047857",
    "danger":       "#DC2626",   # Rojo (errores / botón inválidos)
    "danger_h":     "#B91C1C",
    "warning":      "#D97706",   # Ámbar (advertencias)
    "text":         "#1E293B",   # Texto principal
    "text_m":       "#64748B",   # Texto secundario/muted
    "border":       "#CBD5E1",   # Borde de widgets
    "row_odd":      "#F0F7FF",   # Fila impar en tabla
    "row_even":     "#FFFFFF",   # Fila par en tabla
    "row_sel":      "#BFDBFE",   # Fila seleccionada
    "progress_bg":  "#E2E8F0",   # Fondo barra de progreso
    "progress_fg":  "#2563EB",   # Relleno barra de progreso
}

FONT_TITLE  = ("Segoe UI", 16, "bold")
FONT_SUB    = ("Segoe UI", 11, "bold")
FONT_NORMAL = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas",  9)

# Columnas visibles en la tabla de resultados
COLS_TABLA = [
    ("Usuario",       "Usuario",              160),
    ("MAC_Cliente",   "MAC Cliente",          180),
    ("Inicio_Dia",    "Inicio Día",            95),
    ("Inicio_Hora",   "Inicio Hora",           85),
    ("Fin_Dia",       "Fin Día",               95),
    ("Fin_Hora",      "Fin Hora",              85),
    ("Session_Time",  "Duración (s)",           85),
    ("Input_Octects", "Entrada (B)",            90),
    ("Output_Octects","Salida (B)",             90),
    ("Razon",         "Razón Terminación",     140),
]


# ===========================================================================
# VENTANA DE REGISTROS INVÁLIDOS
# ===========================================================================

class VentanaInvalidos(tk.Toplevel):
    """Ventana secundaria que muestra los registros descartados."""

    def __init__(self, parent, invalidos: list[dict]):
        super().__init__(parent)
        self.invalidos = invalidos
        self.title("Registros Inválidos / Descartados")
        self.geometry("960x560")
        self.minsize(700, 400)
        self.configure(bg=C["bg"])
        self.grab_set()  # Modal

        self._construir()

    def _construir(self):
        # --- Encabezado ---
        hdr = tk.Frame(self, bg="#8B1A1A", height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr,
            text=f"⚠  Registros Descartados — Total: {len(self.invalidos):,}",
            font=FONT_SUB, bg="#8B1A1A", fg="white",
        ).pack(side="left", padx=15, pady=10)

        # --- Barra de herramientas ---
        toolbar = tk.Frame(self, bg=C["bg"], pady=6)
        toolbar.pack(fill="x", padx=10)

        # Buscador de motivos
        tk.Label(toolbar, text="Filtrar motivo:", font=FONT_SMALL,
                 bg=C["bg"], fg=C["text"]).pack(side="left", padx=(0, 4))
        self._filtro_var = tk.StringVar()
        self._filtro_var.trace_add("write", lambda *_: self._aplicar_filtro())
        entry = ttk.Entry(toolbar, textvariable=self._filtro_var, width=35,
                          font=FONT_SMALL)
        entry.pack(side="left", padx=(0, 12))

        ttk.Button(toolbar, text="📤 Exportar a Excel",
                   command=self._exportar).pack(side="right")

        # --- Tabla ---
        frame_tabla = tk.Frame(self, bg=C["panel"])
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("num_fila", "ID", "motivo")
        self._tree = ttk.Treeview(frame_tabla, columns=cols,
                                  show="headings", selectmode="browse")
        self._tree.heading("num_fila", text="N° Fila CSV")
        self._tree.heading("ID",       text="ID")
        self._tree.heading("motivo",   text="Motivo del Descarte")
        self._tree.column("num_fila", width=100, anchor="center")
        self._tree.column("ID",       width=100, anchor="center")
        self._tree.column("motivo",   width=700, anchor="w")

        sb_v = ttk.Scrollbar(frame_tabla, orient="vertical",
                             command=self._tree.yview)
        sb_h = ttk.Scrollbar(frame_tabla, orient="horizontal",
                             command=self._tree.xview)
        self._tree.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)

        sb_v.pack(side="right", fill="y")
        sb_h.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        self._tree.tag_configure("odd",  background="#FFF8F8")
        self._tree.tag_configure("even", background="#FFFFFF")

        self._poblar(self.invalidos)

    def _poblar(self, datos: list[dict]):
        self._tree.delete(*self._tree.get_children())
        for i, inv in enumerate(datos):
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=(
                inv.get("num_fila", ""),
                inv.get("ID", ""),
                inv.get("motivo", ""),
            ), tags=(tag,))

    def _aplicar_filtro(self):
        texto = self._filtro_var.get().lower()
        if not texto:
            self._poblar(self.invalidos)
        else:
            filtrados = [
                inv for inv in self.invalidos
                if texto in inv.get("motivo", "").lower()
                or texto in inv.get("ID", "").lower()
            ]
            self._poblar(filtrados)

    def _exportar(self):
        ruta = filedialog.asksaveasfilename(
            title="Guardar registros inválidos",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"invalidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        )
        if not ruta:
            return
        try:
            exportar_invalidos_excel(self.invalidos, ruta)
            messagebox.showinfo("Exportado", f"Archivo guardado:\n{ruta}", parent=self)
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e), parent=self)


# ===========================================================================
# DIÁLOGO DE PROGRESO DE CARGA
# ===========================================================================

class DialogoProgreso(tk.Toplevel):
    """Ventana modal con barra de progreso durante la carga del CSV."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Cargando CSV…")
        self.geometry("480x200")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # no cerrar con X

        self._construir()

    def _construir(self):
        pad = {"padx": 24, "pady": 8}

        tk.Label(self, text="⚡  Procesando archivo CSV",
                 font=FONT_SUB, bg=C["bg"], fg=C["header_bg"]).pack(**pad)

        self._lbl_estado = tk.Label(
            self, text="Iniciando lectura…",
            font=FONT_SMALL, bg=C["bg"], fg=C["text_m"]
        )
        self._lbl_estado.pack(**pad)

        style = ttk.Style()
        style.configure("Azul.Horizontal.TProgressbar",
                         troughcolor=C["progress_bg"],
                         background=C["progress_fg"],
                         thickness=18)
        self._pbar = ttk.Progressbar(
            self, style="Azul.Horizontal.TProgressbar",
            mode="indeterminate", length=400
        )
        self._pbar.pack(**pad)
        self._pbar.start(12)

        self._lbl_conteo = tk.Label(
            self, text="Leídas: 0 | Válidas: 0 | Inválidas: 0",
            font=FONT_SMALL, bg=C["bg"], fg=C["text"]
        )
        self._lbl_conteo.pack(**pad)

    def actualizar(self, leidas: int, validas: int, invalidas: int):
        """Llama desde el hilo principal vía after()."""
        self._lbl_estado.config(
            text=f"Procesando fila {leidas:,}…"
        )
        self._lbl_conteo.config(
            text=f"Leídas: {leidas:,} | ✅ Válidas: {validas:,} | ❌ Inválidas: {invalidas:,}"
        )
        self.update_idletasks()

    def cerrar(self):
        self._pbar.stop()
        self.destroy()


# ===========================================================================
# APLICACIÓN PRINCIPAL
# ===========================================================================

class App(tk.Tk):
    """Ventana principal de la aplicación."""

    def __init__(self):
        super().__init__()
        self.title("Seguimiento de Conexiones Wi-Fi — TP5 Autómatas y Gramáticas")
        self.geometry("1280x780")
        self.minsize(900, 600)
        self.configure(bg=C["bg"])

        # --- Estado interno ---
        self._ruta_csv     = tk.StringVar()
        self._ap_var       = tk.StringVar()
        self._fecha_desde  = tk.StringVar(value="2019-01-01")
        self._fecha_hasta  = tk.StringVar(value="2023-12-31")

        self._df_validos   = None   # pd.DataFrame con registros válidos
        self._invalidos    = []     # list[dict] con registros inválidos
        self._df_resultado = None   # pd.DataFrame del filtro actual

        self._cola         = queue.Queue()   # comunicación con el hilo de carga
        self._evento_stop  = threading.Event()

        self._configurar_estilos()
        self._construir_interfaz()

    # -----------------------------------------------------------------------
    # Configuración de ttk.Style
    # -----------------------------------------------------------------------

    def _configurar_estilos(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Frame genérico
        style.configure("TFrame", background=C["bg"])
        style.configure("Panel.TFrame", background=C["panel"],
                        relief="flat", borderwidth=1)

        # Labels
        style.configure("TLabel", background=C["bg"],
                        foreground=C["text"], font=FONT_NORMAL)
        style.configure("Muted.TLabel", foreground=C["text_m"], font=FONT_SMALL)
        style.configure("Big.TLabel", font=("Segoe UI", 22, "bold"),
                        foreground=C["accent"])

        # Entries
        style.configure("TEntry", fieldbackground=C["panel"],
                        foreground=C["text"], font=FONT_NORMAL)

        # Combobox
        style.configure("TCombobox", fieldbackground=C["panel"],
                        foreground=C["text"], font=FONT_NORMAL)

        # Separador
        style.configure("TSeparator", background=C["border"])

        # Treeview (tabla de resultados)
        style.configure("Treeview",
                         background=C["row_even"],
                         fieldbackground=C["row_even"],
                         foreground=C["text"],
                         font=FONT_SMALL,
                         rowheight=24)
        style.configure("Treeview.Heading",
                         background=C["header_bg"],
                         foreground="white",
                         font=("Segoe UI", 9, "bold"),
                         relief="flat")
        style.map("Treeview",
                  background=[("selected", C["row_sel"])],
                  foreground=[("selected", C["text"])])
        style.map("Treeview.Heading",
                  background=[("active", C["accent"])])

    # -----------------------------------------------------------------------
    # Construcción de la interfaz
    # -----------------------------------------------------------------------

    def _construir_interfaz(self):
        # == BARRA SUPERIOR ==
        self._construir_header()

        # == CONTENIDO PRINCIPAL ==
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        # Columna izquierda: controles
        left = tk.Frame(main, bg=C["bg"], width=310)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        self._construir_panel_carga(left)
        self._construir_panel_filtros(left)
        self._construir_panel_stats(left)

        # Columna derecha: tabla de resultados
        right = tk.Frame(main, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        self._construir_tabla(right)

        # == BARRA DE ESTADO ==
        self._construir_statusbar()

    def _construir_header(self):
        header = tk.Frame(self, bg=C["header_bg"], height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🔌  Sistema de Seguimiento de Conexiones Wi-Fi",
            font=FONT_TITLE, bg=C["header_bg"], fg="white",
        ).pack(side="left", padx=20, pady=10)

        tk.Label(
            header,
            text="TP5 — Autómatas y Gramáticas",
            font=("Segoe UI", 10), bg=C["header_bg"], fg="#93C5FD",
        ).pack(side="right", padx=20)

    def _card(self, parent, titulo: str) -> tk.Frame:
        """Crea un card (panel con borde redondeado visual y título)."""
        outer = tk.Frame(parent, bg=C["bg"], pady=6)
        outer.pack(fill="x")

        tk.Label(outer, text=titulo.upper(), font=("Segoe UI", 8, "bold"),
                 bg=C["bg"], fg=C["text_m"]).pack(anchor="w", padx=4, pady=(0, 2))

        inner = tk.Frame(outer, bg=C["panel"], bd=1, relief="solid",
                         highlightbackground=C["border"], highlightthickness=1)
        inner.pack(fill="x")
        return inner

    def _boton(self, parent, texto, cmd, color, hover_color, width=22):
        """Botón con efecto hover de color."""
        btn = tk.Button(
            parent, text=texto, command=cmd,
            bg=color, fg="white", activebackground=hover_color,
            activeforeground="white", cursor="hand2",
            font=("Segoe UI", 10, "bold"), relief="flat",
            bd=0, padx=10, pady=7, width=width,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_color))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn

    def _construir_panel_carga(self, parent):
        card = self._card(parent, "📂 Archivo CSV")

        tk.Label(card, text="Ruta del archivo:", font=FONT_SMALL,
                 bg=C["panel"], fg=C["text_m"]).pack(anchor="w", padx=8, pady=(8, 2))

        fila_ruta = tk.Frame(card, bg=C["panel"])
        fila_ruta.pack(fill="x", padx=8, pady=(0, 6))

        entry_ruta = ttk.Entry(fila_ruta, textvariable=self._ruta_csv,
                               font=FONT_SMALL, width=24)
        entry_ruta.pack(side="left", fill="x", expand=True)

        tk.Button(
            fila_ruta, text="…", command=self._seleccionar_csv,
            bg=C["border"], fg=C["text"], relief="flat",
            font=FONT_NORMAL, cursor="hand2", padx=6,
        ).pack(side="left", padx=(4, 0))

        self._btn_cargar = self._boton(
            card, "⚡  Cargar y Validar CSV",
            self._iniciar_carga, C["accent"], C["accent_h"], width=26
        )
        self._btn_cargar.pack(pady=(0, 10), padx=8)

    def _construir_panel_filtros(self, parent):
        card = self._card(parent, "🔍 Filtros de Búsqueda")

        # AP
        tk.Label(card, text="Access Point (MAC_AP):", font=FONT_SMALL,
                 bg=C["panel"], fg=C["text_m"]).pack(anchor="w", padx=8, pady=(8, 2))
        self._combo_ap = ttk.Combobox(card, textvariable=self._ap_var,
                                      state="disabled", font=FONT_SMALL, width=30)
        self._combo_ap.pack(fill="x", padx=8, pady=(0, 6))

        # Fecha desde
        tk.Label(card, text="Fecha desde (YYYY-MM-DD):", font=FONT_SMALL,
                 bg=C["panel"], fg=C["text_m"]).pack(anchor="w", padx=8)
        self._entry_desde = ttk.Entry(card, textvariable=self._fecha_desde,
                                      font=FONT_SMALL, width=30)
        self._entry_desde.pack(fill="x", padx=8, pady=(2, 6))

        # Fecha hasta
        tk.Label(card, text="Fecha hasta (YYYY-MM-DD):", font=FONT_SMALL,
                 bg=C["panel"], fg=C["text_m"]).pack(anchor="w", padx=8)
        self._entry_hasta = ttk.Entry(card, textvariable=self._fecha_hasta,
                                      font=FONT_SMALL, width=30)
        self._entry_hasta.pack(fill="x", padx=8, pady=(2, 6))

        # Botones
        self._btn_buscar = self._boton(
            card, "🔍  Buscar Conexiones",
            self._buscar, C["accent"], C["accent_h"], width=26
        )
        self._btn_buscar.pack(pady=(2, 4), padx=8)
        self._btn_buscar.config(state="disabled")

        self._btn_export = self._boton(
            card, "📤  Exportar a Excel",
            self._exportar, C["success"], C["success_h"], width=26
        )
        self._btn_export.pack(pady=(0, 4), padx=8)
        self._btn_export.config(state="disabled")

        self._btn_invalidos = self._boton(
            card, "⚠  Ver Registros Inválidos",
            self._ver_invalidos, C["danger"], C["danger_h"], width=26
        )
        self._btn_invalidos.pack(pady=(0, 10), padx=8)
        self._btn_invalidos.config(state="disabled")

    def _construir_panel_stats(self, parent):
        card = self._card(parent, "📊 Estadísticas del Resultado")

        self._lbl_stat_total    = self._stat_row(card, "Conexiones encontradas:", "—")
        self._lbl_stat_usuarios = self._stat_row(card, "Usuarios únicos:",        "—")
        self._lbl_stat_macs     = self._stat_row(card, "Dispositivos únicos:",    "—")
        self._lbl_stat_tiempo   = self._stat_row(card, "Tiempo total (horas):",   "—")
        self._lbl_stat_entrada  = self._stat_row(card, "Tráfico entrada (MB):",   "—")
        self._lbl_stat_salida   = self._stat_row(card, "Tráfico salida (MB):",    "—")

        # Resumen de carga (debajo del card stats)
        resumen = self._card(parent, "📋 Resumen de Carga")
        self._lbl_validos   = self._stat_row(resumen, "Registros válidos:",   "—")
        self._lbl_invalidos = self._stat_row(resumen, "Registros inválidos:", "—")
        self._lbl_total_csv = self._stat_row(resumen, "Total leídos:",        "—")

    def _stat_row(self, parent, etiqueta: str, valor_inicial: str) -> tk.Label:
        """Fila de estadística: etiqueta + valor en negrita."""
        fila = tk.Frame(parent, bg=C["panel"])
        fila.pack(fill="x", padx=10, pady=2)
        tk.Label(fila, text=etiqueta, font=FONT_SMALL,
                 bg=C["panel"], fg=C["text_m"], anchor="w").pack(side="left")
        lbl_val = tk.Label(fila, text=valor_inicial,
                           font=("Segoe UI", 9, "bold"),
                           bg=C["panel"], fg=C["accent"], anchor="e")
        lbl_val.pack(side="right")
        return lbl_val

    def _construir_tabla(self, parent):
        # Título de la sección
        titulo_frame = tk.Frame(parent, bg=C["bg"])
        titulo_frame.pack(fill="x", pady=(0, 6))

        tk.Label(titulo_frame, text="Resultados",
                 font=FONT_SUB, bg=C["bg"], fg=C["header_bg"]).pack(side="left")

        self._lbl_n_resultados = tk.Label(
            titulo_frame, text="",
            font=FONT_SMALL, bg=C["bg"], fg=C["text_m"]
        )
        self._lbl_n_resultados.pack(side="left", padx=10)

        # Frame contenedor de la tabla
        tabla_frame = tk.Frame(parent, bg=C["panel"], bd=1,
                               relief="solid",
                               highlightbackground=C["border"],
                               highlightthickness=1)
        tabla_frame.pack(fill="both", expand=True)

        # Scrollbars
        sb_v = ttk.Scrollbar(tabla_frame, orient="vertical")
        sb_h = ttk.Scrollbar(tabla_frame, orient="horizontal")

        # Columnas del treeview
        col_ids = [c[0] for c in COLS_TABLA]
        self._tree = ttk.Treeview(
            tabla_frame,
            columns=col_ids,
            show="headings",
            yscrollcommand=sb_v.set,
            xscrollcommand=sb_h.set,
            selectmode="browse",
        )

        # Encabezados y anchos
        for campo, titulo, ancho in COLS_TABLA:
            self._tree.heading(campo, text=titulo,
                               command=lambda c=campo: self._ordenar_columna(c))
            self._tree.column(campo, width=ancho, minwidth=60, anchor="w")

        # Tags para filas alternas
        self._tree.tag_configure("odd",  background=C["row_odd"])
        self._tree.tag_configure("even", background=C["row_even"])

        # Empaquetar scrollbars y treeview
        sb_v.config(command=self._tree.yview)
        sb_h.config(command=self._tree.xview)
        sb_v.pack(side="right",  fill="y")
        sb_h.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        # Mensaje vacío (placeholder)
        self._lbl_vacio = tk.Label(
            parent,
            text="Cargue el CSV y seleccione un AP para ver conexiones.",
            font=FONT_NORMAL, bg=C["bg"], fg=C["text_m"]
        )
        self._lbl_vacio.place(relx=0.5, rely=0.5, anchor="center")

    def _construir_statusbar(self):
        barra = tk.Frame(self, bg=C["header_bg"], height=26)
        barra.pack(side="bottom", fill="x")
        barra.pack_propagate(False)

        self._lbl_status = tk.Label(
            barra, text="Listo. Seleccione un archivo CSV para comenzar.",
            font=FONT_SMALL, bg=C["header_bg"], fg="#93C5FD", anchor="w"
        )
        self._lbl_status.pack(side="left", padx=12)

        tk.Label(barra, text="TP5 — Autómatas y Gramáticas  |  Python + re + Tkinter",
                 font=FONT_SMALL, bg=C["header_bg"], fg="#64748B").pack(side="right", padx=12)

    # -----------------------------------------------------------------------
    # Acciones del usuario
    # -----------------------------------------------------------------------

    def _seleccionar_csv(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("CSV files", "*.csv"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            self._ruta_csv.set(ruta)
            self._set_status(f"Archivo seleccionado: {os.path.basename(ruta)}")

    def _iniciar_carga(self):
        ruta = self._ruta_csv.get().strip()
        if not ruta:
            messagebox.showwarning("Sin archivo", "Seleccione un archivo CSV primero.")
            return
        if not os.path.isfile(ruta):
            messagebox.showerror("Archivo no encontrado", f"No existe:\n{ruta}")
            return

        # Resetear estado previo
        self._df_validos = None
        self._invalidos = []
        self._df_resultado = None
        self._tree.delete(*self._tree.get_children())
        self._combo_ap.set("")
        self._combo_ap.config(state="disabled", values=[])
        self._btn_buscar.config(state="disabled")
        self._btn_export.config(state="disabled")
        self._btn_invalidos.config(state="disabled")
        self._lbl_n_resultados.config(text="")
        self._lbl_vacio.config(text="Cargando…")

        self._btn_cargar.config(state="disabled", text="Cargando…")
        self._evento_stop.clear()

        # Diálogo de progreso
        self._dialogo_progreso = DialogoProgreso(self)

        # Lanzar hilo de carga
        hilo = threading.Thread(
            target=self._hilo_carga,
            args=(ruta,),
            daemon=True,
        )
        hilo.start()

        # Activar polling de la cola
        self._verificar_cola()

    def _hilo_carga(self, ruta: str):
        """Se ejecuta en un hilo de fondo. Nunca toca Tkinter directamente."""
        try:
            def on_progreso(leidas, validas, invalidas):
                self._cola.put(("progreso", leidas, validas, invalidas))

            df, invalidos = procesar_csv(
                ruta,
                callback_progreso=on_progreso,
                detener_evento=self._evento_stop,
            )
            self._cola.put(("fin", df, invalidos))
        except Exception as e:
            self._cola.put(("error", str(e)))

    def _verificar_cola(self):
        """Polling de la cola desde el hilo principal (after cada 150ms)."""
        try:
            while True:
                msg = self._cola.get_nowait()
                tipo = msg[0]

                if tipo == "progreso":
                    _, leidas, validas, invalidas = msg
                    self._dialogo_progreso.actualizar(leidas, validas, invalidas)
                    self._set_status(
                        f"Procesando… {leidas:,} leídas | "
                        f"{validas:,} válidas | {invalidas:,} inválidas"
                    )

                elif tipo == "fin":
                    _, df, invalidos = msg
                    self._carga_completada(df, invalidos)
                    return  # Dejar de verificar

                elif tipo == "error":
                    self._dialogo_progreso.cerrar()
                    self._btn_cargar.config(state="normal",
                                            text="⚡  Cargar y Validar CSV")
                    messagebox.showerror("Error de carga", msg[1])
                    self._set_status("Error durante la carga del archivo.")
                    return

        except queue.Empty:
            pass

        # Seguir verificando si el hilo sigue vivo
        self.after(150, self._verificar_cola)

    def _carga_completada(self, df, invalidos):
        """Llamado desde el hilo principal cuando la carga terminó."""
        self._dialogo_progreso.cerrar()
        self._df_validos = df
        self._invalidos = invalidos

        n_val = len(df)
        n_inv = len(invalidos)
        n_total = n_val + n_inv

        # Actualizar labels de resumen
        self._lbl_validos.config(text=f"{n_val:,}")
        self._lbl_invalidos.config(
            text=f"{n_inv:,}",
            fg=C["danger"] if n_inv > 0 else C["success"]
        )
        self._lbl_total_csv.config(text=f"{n_total:,}")

        # Poblar combo de APs
        aps = obtener_aps(df)
        self._combo_ap.config(state="readonly", values=aps)
        if aps:
            self._combo_ap.set(aps[0])
            self._ap_var.set(aps[0])

        # Habilitar botones
        self._btn_buscar.config(state="normal")
        self._btn_cargar.config(state="normal", text="⚡  Cargar y Validar CSV")
        if n_inv > 0:
            self._btn_invalidos.config(state="normal")

        self._lbl_vacio.config(
            text=f"CSV cargado. {len(aps)} APs disponibles. Seleccione un AP y busque."
        )
        self._set_status(
            f"✅ Carga completa — {n_val:,} válidos | "
            f"❌ {n_inv:,} inválidos | "
            f"{len(aps)} APs distintos"
        )

    def _buscar(self):
        if self._df_validos is None or self._df_validos.empty:
            messagebox.showwarning("Sin datos", "Primero cargue el CSV.")
            return

        ap = self._ap_var.get().strip()
        if not ap:
            messagebox.showwarning("Sin AP", "Seleccione un Access Point.")
            return

        desde = self._fecha_desde.get().strip()
        hasta = self._fecha_hasta.get().strip()

        # Validar fechas con re (explícito, requisito del TP)
        import re
        patron_fecha = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        if not patron_fecha.fullmatch(desde):
            messagebox.showerror("Fecha inválida",
                                 f"'Fecha desde' no tiene formato YYYY-MM-DD:\n{desde}")
            return
        if not patron_fecha.fullmatch(hasta):
            messagebox.showerror("Fecha inválida",
                                 f"'Fecha hasta' no tiene formato YYYY-MM-DD:\n{hasta}")
            return
        if desde > hasta:
            messagebox.showerror("Rango inválido",
                                 "'Fecha desde' no puede ser posterior a 'Fecha hasta'.")
            return

        self._set_status("Filtrando…")
        self.update_idletasks()

        df_res = filtrar(self._df_validos, ap, desde, hasta)
        self._df_resultado = df_res

        self._poblar_tabla(df_res)

        # Estadísticas
        stats = estadisticas(df_res)
        self._lbl_stat_total.config(text=f"{stats['total']:,}")
        self._lbl_stat_usuarios.config(text=f"{stats['usuarios_unicos']:,}")
        self._lbl_stat_macs.config(text=f"{stats['macs_unicas']:,}")
        self._lbl_stat_tiempo.config(
            text=f"{stats['sesion_total_s'] / 3600:.2f}"
        )
        self._lbl_stat_entrada.config(
            text=f"{stats['trafico_in_b'] / 1_048_576:.2f}"
        )
        self._lbl_stat_salida.config(
            text=f"{stats['trafico_out_b'] / 1_048_576:.2f}"
        )

        self._lbl_n_resultados.config(
            text=f"— {stats['total']:,} registros encontrados"
        )
        self._btn_export.config(
            state="normal" if stats["total"] > 0 else "disabled"
        )

        self._set_status(
            f"Búsqueda completa: {stats['total']:,} conexiones para AP '{ap}' "
            f"entre {desde} y {hasta}."
        )

    def _poblar_tabla(self, df):
        """Llena el Treeview con las filas del DataFrame."""
        self._tree.delete(*self._tree.get_children())

        if df is None or df.empty:
            self._lbl_vacio.config(
                text="No se encontraron conexiones para el filtro aplicado."
            )
            self._lbl_vacio.lift()
            return

        self._lbl_vacio.lower()  # ocultar mensaje vacío

        col_ids = [c[0] for c in COLS_TABLA]
        for i, (_, row) in enumerate(df.iterrows()):
            vals = tuple(str(row.get(c, "")) for c in col_ids)
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=vals, tags=(tag,))

    def _ordenar_columna(self, columna: str):
        """Ordena la tabla por la columna clickeada (toggle asc/desc)."""
        if self._df_resultado is None or self._df_resultado.empty:
            return

        if not hasattr(self, "_orden"):
            self._orden = {}

        asc = self._orden.get(columna, True)
        self._orden[columna] = not asc

        df_ordenado = self._df_resultado.sort_values(
            columna, ascending=asc, na_position="last"
        )
        self._df_resultado = df_ordenado
        self._poblar_tabla(df_ordenado)

    def _exportar(self):
        if self._df_resultado is None or self._df_resultado.empty:
            messagebox.showwarning("Sin resultados", "No hay datos para exportar.")
            return

        ap = self._ap_var.get().strip()
        desde = self._fecha_desde.get().strip()
        hasta = self._fecha_hasta.get().strip()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_sugerido = f"conexiones_{ts}.xlsx"

        ruta = filedialog.asksaveasfilename(
            title="Guardar resultados en Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=nombre_sugerido,
        )
        if not ruta:
            return

        try:
            self._set_status("Exportando a Excel…")
            self.update_idletasks()
            ruta_guardada = exportar_excel(
                self._df_resultado, ap, desde, hasta, ruta
            )
            messagebox.showinfo(
                "Exportación exitosa",
                f"Archivo guardado exitosamente:\n\n{ruta_guardada}",
            )
            self._set_status(f"✅ Exportado: {os.path.basename(ruta_guardada)}")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
            self._set_status("Error durante la exportación.")

    def _ver_invalidos(self):
        if not self._invalidos:
            messagebox.showinfo("Sin inválidos",
                                "No hay registros inválidos registrados.")
            return
        VentanaInvalidos(self, self._invalidos)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _set_status(self, texto: str):
        self._lbl_status.config(text=texto)
        self.update_idletasks()


# ===========================================================================
# PUNTO DE ENTRADA
# ===========================================================================

if __name__ == "__main__":
    app = App()
    app.mainloop()
