"""Script interactivo para probar la visualización de disponibilidad."""

import sys
import os
from datetime import datetime, timedelta

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.services.visualization_service import (
    generar_imagen_disponibilidad,
    generar_imagen_disponibilidad_semana_24h,
)


def main():
    print("=" * 70)
    print("🎨 GENERADOR DE IMAGEN DE DISPONIBILIDAD - MODO INTERACTIVO")
    print("=" * 70)

    # Pedir ID de usuario
    while True:
        try:
            user_id = int(input("\n👤 Ingresa el ID de usuario: "))
            break
        except ValueError:
            print("❌ Por favor ingresa un número válido")

    # Pedir tipo de vista
    print("\n📊 ¿Qué tipo de vista deseas?")
    print("   1. 📅 Un día (00:00 a 23:59)")
    print("   2. 📆 Una semana completa (24h cada día)")
    print("   3. 📅📆 Ambas (día + semana)")

    while True:
        tipo = input("\n   Selecciona (1, 2 o 3): ").strip()
        if tipo in ["1", "2", "3"]:
            break
        print("❌ Por favor ingresa 1, 2 o 3")

    # Pedir fecha
    print("\n📅 Ingresa la fecha (formato: DD/MM/YYYY o deja vacío para hoy)")
    fecha_input = input("   Fecha: ").strip()

    if fecha_input:
        try:
            fecha = datetime.strptime(fecha_input, "%d/%m/%Y")
        except ValueError:
            print("❌ Formato inválido. Usando hoy...")
            fecha = datetime.now()
    else:
        fecha = datetime.now()

    # Generar imagen según tipo
    if tipo in ["1", "3"]:
        print(
            f"\n📊 Generando imagen del día para {fecha.strftime('%A, %d de %B de %Y')}..."
        )

        try:
            imagen_path = generar_imagen_disponibilidad(user_id, fecha)

            if imagen_path and os.path.exists(imagen_path):
                print("   ✅ Imagen del día generada")
                print(f"   📁 {imagen_path}")

                # Abrir la imagen automáticamente
                try:
                    os.startfile(imagen_path)
                except Exception:
                    pass
            else:
                print("   ❌ No se pudo generar la imagen del día")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    if tipo in ["2", "3"]:
        # Calcular el lunes de la semana
        dias_desde_lunes = fecha.weekday()
        fecha_lunes = fecha - timedelta(days=dias_desde_lunes)
        fecha_domingo = fecha_lunes + timedelta(days=6)

        print(
            f"\n📆 Generando imagen semanal para {fecha_lunes.strftime('%d de %B')} - {fecha_domingo.strftime('%d de %B')}..."
        )

        try:
            imagen_path = generar_imagen_disponibilidad_semana_24h(user_id, fecha)

            if imagen_path and os.path.exists(imagen_path):
                print("   ✅ Imagen semanal generada")
                print(f"   📁 {imagen_path}")

                # Abrir la imagen automáticamente
                try:
                    os.startfile(imagen_path)
                except Exception:
                    pass
            else:
                print("   ❌ No se pudo generar la imagen semanal")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    if tipo == "3":
        print("✨ ¡Ambas imágenes generadas!")
    elif tipo == "1":
        print("✨ ¡Imagen del día generada!")
    else:
        print("✨ ¡Imagen semanal generada!")
    print("=" * 70)


if __name__ == "__main__":
    main()
