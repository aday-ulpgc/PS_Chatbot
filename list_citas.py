import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.BBDD.databasecontroller import get_session, CitaCorp

with get_session() as session:
    citas = session.query(CitaCorp).all()
    for c in citas:
        print(
            f"ID: {c.ID_CITA} | Cliente: {c.ID_CLIENTE} | Empleado: {c.ID_EMPLEADO} | Fecha: {c.FECHA} | Eliminado: {c.ELIMINADO}"
        )
