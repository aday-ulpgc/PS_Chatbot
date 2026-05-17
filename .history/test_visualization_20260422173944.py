"""Script de prueba para la visualización de disponibilidad."""

import sys
import os
from datetime import datetime, timedelta

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.services.visualization_service import generar_imagen_disponibilidad, generar_imagen_disponibilidad_semana


def main():
    print("=" * 60)
    print("🧪 PRUEBA DE VISUALIZACIÓN DE DISPONIBILIDAD")
    print("=" * 60)
    
    # ID de usuario para pruebas (usa 1 o cualquier ID que tengas en BD)
    user_id = 1
    
    print(f"\n📌 Probando con user_id: {user_id}")
    
    # Opción 1: Generar imagen para un día específico
    print("\n1️⃣  Generando imagen para un día específico...")
    
    # Usar una fecha en el futuro (ej: mañana)
    fecha_prueba = datetime.now() + timedelta(days=1)
    
    print(f"   Fecha: {fecha_prueba.strftime('%A, %d de %B de %Y')}")
    
    try:
        imagen_path = generar_imagen_disponibilidad(user_id, fecha_prueba)
        
        if imagen_path:
            print(f"   ✅ Imagen generada exitosamente")
            print(f"   📁 Ruta: {imagen_path}")
            print(f"   📊 Abre la imagen en: {imagen_path}")
        else:
            print(f"   ❌ No se pudo generar la imagen")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Opción 2: Generar imagen para una semana
    print("\n2️⃣  Generando imagen para una semana completa...")
    
    fecha_inicio_semana = datetime.now() + timedelta(days=1)
    print(f"   Semana del: {fecha_inicio_semana.strftime('%d de %B de %Y')}")
    
    try:
        imagen_semana_path = generar_imagen_disponibilidad_semana(user_id, fecha_inicio_semana)
        
        if imagen_semana_path:
            print(f"   ✅ Imagen semanal generada exitosamente")
            print(f"   📁 Ruta: {imagen_semana_path}")
            print(f"   📊 Abre la imagen en: {imagen_semana_path}")
        else:
            print(f"   ❌ No se pudo generar la imagen semanal")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✨ Prueba completada")
    print("=" * 60)


if __name__ == "__main__":
    main()
