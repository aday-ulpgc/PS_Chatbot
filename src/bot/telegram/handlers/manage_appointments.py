import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from src.services import calendar_service
from src.BBDD.database_service import (
    obtener_citas_usuario,
    cancelar_cita_db,
    obtener_info_cita_db,
)


async def handle_action_my_appointments(
    query, context: ContextTypes.DEFAULT_TYPE, update=None
) -> None:
    """Muestra las citas con un formato elegante y botones de cancelación."""
    if query is not None:
        telegram_id = query.from_user.id
    else:
        telegram_id = update.effective_user.id

    citas = await asyncio.to_thread(obtener_citas_usuario, telegram_id)

    keyboard = []

    if not citas:
        texto_citas = "📋 *Mis Citas*\n\nActualmente no tienes ninguna reserva activa."
    else:
        texto_citas = "📋 *Tus Próximas Citas:*\n\n"
        for i, cita in enumerate(citas, 1):
            fecha_str = cita["FECHA"].strftime("%d de %B, %Y")
            hora_str = cita["FECHA"].strftime("%H:%M")

            texto_citas += f"🔹 *Cita {i}* — {fecha_str} a las {hora_str}\n\n"

        keyboard.append(
            [
                InlineKeyboardButton(
                    "📝 Modificar", callback_data="action_modify_menu"
                ),
                InlineKeyboardButton("❌ Cancelar", callback_data="action_cancel_menu"),
            ]
        )

    keyboard.append(
        [InlineKeyboardButton("🔙 Volver al Menú", callback_data="action_back_menu")]
    )

    if query is not None:
        try:
            await query.edit_message_text(
                text=texto_citas,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        except BadRequest:
            pass
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
    if query is not None:
        telegram_id = query.from_user.id
    else:
        telegram_id = update.effective_user.id

    citas = await asyncio.to_thread(obtener_citas_usuario, telegram_id)

    if not citas:
        await handle_action_my_appointments(query, context, update)
        return

    texto = "❌ *Cancelar Cita*\n\nSelecciona la cita que deseas anular:"
    keyboard = []

    for i, cita in enumerate(citas, 1):
        dia = cita["FECHA"].day
        mes = cita["FECHA"].month
        hora_str = cita["FECHA"].strftime("%H:%M")
        btn_text = f"Cita {i} ({dia:02d}/{mes:02d} - {hora_str})"

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
                "🔙 Volver a Mis Citas", callback_data="action_my_appointments"
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
    id_cita = int(query.data.split("_")[1])

    await query.edit_message_text(text="⏳ Cancelando tu reserva en Google Calendar...")

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
        await query.answer("✅ Cita cancelada correctamente", show_alert=True)
    else:
        await query.answer("❌ Error al cancelar la cita", show_alert=True)

    await handle_action_my_appointments(query, context)


async def handle_action_modify_menu(
    query, context: ContextTypes.DEFAULT_TYPE, update=None
) -> None:
    """Muestra las citas para elegir cuál modificar.
    Acepta llamadas desde NLP (query=None, update provisto) y desde callbacks.
    """
    if query is not None:
        telegram_id = query.from_user.id
    else:
        telegram_id = update.effective_user.id

    citas = await asyncio.to_thread(obtener_citas_usuario, telegram_id)

    if not citas:
        if query is not None:
            await query.answer("No tienes citas para modificar", show_alert=True)
        else:
            await update.message.reply_text("No tienes citas para modificar.")
        return

    texto = "📝 *Modificar Cita*\n\nSelecciona la cita que quieres cambiar de fecha:"
    keyboard = []

    for i, cita in enumerate(citas, 1):
        dia = cita["FECHA"].day
        mes = cita["FECHA"].month
        hora_str = cita["FECHA"].strftime("%H:%M")
        btn_text = f"✏️ Cita {i} ({dia:02d}/{mes:02d} - {hora_str})"

        keyboard.append(
            [InlineKeyboardButton(btn_text, callback_data=f"modcita_{cita['ID_CITA']}")]
        )

    keyboard.append(
        [InlineKeyboardButton("🔙 Volver", callback_data="action_my_appointments")]
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

    from src.bot.telegram.handlers.reserve import handle_action_reserve

    # handle_action_reserve llama a limpiar_estado_reserva internamente,
    # por eso se establece modifying_id DESPUÉS para que no sea eliminado.
    await handle_action_reserve(query, context)
    context.user_data["modifying_id"] = id_cita
