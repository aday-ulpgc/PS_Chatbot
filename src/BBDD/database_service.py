"""Servicio para gestionar la base de datos desde el bot de Telegram.

Este módulo proporciona funciones de alto nivel para el bot que necesita
interactuar con Empleados y Clientes sin pasar por la API REST.
"""

import sys
import os
from datetime import datetime
from sqlalchemy import func
from src.BBDD.databasecontroller import (
    get_session,
    crear_cliente,
    obtener_o_crear_cliente_telegram,
)

_src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def obtener_o_crear_cliente_por_telegram(
    telegram_id: int, nombre: str | None = None, id_empleado_default: int | None = None
) -> dict:
    """Obtiene o crea un cliente basado en el ID de Telegram.

    Esta es la función principal para el bot. Devuelve un cliente listo para
    usarse en la creación de citas.

    Args:
        telegram_id: ID único del usuario en Telegram
        nombre: Nombre del cliente (usado si se crea nuevo)
        id_empleado_default: ID del empleado por defecto (si se crea cliente nuevo)
                            Si es None, selecciona el primer empleado activo

    Returns:
        Dict con:
        - cliente_id: ID del cliente en DB
        - creado: bool - True si fue creado, False si ya existía
        - error: str - Mensaje de error (si aplica)
    """
    try:
        with get_session() as session:
            # Si no hay empleado por defecto, obtener el primero activo
            if id_empleado_default is None:
                from src.BBDD.databasecontroller import Empleado
                empleado_default = session.query(Empleado).filter(
                    Empleado.ELIMINADO == None
                ).first()
                
                if empleado_default:
                    id_empleado_default = empleado_default.ID_EMPLEADO
                else:
                    return {
                        "cliente_id": None,
                        "creado": False,
                        "error": "No hay empleados disponibles en la BD"
                    }
            
            cliente_data = obtener_o_crear_cliente_telegram(
                session, telegram_id, id_empleado_default, nombre
            )
            return {
                "cliente_id": cliente_data.ID_CLIENTE,
                "creado": cliente_data.CREADO if hasattr(cliente_data, "CREADO") else False,
                "error": None,
            }
    except Exception as e:
        print(f"❌ Error en obtener_o_crear_cliente_por_telegram: {e}")
        import traceback
        traceback.print_exc()
        return {
            "cliente_id": None,
            "creado": False,
            "error": str(e),
        }


def guardar_cita_en_db(
    id_empleado: int,
    id_cliente: int,
    fecha: datetime,
    descripcion: str | None = None,
    duracion: int | None = None,
) -> dict:
    """Guarda una cita en la base de datos.

    Args:
        id_empleado: ID del empleado responsable
        id_cliente: ID del cliente
        fecha: Fecha y hora de la cita
        descripcion: Descripción opcional de la cita
        duracion: Duración en minutos (opcional)

    Returns:
        Dict con:
        - cita_id: ID de la cita creada
        - error: str - Mensaje de error (si aplica)
    """
    try:
        from src.BBDD.databasecontroller import crear_cita_corp

        with get_session() as session:
            cita = crear_cita_corp(
                session,
                id_empleado,
                id_cliente,
                fecha,
                descripcion,
                duracion,
            )
            return {
                "cita_id": cita.ID_CITA,
                "error": None,
            }
    except Exception as e:
        print(f"❌ Error en guardar_cita_en_db: {e}")
        import traceback
        traceback.print_exc()
        return {
            "cita_id": None,
            "error": str(e),
        }


def obtener_o_crear_usuario_telegram(
    telegram_id: int, nombre: str | None = None
) -> dict:
    """DEPRECATED - Use obtener_o_crear_cliente_por_telegram instead.
    
    This function is kept for backward compatibility but should not be used.
    """
    raise NotImplementedError(
        "obtener_o_crear_usuario_telegram is deprecated. "
        "Use obtener_o_crear_cliente_por_telegram instead."
    )


def obtener_usuario_y_contacto_para_cita(
    telegram_id: int, nombre: str | None = None
) -> dict:
    """DEPRECATED - Use obtener_o_crear_cliente_por_telegram instead."""
    raise NotImplementedError(
        "obtener_usuario_y_contacto_para_cita is deprecated. "
        "Use obtener_o_crear_cliente_por_telegram instead."
    )


def guardar_cita_en_db_legacy(
    telegram_id: int, fecha: datetime, hora: str, descripcion: str = ""
) -> bool:
    """DEPRECATED - Use guardar_cita_en_db with new signature instead."""
    raise NotImplementedError(
        "Legacy guardar_cita_en_db is deprecated. "
        "Use the new signature: guardar_cita_en_db(id_empleado, id_cliente, fecha, descripcion, duracion)"
    )


def obtener_horas_ocupadas(fecha_str: str) -> list[str]:
    """Consulta la BD y devuelve una lista de horas ocupadas para una fecha dada.
    El filtrado se delega al motor SQL (O(1) vs O(N) anterior).
    """
    try:
        from src.BBDD.databasecontroller import CitaCorp
        
        with get_session() as session:
            citas_activas = (
                session.query(CitaCorp)
                .filter(
                    CitaCorp.ELIMINADO.is_(None),
                    func.date(CitaCorp.FECHA) == fecha_str,
                )
                .all()
            )
            return [
                f"{cita.FECHA.hour}:{cita.FECHA.minute:02d}" for cita in citas_activas
            ]
    except Exception as e:
        print(f"Error al leer horas ocupadas: {e}")
        return []


