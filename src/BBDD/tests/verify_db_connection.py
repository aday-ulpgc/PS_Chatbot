#!/usr/bin/env python3
"""Script para verificar conexión a base de datos y tablas."""

import sys
import os

# Agregar src al path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from BBDD.databasecontroller import engine, get_session
from sqlalchemy import text, inspect

print("="*80)
print("VERIFICACIÓN DE CONEXIÓN A BASE DE DATOS")
print("="*80)

# Test 1: Conexión al engine
print("\n1️⃣  Probando conexión al engine...")
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Test 2: Verificar tablas existentes
print("\n2️⃣  Tablas existentes en la BD...")
try:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"✅ Tablas encontradas: {len(tables)}")
    for table in sorted(tables):
        print(f"   - {table}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Verificar tabla EMPLEADOS
print("\n3️⃣  Verificando tabla EMPLEADOS...")
try:
    inspector = inspect(engine)
    if 'EMPLEADOS' in inspector.get_table_names():
        columns = inspector.get_columns('EMPLEADOS')
        print(f"✅ Tabla EMPLEADOS existe")
        print("   Columnas:")
        for col in columns:
            print(f"   - {col['name']} ({col['type']})")
    else:
        print("❌ Tabla EMPLEADOS NO existe")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Probar get_session
print("\n4️⃣  Probando get_session()...")
try:
    with get_session() as session:
        result = session.execute(text("SELECT COUNT(*) as total FROM USUARIOS"))
        row = result.fetchone()
        total = row[0] if row else 0
        print(f"✅ get_session() funciona")
        print(f"   Total de usuarios en BD: {total}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*80)
print("✅ VERIFICACIÓN COMPLETADA")
print("="*80)
