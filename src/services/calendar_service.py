import os
import sys
from datetime import datetime, timedelta

# Forzar salida UTF-8 en Windows para evitar UnicodeEncodeError con emojis
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
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

        # Extraer el ID de telegram del user_id (ej: "Nombre (12345)")
        telegram_id = ""
        if "(" in user_id and ")" in user_id:
            telegram_id = user_id.split("(")[-1].rstrip(")")

        print(
            f"[DELETE] Buscando en cal={self.calendar_id} | fecha={date_str} | hora={formatted_hour} | telegram_id={telegram_id}"
        )

        events_del_usuario = []
        for event in events:
            start_time = event["start"].get("dateTime", "")
            summary = event.get("summary", "")
            id_coincide = telegram_id and f"({telegram_id})" in summary
            summary_coincide = summary == f"Reserva de {user_id}"

            print(
                f"  -> start='{start_time}' | summary='{summary}' | id_coincide={id_coincide}"
            )

            hora_coincide = f"T{formatted_hour}:00" in start_time

            if hora_coincide and (id_coincide or summary_coincide):
                event_id = event["id"]
                self.service.events().delete(
                    calendarId=self.calendar_id, eventId=event_id
                ).execute()
                print(
                    f"[INFO] Evento borrado en Google Calendar: {date_str} a las {hour_str}"
                )
                return True

            if id_coincide or summary_coincide:
                events_del_usuario.append(event)

        # Fallback: si hay exactamente un evento de este usuario ese día y no
        # coincidió la hora (posible desfase UTC vs hora local en la BD),
        # lo borramos igualmente para evitar duplicados.
        if len(events_del_usuario) == 1:
            event = events_del_usuario[0]
            event_id = event["id"]
            start_time = event["start"].get("dateTime", "")
            self.service.events().delete(
                calendarId=self.calendar_id, eventId=event_id
            ).execute()
            print(
                f"[INFO] Evento borrado por fallback (unico evento del usuario ese dia): {start_time}"
            )
            return True
        elif len(events_del_usuario) > 1:
            print(
                f"[WARN] Hay {len(events_del_usuario)} eventos del usuario ese dia, no se puede borrar por fallback sin hora exacta."
            )

        print(
            f"[WARN] No se encontro el evento en Google Calendar para borrarlo. Eventos en ese dia: {len(events)}"
        )
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
    user_id: str,
    date: str,
    hour: str,
    gmail_trabajador: str = None,
    skip_db: bool = False,
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
    """
    try:
        calendar = GoogleCalendarService(gmail_trabajador)

        if not calendar.calendar_id:
            return (
                "❌ Error interno: No se ha configurado el CALENDAR_ID en el entorno."
            )

        if not calendar.is_slot_available(date, hour):
            # Buscar horas alternativas
            hour_before, hour_after = calendar.find_alternative_hours(date, hour)

            error_msg = f"❌ Lo siento, la cita de las {hour}h ya no está disponible."

            # Si hay alternativas, incluirlas en el mensaje
            alternatives = []
            if hour_before:
                alternatives.append(hour_before)
            if hour_after:
                alternatives.append(hour_after)

            if alternatives:
                # Convertir fecha a DD/MM/YYYY para el mensaje
                fecha_obj = datetime.strptime(date, "%Y-%m-%d")
                fecha_formato = fecha_obj.strftime("%d/%m/%Y")

                error_msg += " Otras fechas cercanas que podrían interesarte: "
                alt_times = " ".join([f"{fecha_formato} {alt}" for alt in alternatives])
                error_msg += alt_times

            return error_msg

        start_time = datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(hours=1)

        # Crear en Google Calendar
        calendar.create_event(user_id, start_time, end_time)

        # Extraer telegram_id y nombre del formato "Nombre Completo (telegram_id)"
        try:
            telegram_id_str = user_id.split("(")[-1].rstrip(")")
            telegram_id = int(telegram_id_str)
            nombre = user_id.split("(")[0].strip()
        except (IndexError, ValueError):
            print(f"[WARN] No se pudo extraer telegram_id de {user_id}")
            telegram_id = None
            nombre = None

        # Guardar también en la base de datos
        if telegram_id and not skip_db:
            from src.BBDD.database_service import obtener_o_crear_usuario_telegram

            obtener_o_crear_usuario_telegram(telegram_id=telegram_id, nombre=nombre)

            fecha_obj = datetime.strptime(date, "%Y-%m-%d")
            success_db = guardar_cita_en_db(
                telegram_id=telegram_id,
                fecha=fecha_obj,
                hora=hour,
                descripcion="Cita reservada desde Telegram",
            )
            if not success_db:
                print("[WARN] Cita creada en Google Calendar pero no se guardo en DB")

        return f"✅ ¡Reserva confirmada para el {date} a las {hour}!\n"

    except FileNotFoundError as e:
        print(f"[CONFIG ERROR]: {e}")
        return "❌ Error: No se pudo localizar el archivo de llaves de Google."
    except Exception as e:
        print(f"[SYSTEM ERROR]: {e}")
        return "❌ Lo siento, hubo un problema técnico al crear la reserva."


def delete_reservation(user_id: str, date: str, hour: str) -> bool:
    """
    Función de fachada (Facade) para eliminar una reserva.
    Es llamada cuando el usuario cancela o modifica desde Telegram.
    Intenta eliminar en el calendario por defecto y, si no lo encuentra, en el de los trabajadores.
    """
    try:
        from src.bot.telegram.constants import TRABAJADORES

        # 1. Intentar en el calendario por defecto
        calendar_default = GoogleCalendarService()
        if calendar_default.calendar_id:
            if calendar_default.delete_event(user_id, date, hour):
                return True

        # 2. Si no se encontró, buscar en los calendarios de los trabajadores
        for nombre, gmail in TRABAJADORES.items():
            try:
                calendar_trabajador = GoogleCalendarService(gmail_trabajador=gmail)
                if calendar_trabajador.calendar_id:
                    if calendar_trabajador.delete_event(user_id, date, hour):
                        return True
            except Exception as e:
                print(
                    f"[WARN] Error al revisar el calendario de {nombre} ({gmail}): {e}"
                )
                continue

        print("[ERROR] No se encontro la cita en ningun calendario para borrarla.")
        return False

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
