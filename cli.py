import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.lector import procesar_csv
from src.filtrador import obtener_aps, filtrar, estadisticas
from src.exportador import exportar_excel, exportar_invalidos_excel

# Helpers de entrada

def pedir_ruta_csv() -> str:
    while True:
        ruta = input("Ruta del archivo CSV: ").strip()
        if os.path.isfile(ruta):
            return ruta
        print(f" X No se encontró el archivo: {ruta}")

def pedir_fecha(etiqueta: str) -> str:
    patron = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    while True:
        valor = input(f"{etiqueta} (YYYY-MM-DD): ").strip()
        if patron.fullmatch(valor):
            return valor
        print(" X Formato inválido. Usá YYYY-MM-DD (ej: 2021-03-01)")

def pedir_ap(aps: list[str]) -> str:
    print("\nAPs disponibles:")
    for i, ap in enumerate(aps, 1):
        print(f"  {i:>3}. {ap}")

    while True:
        entrada = input("\nSeleccioná el número de AP: ").strip()
        if entrada.isdigit():
            idx = int(entrada) - 1
            if 0 <= idx < len(aps):
                return aps[idx]
        print(f" X Ingresá un número entre 1 y {len(aps)}")

# Flujo principal

def main():

    # 1. Cargar CSV
    ruta = pedir_ruta_csv()
    print("\nLeyendo y validando registros...")

    def on_progreso(leidas, validas, invalidas):
        print(f"  {leidas:>10,} leídas | {validas:,} válidas | {invalidas:,} inválidas",
              end="\r")

    df, invalidos = procesar_csv(ruta, callback_progreso=on_progreso)
    print()
    print(f"\n✔ Carga completa: {len(df):,} válidos | {len(invalidos):,} inválidos")

    if df.empty:
        print("No hay registros válidos. Revisá el archivo.")
        return

    # 2. Seleccionar AP
    aps = obtener_aps(df)
    ap = pedir_ap(aps)

    # 3. Rango de fechas
    print()
    desde = pedir_fecha("Fecha desde (2020-12-20)")
    hasta = pedir_fecha("Fecha hasta (2021-12-31)")
    if desde > hasta:
        print(" X 'Fecha desde' no puede ser posterior a 'Fecha hasta'.")
        return

    # 4. Filtrar
    df_res = filtrar(df, ap, desde, hasta)
    stats = estadisticas(df_res)

    print(f"\n{'─' * 60}")
    print(f"  Conexiones encontradas : {stats['total']:,}")
    print(f"  Usuarios únicos        : {stats['usuarios_unicos']:,}")
    print(f"  Dispositivos únicos    : {stats['macs_unicas']:,}")
    print(f"  Tiempo total           : {stats['sesion_total_s'] / 3600:.2f} horas")
    print(f"  Tráfico entrada        : {stats['trafico_in_b'] / 1_048_576:.2f} MB")
    print(f"  Tráfico salida         : {stats['trafico_out_b'] / 1_048_576:.2f} MB")
    print(f"{'─' * 60}")

    while True:
        print("\n¿Qué deseas hacer?")
        print("  1. Exportar conexiones válidas a Excel")
        print("  2. Exportar registros inválidos a Excel")
        print("  3. Exportar ambos archivos Excel")
        print("  4. Ver registros inválidos en pantalla (primeros 50)")
        print("  5. Salir")

        opcion = input("\nSeleccioná una opción: ").strip()

        if opcion == "1":
            if stats["total"] > 0:
                ruta_out = exportar_excel(df_res, ap, desde, hasta)
                print(f"  ✔ Conexiones guardadas en: {ruta_out}")
            else:
                print(" X No hay conexiones filtradas para exportar.")
        elif opcion == "2":
            if invalidos:
                ruta_inv = exportar_invalidos_excel(invalidos)
                print(f"  ✔ Registros inválidos guardados en: {ruta_inv}")
            else:
                print(" X No hay registros inválidos para exportar.")
        elif opcion == "3":
            if stats["total"] > 0:
                ruta_out = exportar_excel(df_res, ap, desde, hasta)
                print(f"  ✔ Conexiones guardadas en: {ruta_out}")
            else:
                print(" X No hay conexiones filtradas para exportar.")
            if invalidos:
                ruta_inv = exportar_invalidos_excel(invalidos)
                print(f"  ✔ Registros inválidos guardados en: {ruta_inv}")
            else:
                print(" X No hay registros inválidos para exportar.")
        elif opcion == "4":
            if invalidos:
                print(f"\n{'N° Fila':<10} {'ID':<12} Motivo")
                print("─" * 80)
                for inv in invalidos[:50]:
                    motivo = inv.get("motivo", "")[:60]
                    print(f"  {inv.get('num_fila', ''):>6}   {inv.get('ID', ''):>10}   {motivo}")
                if len(invalidos) > 50:
                    print(f"  ... y {len(invalidos) - 50:,} más.")
            else:
                print(" X No hay registros inválidos para mostrar.")
        elif opcion == "5":
            break
        else:
            print(" X Opción inválida. Ingresá un número del 1 al 5.")

if __name__ == "__main__":
    main()
