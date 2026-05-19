#!/usr/bin/env python3
"""Script para cambiar ID_TELEGRAM de INT a BIGINT en CLIENTES."""

import sys
import os
from sqlalchemy import text
from src.BBDD.databasecontroller import engine

# Agregar paths para imports - subir 2 niveles desde migrations
_script_dir = os.path.dirname(os.path.abspath(__file__))
_root_path = os.path.abspath(os.path.join(_script_dir, "..", ".."))
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)


def migrate_id_telegram_bigint():
    """Cambiar ID_TELEGRAM de INT a BIGINT en CLIENTES."""
    try:
        print("🔄 Conectando a la BD...")
        with engine.connect() as conn:
            print("✅ Conexión exitosa")

            # Verificar estado actual
            print("\n🔄 Verificando columna ID_TELEGRAM en CLIENTES...")
            result = conn.execute(
                text("""
                SELECT COLUMN_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'CLIENTES' 
                AND COLUMN_NAME = 'ID_TELEGRAM'
                LIMIT 1
            """)
            )
            column_info = result.fetchone()
            if column_info:
                print(f"   Tipo actual: {column_info[0]}, Nullable: {column_info[1]}")

                if "INT" in column_info[0] and "BIGINT" not in column_info[0]:
                    print("\n🔄 Cambiando ID_TELEGRAM a BIGINT...")
                    conn.execute(
                        text("""
                        ALTER TABLE CLIENTES MODIFY ID_TELEGRAM BIGINT NULL UNIQUE
                    """)
                    )
                    conn.commit()
                    print("✅ ID_TELEGRAM en CLIENTES ahora es BIGINT")
                elif "BIGINT" in column_info[0]:
                    print("✅ ID_TELEGRAM en CLIENTES ya es BIGINT")
                else:
                    print(f"⚠️ Tipo inesperado: {column_info[0]}")
            else:
                print("❌ Columna ID_TELEGRAM no encontrada")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRACIÓN: ID_TELEGRAM INT → BIGINT")
    print("=" * 60)
    success = migrate_id_telegram_bigint()
    if success:
        print("\n✅ Migración completada exitosamente")
    else:
        print("\n❌ Migración falló")
