import sys

sys.path.insert(0, ".")

from src.BBDD.database_service import get_session
from src.BBDD.databasecontroller import CitaInd, Usuario


def main():
    print("Consultando citas en la base de datos...")
    with get_session() as session:
        citas = (
            session.query(CitaInd)
            .filter(CitaInd.ELIMINADO.is_(None))
            .order_by(CitaInd.FECHA.asc())
            .all()
        )
        for cita in citas:
            usuario = (
                session.query(Usuario)
                .filter(Usuario.ID_USUARIO == cita.ID_USUARIO)
                .first()
            )
            print(
                f"ID={cita.ID_CITA} | {usuario.EMAIL if usuario else 'N/A'} | FECHA raw={cita.FECHA} | hora='{cita.FECHA.strftime('%H:%M')}'"
            )


if __name__ == "__main__":
    main()
