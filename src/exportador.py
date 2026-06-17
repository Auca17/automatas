"""
src/exportador.py
=================
Exportación de resultados a Excel con formato profesional.

Usa openpyxl directamente (no pandas.to_excel) para control total
del estilo: colores de cabecera, filas alternas, anchos de columna,
freezepanes y metadatos del reporte.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
import pandas as pd
import os

# ---------------------------------------------------------------------------
# Definición de columnas a exportar (campo_interno → título en Excel)
# ---------------------------------------------------------------------------

COLUMNAS_EXPORT: list[tuple[str, str]] = [
    ("Usuario",       "Usuario"),
    ("MAC_Cliente",   "MAC Cliente"),
    ("IP_NAS_AP",     "IP del AP"),
    ("Inicio_Dia",    "Inicio Día"),
    ("Inicio_Hora",   "Inicio Hora"),
    ("Fin_Dia",       "Fin Día"),
    ("Fin_Hora",      "Fin Hora"),
    ("Session_Time",  "Duración (seg)"),
    ("Input_Octects", "Entrada (bytes)"),
    ("Output_Octects","Salida (bytes)"),
    ("Razon",         "Razón Terminación"),
    ("ID",            "ID Registro"),
    ("ID_Sesion",     "ID Sesión"),
    ("MAC_AP",        "MAC AP"),
]

# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------

COLOR_TITULO   = "0F2B5B"   # Azul marino oscuro (título)
COLOR_HEADER   = "1F4E79"   # Azul marino (encabezados de columna)
COLOR_INFO     = "2E75B6"   # Azul medio (fila de info)
COLOR_ALT      = "D6E4F0"   # Celeste muy claro (filas alternas)
COLOR_BLANCO   = "FFFFFF"   # Blanco (filas pares)
COLOR_TEXTO_L  = "FFFFFF"   # Texto claro (sobre fondo oscuro)
COLOR_TEXTO_D  = "0F2B5B"   # Texto oscuro (sobre fondo claro)


def _borde_delgado() -> Border:
    lado = Side(style="thin", color="B0C4DE")
    return Border(left=lado, right=lado, top=lado, bottom=lado)


def exportar_excel(
    df_resultado: pd.DataFrame,
    mac_ap: str,
    fecha_desde: str,
    fecha_hasta: str,
    ruta: str | None = None,
) -> str:
    """
    Exporta el DataFrame filtrado a un archivo .xlsx con estilos profesionales.

    Args:
        df_resultado: DataFrame con los registros a exportar
        mac_ap:       MAC del AP seleccionado
        fecha_desde:  Fecha de inicio del filtro
        fecha_hasta:  Fecha de fin del filtro
        ruta:         Path de salida; si es None, se genera automáticamente

    Returns:
        Ruta del archivo generado (str)
    """
    if ruta is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"conexiones_{ts}.xlsx"
        ruta = os.path.join(os.path.expanduser("~"), "Desktop", nombre)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Conexiones Filtradas"

    n_cols = len(COLUMNAS_EXPORT)
    ultima_col = get_column_letter(n_cols)

    # -----------------------------------------------------------------------
    # FILA 1 — Título principal
    # -----------------------------------------------------------------------
    ws.merge_cells(f"A1:{ultima_col}1")
    celda_titulo = ws["A1"]
    celda_titulo.value = "Sistema de Seguimiento de Conexiones Wi-Fi — TP5 Autómatas y Gramáticas"
    celda_titulo.font = Font(bold=True, size=14, color=COLOR_TEXTO_L, name="Calibri")
    celda_titulo.fill = PatternFill(fill_type="solid", fgColor=COLOR_TITULO)
    celda_titulo.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    # -----------------------------------------------------------------------
    # FILA 2 — Información del filtro aplicado
    # -----------------------------------------------------------------------
    info_celdas = {
        "A2": f"AP: {mac_ap}",
        "C2": f"Período: {fecha_desde}  →  {fecha_hasta}",
        "F2": f"Registros: {len(df_resultado):,}",
        "H2": f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    }
    for ref, texto in info_celdas.items():
        c = ws[ref]
        c.value = texto
        c.font = Font(bold=True, color=COLOR_TEXTO_L, name="Calibri")
        c.fill = PatternFill(fill_type="solid", fgColor=COLOR_INFO)
        c.alignment = Alignment(vertical="center")
    ws.row_dimensions[2].height = 22

    # -----------------------------------------------------------------------
    # FILA 3 — Vacía (separador visual)
    # -----------------------------------------------------------------------
    ws.row_dimensions[3].height = 6

    # -----------------------------------------------------------------------
    # FILA 4 — Encabezados de columnas
    # -----------------------------------------------------------------------
    encabezados = [col[1] for col in COLUMNAS_EXPORT]
    ws.append(encabezados)  # fila 4
    fila_header = 4
    for cell in ws[fila_header]:
        cell.font = Font(bold=True, color=COLOR_TEXTO_L, name="Calibri", size=10)
        cell.fill = PatternFill(fill_type="solid", fgColor=COLOR_HEADER)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
        cell.border = _borde_delgado()
    ws.row_dimensions[fila_header].height = 20

    # -----------------------------------------------------------------------
    # FILAS DE DATOS (a partir de fila 5)
    # -----------------------------------------------------------------------
    borde = _borde_delgado()
    fill_alt   = PatternFill(fill_type="solid", fgColor=COLOR_ALT)
    fill_blanco = PatternFill(fill_type="solid", fgColor=COLOR_BLANCO)

    for idx, (_, row) in enumerate(df_resultado.iterrows()):
        fila_datos = [str(row.get(col[0], "")) for col in COLUMNAS_EXPORT]
        ws.append(fila_datos)

        num_fila_excel = fila_header + 1 + idx
        fill_actual = fill_alt if idx % 2 == 0 else fill_blanco

        for cell in ws[num_fila_excel]:
            cell.fill = fill_actual
            cell.border = borde
            cell.font = Font(name="Calibri", size=9, color=COLOR_TEXTO_D)
            cell.alignment = Alignment(vertical="center")

    # -----------------------------------------------------------------------
    # ANCHOS DE COLUMNA (automáticos con límite máximo)
    # -----------------------------------------------------------------------
    anchos_minimos = {
        "Inicio Día": 12, "Fin Día": 12,
        "Inicio Hora": 12, "Fin Hora": 12,
        "MAC Cliente": 20, "MAC AP": 26,
        "IP del AP": 16,
    }
    for col_idx, (campo, titulo) in enumerate(COLUMNAS_EXPORT, 1):
        col_letter = get_column_letter(col_idx)
        if not df_resultado.empty:
            max_val = df_resultado[campo].astype(str).str.len().max()
        else:
            max_val = 0
        ancho = max(len(titulo), int(max_val), anchos_minimos.get(titulo, 10)) + 3
        ws.column_dimensions[col_letter].width = min(ancho, 40)

    # -----------------------------------------------------------------------
    # FREEZE PANES — fijar encabezados al hacer scroll
    # -----------------------------------------------------------------------
    ws.freeze_panes = "A5"

    # -----------------------------------------------------------------------
    # HOJA DE ESTADÍSTICAS
    # -----------------------------------------------------------------------
    ws_stats = wb.create_sheet("Estadísticas")
    _agregar_hoja_stats(ws_stats, df_resultado, mac_ap, fecha_desde, fecha_hasta)

    wb.save(ruta)
    return ruta


def _agregar_hoja_stats(ws, df: pd.DataFrame, mac_ap, f_desde, f_hasta):
    """Agrega una hoja resumen con estadísticas del conjunto filtrado."""
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 22

    def escribir(etiqueta, valor, negrita=False):
        ws.append([etiqueta, valor])
        fila = ws.max_row
        ws.cell(fila, 1).font = Font(bold=negrita, name="Calibri")
        ws.cell(fila, 2).font = Font(bold=True, name="Calibri", color="1F4E79")
        ws.cell(fila, 2).alignment = Alignment(horizontal="right")

    ws["A1"] = "Estadísticas del Filtro Aplicado"
    ws["A1"].font = Font(bold=True, size=13, color=COLOR_TEXTO_L)
    ws["A1"].fill = PatternFill(fill_type="solid", fgColor=COLOR_TITULO)
    ws.row_dimensions[1].height = 28
    ws.append([])

    escribir("Access Point (MAC_AP):", mac_ap, True)
    escribir("Fecha desde:", f_desde)
    escribir("Fecha hasta:", f_hasta)
    ws.append([])

    if not df.empty:
        sesion_total = df["Session_Time"].astype(int).sum()
        entrada_total = df["Input_Octects"].astype(int).sum()
        salida_total = df["Output_Octects"].astype(int).sum()

        escribir("Total de conexiones:", f"{len(df):,}", True)
        escribir("Usuarios únicos:", f"{df['Usuario'].nunique():,}")
        escribir("Dispositivos únicos (MAC):", f"{df['MAC_Cliente'].nunique():,}")
        ws.append([])
        escribir("Tiempo total de sesión (seg):", f"{sesion_total:,}")
        escribir("Tiempo total de sesión (horas):", f"{sesion_total / 3600:.2f}")
        ws.append([])
        escribir("Tráfico de entrada total (bytes):", f"{entrada_total:,}")
        escribir("Tráfico de salida total (bytes):", f"{salida_total:,}")
        escribir("Tráfico de entrada total (MB):", f"{entrada_total / 1_048_576:.2f}")
        escribir("Tráfico de salida total (MB):", f"{salida_total / 1_048_576:.2f}")
    else:
        ws.append(["Sin datos para el filtro aplicado.", ""])


def exportar_invalidos_excel(
    invalidos: list[dict],
    ruta: str | None = None,
) -> str:
    """
    Exporta la lista de registros inválidos a Excel.

    Args:
        invalidos: lista de dicts {"num_fila", "ID", "motivo"}
        ruta:      path de salida; si es None se genera automáticamente

    Returns:
        Ruta del archivo generado
    """
    if ruta is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = os.path.join(os.path.expanduser("~"), "Desktop", f"invalidos_{ts}.xlsx")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Registros Inválidos"

    # Título
    ws.merge_cells("A1:C1")
    ws["A1"] = f"Registros Inválidos — Total: {len(invalidos):,}"
    ws["A1"].font = Font(bold=True, size=12, color=COLOR_TEXTO_L)
    ws["A1"].fill = PatternFill(fill_type="solid", fgColor="8B0000")
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[1].height = 25

    # Encabezados
    ws.append(["N° Fila CSV", "ID del Registro", "Motivo del Descarte"])
    for cell in ws[2]:
        cell.font = Font(bold=True, color=COLOR_TEXTO_L)
        cell.fill = PatternFill(fill_type="solid", fgColor=COLOR_HEADER)
        cell.alignment = Alignment(horizontal="center")

    # Datos
    for inv in invalidos:
        ws.append([inv.get("num_fila", ""), inv.get("ID", ""), inv.get("motivo", "")])

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 80
    ws.freeze_panes = "A3"

    wb.save(ruta)
    return ruta
