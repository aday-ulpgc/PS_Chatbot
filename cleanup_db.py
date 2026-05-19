#!/usr/bin/env python3
"""Script para limpiar BD: borrar empleados y renombrar tabla CITAS_COR a CITAS."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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
print("LIMPIEZA DE BD")
print("=" * 70)

try:
    with engine.connect() as conn:
        print("\n✅ Conexión a BD exitosa\n")

        # Verificar qué tablas existen
        result = conn.execute(
            text("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('CITAS_COR', 'CITAS')
        """)
        )
        existing_tables = [row[0] for row in result]
        print(f"📋 Tablas existentes: {existing_tables}")

        # Determinar el nombre correcto de la tabla
        table_name = "CITAS" if "CITAS" in existing_tables else "CITAS_COR"
        print(f"🔍 Usando tabla: {table_name}\n")

        # Desactivar constraints temporalmente
        print("🔄 Desactivando foreign key constraints...")
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        # 1. Borrar citas de empleados que no sean Raul (ID=7) ni Maria (ID=8)
        print("🔄 Borrando citas de empleados que no sean Raul ni Maria...")
        result = conn.execute(
            text(f"""
            DELETE FROM {table_name}
            WHERE ID_EMPLEADO NOT IN (7, 8)
        """)
        )
        conn.commit()
        print(f"✅ Eliminadas {result.rowcount} citas")

        # 2. Borrar empleados que no sean Raul (ID=7) ni Maria (ID=8)
        print("🔄 Borrando empleados que no sean Raul ni Maria...")
        result = conn.execute(
            text("""
            DELETE FROM EMPLEADOS 
            WHERE ID_EMPLEADO NOT IN (7, 8)
        """)
        )
        conn.commit()
        print(f"✅ Eliminados {result.rowcount} empleados")

        # Reactivar constraints
        print("🔄 Reactivando foreign key constraints...")
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()

        # Verificar empleados restantes
        result = conn.execute(text("SELECT ID_EMPLEADO, NOMBRE, EMAIL FROM EMPLEADOS"))
        print("\n📋 Empleados restantes:")
        for row in result:
            print(f"   - ID {row[0]}: {row[1]} ({row[2]})")

        # Verificar citas restantes
        result = conn.execute(
            text(f"""
            SELECT ID_EMPLEADO FROM {table_name} GROUP BY ID_EMPLEADO
        """)
        )
        emp_ids = [row[0] for row in result]
        print(f"\n📅 Citas para empleados: {emp_ids}")

        # 2. Renombrar tabla CITAS_COR a CITAS (si existe)
        print("\n🔄 Renombrando tabla CITAS_COR a CITAS...")

        # Verificar si la tabla CITAS_COR existe
        result = conn.execute(
            text("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'CITAS_COR' AND TABLE_SCHEMA = DATABASE()
        """)
        )

        if result.fetchone():
            conn.execute(text("ALTER TABLE CITAS_COR RENAME TO CITAS"))
            conn.commit()
            print("✅ Tabla renombrada: CITAS_COR → CITAS")
        else:
            # Si no existe CITAS_COR, verificar si existe CITAS
            result = conn.execute(
                text("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'CITAS' AND TABLE_SCHEMA = DATABASE()
            """)
            )
            if result.fetchone():
                print("⚠️ La tabla ya se llama CITAS")
            else:
                print("❌ Tabla CITAS_COR o CITAS no encontrada")

        print("\n✅ Limpieza completada")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
