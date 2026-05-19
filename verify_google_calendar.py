"""
Script para verificar citas en Google Calendar
Muestra todos los eventos creados en el calendario
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Añadir el directorio src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from services.calendar_service import GoogleCalendarService, TIMEZONE
import pytz


def listar_eventos_google_calendar(dias=7):
    """
    Lista los eventos próximos en Google Calendar

    Args:
        dias: Número de días hacia el futuro a buscar (default: 7)
    """
    try:
        # Inicializar servicio
        service = GoogleCalendarService()

        # Rango de fechas
        tz = pytz.timezone(TIMEZONE)
        ahora = datetime.now(tz)
        fin = ahora + timedelta(days=dias)

        print(f"\n{'='*70}")
        print(f"📅 EVENTOS EN GOOGLE CALENDAR (próximos {dias} días)")
        print(f"{'='*70}")
        print(f"Desde: {ahora.strftime('%d de %B de %Y, %H:%M')}")
        print(f"Hasta: {fin.strftime('%d de %B de %Y, %H:%M')}")
        print(f"{'='*70}\n")

        # Obtener eventos
        events_result = (
            service.service.events()
            .list(
                calendarId=service.calendar_id,
                timeMin=ahora.isoformat(),
                timeMax=fin.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        if not events:
            print("✅ No hay eventos en el rango especificado")
            return

        print(f"✅ Se encontraron {len(events)} evento(s):\n")

        for i, event in enumerate(events, 1):
            # Extraer información
            summary = event.get("summary", "Sin nombre")
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            description = event.get("description", "Sin descripción")
            event_id = event.get("id", "N/A")

            # Parsear fechas
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                start_dt = start_dt.astimezone(tz)
                start_str = start_dt.strftime("%d de %B de %Y, %H:%M")
            except Exception:
                start_str = start

            try:
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                end_dt = end_dt.astimezone(tz)
                end_str = end_dt.strftime("%d de %B de %Y, %H:%M")
            except Exception:
                end_str = end

            print(f"🔹 Evento {i}:")
            print(f"   📝 Título: {summary}")
            print(f"   ⏰ Inicio: {start_str}")
            print(f"   ⏰ Fin: {end_str}")
            print(f"   📄 Descripción: {description}")
            print(f"   🔗 ID: {event_id}")
            print()

        print(f"{'='*70}")
        print("✅ Verificación completada")
        print(f"{'='*70}\n")

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("Asegúrate de que existe el archivo: env/service_account.json\n")
    except Exception as e:
        print(f"\n❌ Error al conectar con Google Calendar: {e}")
        print("Verifica que tus credenciales sean válidas\n")


if __name__ == "__main__":
    dias = 7
    if len(sys.argv) > 1:
        try:
            dias = int(sys.argv[1])
        except ValueError:
            print(f"⚠️ Argumento inválido. Usando {dias} días por defecto")

    listar_eventos_google_calendar(dias)
