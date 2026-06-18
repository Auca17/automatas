"""
Validación campo a campo de cada fila del CSV usando expresiones regulares.

El módulo `re` es CENTRAL: cada campo se valida con patron.fullmatch(valor),
que internamente usa el motor de regex de Python.

Criterios de validación:
- Campos obligatorios vacíos → registro inválido
- Campo que no coincide con su patrón → registro inválido
- Razón de terminación vacía → VÁLIDO (sesión sin cierre explícito)
- Columnas 16 y 17 → siempre ignoradas
"""

import re
from src.patrones import PATRONES

# Definición de reglas de validación
# Tupla: (nombre_display, clave_patron, índice_csv, obligatorio)

REGLAS: list[tuple[str, str, int, bool]] = [
    ("ID",              "ID",            0,  True),
    ("ID_Sesion",       "ID_Sesion",     1,  True),
    ("ID_Conexion",     "ID_Conexion",   2,  True),
    ("Usuario",         "Usuario",       3,  True),
    ("IP_NAS_AP",       "IP_NAS_AP",     4,  True),
    ("Tipo_conexion",   "Tipo_conexion", 5,  True),   # ← detector de filas corruptas
    ("Inicio_Dia",      "Fecha",         6,  True),
    ("Inicio_Hora",     "Hora",          7,  True),
    ("Fin_Dia",         "Fecha",         8,  True),
    ("Fin_Hora",        "Hora",          9,  True),
    ("Session_Time",    "Numero",        10, True),
    ("Input_Octects",   "Numero",        11, True),
    ("Output_Octects",  "Numero",        12, True),
    ("MAC_AP",          "MAC_AP",        13, True),
    ("MAC_Cliente",     "MAC_Cliente",   14, True),
    ("Razon",           "Razon",         15, False),  # vacío permitido
    # Columnas 16 y 17 → siempre ignoradas, no aparecen en REGLAS
]

# Nombres internos de los campos (mismo orden que REGLAS)
NOMBRES_CAMPOS: list[str] = [r[0] for r in REGLAS]

# Función principal de validación

def validar_fila(fila: list[str]) -> tuple[dict | None, str | None]:
    """
    Valida una fila del CSV campo a campo usando re.fullmatch().

    Args:
        fila: lista de strings leída por csv.reader (puede tener 16-18 cols)

    Returns:
        (dict_campos, None)      → fila válida; dict con todos los campos
        (None, "motivo_error")   → fila inválida; string con errores concatenados

    Ejemplo de uso:
        datos, error = validar_fila(["603877", "5AA0184E-000001CA", ...])
        if error:
            print(f"Inválido: {error}")
        else:
            print(f"Usuario: {datos['Usuario']}")
    """
    # --- Verificar cantidad mínima de columnas ---
    if len(fila) < 15:
        return None, f"Columnas insuficientes: se obtuvieron {len(fila)}, mínimo 15"

    errores: list[str] = []

    for nombre, clave_patron, idx, obligatorio in REGLAS:
        # Extraer y limpiar el valor del campo
        valor: str = fila[idx].strip() if idx < len(fila) else ""

        if not valor:
            # Campo vacío
            if obligatorio:
                errores.append(f"{nombre}: campo vacío (obligatorio)")
            # Si no es obligatorio (Razon), el vacío es válido → no se agrega error
        else:
            # USO CENTRAL DE re: se llama fullmatch() sobre el patrón compilado
            # patron.fullmatch(valor) ≡ re.fullmatch(patron.pattern, valor)
            # pero reutiliza el patrón compilado para mayor rendimiento
            patron: re.Pattern = PATRONES[clave_patron]
            if not patron.fullmatch(valor):
                # Truncar valores muy largos en el mensaje de error
                valor_corto = valor[:40] + "…" if len(valor) > 40 else valor
                errores.append(f"{nombre}: '{valor_corto}' no coincide con /{patron.pattern}/")

    if errores:
        return None, " | ".join(errores)

    # --- Construir diccionario de campos validados ---
    registro: dict[str, str] = {}
    for nombre, _, idx, _ in REGLAS:
        registro[nombre] = fila[idx].strip() if idx < len(fila) else ""

    return registro, None
