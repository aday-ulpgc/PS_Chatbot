"""Servicio para interactuar con Google Calendar."""

import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def crear_reserva(usuario_id: str, fecha: str) -> str:
    """
    Se autentica en Google Calendar y crea un evento para la fecha indicada.
    
    Args:
        usuario_id: El ID del usuario de Telegram.
        fecha: Fecha seleccionada en formato 'YYYY-MM-DD'.
        
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
        service = build('calendar', 'v3', credentials=creds)

        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
        
        start_time = fecha_obj.replace(hour=10, minute=0, second=0)
        end_time = start_time + timedelta(hours=1) 

        event = {
            'summary': f'Reserva de usuario {usuario_id}',
            'description': f'Reserva generada automáticamente por SaaS-Bot.',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Europe/Madrid', 
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Europe/Madrid',
            },
        }

        event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        evento_url = event_result.get('htmlLink', '')
        
        return f"✅ ¡Reserva confirmada para el {fecha} a las 10:00!\n📅 Puedes verla en el calendario."

    except Exception as e:
        print(f"Error creando reserva en Google Calendar: {e}")
        return "❌ Lo siento, hubo un problema al intentar crear la reserva con Google."
