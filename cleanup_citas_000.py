"""
Script para eliminar citas con hora 00:00:00 (no fueron grabadas correctamente)
"""
import sys
sys.path.insert(0, 'src')

from sqlalchemy import text
from BBDD.databasecontroller import engine

# Crear conexión
try:
    with engine.connect() as conn:
        # Obtener el count antes
        result_before = conn.execute(text("""
            SELECT COUNT(*) as total FROM CITAS 
            WHERE ELIMINADO IS NULL AND HOUR(FECHA) = 0 AND MINUTE(FECHA) = 0
        """))
        count_before = result_before.scalar()
        
        print(f"\n📊 Citas con hora 00:00:00 encontradas: {count_before}")
        
        if count_before > 0:
            # Mostrar las citas que se van a eliminar
            result_show = conn.execute(text("""
                SELECT 
                    ID_CITA,
                    FECHA,
                    (SELECT NOMBRE FROM EMPLEADOS WHERE ID_EMPLEADO = CITAS.ID_EMPLEADO LIMIT 1) as EMPLEADO,
                    (SELECT NOMBRE FROM CLIENTES WHERE ID_CLIENTE = CITAS.ID_CLIENTE LIMIT 1) as CLIENTE
                FROM CITAS 
                WHERE ELIMINADO IS NULL AND HOUR(FECHA) = 0 AND MINUTE(FECHA) = 0
            """))
            
            print("\n🗑️  CITAS A ELIMINAR:")
            print("-" * 70)
            for row in result_show:
                print(f"  ID: {row[0]} | Fecha: {row[1]} | {row[2]} - {row[3]}")
            
            # Usar soft-delete: marcar como ELIMINADO
            result_delete = conn.execute(text("""
                UPDATE CITAS 
                SET ELIMINADO = NOW()
                WHERE ELIMINADO IS NULL AND HOUR(FECHA) = 0 AND MINUTE(FECHA) = 0
            """))
            conn.commit()
            
            print("\n" + "-" * 70)
            print(f"✅ {count_before} citas marcadas como eliminadas (soft-delete)")
            
            # Verificar el resultado
            result_after = conn.execute(text("""
                SELECT COUNT(*) as total FROM CITAS WHERE ELIMINADO IS NULL
            """))
            count_after = result_after.scalar()
            print(f"✅ Citas activas ahora: {count_after}")
        else:
            print("\n✅ No hay citas con hora 00:00:00, todo limpio!")
            
            # Mostrar citas actuales
            result_show = conn.execute(text("""
                SELECT 
                    ID_CITA,
                    FECHA,
                    (SELECT NOMBRE FROM EMPLEADOS WHERE ID_EMPLEADO = CITAS.ID_EMPLEADO LIMIT 1) as EMPLEADO,
                    (SELECT NOMBRE FROM CLIENTES WHERE ID_CLIENTE = CITAS.ID_CLIENTE LIMIT 1) as CLIENTE
                FROM CITAS 
                WHERE ELIMINADO IS NULL
                ORDER BY ID_CITA DESC
            """))
            
            print("\n📋 CITAS ACTIVAS ACTUALMENTE:")
            print("-" * 70)
            for row in result_show:
                print(f"  ID: {row[0]} | Fecha: {row[1]} | {row[2]} - {row[3]}")
                
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
finally:
    engine.dispose()

print("\n" + "=" * 70)
print("✅ Limpieza completada")
print("=" * 70)
