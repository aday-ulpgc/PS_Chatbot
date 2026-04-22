#!/usr/bin/env python3
"""Script para insertar directamente una cita de prueba."""

import sys
import os

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from datetime import datetime  # noqa: E402
from src.BBDD.databasecontroller import (  # noqa: E402
    get_session,
    crear_contacto,
    crear_cita,
    Usuario,
    Contacto,
)


def test_insert_cita():
    """Test insertar cita con ELIMINADO = None."""
    try:
        print("🔄 Probando inserción de cita...")
        with get_session() as session:
            # Buscar usuario existente
            usuario = (
                session.query(Usuario).filter(Usuario.EMAIL.like("telegram_%")).first()
            )
            if not usuario:
                print("❌ No hay usuarios de Telegram. Ejecuta el bot primero.")
                return

            print(f"✅ Usuario encontrado: {usuario.NOMBRE} (ID: {usuario.ID_USUARIO})")

            # Buscar o crear contacto
            contacto = (
                session.query(Contacto)
                .filter(
                    Contacto.ID_USUARIO == usuario.ID_USUARIO,
                    Contacto.ELIMINADO is None,
                )
                .first()
            )

            if not contacto:
                print("🔄 Creando contacto...")
                contacto = crear_contacto(
                    session,
                    id_usuario=usuario.ID_USUARIO,
                    nombre=usuario.NOMBRE,
                    email=usuario.EMAIL,
                )
                session.flush()
                print(f"✅ Contacto creado (ID: {contacto.ID_CONTACTO})")
            else:
                print(f"✅ Contacto encontrado (ID: {contacto.ID_CONTACTO})")

            # Crear cita
            print("🔄 Creando cita...")
            cita = crear_cita(
                session,
                id_contacto=contacto.ID_CONTACTO,
                fecha=datetime(2026, 4, 15, 14, 30),
                descripcion="Cita de prueba",
            )
            print(f"✅ Cita creada (ID: {cita.ID_CITA})")

            # Commit
            session.commit()
            print("✅ Cita guardada en BD")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_insert_cita()
