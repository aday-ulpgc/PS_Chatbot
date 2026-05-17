"""Script interactivo para probar la visualización de disponibilidad."""

import sys
import os
from datetime import datetime, timedelta

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.services.visualization_service import (
    generar_imagen_disponibilidad,
    generar_imagen_disponibilidad_semana_24h
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
    
    while True:
        tipo = input("\n   Selecciona (1 o 2): ").strip()
        if tipo in ['1', '2']:
            break
        print("❌ Por favor ingresa 1 o 2")
    
    # Pedir fecha
    print("\n📅 Ingresa la fecha (formato: DD/MM/YYYY o deja vacío para hoy/mañana)")
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
    if tipo == '1':
        print(f"\n📊 Generando imagen para {fecha.strftime('%A, %d de %B de %Y')}...")
        
        try:
            imagen_path = generar_imagen_disponibilidad(user_id, fecha)
            
            if imagen_path and os.path.exists(imagen_path):
                print(f"\n✅ ¡Imagen generada exitosamente!")
                print(f"   📁 Ubicación: {imagen_path}")
                print(f"\n💡 Puedes abrir la imagen desde:")
                print(f"   - File Explorer: {imagen_path}")
                print(f"   - VS Code: Ctrl+O y busca en la carpeta 'temp'")
                
                # Abrir la imagen automáticamente
                try:
                    os.startfile(imagen_path)
                    print(f"\n🖼️  Abriendo imagen...")
                except:
                    pass
            else:
                print(f"\n❌ No se pudo generar la imagen")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    elif tipo == '2':
        # Calcular el lunes de la semana
        dias_desde_lunes = fecha.weekday()
        fecha_lunes = fecha - timedelta(days=dias_desde_lunes)
        fecha_domingo = fecha_lunes + timedelta(days=6)
        
        print(f"\n📊 Generando imagen para la semana del {fecha_lunes.strftime('%d de %B')} al {fecha_domingo.strftime('%d de %B')}...")
        
        try:
            imagen_path = generar_imagen_disponibilidad_semana_24h(user_id, fecha)
            
            if imagen_path and os.path.exists(imagen_path):
                print(f"\n✅ ¡Imagen semanal generada exitosamente!")
                print(f"   📁 Ubicación: {imagen_path}")
                print(f"\n💡 Puedes abrir la imagen desde:")
                print(f"   - File Explorer: {imagen_path}")
                print(f"   - VS Code: Ctrl+O y busca en la carpeta 'temp'")
                
                # Abrir la imagen automáticamente
                try:
                    os.startfile(imagen_path)
                    print(f"\n🖼️  Abriendo imagen...")
                except:
                    pass
            else:
                print(f"\n❌ No se pudo generar la imagen")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
