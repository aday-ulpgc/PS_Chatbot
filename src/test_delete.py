import asyncio
from src.services import calendar_service
from src.services.calendar_service import GoogleCalendarService


async def test():
    # Primero, veamos todos los eventos de hoy en el calendario por defecto
    date_str = "2026-05-04"
    cal = GoogleCalendarService()
    time_min = f"{date_str}T00:00:00Z"
    time_max = f"{date_str}T23:59:59Z"
    events_result = (
        cal.service.events()
        .list(
            calendarId=cal.calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
        )
        .execute()
    )
    events = events_result.get("items", [])
    print(f"Total eventos en calendario por defecto: {len(events)}")
    for e in events:
        start = e["start"].get("dateTime", "")
        summary = e.get("summary", "")
        print(f"  start='{start}' | summary='{summary}'")
        # Simulate the check
        formatted_hour = "10:00"
        telegram_id = "2122121904"
        hora_coincide = f"T{formatted_hour}:00" in start
        id_coincide = telegram_id and f"({telegram_id})" in summary
        print(f"    hora_coincide={hora_coincide} | id_coincide={id_coincide}")

    # Now try the actual delete
    print("\n--- Llamando a delete_reservation ---")
    name_and_id = "Alba Ramos Quintana (2122121904)"
    old_fecha = "2026-05-04"
    old_hora = "10:00"
    result = await asyncio.to_thread(
        calendar_service.delete_reservation,
        name_and_id,
        old_fecha,
        old_hora,
    )
    print(f"Resultado: {result}")


if __name__ == "__main__":
    asyncio.run(test())
