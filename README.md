# TP5 — Sistema de Seguimiento de Conexiones Wi-Fi

## Autómatas y Gramáticas

### Descripción

Aplicación Python que carga un archivo CSV de registros de red Wi-Fi (~1M filas),
valida cada registro campo a campo con **expresiones regulares** (`re`),
y permite filtrar conexiones por Access Point y rango de fechas.

---

### Requisitos

- Python 3.10 o superior
- pandas >= 2.0
- openpyxl >= 3.1

### Instalación

```bash
pip install -r requirements.txt
```

### Ejecución

1. Colocar el archivo `export-2019-to-now-v4.csv` en cualquier carpeta accesible.
2. Ejecutar:

```bash
python main.py
```

---

### Estructura del proyecto

```
automatas/
├── src/
│   ├── __init__.py
│   ├── patrones.py      # Regex compiladas con re.compile()
│   ├── validador.py     # Validación campo a campo con re.fullmatch()
│   ├── lector.py        # Lectura CSV streaming (csv.reader)
│   ├── filtrador.py     # Filtrado por AP y fechas
│   └── exportador.py    # Exportación a Excel (openpyxl)
├── main.py              # GUI Tkinter
├── requirements.txt
└── README.md
```

### Flujo de la aplicación

1. **Seleccionar CSV** → cuadro de diálogo
2. **Cargar y Validar** → hilo de fondo con barra de progreso
3. **Seleccionar AP** → combo poblado dinámicamente
4. **Ingresar fechas** → formato YYYY-MM-DD (validado también con re)
5. **Buscar** → tabla de resultados + estadísticas
6. **Exportar Excel** → archivo .xlsx con estilos y hoja de estadísticas
7. **Ver Inválidos** → ventana con todos los registros descartados y motivos
