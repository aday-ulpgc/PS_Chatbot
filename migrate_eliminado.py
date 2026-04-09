#!/usr/bin/env python3
"""Script para quitarle NOT NULL a la columna ELIMINADO en CITAS_IND."""

import sys
import os
from sqlalchemy import text

# Agregar src al path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from BBDD.databasecontroller import engine

def migrate_eliminado_nullable():
    """Hacer ELIMINADO nullable en CITAS_IND."""
    try:
        print("🔄 Conectando a la BD para migración...")
        with engine.connect() as conn:
            print("✅ Conexión exitosa")
            
            # Verificar estructura actual de CITAS_IND
            print("\n🔄 Verificando columna ELIMINADO en CITAS_IND...")
            result = conn.execute(text("""
                SELECT COLUMN_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'CITAS_IND' 
                AND COLUMN_NAME = 'ELIMINADO'
                LIMIT 1
            """))
            column_info = result.fetchone()
            if column_info:
                print(f"✅ Tipo actual: {column_info[0]}, Nullable: {column_info[1]}")
                
                if column_info[1] == "NO":
                    print("\n🔄 Quitando NOT NULL de ELIMINADO en CITAS_IND...")
                    conn.execute(text("""
                        ALTER TABLE CITAS_IND MODIFY ELIMINADO DATETIME NULL
                    """))
                    conn.commit()
                    print("✅ CITAS_IND.ELIMINADO ahora es nullable")
                else:
                    print("✅ CITAS_IND.ELIMINADO ya es nullable")
            else:
                print("❌ Columna ELIMINADO no encontrada en CITAS_IND")
                
            # También verificar CONTACTOS
            print("\n🔄 Verificando columna ELIMINADO en CONTACTOS...")
            result = conn.execute(text("""
                SELECT COLUMN_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'CONTACTOS' 
                AND COLUMN_NAME = 'ELIMINADO'
                LIMIT 1
            """))
            column_info = result.fetchone()
            if column_info:
                print(f"✅ Tipo actual: {column_info[0]}, Nullable: {column_info[1]}")
                
                if column_info[1] == "NO":
                    print("\n🔄 Quitando NOT NULL de ELIMINADO en CONTACTOS...")
                    conn.execute(text("""
                        ALTER TABLE CONTACTOS MODIFY ELIMINADO DATETIME NULL
                    """))
                    conn.commit()
                    print("✅ CONTACTOS.ELIMINADO ahora es nullable")
                else:
                    print("✅ CONTACTOS.ELIMINADO ya es nullable")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_eliminado_nullable()
