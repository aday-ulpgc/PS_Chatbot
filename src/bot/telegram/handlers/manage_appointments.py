import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from src.services import calendar_service
from src.services.translator_service import TranslatorService
from src.BBDD.database_service import (
    obtener_cliente_por_telegram_id,
    obtener_citas_cliente,
    cancelar_cita_db,
    obtener_info_cita_db,
)


async def handle_action_my_appointments(
    query, context: ContextTypes.DEFAULT_TYPE, update=None
) -> None:
    """Muestra las citas con un formato elegante y botones de cancelación."""
    idioma = context.user_data.get("idioma", "es")

    if query is not None:
        telegram_id = query.from_user.id
    else:
        telegram_id = update.effective_user.id

    # Obtener cliente_id basado en telegram_id
    cliente_id = await asyncio.to_thread(obtener_cliente_por_telegram_id, telegram_id)

    if not cliente_id:
        texto_citas = "📋 *Mis Citas*\n\nAún no tienes perfil de cliente registrado."
        citas = []
    else:
        citas = await asyncio.to_thread(obtener_citas_cliente, cliente_id)

    keyboard = []

    if not citas:
        texto_base = "📋 *Mis Citas*"
        texto_citas = (
            TranslatorService.traducir(texto_base, idioma)
            + "\n\n"
            + TranslatorService.traducir(
                "Actualmente no tienes ninguna reserva activa.",
                idioma,
            )
        )
    else:
        texto_base = "📋 *Tus Próximas Citas:*"
        texto_citas = TranslatorService.traducir(texto_base, idioma) + "\n\n"

        palabra_cita = TranslatorService.traducir("reserva", idioma).capitalize()
        palabra_alas = TranslatorService.traducir("a las", idioma)

        for i, cita in enumerate(citas, 1):
            fecha_dt = cita["FECHA"]
            if idioma == "es":
                meses_es = {
                    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
                    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
                }
                nombre_mes = meses_es.get(fecha_dt.month, "enero")
                fecha_formateada = f"{fecha_dt.strftime('%d')} de {nombre_mes} de {fecha_dt.strftime('%Y')}"
            else:
                meses_en = {
                    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
                }
                nombre_mes = meses_en.get(fecha_dt.month, "January")
                fecha_formateada = f"{nombre_mes} {fecha_dt.strftime('%d')}, {fecha_dt.strftime('%Y')}"

            hora_str = fecha_dt.strftime("%H:%M")
            nombre_empleado = cita.get("NOMBRE_EMPLEADO", "No especificado")
            palabra_con = TranslatorService.traducir("con", idioma)

            texto_citas += f"🔹 *{palabra_cita} {i}* — {fecha_formateada} {palabra_alas} {hora_str}\n"
            texto_citas += f"   👤 {palabra_con.capitalize()}: {nombre_empleado}\n\n"

        keyboard.append(
            [
                InlineKeyboardButton(
                    TranslatorService.traducir("📝 Modificar", idioma),
                    callback_data="action_modify_menu",
                ),
                InlineKeyboardButton(
                    TranslatorService.traducir("❌ Cancelar", idioma),
                    callback_data="action_cancel_menu",
                ),
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                TranslatorService.traducir("🔙 Volver al Menú", idioma),
                callback_data="action_back_menu",
            )
        ]
    )

    if query is not None:
        try:
            await query.edit_message_text(
                text=texto_citas,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        except BadRequest as e:
            print(f"⚠️ Aviso (esperado si el texto no cambia): {e}")
    else:
        await update.message.reply_text(
            text=texto_citas,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )


async def handle_action_cancel_menu(
    query, context: ContextTypes.DEFAULT_TYPE, update=None
) -> None:
    """Muestra los botones específicos para elegir qué cita borrar.
    Acepta llamadas desde NLP (query=None, update provisto) y desde callbacks.
    """
    idioma = context.user_data.get("idioma", "es")

    if query is not None:
        telegram_id = query.from_user.id
    else:
        telegram_id = update.effective_user.id

    # Obtener cliente_id y luego sus citas
    cliente_id = await asyncio.to_thread(obtener_cliente_por_telegram_id, telegram_id)
    if not cliente_id:
        await handle_action_my_appointments(query, context, update)
        return

    citas = await asyncio.to_thread(obtener_citas_cliente, cliente_id)

    if not citas:
        await handle_action_my_appointments(query, context, update)
        return

    texto_base = "❌ *Cancelar Cita*\nSelecciona la cita que deseas anular:"
    texto = TranslatorService.traducir(texto_base, idioma) + "\n\n"
    keyboard = []

    palabra_cita = TranslatorService.traducir("reserva", idioma).capitalize()

    for i, cita in enumerate(citas, 1):
        dia = cita["FECHA"].day
        mes = cita["FECHA"].month
        hora_str = cita["FECHA"].strftime("%H:%M")
        btn_text = f"{palabra_cita} {i} ({dia:02d}/{mes:02d} - {hora_str})"

        keyboard.append(
            [
                InlineKeyboardButton(
                    btn_text, callback_data=f"cancelcita_{cita['ID_CITA']}"
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                TranslatorService.traducir("🔙 Volver a Mis Citas", idioma),
                callback_data="action_my_appointments",
            )
        ]
    )

    markup = InlineKeyboardMarkup(keyboard)

    if query is not None:
        try:
            await query.edit_message_text(
                text=texto,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        except BadRequest as e:
            print(f"No se pudo editar el mensaje en handle_action_cancel_menu: {e}")
    else:
        await update.message.reply_text(
            text=texto,
            reply_markup=markup,
            parse_mode="Markdown",
        )


async def handle_cancel_appointment(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa el clic en un botón de 'Cancelar Cita'."""
    idioma = context.user_data.get("idioma", "es")
    id_cita = int(query.data.split("_")[1])

    msg_espera = TranslatorService.traducir(
        "⏳ Cancelando tu reserva en Google Calendar...", idioma
    )
    await query.edit_message_text(text=msg_espera)

    cita = await asyncio.to_thread(obtener_info_cita_db, id_cita)
    if cita:
        old_fecha = cita["FECHA"].strftime("%Y-%m-%d")
        old_hora = cita["FECHA"].strftime("%H:%M")
        name_and_id = f"{query.from_user.full_name} ({query.from_user.id})"
        email_empleado = cita.get("EMAIL_EMPLEADO")

        await asyncio.to_thread(
            calendar_service.delete_reservation, name_and_id, old_fecha, old_hora, email_empleado
        )

    exito = await asyncio.to_thread(cancelar_cita_db, id_cita)

    from src.BBDD.database_service import (
        obtener_usuarios_esperando,
        marcar_espera_notificada,
    )

    if cita:
        usuarios_espera = await asyncio.to_thread(
            obtener_usuarios_esperando, cita["FECHA"]
        )

        for usuario in usuarios_espera:
            try:
                fecha_str = cita["FECHA"].strftime("%d/%m/%Y")
                hora_str = cita["FECHA"].strftime("%H:%M")

                user_data_target = context.application.user_data.get(
                    usuario.TELEGRAM_ID, {}
                )
                idioma_target = user_data_target.get("idioma", "es")

                msg_notificacion = TranslatorService.traducir(
                    f"📢 ¡Tenemos una buena noticia!\n\n"
                    f"Se acaba de liberar el horario en el que estabas interesado:\n"
                    f"📅 Fecha: {fecha_str}\n"
                    f"⏰ Hora: {hora_str}\n\n"
                    f"Si aún deseas esta cita, ya está disponible para que la reserves.",
                    idioma_target,
                )

                # Marcar notificado ANTES de enviar el mensaje, para evitar intentos infinitos si el usuario bloqueó el bot
                await asyncio.to_thread(marcar_espera_notificada, usuario.ID_LISTA)

                from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                fecha_iso = cita["FECHA"].strftime("%Y-%m-%d")
                hora_iso = cita["FECHA"].strftime("%H:%M")
                texto_boton = TranslatorService.traducir(
                    "🗓️ Reservar este hueco ahora", idioma_target
                )
                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                texto_boton,
                                callback_data=f"waitlistbook_{fecha_iso}_{hora_iso}",
                            )
                        ]
                    ]
                )

                await context.bot.send_message(
                    chat_id=usuario.TELEGRAM_ID,
                    text=msg_notificacion,
                    reply_markup=keyboard,
                )

            except Exception as e:
                print(f"❌ Error notificando usuario: {e}")

    if exito:
        msg_exito = TranslatorService.traducir(
            "✅ Cita cancelada correctamente", idioma
        )
        await query.answer(msg_exito, show_alert=True)
    else:
        msg_error = TranslatorService.traducir("❌ Error al cancelar la cita", idioma)
        await query.answer(msg_error, show_alert=True)

    await handle_action_my_appointments(query, context)


async def handle_action_modify_menu(
    query, context: ContextTypes.DEFAULT_TYPE, update=None
) -> None:
    """Muestra las citas para elegir cuál modificar.
    Acepta llamadas desde NLP (query=None, update provisto) y desde callbacks.
    """
    idioma = context.user_data.get("idioma", "es")

    if query is not None:
        telegram_id = query.from_user.id
    else:
        telegram_id = update.effective_user.id

    # Obtener cliente_id y luego sus citas
    cliente_id = await asyncio.to_thread(obtener_cliente_por_telegram_id, telegram_id)
    if not cliente_id:
        if query is not None:
            await query.answer("No tienes citas para modificar", show_alert=True)
        else:
            await update.message.reply_text("No tienes citas para modificar.")
        return

    citas = await asyncio.to_thread(obtener_citas_cliente, cliente_id)

    msg_no_citas = TranslatorService.traducir("No tienes citas para modificar.", idioma)

    if not citas:
        if query is not None:
            await query.answer(msg_no_citas, show_alert=True)
        else:
            await update.message.reply_text(msg_no_citas)
        return

    texto_base = (
        "📝 *Modificar Cita*\n\nSelecciona la cita que quieres cambiar de fecha:"
    )
    texto = TranslatorService.traducir(texto_base, idioma)
    keyboard = []

    palabra_cita = TranslatorService.traducir("reserva", idioma).capitalize()

    for i, cita in enumerate(citas, 1):
        dia = cita["FECHA"].day
        mes = cita["FECHA"].month
        hora_str = cita["FECHA"].strftime("%H:%M")
        btn_text = f"✏️ {palabra_cita} {i} ({dia:02d}/{mes:02d} - {hora_str})"

        keyboard.append(
            [InlineKeyboardButton(btn_text, callback_data=f"modcita_{cita['ID_CITA']}")]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                TranslatorService.traducir("🔙 Volver", idioma),
                callback_data="action_my_appointments",
            )
        ]
    )

    markup = InlineKeyboardMarkup(keyboard)

    if query is not None:
        await query.edit_message_text(
            text=texto, reply_markup=markup, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=texto, reply_markup=markup, parse_mode="Markdown"
        )


async def handle_start_modify_calendar(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Guarda el ID de la cita a modificar y lanza el calendario."""
    id_cita = int(query.data.split("_")[1])

    from src.bot.telegram.handlers.reserve.booking import handle_action_reserve

    await handle_action_reserve(query, context)
    context.user_data["modifying_id"] = id_cita
