import sys

sys.path.insert(0, "src")
from BBDD.databasecontroller import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT ID_EMPLEADO, NOMBRE, ELIMINADO FROM EMPLEADOS"))
    rows = res.fetchall()
    print("Empleados en BD:", len(rows))
    for r in rows:
        print("  ID:", r[0], "| Nombre:", r[1], "| ELIMINADO:", r[2])

    print()
    res2 = conn.execute(
        text(
            "SELECT ID_EMPLEADO, NOMBRE, ELIMINADO FROM EMPLEADOS WHERE ELIMINADO IS NULL"
        )
    )
    rows2 = res2.fetchall()
    print("Empleados activos (ELIMINADO IS NULL):", len(rows2))
    for r in rows2:
        print("  -", r[1])
