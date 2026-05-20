import datetime
from telegram.ext import ContextTypes
from src.BBDD.databasecontroller import get_session, CitaCorp
from src.services.translator_service import TranslatorService


async def check_daily_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Tarea diaria: Revisa la BD y envía recordatorios para citas en 3, 2 o 1 día.
    Envía recordatorios a clientes con TELEGRAM_ID registrado.
    """
    print("🔄 Ejecutando revisión diaria de recordatorios...")
    try:
        now = datetime.datetime.now()
        today = now.date()

        with get_session() as session:
            # Obtener citas corporativas activas con clientes que tengan TELEGRAM_ID
            citas_activas = (
                session.query(CitaCorp)
                .join(CitaCorp.cliente)
                .filter(
                    CitaCorp.ELIMINADO.is_(None),
                    CitaCorp.FECHA >= now,
                )
                .all()
            )

            for cita in citas_activas:
                # Verificar que el cliente tenga TELEGRAM_ID
                if not cita.cliente or not cita.cliente.TELEGRAM_ID:
                    continue

                dias_restantes = (cita.FECHA.date() - today).days

                if dias_restantes in [1, 2, 3]:
                    chat_id = cita.cliente.TELEGRAM_ID

                    try:
                        user_data = context.application.user_data.get(chat_id, {})
                        idioma = user_data.get("idioma", "es")

                        fecha_str = cita.FECHA.strftime("%d/%m/%Y")
                        hora_str = cita.FECHA.strftime("%H:%M")

                        if dias_restantes == 1:
                            intro = "¡Mañana es tu cita!"
                        else:
                            intro = f"¡Faltan {dias_restantes} días para tu cita!"

                        mensaje_base = (
                            f"🔔 *Recordatorio de Cita!*\n\n"
                            f"Hola {cita.cliente.NOMBRE}, {intro.lower()} "
                            f"Será el *{fecha_str}* a las *{hora_str}*.\n\n"
                            f"¡Te esperamos!"
                        )

                        mensaje_traducido = TranslatorService.traducir(
                            mensaje_base, idioma
                        )

                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=mensaje_traducido,
                            parse_mode="Markdown",
                        )
                        print(
                            f"✅ Recordatorio enviado a {chat_id} para cita en {dias_restantes} dias."
                        )

                    except Exception as e:
                        print(
                            f"⚠️ No se pudo enviar recordatorio al usuario {chat_id}. Razón: {e}"
                        )

    except Exception as e:
        print(f"❌ Error CRÍTICO en la tarea diaria de recordatorios: {e}")
