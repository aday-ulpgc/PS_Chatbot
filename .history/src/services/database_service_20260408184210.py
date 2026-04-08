"""Servicio para gestionar la base de datos desde el bot de Telegram."""

from datetime import datetime
from sqlalchemy.orm import Session
from BBDD.databasecontroller import (
    get_session,
    Usuario,
    Contacto,
    crear_usuario,
    crear_contacto,
    crear_cita,
)


def obtener_o_crear_usuario_telegram(telegram_id: int, nombre: str | None = None) -> dict:
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


def guardar_cita_en_db(telegram_id: int, fecha: datetime, hora: str, descripcion: str = "") -> bool:
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
            usuario = session.query(Usuario).filter(
                Usuario.EMAIL == f"telegram_{telegram_id}@bot.local"
            ).first()
            
            if not usuario:
                return False
            
            # 2. Obtener o crear contacto (para el usuario consigo mismo)
            contacto = session.query(Contacto).filter(
                Contacto.ID_USUARIO == usuario.ID_USUARIO,
                Contacto.NOMBRE == usuario.NOMBRE,
            ).first()
            
            if not contacto:
                contacto = crear_contacto(
                    session,
                    id_usuario=usuario.ID_USUARIO,
                    nombre=usuario.NOMBRE,
                    email=usuario.EMAIL,
                )
            
            # 3. Combinar fecha y hora
            hora_parts = hora.split(":")
            cita_fecha = fecha.replace(
                hour=int(hora_parts[0]),
                minute=int(hora_parts[1]) if len(hora_parts) > 1 else 0,
            )
            
            # 4. Crear cita
            crear_cita(
                session,
                id_contacto=contacto.ID_CONTACTO,
                fecha=cita_fecha,
                descripcion=descripcion or f"Cita reservada desde Telegram",
                prioridad=1,
            )
            session.commit()
            return True
            
    except Exception as e:
        print(f"Error al guardar cita en DB: {e}")
        return False