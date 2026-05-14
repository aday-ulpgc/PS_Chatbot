import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from src.services import calendar_service
from src.services.translator_service import TranslatorService
from src.BBDD.database_service import (
    obtener_citas_usuario,
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

    citas = await asyncio.to_thread(obtener_citas_usuario, telegram_id)

    keyboard = []

    if not citas:
        texto_base = "📋 *Mis Citas*"
        texto_citas = (
            TranslatorService.traducir(texto_base, idioma)
            + "\n\nActualmente no tienes ninguna reserva activa."
        )
    else:
        texto_base = "📋 *Tus Próximas Citas:*"
        texto_citas = TranslatorService.traducir(texto_base, idioma) + "\n\n"

        palabra_cita = TranslatorService.traducir("reserva", idioma).capitalize()
        palabra_alas = TranslatorService.traducir("a las", idioma)

        for i, cita in enumerate(citas, 1):
            fecha_str = cita["FECHA"].strftime("%d de %B, %Y")
            fecha_traducida = TranslatorService.traducir(fecha_str, idioma)
            hora_str = cita["FECHA"].strftime("%H:%M")

            texto_citas += f"🔹 *{palabra_cita} {i}* — {fecha_traducida} {palabra_alas} {hora_str}\n\n"

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

    citas = await asyncio.to_thread(obtener_citas_usuario, telegram_id)

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

        await asyncio.to_thread(
            calendar_service.delete_reservation, name_and_id, old_fecha, old_hora
        )

    exito = await asyncio.to_thread(cancelar_cita_db, id_cita)

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

    citas = await asyncio.to_thread(obtener_citas_usuario, telegram_id)

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
