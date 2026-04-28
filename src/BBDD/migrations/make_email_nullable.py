#!/usr/bin/env python3
"""Script para hacer EMAIL nullable en CONTACTOS."""

import sys
import os
from sqlalchemy import text
from BBDD.databasecontroller import engine

# Agregar src al path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def make_email_nullable():
    """Hacer EMAIL nullable en CONTACTOS."""
    try:
        print("🔄 Conectando a la BD...")
        with engine.connect() as conn:
            print("✅ Conexión exitosa")

            # Verificar estado actual
            print("\n🔄 Verificando columna EMAIL en CONTACTOS...")
            result = conn.execute(
                text("""
                SELECT COLUMN_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'CONTACTOS' 
                AND COLUMN_NAME = 'EMAIL'
                LIMIT 1
            """)
            )
            column_info = result.fetchone()
            if column_info:
                print(f"   Tipo actual: {column_info[0]}, Nullable: {column_info[1]}")

                if column_info[1] == "NO":
                    print("\n🔄 Quitando NOT NULL de EMAIL...")
                    conn.execute(
                        text("""
                        ALTER TABLE CONTACTOS MODIFY EMAIL VARCHAR(200) NULL
                    """)
                    )
                    conn.commit()
                    print("✅ EMAIL en CONTACTOS ahora es NULLABLE")
                else:
                    print("✅ EMAIL en CONTACTOS ya es nullable")
            else:
                print("❌ Columna EMAIL no encontrada")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    make_email_nullable()
