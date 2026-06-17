"""
src/lector.py
=============
Lectura del CSV en modo streaming y validación campo a campo.

Estrategia para archivo grande (~190MB, ~1M filas):
- Se usa csv.reader para leer línea a línea (no carga todo en RAM)
- Cada fila se valida inmediatamente con validar_fila()
- Los registros válidos se acumulan en buffers de 10.000 filas
- Cada buffer se convierte a DataFrame y se concatena al final
- Los inválidos se guardan solo con num_fila, ID y motivo (mínima memoria)
- Un callback opcional permite actualizar una barra de progreso en la GUI
"""

import csv
import pandas as pd
from src.validador import validar_fila, NOMBRES_CAMPOS

# Tamaño del buffer antes de convertir a DataFrame
CHUNK_SIZE = 10_000

# Columnas del DataFrame resultante (mismo orden que NOMBRES_CAMPOS)
COLUMNAS_DF = NOMBRES_CAMPOS  # 16 campos


def procesar_csv(
    ruta: str,
    callback_progreso=None,
    detener_evento=None,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Lee el CSV, valida cada fila con regex, y retorna registros válidos e inválidos.

    Args:
        ruta: path completo al archivo CSV
        callback_progreso: callable(n_leidas, n_validas, n_invalidas) o None
            Llamado cada 5.000 filas para actualizar la UI.
        detener_evento: threading.Event o None
            Si se activa, se detiene el procesamiento anticipadamente.

    Returns:
        (DataFrame_validos, lista_invalidos)
        - DataFrame_validos: pd.DataFrame con COLUMNAS_DF
        - lista_invalidos: list de dicts {"num_fila", "ID", "motivo"}
    """
    buffer_validos: list[dict] = []
    lista_invalidos: list[dict] = []
    chunks: list[pd.DataFrame] = []

    with open(ruta, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)

        # --- Saltar la fila de encabezado ---
        try:
            _header = next(reader)
        except StopIteration:
            # Archivo vacío
            return pd.DataFrame(columns=COLUMNAS_DF), []

        for num_fila, fila in enumerate(reader, start=2):

            # Verificar señal de cancelación (botón Cancelar en UI)
            if detener_evento is not None and detener_evento.is_set():
                break

            # --- Validar fila con expresiones regulares ---
            datos, error = validar_fila(fila)

            if error:
                # Guardar solo lo mínimo del registro inválido
                lista_invalidos.append({
                    "num_fila": num_fila,
                    "ID":       fila[0].strip() if fila else "",
                    "motivo":   error,
                })
            else:
                buffer_validos.append(datos)

            # --- Vaciar buffer al DataFrame cada CHUNK_SIZE filas válidas ---
            if len(buffer_validos) >= CHUNK_SIZE:
                chunks.append(pd.DataFrame(buffer_validos, columns=COLUMNAS_DF))
                buffer_validos = []

            # --- Callback de progreso cada 5.000 filas leídas ---
            if callback_progreso is not None and (num_fila % 5_000 == 0):
                n_validas = sum(len(c) for c in chunks) + len(buffer_validos)
                callback_progreso(num_fila - 1, n_validas, len(lista_invalidos))

    # --- Último buffer (si quedaron filas) ---
    if buffer_validos:
        chunks.append(pd.DataFrame(buffer_validos, columns=COLUMNAS_DF))

    # --- Concatenar todos los chunks en un único DataFrame ---
    if chunks:
        df_final = pd.concat(chunks, ignore_index=True)

        # Optimización de memoria: columnas de baja cardinalidad como Categorical
        for col_cat in ("Tipo_conexion", "MAC_AP", "Razon"):
            if col_cat in df_final.columns:
                df_final[col_cat] = df_final[col_cat].astype("category")
    else:
        df_final = pd.DataFrame(columns=COLUMNAS_DF)

    return df_final, lista_invalidos
