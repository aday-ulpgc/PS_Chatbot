#!/usr/bin/env python3
"""Script para inspeccionar la estructura de CITAS_IND."""

import sys
import os
from sqlalchemy import text

# Agregar src al path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from BBDD.databasecontroller import engine

def inspect_table():
    """Inspeccionar estructura de CITAS_IND."""
    try:
        print("🔄 Inspeccionando tabla CITAS_IND...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                DESCRIBE CITAS_IND
            """))
            
            print("\n📋 Estructura de CITAS_IND:")
            print("-" * 80)
            for row in result:
                print(f"Campo: {row[0]:<15} | Tipo: {row[1]:<20} | Null: {row[2]:<5} | Key: {row[3]:<5} | Default: {row[4]:<10}")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_table()
