"""
Script para verificar citas en fechas específicas
Busca en la base de datos y Google Calendar
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from BBDD.databasecontroller import get_session, CitaCorp, Empleado, Cliente
from services.calendar_service import GoogleCalendarService

# Fechas a buscar
FECHAS_A_BUSCAR = [
    "2027-08-22 00:00:00",
    "2028-10-23 00:00:00",
    "2026-10-13 16:00:00",
]


def verificar_citas_en_bd(fechas):
    """Verifica citas en la base de datos para las fechas especificadas."""
    print(f"\n{'='*70}")
    print("📊 BÚSQUEDA EN BASE DE DATOS")
    print(f"{'='*70}\n")

    try:
        with get_session() as session:
            for fecha_str in fechas:
                print(f"🔍 Buscando citas en: {fecha_str}")

                # Parsear fecha
                try:
                    fecha_obj = datetime.fromisoformat(fecha_str)
                except ValueError:
                    print("   ❌ Formato de fecha inválido\n")
                    continue

                # Buscar citas activas en esa fecha
                citas_activas = (
                    session.query(CitaCorp)
                    .filter(CitaCorp.FECHA == fecha_obj, CitaCorp.ELIMINADO.is_(None))
                    .all()
                )

                # Buscar citas eliminadas en esa fecha
                citas_eliminadas = (
                    session.query(CitaCorp)
                    .filter(CitaCorp.FECHA == fecha_obj, CitaCorp.ELIMINADO.isnot(None))
                    .all()
                )

                if citas_activas:
                    print(f"   ✅ {len(citas_activas)} cita(s) ACTIVA(S):")
                    for cita in citas_activas:
                        empleado = (
                            session.query(Empleado)
                            .filter(Empleado.ID_EMPLEADO == cita.ID_EMPLEADO)
                            .first()
                        )
                        cliente = (
                            session.query(Cliente)
                            .filter(Cliente.ID_CLIENTE == cita.ID_CLIENTE)
                            .first()
                        )
                        print(f"      - ID: {cita.ID_CITA}")
                        print(
                            f"        Empleado: {empleado.NOMBRE if empleado else 'Unknown'}"
                        )
                        print(
                            f"        Cliente: {cliente.NOMBRE if cliente else 'Unknown'}"
                        )
                        print(f"        Descripción: {cita.DESCRIPCION}")
                else:
                    print("   ⚠️  NO hay citas activas en esa fecha")

                if citas_eliminadas:
                    print(f"   🗑️  {len(citas_eliminadas)} cita(s) ELIMINADA(S):")
                    for cita in citas_eliminadas:
                        empleado = (
                            session.query(Empleado)
                            .filter(Empleado.ID_EMPLEADO == cita.ID_EMPLEADO)
                            .first()
                        )
                        cliente = (
                            session.query(Cliente)
                            .filter(Cliente.ID_CLIENTE == cita.ID_CLIENTE)
                            .first()
                        )
                        print(f"      - ID: {cita.ID_CITA}")
                        print(
                            f"        Empleado: {empleado.NOMBRE if empleado else 'Unknown'}"
                        )
                        print(
                            f"        Cliente: {cliente.NOMBRE if cliente else 'Unknown'}"
                        )
                        print(f"        Eliminado: {cita.ELIMINADO}")

                if not citas_activas and not citas_eliminadas:
                    print("   ❌ NO hay citas en esa fecha (ni activas ni eliminadas)")

                print()

    except Exception as e:
        print(f"❌ Error al consultar BD: {e}\n")


def verificar_citas_en_google(fechas):
    """Verifica citas en Google Calendar para las fechas especificadas."""
    print(f"{'='*70}")
    print("📅 BÚSQUEDA EN GOOGLE CALENDAR")
    print(f"{'='*70}\n")

    try:
        service = GoogleCalendarService()

        for fecha_str in fechas:
            print(f"🔍 Buscando eventos en: {fecha_str}")

            # Parsear fecha
            try:
                fecha_obj = datetime.fromisoformat(fecha_str)
            except ValueError:
                print("   ❌ Formato de fecha inválido\n")
                continue

            # Rango del día
            dia_inicio = fecha_obj.replace(hour=0, minute=0, second=0)
            dia_fin = fecha_obj.replace(hour=23, minute=59, second=59)

            events_result = (
                service.service.events()
                .list(
                    calendarId=service.calendar_id,
                    timeMin=dia_inicio.isoformat(),
                    timeMax=dia_fin.isoformat(),
                    singleEvents=True,
                )
                .execute()
            )

            events = events_result.get("items", [])

            if events:
                print(f"   ✅ {len(events)} evento(s) encontrado(s):")
                for event in events:
                    print(f"      - {event.get('summary', 'Sin nombre')}")
                    print(
                        f"        Hora: {event['start'].get('dateTime', event['start'].get('date'))}"
                    )
            else:
                print("   ❌ NO hay eventos en Google Calendar ese día")

            print()

    except Exception as e:
        print(f"❌ Error al consultar Google Calendar: {e}\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔎 VERIFICADOR DE CITAS")
    print("=" * 70)

    verificar_citas_en_bd(FECHAS_A_BUSCAR)
    verificar_citas_en_google(FECHAS_A_BUSCAR)

    print("=" * 70)
    print("✅ Verificación completada")
    print("=" * 70 + "\n")
