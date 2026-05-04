from src.services.calendar_service import GoogleCalendarService
from src.bot.telegram.constants import TRABAJADORES


def main():
    date_str = "2026-05-04"
    time_min = f"{date_str}T00:00:00Z"
    time_max = f"{date_str}T23:59:59Z"

    calendars = [None] + list(TRABAJADORES.values())

    for cal in calendars:
        print(f"\n--- Revisando calendario: {cal or 'DEFAULT'} ---")
        service = GoogleCalendarService(gmail_trabajador=cal)
        if not service.calendar_id:
            print("No calendar ID")
            continue

        events_result = (
            service.service.events()
            .list(
                calendarId=service.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
            )
            .execute()
        )
        events = events_result.get("items", [])
        for e in events:
            start = e["start"].get("dateTime")
            summary = e.get("summary")
            print(f"Evento encontrado: {start} | {summary}")


if __name__ == "__main__":
    main()
