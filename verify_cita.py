#!/usr/bin/env python3
"""Script para verificar las citas guardadas en la BD."""

import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Cargar .env
_dotenv_path = os.path.join(os.path.dirname(__file__), "env", ".env")
load_dotenv(dotenv_path=_dotenv_path)

_CA_PATH = os.path.join(os.path.dirname(__file__), "src", "BBDD", "ca.pem")

USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
if USE_SQLITE:
    _DB_URL = "sqlite:///./ps_chatbot.db"
else:
    _DB_URL = os.getenv("DB_URL", "")

if USE_SQLITE:
    engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        _DB_URL,
        connect_args={
            "ssl": {"ca": _CA_PATH},
            "connect_timeout": 30,
        },
        pool_pre_ping=True,
        pool_recycle=3600,
    )

print("=" * 70)
print("VERIFICACIÓN DE CITAS EN LA BD")
print("=" * 70)

try:
    with engine.connect() as conn:
        print("\n✅ Conexión a BD exitosa\n")

        # Verificar citas más recientes
        print("📅 ÚLTIMAS 5 CITAS CREADAS:")
        print("-" * 70)

        result = conn.execute(
            text("""
            SELECT 
                c.ID_CITA,
                c.FECHA,
                e.NOMBRE as EMPLEADO,
                e.EMAIL as EMAIL_EMPLEADO,
                cl.NOMBRE as CLIENTE,
                cl.ID_TELEGRAM,
                cl.DNI,
                c.`DESCRIPCIÓN` as DESCRIPCION,
                c.DURACION
            FROM CITAS c
            JOIN EMPLEADOS e ON c.ID_EMPLEADO = e.ID_EMPLEADO
            JOIN CLIENTES cl ON c.ID_CLIENTE = cl.ID_CLIENTE
            WHERE c.ELIMINADO IS NULL
            ORDER BY c.ID_CITA DESC
            LIMIT 5
        """)
        )

        rows = result.fetchall()
        if rows:
            for i, row in enumerate(rows, 1):
                print(f"\n🔹 Cita #{i}:")
                print(f"   ID: {row[0]}")
                print(f"   Fecha/Hora: {row[1]}")
                print(f"   Empleado: {row[2]} ({row[3]})")
                print(f"   Cliente: {row[4]}")
                print(f"   Telegram ID: {row[5]}")
                print(f"   DNI: {row[6]}")
                print(f"   Descripción: {row[7]}")
                print(
                    f"   Duración: {row[8]} min"
                    if row[8]
                    else "   Duración: No especificada"
                )
        else:
            print("❌ No hay citas registradas en la BD")

        # Resumen
        print("\n" + "-" * 70)
        print("📊 RESUMEN:")
        print("-" * 70)

        result_count = conn.execute(
            text("""
            SELECT COUNT(*) as total FROM CITAS WHERE ELIMINADO IS NULL
        """)
        )
        total = result_count.fetchone()[0]
        print(f"Total de citas activas: {total}")

        result_clientes = conn.execute(
            text("""
            SELECT COUNT(*) as total FROM CLIENTES WHERE ELIMINADO IS NULL
        """)
        )
        total_clientes = result_clientes.fetchone()[0]
        print(f"Total de clientes activos: {total_clientes}")

        result_empleados = conn.execute(
            text("""
            SELECT COUNT(*) as total FROM EMPLEADOS WHERE ELIMINADO IS NULL
        """)
        )
        total_empleados = result_empleados.fetchone()[0]
        print(f"Total de empleados activos: {total_empleados}")

        print("\n✅ Verificación completada")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
