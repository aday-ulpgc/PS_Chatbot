"""
Script para verificar el estado exacto de las citas en la BD
Consulta SQL directa sin filtros
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from BBDD.databasecontroller import engine
from sqlalchemy import text


def verificar_citas_exactas():
    """Verificación SQL directa de las citas específicas."""

    print(f"\n{'='*80}")
    print("🔍 VERIFICACIÓN EXACTA DE CITAS EN BD (SQL DIRECTO)")
    print(f"{'='*80}\n")

    try:
        with engine.connect() as conn:
            # Consulta SQL directa
            query = text("""
                SELECT 
                    ID_CITA,
                    FECHA,
                    ID_EMPLEADO,
                    ID_CLIENTE,
                    ELIMINADO,
                    DESCRIPCIÓN,
                    DURACION
                FROM CITAS
                WHERE ID_CITA IN (3, 4, 5)
                ORDER BY ID_CITA
            """)

            result = conn.execute(query)
            rows = result.fetchall()

            if not rows:
                print("❌ No se encontraron citas con IDs 3, 4, 5")
                return

            print("📋 ESTADO ACTUAL DE LAS CITAS EN BD:\n")

            for row in rows:
                id_cita = row[0]
                fecha = row[1]
                id_empleado = row[2]
                id_cliente = row[3]
                eliminado = row[4]
                descripcion = row[5]
                duracion = row[6]

                print(f"🔹 CITA ID: {id_cita}")
                print(f"   FECHA: {fecha}")
                print(f"   ID_EMPLEADO: {id_empleado}")
                print(f"   ID_CLIENTE: {id_cliente}")
                print(f"   ELIMINADO: {eliminado}")
                print(f"   DESCRIPCIÓN: {descripcion}")
                print(f"   DURACIÓN: {duracion}")

                if eliminado is None:
                    print("   ✅ ACTIVA (ELIMINADO = NULL)")
                else:
                    print(f"   🗑️  ELIMINADA (ELIMINADO = {eliminado})")

                print()

            # Contar todas las citas
            print(f"{'='*80}")
            print("\n📊 RESUMEN DE TODAS LAS CITAS:\n")

            count_query = text("""
                SELECT 
                    COUNT(*) as total_registros,
                    SUM(CASE WHEN ELIMINADO IS NULL THEN 1 ELSE 0 END) as activas,
                    SUM(CASE WHEN ELIMINADO IS NOT NULL THEN 1 ELSE 0 END) as eliminadas
                FROM CITAS
            """)

            count_result = conn.execute(count_query)
            count_row = count_result.fetchone()

            print(f"Total de registros en CITAS: {count_row[0]}")
            print(f"✅ Citas activas (ELIMINADO = NULL): {count_row[1]}")
            print(f"🗑️  Citas eliminadas (ELIMINADO != NULL): {count_row[2]}")

            print(f"\n{'='*80}")
            print("✅ Verificación completada")
            print(f"{'='*80}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    verificar_citas_exactas()
