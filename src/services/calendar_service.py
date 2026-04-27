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
