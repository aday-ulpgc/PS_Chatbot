#!/usr/bin/env python3
"""
Migración: Eliminar arquitecura Individual y mantener solo Corporativa.
- Migra datos de CITAS_IND a CITAS_COR
- Elimina tabla CITAS_IND
- Limpia tabla USUARIOS (elimina relación con citas individuales)
"""

import sys
import os
from sqlalchemy import text
from BBDD.databasecontroller import engine

# Agregar src al path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def migrate_to_corp_only():
    """Migración a arquitectura corporativa única."""
    try:
        print("🔄 Iniciando migración: Individual → Solo Corporativa...\n")
        
        with engine.connect() as conn:
            # 1. Verificar si CITAS_IND existe
            print("1️⃣  Verificando tabla CITAS_IND...")
            result = conn.execute(
                text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'CITAS_IND'
            """)
            )
            exists = result.fetchone()[0] > 0
            
            if exists:
                # 2. Contar registros en CITAS_IND
                result = conn.execute(text("SELECT COUNT(*) FROM CITAS_IND"))
                count = result.fetchone()[0]
                print(f"✅ CITAS_IND encontrada con {count} registros")
                
                if count > 0:
                    print("\n2️⃣  Migrando datos de CITAS_IND a CITAS_COR...")
                    print("⚠️  Nota: Se crearán empleados genéricos para cada usuario de CITAS_IND")
                    
                    # Para cada usuario con CITAS_IND, crear un empleado
                    # y luego migrar la cita
                    print("   - Creando empleados genéricos...")
                    conn.execute(text("""
                        INSERT INTO EMPLEADOS (ID_USUARIO, TIPO, NOMBRE, ELIMINADO)
                        SELECT DISTINCT 
                            u.ID_USUARIO,
                            'E',
                            CONCAT('Empleado - ', u.NOMBRE),
                            NULL
                        FROM USUARIOS u
                        LEFT JOIN EMPLEADOS e ON u.ID_USUARIO = e.ID_USUARIO
                        WHERE u.ID_USUARIO IN (SELECT DISTINCT ID_USUARIO FROM CITAS_IND)
                        AND e.ID_EMPLEADO IS NULL
                    """))
                    
                    # Crear clientes genéricos y migrar citas
                    print("   - Creando clientes genéricos...")
                    conn.execute(text("""
                        INSERT INTO CLIENTES (ID_EMPLEADO_USUAL, DNI, NOMBRE, ELIMINADO)
                        SELECT DISTINCT 
                            e.ID_EMPLEADO,
                            CONCAT('GENERIC-', ci.ID_CITA),
                            CONCAT('Cliente Genérico - Cita ', ci.ID_CITA),
                            NULL
                        FROM CITAS_IND ci
                        JOIN USUARIOS u ON ci.ID_USUARIO = u.ID_USUARIO
                        JOIN EMPLEADOS e ON u.ID_USUARIO = e.ID_USUARIO
                        WHERE ci.ELIMINADO IS NULL
                    """))
                    
                    print("   - Migrando citas...")
                    conn.execute(text("""
                        INSERT INTO CITAS_COR (ID_EMPLEADO, ID_CLIENTE, FECHA, DURACION, DESCRIPCIÓN, ELIMINADO)
                        SELECT 
                            e.ID_EMPLEADO,
                            c.ID_CLIENTE,
                            ci.FECHA,
                            ci.DURACION,
                            ci.DESCRIPCIÓN,
                            ci.ELIMINADO
                        FROM CITAS_IND ci
                        JOIN USUARIOS u ON ci.ID_USUARIO = u.ID_USUARIO
                        JOIN EMPLEADOS e ON u.ID_USUARIO = e.ID_USUARIO
                        JOIN CLIENTES c ON e.ID_EMPLEADO = c.ID_EMPLEADO_USUAL
                        AND CONCAT('GENERIC-', ci.ID_CITA) = c.DNI
                    """))
                    
                    print("✅ Datos migrados correctamente")
                else:
                    print("✅ CITAS_IND vacía, no hay datos para migrar")
                
                # 3. Eliminar tabla CITAS_IND
                print("\n3️⃣  Eliminando tabla CITAS_IND...")
                conn.execute(text("DROP TABLE CITAS_IND"))
                print("✅ Tabla CITAS_IND eliminada")
            else:
                print("✅ CITAS_IND no existe (ya fue eliminada)")
            
            # 4. Limpiar USUARIOS: remover referencia a TIPO='I'
            print("\n4️⃣  Actualizando tabla USUARIOS...")
            # Cambiar todos los TIPO='I' a 'C' o dejarlos sin tipo
            conn.execute(text("""
                UPDATE USUARIOS SET TIPO = 'C' WHERE TIPO = 'I' OR TIPO IS NULL
            """))
            print("✅ USUARIOS actualizados (TIPO='I' → 'C')")
            
            # 5. Agregar columna telegram_id a CLIENTE (si no existe)
            print("\n5️⃣  Agregando columna telegram_id a CLIENTE...")
            try:
                conn.execute(text("""
                    ALTER TABLE CLIENTES ADD COLUMN telegram_id INT NULL AFTER ID_CLIENTE
                """))
                print("✅ Columna telegram_id agregada a CLIENTE")
            except Exception as e:
                print(f"⚠️  Columna telegram_id ya existe o error: {e}")
            
            # Confirmar cambios
            conn.commit()
            
            print("\n✅ Migración completada exitosamente")
            print("   - Arquitectura: Solo Corporativa")
            print("   - Tabla CITAS_IND: Eliminada")
            print("   - Tabla USUARIOS: Actualizada (TIPO='C')")
            print("   - Tabla CLIENTE: Agregado campo telegram_id")
            
    except Exception as e:
        print(f"\n❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate_to_corp_only()
