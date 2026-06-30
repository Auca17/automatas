# Expresiones regulares compiladas para validación de campos del CSV.
    #libreria
import re

PATRONES: dict[str, re.Pattern] = {

    # ID: entero positivo (ej: "603877")
    # ^          → inicio de cadena
    # \d+        → uno o más dígitos
    # $          → fin de cadena
    "ID": re.compile(r"^\d+$"),

    # ID_Sesion: segmentos hexadecimales separados por guión (ej: "5AA0184E-000001CA")
    # [0-9A-Fa-f]+ → uno o más dígitos hex (mayúsculas o minúsculas)
    # -            → guión literal separador
    # ?            → el guión es opcional
    # [0-9A-Fa-f]+ → segundo segmento hex
    "ID_Sesion": re.compile(r"^[0-9A-Fa-f]+-?[0-9A-Fa-f]+$"),

    # ID_Conexion: exactamente 16 caracteres hexadecimales en minúsculas
    # (ej: "d6104707df0cd315")
    # {16} → exactamente 16 caracteres
    "ID_Conexion": re.compile(r"^[0-9a-f]{16}$"),

    # Usuario: alfanumérico, guiones, puntos y underscores
    # (ej: "invitado-deca", "JTaniasdu", "user.name_01")
    # \w   → [a-zA-Z0-9_]
    # .    → punto literal 
    # \-   → guión literal
    "Usuario": re.compile(r"^[\w.\-]+$"),

    # IP_NAS_AP: dirección IPv4 (ej: "192.168.247.11")
    # (\d{1,3}\.){3} → tres octetos con punto
    # \d{1,3}        → cuarto octeto sin punto
    # Nota: no valida rangos (0-255), solo formato
    "IP_NAS_AP": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),

    # Tipo_conexion: valor exacto y fijo "Wireless-802.11"
    # \.  → punto literal (escapado, no cualquier carácter)
    # Cualquier otro valor → fila corrupta
    "Tipo_conexion": re.compile(r"^Wireless-802\.11$"),

    # Fecha: formato ISO YYYY-MM-DD (ej: "2019-02-07")
    # \d{4} → 4 dígitos año
    # -     → guión literal
    # \d{2} → 2 dígitos mes
    # -     → guión literal
    # \d{2} → 2 dígitos día
    "Fecha": re.compile(r"^\d{4}-\d{2}-\d{2}$"),

    # Hora: formato HH:MM:SS (ej: "19:46:08")
    "Hora": re.compile(r"^\d{2}:\d{2}:\d{2}$"),

    # Numero: entero no negativo (ej: "0", "39517", "505219")
    # Aplica a Session_Time, Input_Octects, Output_Octects
    # El valor 0 es válido (sesión sin tráfico)
    "Numero": re.compile(r"^\d+$"),

    # MAC_AP: dirección MAC con sufijo (ej: "DC-9F-DB-12-F3-EA:HCDD")
    # ([0-9A-Fa-f]{2}-){5} → 5 pares hex con guión
    # [0-9A-Fa-f]{2}       → 6to par hex (sin guión final)
    # :                    → dos puntos separador
    # .+                   → sufijo (ej: "HCDD", al menos 1 carácter)
    "MAC_AP": re.compile(r"^([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}:.+$"),

    # MAC_Cliente: dirección MAC estándar (ej: "DC-BF-E9-1A-B5-D0")
    # ([0-9A-Fa-f]{2}-){5} → 5 pares hex con guión
    # [0-9A-Fa-f]{2}       → 6to par sin guión
    "MAC_Cliente": re.compile(r"^([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}$"),

    # Razon: texto con letras, dígitos, underscores y guiones — O VACÍO
    # (ej: "User-Request", "Session-Timeout", "NAS-Reboot", "")
    # [\w\-]* → cero o más caracteres (vacío = válido)
    "Razon": re.compile(r"^[\w\-]*$"),
}
