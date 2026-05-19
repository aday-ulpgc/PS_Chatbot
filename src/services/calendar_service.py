import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.BBDD.database_service import guardar_cita_en_db

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TIMEZONE = "Atlantic/Canary"


class GoogleCalendarService:
    """Servicio especializado en la interacción con la API de Google Calendar."""

    def __init__(self, gmail_trabajador: str = None):
        self.calendar_id = gmail_trabajador or os.getenv("CALENDAR_ID")
        self.service = self._authenticate()

    def _authenticate(self):
        """
        Maneja la autenticación buscando las credenciales en la raíz del proyecto.
        Estructura asumida: raíz/env/service_account.json
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))

        project_root = os.path.dirname(os.path.dirname(current_dir))

        creds_path = os.path.join(project_root, "env", "service_account.json")

        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                f"No se encontró el archivo de credenciales en: {creds_path}"
            )

        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
        return build("calendar", "v3", credentials=credentials)

    def is_slot_available(self, date_str: str, hour_str: str) -> bool:
        """Verifica si el hueco horario está libre comparando con eventos existentes."""
        time_min = f"{date_str}T00:00:00Z"
        time_max = f"{date_str}T23:59:59Z"

        events_result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
            )
            .execute()
        )

        events = events_result.get("items", [])

        formatted_hour = hour_str.zfill(5)

        for event in events:
            start_time = event["start"].get("dateTime", "")
            if f"T{formatted_hour}:00" in start_time:
                return False
        return True

    def create_event(self, user_id: str, start_dt: datetime, end_dt: datetime) -> dict:
        """Inserta un nuevo evento en el calendario configurado."""
        event_body = {
            "summary": f"Reserva de {user_id}",
            "description": "Reserva generada automáticamente por SaaS-Bot.",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
        }
        return (
            self.service.events()
            .insert(calendarId=self.calendar_id, body=event_body)
            .execute()
        )

    def delete_event(self, user_id: str, date_str: str, hour_str: str) -> bool:
        """Busca y elimina un evento específico en el calendario."""
        time_min = f"{date_str}T00:00:00Z"
        time_max = f"{date_str}T23:59:59Z"

        events_result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
            )
            .execute()
        )

        events = events_result.get("items", [])
        formatted_hour = hour_str.zfill(5)
        expected_summary = f"Reserva de {user_id}"

        for event in events:
            start_time = event["start"].get("dateTime", "")
            summary = event.get("summary", "")

            if f"T{formatted_hour}:00" in start_time and summary == expected_summary:
                event_id = event["id"]
                self.service.events().delete(
                    calendarId=self.calendar_id, eventId=event_id
                ).execute()
                print(
                    f"✅ Evento borrado en Google Calendar: {date_str} a las {hour_str}"
                )
                return True

        print("⚠️ No se encontró el evento en Google Calendar para borrarlo.")
        return False

    def get_available_hours(self, date_str: str) -> list:
        """Obtiene todas las horas disponibles del día (9:00 a 20:00).

        Considera la duración completa de los eventos, no solo la hora de inicio.
        """
        time_min = f"{date_str}T00:00:00Z"
        time_max = f"{date_str}T23:59:59Z"

        events_result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
            )
            .execute()
        )

        events = events_result.get("items", [])
        occupied_hours = set()

        # Extraer todas las horas ocupadas, considerando la duración del evento
        for event in events:
            start_time = event["start"].get("dateTime", "")
            end_time = event["end"].get("dateTime", "")

            if start_time and end_time:
                try:
                    # Parsear las horas de inicio y fin
                    start_hour = int(start_time.split("T")[1][:2])
                    end_hour = int(end_time.split("T")[1][:2])

                    # Marcar todas las horas ocupadas en el rango
                    # Si un evento es de 16:00-17:00, marca 16 como ocupada
                    for h in range(start_hour, end_hour):
                        occupied_hours.add(f"{h:02d}")
                except (IndexError, ValueError):
                    pass

        # Generar lista de horas disponibles (9:00 a 20:00)
        available_hours = []
        for h in range(9, 21):
            hour_code = f"{h:02d}"
            if hour_code not in occupied_hours:
                available_hours.append(f"{h:02d}:00")

        return available_hours

    def find_alternative_hours(self, date_str: str, hour_str: str) -> tuple:
        """Encuentra las dos horas más cercanas disponibles (anterior y posterior).

        Returns:
            Tuple de (hora_anterior_disponible, hora_posterior_disponible)
        """
        available_hours = self.get_available_hours(date_str)

        if not available_hours:
            return (None, None)

        # Convertir la hora solicitada a entero para comparación
        requested_hour = int(hour_str.split(":")[0])
        available_hours_int = [int(h.split(":")[0]) for h in available_hours]

        # Buscar todas las horas ANTES de la solicitada, retornar la más cercana (la máxima)
        hours_before = [h for h in available_hours_int if h < requested_hour]
        hour_before = None
        if hours_before:
            hour_before = f"{max(hours_before):02d}:00"

        # Buscar todas las horas DESPUÉS de la solicitada, retornar la más cercana (la mínima)
        hours_after = [h for h in available_hours_int if h > requested_hour]
        hour_after = None
        if hours_after:
            hour_after = f"{min(hours_after):02d}:00"

        return (hour_before, hour_after)


def create_reservation(
    user_id: str, date: str, hour: str, gmail_trabajador: str = None, id_empleado_seleccionado: int = None
) -> str:
    """
    Función de fachada (Facade) que orquestra la reserva.
    Crea en Google Calendar Y en la base de datos.
    Mantiene los mensajes de retorno en español para el usuario del bot.

    Si el horario no está disponible, busca automáticamente alternativas.

    Args:
        user_id: Formato "Nombre Completo (telegram_id)"
        date: Formato "YYYY-MM-DD"
        hour: Formato "HH:MM"
        id_empleado_seleccionado: ID del empleado seleccionado por el usuario (opcional)
    """
    try:
        calendar = GoogleCalendarService(gmail_trabajador)

        if not calendar.calendar_id:
            return (
                "❌ Error interno: No se ha configurado el CALENDAR_ID en el entorno."
            )

        if not calendar.is_slot_available(date, hour):
            hour_before, hour_after = calendar.find_alternative_hours(date, hour)

            error_msg = f"❌ Lo siento, la cita de las {hour}h ya no está disponible."

            alternatives = []
            if hour_before:
                alternatives.append(hour_before)
            if hour_after:
                alternatives.append(hour_after)

            if alternatives:
                fecha_obj = datetime.strptime(date, "%Y-%m-%d")
                fecha_formato = fecha_obj.strftime("%d/%m/%Y")

                error_msg += " Otras fechas cercanas que podrían interesarte: "
                alt_times = " ".join([f"{fecha_formato} {alt}" for alt in alternatives])
                error_msg += alt_times

            return error_msg

        start_time = datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(hours=1)

        calendar.create_event(user_id, start_time, end_time)

        try:
            telegram_id_str = user_id.split("(")[-1].rstrip(")")
            telegram_id = int(telegram_id_str)
            nombre = user_id.split("(")[0].strip()
        except (IndexError, ValueError):
            print(f"⚠️ No se pudo extraer telegram_id de {user_id}")
            telegram_id = None
            nombre = None

        if telegram_id:
            from src.BBDD.database_service import obtener_o_crear_cliente_por_telegram
            from src.BBDD.databasecontroller import Empleado, get_session
            
            cliente_result = obtener_o_crear_cliente_por_telegram(telegram_id, nombre)
            cliente_id = cliente_result.get("cliente_id")
            
            if cliente_id:
                id_empleado = id_empleado_seleccionado

                if not id_empleado and gmail_trabajador:
                    try:
                        with get_session() as session:
                            empleado = session.query(Empleado).filter(
                                Empleado.EMAIL == gmail_trabajador,
                                Empleado.ELIMINADO == None,
                            ).first()
                            if empleado:
                                id_empleado = empleado.ID_EMPLEADO
                    except Exception as e:
                        print(f"⚠️ Error al obtener empleado por email: {e}")

                if not id_empleado:
                    try:
                        with get_session() as session:
                            empleado = session.query(Empleado).filter(
                                Empleado.ELIMINADO == None
                            ).first()
                            if empleado:
                                id_empleado = empleado.ID_EMPLEADO
                    except Exception as e:
                        print(f"⚠️ Error getting first empleado: {e}")
                        id_empleado = 1
                
                # Crear datetime con fecha Y hora
                fecha_obj = datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M")
                success_db = guardar_cita_en_db(
                    id_empleado=id_empleado,
                    id_cliente=cliente_id,
                    fecha=fecha_obj,
                    descripcion="Cita reservada desde Telegram",
                )
                if success_db:
                    return f"✅ ¡Reserva confirmada para el {date} a las {hour}!\n"
                else:
                    print("⚠️ Cita creada en Google Calendar pero no se guardó en DB")

        return f"OK Reserva confirmada para el {date} a las {hour}!\n"

    except FileNotFoundError as e:
        print(f"[CONFIG ERROR]: {e}")
        return "ERROR: No se pudo localizar el archivo de llaves de Google."
    except Exception as e:
        print(f"[SYSTEM ERROR]: {e}")
        return "❌ Lo siento, hubo un problema técnico al crear la reserva."


def delete_reservation(user_id: str, date: str, hour: str) -> bool:
    """
    Función de fachada (Facade) para eliminar una reserva.
    Es llamada cuando el usuario cancela o modifica desde Telegram.
    """
    try:
        calendar = GoogleCalendarService()

        if not calendar.calendar_id:
            print("❌ Error: No se ha configurado el CALENDAR_ID.")
            return False

        return calendar.delete_event(user_id, date, hour)

    except Exception as e:
        print(f"[SYSTEM ERROR]: Error al intentar borrar la reserva en Google: {e}")
        return False


def get_weekly_availability(days=7, gmail_trabajador: str = None) -> str:
    """
    Obtiene todos los eventos de los próximos 'X' días y devuelve
    un resumen legible para que la IA lo entienda.
    """
    try:
        calendar = GoogleCalendarService(gmail_trabajador)
        ahora = datetime.now()
        fin_ventana = ahora + timedelta(days=days)

        events_result = (
            calendar.service.events()
            .list(
                calendarId=calendar.calendar_id,
                timeMin=ahora.isoformat() + "Z",
                timeMax=fin_ventana.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        agenda_resumen = {}
        for event in events:
            start = event["start"].get("dateTime")
            if start:
                dt = datetime.fromisoformat(start)
                fecha = dt.strftime("%Y-%m-%d")
                hora = dt.strftime("%H:%M")

                if fecha not in agenda_resumen:
                    agenda_resumen[fecha] = []
                agenda_resumen[fecha].append(hora)

        texto_disponibilidad = ""
        for i in range(days):
            dia_target = (ahora + timedelta(days=i)).strftime("%Y-%m-%d")
            ocupados = agenda_resumen.get(dia_target, [])
            if ocupados:
                texto_disponibilidad += (
                    f"- {dia_target}: Ocupado a las {', '.join(ocupados)}\n"
                )
            else:
                texto_disponibilidad += f"- {dia_target}: Todo libre\n"

        return texto_disponibilidad

    except Exception as e:
        print(f"Error en vista semanal: {e}")
        return "No disponible."


async def create_reservation_via_api(
    telegram_id: int,
    date: str,
    hour: str,
    usuario_id: int = None,
    contacto_id: int = None,
    bloqueante: int = None,
    nombre: str = None,
    id_empleado: int = None,
    gmail_trabajador: str = None,
) -> str:
    """
    Función async para crear reservas desde los handlers del bot.
    Delegada a create_reservation() con parámetros de Telegram.
    
    Args:
        telegram_id: ID del usuario en Telegram
        date: Fecha en formato "YYYY-MM-DD"
        hour: Hora en formato "HH:MM"
        usuario_id: ID del usuario (deprecated, para compatibilidad)
        contacto_id: ID del contacto (deprecated, para compatibilidad)
        bloqueante: Empleado ID (deprecated, para compatibilidad)
        nombre: Nombre del usuario (si no se proporciona, se usa "Usuario")
        id_empleado: ID del empleado seleccionado por el usuario
    
    Returns:
        Mensaje de confirmación o error para el usuario
    """
    try:
        # Construir el user_id en formato esperado
        if nombre:
            user_id_str = f"{nombre} ({telegram_id})"
        else:
            user_id_str = f"Usuario ({telegram_id})"
        
        # Llamar a la función sincrónica create_reservation
        response = create_reservation(
            user_id=user_id_str,
            date=date,
            hour=hour,
            gmail_trabajador=gmail_trabajador,
            id_empleado_seleccionado=id_empleado,
        )
        
        return response
    
    except Exception as e:
        print(f"❌ Error en create_reservation_via_api: {e}")
        return f"❌ Error al crear la reserva: {str(e)}"
