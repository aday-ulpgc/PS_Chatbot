#!/usr/bin/env python3
"""Script para probar crear_empleado directamente (sin HTTP)."""

import sys
import os

# Agregar src al path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from BBDD.databasecontroller import (
    get_session,
    crear_usuario,
    crear_empleado,
)

print("="*80)
print("PRUEBA DIRECTA: Crear Empleado")
print("="*80)

try:
    with get_session() as session:
        # 1. Crear usuario corporativo
        print("\n1️⃣  Crear usuario corporativo...")
        usuario = crear_usuario(
            session,
            tipo="C",
            nombre="Empresa Test",
            email=f"empresa_{os.urandom(4).hex()}@test.com",
            contrasena="empresa_pass123"
        )
        session.commit()
        print(f"✅ Usuario creado (ID: {usuario.ID_USUARIO}, TIPO: {usuario.TIPO})")
        
        # 2. Crear empleado
        print("\n2️⃣  Crear empleado...")
        empleado = crear_empleado(
            session,
            id_usuario=usuario.ID_USUARIO,
            tipo="E",
            nombre="Dr. Pérez",
            contrasena="empleado_pass123"
        )
        session.commit()
        print(f"✅ Empleado creado (ID: {empleado.ID_EMPLEADO})")
        print(f"   - Nombre: {empleado.NOMBRE}")
        print(f"   - Tipo: {empleado.TIPO}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
