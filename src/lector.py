#Lectura del CSV y validación campo a campo.

import csv 
import pandas as pd # Los df son de esta libreria y son como tablas que te permiten hacer operaciones sobre ellas
from src.validador import validar_fila, NOMBRES_CAMPOS

# Tamaño del buffer antes de convertir a DataFrame, se divide el csv en trozos de este tamaño 
# para no sobrecargar la memoria
CHUNK_SIZE = 10_000

# Columnas del DataFrame resultante (mismo orden que NOMBRES_CAMPOS)
COLUMNAS_DF = NOMBRES_CAMPOS  # 16 campos

def procesar_csv(
    ruta: str,
    callback_progreso=None,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Lee el CSV, valida cada fila con regex, y retorna registros válidos e inválidos.

    Args:
        ruta: path completo al archivo CSV
        callback_progreso: callable(n_leidas, n_validas, n_invalidas) o None
            Llamado cada 5.000 filas para mostrar progreso en la consola.

    Returns:
        (DataFrame_validos, lista_invalidos)
        - DataFrame_validos: pd.DataFrame con COLUMNAS_DF
        - lista_invalidos: list de dicts {"num_fila", "ID", "motivo"}
    """
    buffer_validos: list[dict] = [] # Lista de dict para guardar los datos validos
    lista_invalidos: list[dict] = [] # Lista de dict para guardar los datos invalidos
    chunks: list[pd.DataFrame] = [] # Lista de df que se irán concatenando

    with open(ruta, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)

        # Saltar el encabezado y empezar por la segunda fila
        try:
            _header = next(reader)
        except StopIteration:
            # Archivo vacío
            return pd.DataFrame(columns=COLUMNAS_DF), []

        for num_fila, fila in enumerate(reader, start=2):

            # Validar fila con expresiones regulares con funcion de validador.py
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

            # Vaciar buffer hacia al dataframe cada CHUNK_SIZE filas
            if len(buffer_validos) >= CHUNK_SIZE:
                chunks.append(pd.DataFrame(buffer_validos, columns=COLUMNAS_DF))
                buffer_validos = []

            # Callback de progreso cada 5.000 filas leídas 
            if callback_progreso is not None and (num_fila % 5_000 == 0):
                n_validas = sum(len(c) for c in chunks) + len(buffer_validos)
                callback_progreso(num_fila - 1, n_validas, len(lista_invalidos))

    # Último buffer (si quedaron filas)
    if buffer_validos:
        chunks.append(pd.DataFrame(buffer_validos, columns=COLUMNAS_DF))

    # Concatenar todos los chunks en un único DataFrame
    if chunks:
        df_final = pd.concat(chunks, ignore_index=True)

        # Esto es porque estas filas no varian tanto entonces asi optimizamos la memoria
        for col_cat in ("Tipo_conexion", "MAC_AP", "Razon"):
            if col_cat in df_final.columns:
                df_final[col_cat] = df_final[col_cat].astype("category")
    else:
        df_final = pd.DataFrame(columns=COLUMNAS_DF)

    return df_final, lista_invalidos
