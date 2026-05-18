"""
Script para verificar que las citas específicas de la BD estén en Google Calendar
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from BBDD.databasecontroller import get_session, CitaCorp, Empleado, Cliente
from services.calendar_service import GoogleCalendarService, TIMEZONE
import pytz

def verificar_citas_especificas():
    """Verifica que las citas activas de la BD estén en Google Calendar."""
    
    print(f"\n{'='*80}")
    print("🔍 VERIFICACIÓN DE CITAS: BD vs GOOGLE CALENDAR")
    print(f"{'='*80}\n")
    
    # Obtener citas activas de la BD
    print("📊 CITAS ACTIVAS EN BASE DE DATOS:\n")
    
    citas_data = []
    
    try:
        with get_session() as session:
            citas_activas = session.query(CitaCorp).filter(
                CitaCorp.ELIMINADO == None
            ).order_by(CitaCorp.FECHA).all()
            
            if not citas_activas:
                print("❌ No hay citas activas en la BD\n")
                return
            
            print(f"✅ Se encontraron {len(citas_activas)} citas activas:\n")
            
            for cita in citas_activas:
                empleado = session.query(Empleado).filter(
                    Empleado.ID_EMPLEADO == cita.ID_EMPLEADO
                ).first()
                cliente = session.query(Cliente).filter(
                    Cliente.ID_CLIENTE == cita.ID_CLIENTE
                ).first()
                
                # Guardar datos antes de cerrar sesión
                citas_data.append({
                    'id': cita.ID_CITA,
                    'fecha': cita.FECHA,
                    'empleado': empleado.NOMBRE if empleado else 'Unknown',
                    'cliente': cliente.NOMBRE if cliente else 'Unknown'
                })
                
                print(f"🔹 Cita ID: {cita.ID_CITA}")
                print(f"   Fecha: {cita.FECHA}")
                print(f"   Empleado: {empleado.NOMBRE if empleado else 'Unknown'}")
                print(f"   Cliente: {cliente.NOMBRE if cliente else 'Unknown'}")
                print()
    
    except Exception as e:
        print(f"❌ Error al consultar BD: {e}\n")
        return
    
    # Verificar en Google Calendar
    print(f"\n{'='*80}")
    print("📅 BÚSQUEDA EN GOOGLE CALENDAR:\n")
    
    try:
        service = GoogleCalendarService()
        tz = pytz.timezone(TIMEZONE)
        
        for cita in citas_data:
            fecha_obj = cita['fecha']
            
            # Asegurar que la fecha tenga timezone
            if fecha_obj.tzinfo is None:
                fecha_obj = tz.localize(fecha_obj)
            
            dia_inicio = fecha_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            dia_fin = (dia_inicio + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            events_result = service.service.events().list(
                calendarId=service.calendar_id,
                timeMin=dia_inicio.isoformat(),
                timeMax=dia_fin.isoformat(),
                singleEvents=True
            ).execute()
            
            events = events_result.get('items', [])
            
            if events:
                print(f"✅ Cita ID {cita['id']} ({fecha_obj.strftime('%d/%m/%Y %H:%M')}) ENCONTRADA en Google Calendar:")
                for event in events:
                    print(f"   - {event.get('summary', 'Sin nombre')}")
            else:
                print(f"❌ Cita ID {cita['id']} ({fecha_obj.strftime('%d/%m/%Y %H:%M')}) NO encontrada en Google Calendar")
            
            print()
    
    except Exception as e:
        print(f"❌ Error al consultar Google Calendar: {e}\n")
    
    print(f"{'='*80}")
    print("✅ Verificación completada")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    verificar_citas_especificas()
