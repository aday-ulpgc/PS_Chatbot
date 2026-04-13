#!/usr/bin/env python3
"""Script para migrar/actualizar la estructura de la BD."""

import sys
import os

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from sqlalchemy import text
from src.BBDD.databasecontroller import engine


def migrate_db():
    """Ejecutar migraciones necesarias."""
    try:
        print("🔄 Conectando a la BD para migración...")
        with engine.connect() as conn:
            print("✅ Conexión exitosa")

            # Obtener información de la columna CONTRASEÑA
            print("\n🔄 Verificando columna CONTRASEÑA...")
            result = conn.execute(
                text("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'USUARIOS' 
                AND COLUMN_NAME = 'CONTRASEÑA'
                LIMIT 1
            """)
            )
            column_def = result.fetchone()
            if column_def:
                print(f"✅ Definición actual: {column_def[0]}")
            else:
                print("❌ Columna no encontrada")
                return

            # Aumentar el tamaño si es necesario
            if "varchar" in column_def[0].lower():
                length = int(column_def[0].split("(")[1].split(")")[0])
                if length < 255:
                    print(
                        f"\n🔄 Aumentando tamaño de VARCHAR({length}) a VARCHAR(255)..."
                    )
                    conn.execute(
                        text("""
                        ALTER TABLE USUARIOS MODIFY CONTRASEÑA VARCHAR(255) NOT NULL
                    """)
                    )
                    conn.commit()
                    print("✅ Columna actualizada a VARCHAR(255)")
                else:
                    print(f"✅ Columna ya tiene tamaño suficiente: {length}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    migrate_db()
