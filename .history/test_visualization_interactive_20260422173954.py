"""Script interactivo para probar la visualización de disponibilidad."""

import sys
import os
from datetime import datetime, timedelta

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.services.visualization_service import generar_imagen_disponibilidad


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
    
    # Pedir fecha
    print("\n📅 Ingresa la fecha (formato: DD/MM/YYYY o deja vacío para mañana)")
    fecha_input = input("   Fecha: ").strip()
    
    if fecha_input:
        try:
            fecha = datetime.strptime(fecha_input, "%d/%m/%Y")
        except ValueError:
            print("❌ Formato inválido. Usando mañana...")
            fecha = datetime.now() + timedelta(days=1)
    else:
        fecha = datetime.now() + timedelta(days=1)
    
    print(f"\n📊 Generando imagen para {fecha.strftime('%A, %d de %B de %Y')}...")
    
    try:
        imagen_path = generar_imagen_disponibilidad(user_id, fecha)
        
        if imagen_path and os.path.exists(imagen_path):
            print(f"\n✅ ¡Imagen generada exitosamente!")
            print(f"   📁 Ubicación: {imagen_path}")
            print(f"\n💡 Puedes abrir la imagen desde:")
            print(f"   - File Explorer: {imagen_path}")
            print(f"   - VS Code: Ctrl+O y busca en la carpeta 'temp'")
            
            # Abrir la imagen automáticamente si es posible
            try:
                import webbrowser
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
