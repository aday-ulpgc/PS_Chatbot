"""Script para crear cita de prueba - VERSION MEJORADA."""

import sys
import os
from datetime import datetime, timedelta

# Asegurar path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    print("=" * 70)
    print("🧪 CREADOR DE CITA DE PRUEBA")
    print("=" * 70)
    
    try:
        print("\n📦 Importando módulos...")
        from src.BBDD.databasecontroller import (
            get_session, crear_usuario, crear_contacto, crear_cita
        )
        print("   ✅ Módulos importados")
        
        print("\n🔌 Conectando a BD...")
        with get_session() as session:
            print("   ✅ Conexión exitosa")
            
            # Crear usuario
            print("\n👤 Creando usuario de prueba...")
            usuario = crear_usuario(
                session,
                tipo="I",
                nombre="Usuario Prueba",
                email="prueba@test.com",
                contrasena="123456"
            )
            session.flush()
            print(f"   ✅ Usuario creado - ID: {usuario.ID_USUARIO}")
            
            # Crear contacto
            print("\n📇 Creando contacto...")
            contacto = crear_contacto(
                session,
                id_usuario=usuario.ID_USUARIO,
                nombre="Contacto Prueba",
                email="contacto@test.com"
            )
            session.flush()
            print(f"   ✅ Contacto creado - ID: {contacto.ID_CONTACTO}")
            
            # Crear citas múltiples para prueba
            print("\n📅 Creando citas de prueba...")
            
            # Cita 1: Mañana 10:00-11:00
            fecha_cita1 = datetime.now() + timedelta(days=1)
            fecha_cita1 = fecha_cita1.replace(hour=10, minute=0, second=0, microsecond=0)
            
            crear_cita(
                session,
                id_usuario=usuario.ID_USUARIO,
                id_contacto=contacto.ID_CONTACTO,
                fecha=fecha_cita1,
                descripcion="Cita 1: 10:00",
                prioridad=1,
                duracion=60
            )
            print(f"   ✅ Cita 1 creada: {fecha_cita1.strftime('%d/%m/%Y %H:%M')}")
            
            # Cita 2: Mañana 14:00-15:00
            fecha_cita2 = datetime.now() + timedelta(days=1)
            fecha_cita2 = fecha_cita2.replace(hour=14, minute=0, second=0, microsecond=0)
            
            crear_cita(
                session,
                id_usuario=usuario.ID_USUARIO,
                id_contacto=contacto.ID_CONTACTO,
                fecha=fecha_cita2,
                descripcion="Cita 2: 14:00",
                prioridad=1,
                duracion=90
            )
            print(f"   ✅ Cita 2 creada: {fecha_cita2.strftime('%d/%m/%Y %H:%M')}")
            
            # Cita 3: Mañana 17:00-17:30
            fecha_cita3 = datetime.now() + timedelta(days=1)
            fecha_cita3 = fecha_cita3.replace(hour=17, minute=0, second=0, microsecond=0)
            
            crear_cita(
                session,
                id_usuario=usuario.ID_USUARIO,
                id_contacto=contacto.ID_CONTACTO,
                fecha=fecha_cita3,
                descripcion="Cita 3: 17:00",
                prioridad=1,
                duracion=30
            )
            print(f"   ✅ Cita 3 creada: {fecha_cita3.strftime('%d/%m/%Y %H:%M')}")
            
            session.commit()
            
            print("\n" + "=" * 70)
            print("✨ ¡ÉXITO! Datos de prueba creados")
            print("=" * 70)
            print(f"\n📌 Información creada:")
            print(f"   • Usuario ID: {usuario.ID_USUARIO}")
            print(f"   • Email: {usuario.EMAIL}")
            print(f"   • Contacto ID: {contacto.ID_CONTACTO}")
            print(f"\n🎯 Próximos pasos:")
            print(f"   1. Ejecuta el script de visualización:")
            print(f"      python test_visualization_interactive.py")
            print(f"   2. Usa Usuario ID: {usuario.ID_USUARIO}")
            print(f"   3. Usa fecha: mañana (o {(datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')})")
            print(f"\n✅ Verás las citas en ROJO y las horas libres en VERDE")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n" + "=" * 70)
        print("💡 SOLUCIONES POSIBLES:")
        print("=" * 70)
        print("1. Verifica que el archivo .env está configurado correctamente")
        print("2. Comprueba que la base de datos está accesible")
        print("3. Asegúrate de que estás en la raíz del proyecto")
        print("4. Intenta reinstalar las dependencias: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
