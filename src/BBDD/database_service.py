"""Servicio para gestionar la base de datos desde el bot de Telegram."""

from datetime import datetime
from .databasecontroller import (
    get_session,
    Usuario,
    Contacto,
    crear_usuario,
    crear_contacto,
    crear_cita,
    CitaInd,
)


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
            email = f"telegram_{telegram_id}@bot.local"
            usuario = session.query(Usuario).filter(Usuario.EMAIL == email).first()

            if not usuario:
                print(f"❌ Usuario no encontrado: {email}")
                return False

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

            hora_parts = hora.split(":")
            cita_fecha = fecha.replace(
                hour=int(hora_parts[0]),
                minute=int(hora_parts[1]) if len(hora_parts) > 1 else 0,
                second=0,
                microsecond=0,
            )

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


def obtener_horas_ocupadas(fecha_str: str) -> list[str]:
    """Consulta la BD y devuelve una lista de horas ocupadas para una fecha dada."""
    try:
        with get_session() as session:
            citas_activas = (
                session.query(CitaInd).filter(CitaInd.ELIMINADO.is_(None)).all()
            )

            horas_ocupadas = []
            for cita in citas_activas:
                if cita.FECHA.strftime("%Y-%m-%d") == fecha_str:
                    hora_formateada = f"{cita.FECHA.hour}:{cita.FECHA.minute:02d}"
                    horas_ocupadas.append(hora_formateada)

            return horas_ocupadas
    except Exception as e:
        print(f"❌ Error al leer horas ocupadas: {e}")
        return []
    
def obtener_citas_usuario(telegram_id: int) -> list:
    """Recupera las citas activas de un usuario por su ID de Telegram."""
    try:
        with get_session() as session:
            email = f"telegram_{telegram_id}@bot.local"
            usuario = session.query(Usuario).filter(Usuario.EMAIL == email).first()
            
            if not usuario:
                return []

            # Obtenemos citas no eliminadas ordenadas por fecha
            citas_db = (
                session.query(CitaInd)
                .filter(CitaInd.ID_USUARIO == usuario.ID_USUARIO, CitaInd.ELIMINADO.is_(None))
                .order_by(CitaInd.FECHA.asc())
                .all()
            )

            citas_lista = []
            for cita in citas_db:
                citas_lista.append({
                    "ID_CITA": cita.ID_CITA,
                    "FECHA": cita.FECHA,
                    "DESCRIPCION": cita.DESCRIPCION
                })
                
            return citas_lista

    except Exception as e:
        print(f"❌ Error al obtener citas: {e}")
        return []
    
def cancelar_cita_db(id_cita: int) -> bool:
    """Marca una cita como eliminada en la base de datos."""
    try:
        from datetime import datetime
        with get_session() as session:
            cita = session.get(CitaInd, id_cita)
            if cita and cita.ELIMINADO is None:
                cita.ELIMINADO = datetime.now()
                session.commit()
                return True
    except Exception as e:
        print(f"❌ Error al cancelar cita: {e}")
    return False

def actualizar_cita_fecha_db(id_cita: int, nueva_fecha: datetime) -> bool:
    """Actualiza la fecha y hora de una cita en la base de datos."""
    try:
        with get_session() as session:
            from .databasecontroller import CitaInd
            cita = session.get(CitaInd, id_cita)
            if cita:
                cita.FECHA = nueva_fecha
                session.commit()
                return True
    except Exception as e:
        print(f"❌ Error al actualizar cita: {e}")
    return False

def obtener_info_cita_db(id_cita: int) -> dict:
    """Recupera la fecha de una cita específica antes de ser alterada."""
    try:
        with get_session() as session:
            from .databasecontroller import CitaInd
            cita = session.get(CitaInd, id_cita)
            if cita and cita.ELIMINADO is None:
                return {"FECHA": cita.FECHA}
    except Exception as e:
        print(f"❌ Error al obtener info de la cita: {e}")
    return None
