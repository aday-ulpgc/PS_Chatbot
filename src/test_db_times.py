"""Test file for database times - DEPRECATED.

This test file uses the old Usuario/CitaInd architecture which has been removed.
Will be updated when necessary.
"""
import sys

sys.path.insert(0, ".")

from src.BBDD.database_service import get_session
from src.BBDD.databasecontroller import CitaCorp


def main():
    print("Consultando citas en la base de datos...")
    with get_session() as session:
        citas = (
            session.query(CitaCorp)
            .filter(CitaCorp.ELIMINADO.is_(None))
            .order_by(CitaCorp.FECHA.asc())
            .all()
        )
        for cita in citas:
            cliente_nombre = (
                cita.cliente.NOMBRE if cita.cliente else 'N/A'
            )
            print(
                f"ID={cita.ID_CITA} | {cliente_nombre} | FECHA raw={cita.FECHA} | hora='{cita.FECHA.strftime('%H:%M')}'"
            )


if __name__ == "__main__":
    main()
