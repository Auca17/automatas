"""
src/filtrador.py
================
Lógica de filtrado sobre el DataFrame de registros válidos.

Operaciones disponibles:
1. obtener_aps(df)          → lista de Access Points únicos (MAC_AP)
2. filtrar(df, ap, d1, d2)  → registros del AP en el rango de fechas

La comparación de fechas es puramente lexicográfica porque el formato
validado YYYY-MM-DD garantiza que el orden alfabético = orden cronológico.
"""

import pandas as pd


def obtener_aps(df: pd.DataFrame) -> list[str]:
    """
    Retorna la lista de MACs de AP únicas, ordenadas alfabéticamente.

    Args:
        df: DataFrame de registros válidos

    Returns:
        Lista de strings (ej: ["AA-BB-CC-DD-EE-FF:HCDD", ...])
    """
    if df is None or df.empty:
        return []
    return sorted(df["MAC_AP"].astype(str).unique().tolist())


def filtrar(
    df: pd.DataFrame,
    mac_ap: str,
    fecha_desde: str,
    fecha_hasta: str,
) -> pd.DataFrame:
    """
    Filtra registros por Access Point y rango de fechas de inicio de conexión.

    Args:
        df:          DataFrame de registros válidos
        mac_ap:      MAC completa del AP (ej: "DC-9F-DB-12-F3-EA:HCDD")
        fecha_desde: YYYY-MM-DD (inclusive)
        fecha_hasta: YYYY-MM-DD (inclusive)

    Returns:
        DataFrame filtrado (puede estar vacío si no hay coincidencias)

    Nota sobre la comparación de fechas:
        Como el formato YYYY-MM-DD fue validado con regex, la comparación
        lexicográfica '2019-01-01' <= '2019-06-15' <= '2023-12-31' es
        equivalente a la comparación cronológica, sin necesidad de parsear.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=df.columns if df is not None else [])

    # Construir máscara booleana con tres condiciones
    mascara = (
        (df["MAC_AP"].astype(str) == mac_ap) &
        (df["Inicio_Dia"] >= fecha_desde) &
        (df["Inicio_Dia"] <= fecha_hasta)
    )

    return df[mascara].copy()


def estadisticas(df_resultado: pd.DataFrame) -> dict:
    """
    Calcula estadísticas básicas del conjunto de resultados filtrados.

    Args:
        df_resultado: DataFrame filtrado por filtrar()

    Returns:
        Dict con métricas útiles para mostrar en la UI
    """
    if df_resultado is None or df_resultado.empty:
        return {
            "total":          0,
            "usuarios_unicos": 0,
            "macs_unicas":    0,
            "sesion_total_s": 0,
            "trafico_in_b":   0,
            "trafico_out_b":  0,
        }

    return {
        "total":           len(df_resultado),
        "usuarios_unicos": df_resultado["Usuario"].nunique(),
        "macs_unicas":     df_resultado["MAC_Cliente"].nunique(),
        "sesion_total_s":  df_resultado["Session_Time"].astype(int).sum(),
        "trafico_in_b":    df_resultado["Input_Octects"].astype(int).sum(),
        "trafico_out_b":   df_resultado["Output_Octects"].astype(int).sum(),
    }
