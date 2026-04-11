"""Servicio para gestionar la base de datos desde el bot de Telegram."""

import sys
import os
from datetime import datetime
from BBDD.databasecontroller import (
    get_session,
    Usuario,
    Contacto,
    crear_usuario,
    crear_contacto,
    crear_cita,
)

# Agregar el directorio src al path para importaciones correctas
_src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def obtener_o_crear_usuario_telegram(
    telegram_id: int, nombre: str | None = None
) -> dict:
    """Obtiene o crea un usuario basado en el ID de Telegram.

    Args:
        telegram_id: ID único del usuario en Telegram
        nombre: Nombre del usuario (usado si se crea nuevo)

    Returns:
        Dict con el ID de usuario en DB y si fue creado o no
    """
    try:
        with get_session() as session:
            email = f"telegram_{telegram_id}@bot.local"
            usuario = session.query(Usuario).filter(Usuario.EMAIL == email).first()

            if usuario:
                return {"id_usuario": usuario.ID_USUARIO, "creado": False}

            # Crear nuevo usuario
            nuevo_usuario = crear_usuario(
                session,
                tipo="I",
                nombre=nombre or f"Usuario Telegram {telegram_id}",
                email=email,
                contrasena="telegram_bot",  # Contraseña por defecto
            )
            session.commit()
            return {"id_usuario": nuevo_usuario.ID_USUARIO, "creado": True}
    except Exception as e:
        print(f"❌ Error en obtener_o_crear_usuario_telegram: {e}")
        return {"id_usuario": None, "creado": False, "error": str(e)}


def guardar_cita_en_db(
    telegram_id: int, fecha: datetime, hora: str, descripcion: str = ""
) -> bool:
    """Guarda una cita en la base de datos.

    Args:
        telegram_id: ID del usuario en Telegram
        fecha: Fecha de la cita (datetime)
        hora: Hora en formato "HH:MM"
        descripcion: Descripción de la cita

    Returns:
        True si se guardó correctamente, False si hubo error
    """
    try:
        with get_session() as session:
            # 1. Obtener usuario
            email = f"telegram_{telegram_id}@bot.local"
            usuario = session.query(Usuario).filter(Usuario.EMAIL == email).first()

            if not usuario:
                print(f"❌ Usuario no encontrado: {email}")
                return False

            # 2. Obtener o crear contacto genérico de reserva
            # Los contactos representan personas/servicios con los que se agenda,
            # no al propio usuario del bot. Se usa un contacto genérico "Reserva general"
            # por usuario para las citas creadas directamente desde el bot.
            NOMBRE_CONTACTO_BOT = "Reserva general"
            contacto = (
                session.query(Contacto)
                .filter(
                    Contacto.ID_USUARIO == usuario.ID_USUARIO,
                    Contacto.NOMBRE == NOMBRE_CONTACTO_BOT,
                    Contacto.ELIMINADO is None,
                )
                .first()
            )

            if not contacto:
                contacto = crear_contacto(
                    session,
                    id_usuario=usuario.ID_USUARIO,
                    nombre=NOMBRE_CONTACTO_BOT,
                    email=f"reserva_general_{usuario.ID_USUARIO}@bot.local",
                )
                session.flush()

            # 3. Combinar fecha y hora
            hora_parts = hora.split(":")
            cita_fecha = fecha.replace(
                hour=int(hora_parts[0]),
                minute=int(hora_parts[1]) if len(hora_parts) > 1 else 0,
                second=0,
                microsecond=0,
            )

            # 4. Crear cita
            crear_cita(
                session,
                id_usuario=usuario.ID_USUARIO,
                id_contacto=contacto.ID_CONTACTO,
                fecha=cita_fecha,
                descripcion=descripcion or "Cita reservada desde Telegram",
                prioridad=1,
            )
            session.commit()
            print(f"✅ Cita guardada para usuario {telegram_id} en {cita_fecha}")
            return True

    except Exception as e:
        print(f"❌ Error al guardar cita en DB: {e}")
        return False
