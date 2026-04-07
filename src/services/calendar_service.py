"""Servicio para interactuar con Google Calendar."""

import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def crear_reserva(usuario_id: str, fecha: str, hora: str) -> str:
    """
    Se autentica en Google Calendar y crea un evento para la fecha indicada.

    Args:
        usuario_id: El ID del usuario de Telegram.
        fecha: Fecha seleccionada en formato 'YYYY-MM-DD'.
        hora: Hora seleccionada en formato 'HH:MM'.

    Returns:
        Mensaje de éxito o error para mostrar al usuario.
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        creds_path = os.path.join(base_dir, "env", "service_account.json")

        calendar_id = os.getenv("CALENDAR_ID")
        if not calendar_id:
            return "❌ Error interno: No se ha configurado el CALENDAR_ID."

        if not os.path.exists(creds_path):
            return "❌ Error interno: Archivo de credenciales no encontrado."

        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)

        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
        hora_obj = datetime.strptime(hora, "%H:%M").time()

        start_time = datetime.combine(fecha_obj, hora_obj)
        end_time = start_time + timedelta(hours=1)

        inicio_dia = fecha_obj.isoformat() + "Z"
        fin_dia = (fecha_obj + timedelta(days=1)).isoformat() + "Z"

        eventos_existentes = service.events().list(
            calendarId=calendar_id,
            timeMin=inicio_dia,
            timeMax=fin_dia,
            singleEvents=True
        ).execute()

        lista_eventos = eventos_existentes.get("items", [])
        for cita_guardada in lista_eventos:
            fecha_inicio_guardada = cita_guardada["start"].get("dateTime", "")
            
            if f"T{hora}:00" in fecha_inicio_guardada:
                return f"❌ Lo siento, la cita de las {hora}h ya no está disponible."

        event = {
            "summary": f"Reserva de {usuario_id}",
            "description": "Reserva generada automáticamente por SaaS-Bot.",
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "Atlantic/Canary",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "Atlantic/Canary",
            },
        }

        event_result = (
            service.events().insert(calendarId=calendar_id, body=event).execute()
        )

        return f"✅ ¡Reserva confirmada para el {fecha} a las {hora}!\n"

    except Exception as e:
        print(f"Error creando reserva en Google Calendar: {e}")
        return "❌ Lo siento, hubo un problema al intentar crear la reserva con Google."