def obtener_citas_usuario(telegram_id: int) -> list:
    """DEPRECATED - Use obtener_citas_cliente instead."""
    raise NotImplementedError(
        "obtener_citas_usuario is deprecated. "
        "Use obtener_citas_cliente with a specific client ID."
    )


def obtener_cliente_por_telegram_id(telegram_id: int) -> int | None:
    """Obtiene el cliente_id basado en el telegram_id.
    
    Args:
        telegram_id: ID único del usuario en Telegram
        
    Returns:
        cliente_id si existe, None si no se encuentra
    """
    try:
        from src.BBDD.databasecontroller import Cliente
        
        with get_session() as session:
            cliente = session.query(Cliente).filter(
                Cliente.TELEGRAM_ID == telegram_id,
                Cliente.ELIMINADO == None
            ).first()
            
            if cliente:
                return cliente.ID_CLIENTE
            return None
    except Exception as e:
        print(f"Error al obtener cliente por telegram_id: {e}")
    return None


def obtener_citas_cliente(cliente_id: int) -> list[dict]:
    """Obtiene todas las citas activas de un cliente.
    
    Args:
        cliente_id: ID del cliente
        
    Returns:
        Lista de dicts con info de citas: FECHA, ID_EMPLEADO, NOMBRE_EMPLEADO, etc.
    """
    try:
        from src.BBDD.databasecontroller import CitaCorp, Empleado
        
        with get_session() as session:
            citas = session.query(CitaCorp).filter(
                CitaCorp.ID_CLIENTE == cliente_id,
                CitaCorp.ELIMINADO == None
            ).order_by(CitaCorp.FECHA).all()
            
            result = []
            for cita in citas:
                empleado = session.query(Empleado).filter(
                    Empleado.ID_EMPLEADO == cita.ID_EMPLEADO
                ).first()
                
                result.append({
                    "ID_CITA": cita.ID_CITA,
                    "FECHA": cita.FECHA,
                    "DESCRIPCION": cita.DESCRIPCION,
                    "DURACION": cita.DURACION,
                    "ID_EMPLEADO": cita.ID_EMPLEADO,
                    "NOMBRE_EMPLEADO": empleado.NOMBRE if empleado else "Unknown",
                })
            
            return result
    except Exception as e:
        print(f"Error al obtener citas del cliente: {e}")
    return []


def cancelar_cita_db(id_cita: int) -> bool:
    """Marca una cita como eliminada."""
    try:
        from src.BBDD.databasecontroller import CitaCorp
        
        with get_session() as session:
            cita = session.query(CitaCorp).filter(CitaCorp.ID_CITA == id_cita).first()
            if cita:
                cita.ELIMINADO = datetime.now()
                session.commit()
                return True
        return False
    except Exception as e:
        print(f"Error al cancelar cita: {e}")
    return False


def obtener_empleados_activos() -> list[dict]:
    """Obtiene todos los empleados activos (no eliminados).
    
    Devuelve:
        Lista de dicts con: ID_EMPLEADO, NOMBRE, EMAIL
    """
    try:
        from src.BBDD.databasecontroller import Empleado
        
        with get_session() as session:
            empleados = session.query(Empleado).filter(
                Empleado.ELIMINADO == None
            ).all()
            
            return [
                {
                    "ID_EMPLEADO": emp.ID_EMPLEADO,
                    "NOMBRE": emp.NOMBRE,
                    "EMAIL": emp.EMAIL,
                }
                for emp in empleados
            ]
    except Exception as e:
        print(f"Error al obtener empleados: {e}")
    return []


def actualizar_cita_fecha_db(id_cita: int, nueva_fecha: datetime) -> bool:
    """Actualiza la fecha y hora de una cita."""
    try:
        from src.BBDD.databasecontroller import CitaCorp
        
        with get_session() as session:
            cita = session.query(CitaCorp).filter(CitaCorp.ID_CITA == id_cita).first()
            if cita:
                cita.FECHA = nueva_fecha
                session.commit()
                return True
        return False
    except Exception as e:
        print(f"Error al actualizar cita: {e}")
    return False


def obtener_info_cita_db(id_cita: int) -> dict | None:
    """Recupera la fecha de una cita específica."""
    try:
        from src.BBDD.databasecontroller import CitaCorp
        
        with get_session() as session:
            cita = session.query(CitaCorp).filter(CitaCorp.ID_CITA == id_cita).first()
            if cita:
                return {"FECHA": cita.FECHA}
    except Exception as e:
        print(f"Error al obtener info de la cita: {e}")
    return None


def obtener_email_empleado_por_nombre(nombre_empleado: str) -> str | None:
    """Obtiene el email del empleado por su nombre desde la BD.
    
    Args:
        nombre_empleado: Nombre del empleado a buscar
        
    Returns:
        Email del empleado si existe, None si no se encuentra
    """
    try:
        from src.BBDD.databasecontroller import Empleado
        
        with get_session() as session:
            # Busca el empleado por nombre (case-insensitive), excluyendo eliminados
            empleado = session.query(Empleado).filter(
                Empleado.NOMBRE.ilike(f"%{nombre_empleado}%"),
                Empleado.ELIMINADO == None
            ).first()
            
            if empleado and empleado.EMAIL:
                return empleado.EMAIL
            return None
    except Exception as e:
        print(f"Error al obtener email del empleado: {e}")
    return None
