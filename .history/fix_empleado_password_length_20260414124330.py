#!/usr/bin/env python3
"""Script para aumentar el tamaño de CONTRASEÑA_CORPORATIVA."""

import sys
import os
from sqlalchemy import text

# Agregar src al path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from BBDD.databasecontroller import engine

print("🔄 Aumentando tamaño de CONTRASEÑA_CORPORATIVA...")
with engine.connect() as conn:
    try:
        conn.execute(text("""
            ALTER TABLE EMPLEADOS MODIFY CONTRASEÑA_CORPORATIVA VARCHAR(255) NOT NULL
        """))
        conn.commit()
        print("✅ CONTRASEÑA_CORPORATIVA aumentado a VARCHAR(255)")
    except Exception as e:
        print(f"❌ Error: {e}")
