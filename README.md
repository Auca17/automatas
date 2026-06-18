# TP 5 — Sistema de Seguimiento de Conexiones Wi-Fi (APs)

## Autómatas y Gramáticas

# Integrantes: 
  - Ezequiel Blajevitch
  - Augustus Rufino
  - Regina Mathon
  - Yannick Barone

## 1. Explicación del Proyecto: Información Obtenida y Utilidad

### ¿Qué información se obtiene?
A partir del procesamiento de un archivo de tráfico de conexiones Wi-Fi de gran volumen (~1.000.000 de registros, ~190 MB), la aplicación filtra, valida y procesa los datos para extraer la siguiente información:
- **Total de conexiones**: Sesiones que coinciden con el Access Point (AP) y período de tiempo seleccionado.
- **Usuarios únicos**: Cantidad de cuentas/credenciales de usuarios distintos que utilizaron el servicio.
- **Dispositivos únicos (direcciones MAC)**: Equipos físicos distintos identificados en la red.
- **Tiempo total consumido**: Suma total del tiempo acumulado de las sesiones en horas (convertido desde la unidad de medida original en segundos).
- **Tráfico total transferido**: Volumen de datos consumido (en Megabytes), calculando por separado la entrada (Upload) y la salida (Download) a partir de los bytes originales.
- **Registros Inválidos**: Detalle de todos los registros del CSV original que no cumplen con los formatos esperados, identificando la fila exacta, el identificador y el motivo específico de descarte.

### Utilidad de la Información
Esta herramienta es sumamente útil para administradores de red e infraestructura:
1. **Auditoría de Seguridad**: Detecta patrones inusuales o intentos de conexión con formatos de credenciales corruptos o maliciosos, permitiendo aislar dispositivos comprometidos.
2. **Dimensionamiento de Red (Capacity Planning)**: Permite identificar qué Access Points (AP) concentran la mayor cantidad de usuarios, dispositivos y tráfico. Esto facilita la toma de decisiones para balancear la carga física de la red o añadir nuevos APs en zonas saturadas.
3. **Optimización de Tráfico**: Clasifica las conexiones por volumen de datos consumido (bytes de entrada/salida) para detectar anomalías (ej: dispositivos con consumos excesivos de ancho de banda o conexiones de 0 bytes).
4. **Depuración de Sistemas**: Al segmentar los registros inválidos y mostrar la "Razón de Terminación", ayuda a diagnosticar fallas de comunicación recurrentes entre los APs y el servidor de autenticación (RADIUS).

---

## 2. Explicación de la Aplicación Desarrollada

La aplicación cuenta con una **arquitectura modular** en Python que divide las responsabilidades en componentes independientes. Se puede ejecutar mediante una **Interfaz de Línea de Comandos (CLI)** interactiva.

### Componentes del Sistema

1. **Patrones de Validación (`src/patrones.py`)**:
   - Define y compila las expresiones regulares utilizando el módulo `re` de Python.
   - Cada patrón está optimizado con `re.compile()` para garantizar alto rendimiento durante la validación masiva.
   - Valida formatos específicos como: MACs (`^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$`), IPs, fechas (`^\d{4}-\d{2}-\d{2}$`), IDs en formato hexadecimal, etc.

2. **Validador de Registros (`src/validador.py`)**:
   - Módulo central que aplica las reglas utilizando `patron.fullmatch(valor)`.
   - Clasifica los registros en válidos o inválidos. Si un registro tiene un campo obligatorio vacío o no coincide con su patrón `re`, se descarta y se registra el motivo detallado junto al número de fila física del CSV.

3. **Lector de Archivos (`src/lector.py`)**:
   - Cumple con la pauta de **guardar los registros leídos en listas y diccionarios de Python** (`list[dict]`).
   - Lee el archivo en streaming (fila por fila) utilizando el módulo `csv` nativo de Python para evitar el desbordamiento de memoria RAM con el archivo de ~190MB.
   - Al finalizar el proceso, consolida los registros válidos en un DataFrame de `pandas` y los registros inválidos en una lista de diccionarios de Python (`list[dict]`).

4. **Filtrador y Estadísticas (`src/filtrador.py`)**:
   - Obtiene la lista ordenada de APs (MACs únicas).
   - Filtra los registros válidos basándose en el AP seleccionado y el rango de fechas (desde/hasta).
   - Calcula las métricas acumuladas (tiempo en horas, conversión de bytes a MB, conteos únicos de usuarios y MACs).

5. **Exportador a Excel (`src/exportador.py`)**:
   - Escribe los archivos de salida utilizando `openpyxl` en modo escritura directa (`write_only=True`). Esto permite guardar cientos de miles de registros en pocos segundos sin congelar la aplicación.
   - Permite exportar tanto el conjunto de conexiones filtradas (válidas) como el reporte detallado de los registros descartados sin estilos ni sobrecarga innecesaria.

---

## 3. Requisitos

- Python 3.10 o superior
- pandas >= 2.0
- openpyxl >= 3.1

### Instalación

```bash
pip install -r requirements.txt
```

---

## 4. Ejecución

### Interfaz de Consola (CLI)
La consola interactiva es ideal para ejecuciones rápidas y uso en servidores sin entorno gráfico. Permite ingresar rutas, elegir APs del listado y operar mediante un menú interactivo de exportación.

Para ejecutarla:
```bash
python cli.py
```
