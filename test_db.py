#!/usr/bin/env python3
"""Script para probar la conexión a base de datos y creación de usuario."""

import sys
import os
from BBDD.databasecontroller import get_session, crear_usuario, Usuario


# Agregar src al path
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def test_db():
    """Test de creación de usuario en la BD."""
    try:
        print("🔄 Probando conexión a base de datos...")
        with get_session() as session:
            print("✅ Conexión exitosa")

            # Prueba de creación de usuario
            print("\n🔄 Creando usuario de prueba...")
            nuevo_usuario = crear_usuario(
                session,
                tipo="I",
                nombre="Usuario Test",
                email="test@example.com",
                contrasena="password123",
            )
            print(f"✅ Usuario creado (ID: {nuevo_usuario.ID_USUARIO})")

            # Commit
            session.commit()
            print("✅ Usuario commiteado en la BD")

            # Verificar que existe
            usuario_verificado = (
                session.query(Usuario)
                .filter(Usuario.EMAIL == "test@example.com")
                .first()
            )
            if usuario_verificado:
                print(f"✅ Usuario verificado en la BD: {usuario_verificado.NOMBRE}")
            else:
                print("❌ Usuario no encontrado después del commit")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_db()
