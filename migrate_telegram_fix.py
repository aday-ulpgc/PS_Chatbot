#!/usr/bin/env python3
"""Migración temporal para ID_TELEGRAM."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Cargar variables de entorno
_dotenv_path = os.path.join(os.path.dirname(__file__), "env", ".env")
load_dotenv(dotenv_path=_dotenv_path)

_CA_PATH = os.path.join(os.path.dirname(__file__), "src", "BBDD", "ca.pem")

USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
if USE_SQLITE:
    _DB_URL = "sqlite:///./ps_chatbot.db"
else:
    _DB_URL = os.getenv("DB_URL", "")

if USE_SQLITE:
    engine = create_engine(
        _DB_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
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

print("=" * 60)
print("MIGRACIÓN: ID_TELEGRAM INT → BIGINT")
print("=" * 60)

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

            column_type_upper = str(column_info[0]).upper()
            if "INT" in column_type_upper and "BIGINT" not in column_type_upper:
                print("\n🔄 Cambiando ID_TELEGRAM a BIGINT...")
                conn.execute(
                    text("""
                    ALTER TABLE CLIENTES MODIFY ID_TELEGRAM BIGINT NULL UNIQUE
                """)
                )
                conn.commit()
                print("✅ ID_TELEGRAM en CLIENTES ahora es BIGINT")
            elif "BIGINT" in column_type_upper:
                print("✅ ID_TELEGRAM en CLIENTES ya es BIGINT")
            else:
                print(f"⚠️ Tipo inesperado: {column_info[0]}")
        else:
            print("❌ Columna ID_TELEGRAM no encontrada")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n✅ Migración completada")
