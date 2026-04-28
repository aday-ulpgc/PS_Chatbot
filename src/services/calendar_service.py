import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
                    calendarId=self.calendar_id, 
                    eventId=event_id
                ).execute()
                print(f"✅ Evento borrado en Google Calendar: {date_str} a las {hour_str}")
                return True
                
        print("⚠️ No se encontró el evento en Google Calendar para borrarlo.")
        return False


def create_reservation(
    user_id: str, date: str, hour: str, gmail_trabajador: str = None
) -> str:
    """
    Función de fachada (Facade) que orquestra la reserva.
    Mantiene los mensajes de retorno en español para el usuario del bot.
    """
    try:
        calendar = GoogleCalendarService(gmail_trabajador)

        if not calendar.calendar_id:
            return (
                "❌ Error interno: No se ha configurado el CALENDAR_ID en el entorno."
            )

        if not calendar.is_slot_available(date, hour):
            return f"❌ Lo siento, la cita de las {hour}h ya no está disponible."

        start_time = datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(hours=1)

        calendar.create_event(user_id, start_time, end_time)

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
