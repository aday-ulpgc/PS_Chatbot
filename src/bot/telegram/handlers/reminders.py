import datetime
from telegram.ext import ContextTypes
from src.BBDD.databasecontroller import get_session, CitaInd, Usuario

async def check_daily_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Tarea diaria: Revisa la BD y envía recordatorios para citas en 3, 2 o 1 día.
    """
    print("🔄 Ejecutando revisión diaria de recordatorios...")
    try:
        now = datetime.datetime.now()
        today = now.date()

        with get_session() as session:
            citas_activas = session.query(CitaInd).join(Usuario).filter(
                CitaInd.ELIMINADO == None,
                CitaInd.FECHA >= now
            ).all()

            for cita in citas_activas:
                dias_restantes = (cita.FECHA.date() - today).days
                
                if dias_restantes in [1, 2, 3]:
                    
                    email = cita.usuario.EMAIL
                    if email.startswith("telegram_"):
                        chat_id = email.split('_')[1].split('@')[0]
                        
                        fecha_str = cita.FECHA.strftime("%d/%m/%Y")
                        hora_str = cita.FECHA.strftime("%H:%M")
                        
                        mensaje = (
                            f"🔔 *¡Recordatorio de Cita!*\n\n"
                            f"Hola {cita.usuario.NOMBRE}, te recordamos que tienes una cita "
                            f"el *{fecha_str}* a las *{hora_str}*.\n\n"
                            f"¡Te esperamos!"
                        )
                        
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=mensaje,
                            parse_mode="Markdown"
                        )
                        print(f"✅ Recordatorio enviado a {chat_id} para cita en {dias_restantes} días.")

    except Exception as e:
        print(f"❌ Error en la tarea diaria de recordatorios: {e}")