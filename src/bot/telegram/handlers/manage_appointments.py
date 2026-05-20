import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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

MESES_ES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
MESES_EN = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}

async def _send_or_edit(query, update, text, keyboard):
    """Función auxiliar para enviar o editar mensajes de forma segura."""
    if query:
        try:
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except BadRequest:
            pass
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_action_my_appointments(query, context: ContextTypes.DEFAULT_TYPE, update=None) -> None:
    """Muestra las citas agrupadas en bloques de 5 con formato elegante."""
    idioma = context.user_data.get("idioma", "es")
    telegram_id = query.from_user.id if query else update.effective_user.id

    cliente_id = await asyncio.to_thread(obtener_cliente_por_telegram_id, telegram_id)
    if not cliente_id:
        msg = TranslatorService.traducir("📋 *Mis Citas*\n\nAún no tienes perfil de cliente registrado.", idioma)
        return await _send_or_edit(query, update, msg, [[InlineKeyboardButton(TranslatorService.traducir("🔙 Volver al Menú", idioma), callback_data="action_back_menu")]])

    citas = await asyncio.to_thread(obtener_citas_cliente, cliente_id)

    if not citas:
        msg = TranslatorService.traducir("📋 *Mis Citas*\n\nActualmente no tienes ninguna reserva activa.", idioma)
        return await _send_or_edit(query, update, msg, [[InlineKeyboardButton(TranslatorService.traducir("🔙 Volver al Menú", idioma), callback_data="action_back_menu")]])

    bloques = [citas[i : i + 5] for i in range(0, len(citas), 5)]
    context.user_data["citas_bloques"] = bloques
    context.user_data["citas_bloque_actual"] = 0

    await _render_bloque_citas(query, context, update, 0)

async def _render_bloque_citas(query, context, update, index_bloque):
    """Genera el mensaje y el teclado para la página actual de citas."""
    idioma = context.user_data.get("idioma", "es")
    bloques = context.user_data.get("citas_bloques", [])
    if not bloques: return

    citas_bloque = bloques[index_bloque]

    lbl_titulo = TranslatorService.traducir("📋 *Mis Próximas Citas:*", idioma)
    lbl_pag = TranslatorService.traducir("Pág.", idioma)
    palabra_cita = TranslatorService.traducir("reserva", idioma).capitalize()
    palabra_alas = TranslatorService.traducir("a las", idioma)
    palabra_con = TranslatorService.traducir("con", idioma).capitalize()

    texto_citas = f"{lbl_titulo} ({lbl_pag} {index_bloque + 1}/{len(bloques)})\n\n"
    start_idx = index_bloque * 5 + 1

    for i, cita in enumerate(citas_bloque, start_idx):
        fecha_dt = cita["FECHA"] if isinstance(cita, dict) else cita.FECHA
        hora_str = fecha_dt.strftime("%H:%M")
        nombre_empleado = cita.get("NOMBRE_EMPLEADO", "No especificado") if isinstance(cita, dict) else getattr(cita, 'NOMBRE_EMPLEADO', "No especificado")

        if idioma == "es":
            fecha_formateada = f"{fecha_dt.strftime('%d')} de {MESES_ES.get(fecha_dt.month, 'enero')} de {fecha_dt.strftime('%Y')}"
        else:
            fecha_formateada = f"{MESES_EN.get(fecha_dt.month, 'January')} {fecha_dt.strftime('%d')}, {fecha_dt.strftime('%Y')}"

        texto_citas += f"🔹 *{palabra_cita} {i}* — {fecha_formateada} {palabra_alas} {hora_str}\n"
        texto_citas += f"   👤 {palabra_con}: {nombre_empleado}\n\n"

    keyboard = []

    keyboard.append([
        InlineKeyboardButton(TranslatorService.traducir("📝 Modificar", idioma), callback_data="action_modify_menu"),
        InlineKeyboardButton(TranslatorService.traducir("❌ Cancelar", idioma), callback_data="action_cancel_menu"),
    ])

    nav_buttons = []
    if len(bloques) > 1:
        if index_bloque > 0:
            nav_buttons.append(InlineKeyboardButton(TranslatorService.traducir("⬅️ Anterior", idioma), callback_data="action_prev_citas_group"))
        if index_bloque < len(bloques) - 1:
            nav_buttons.append(InlineKeyboardButton(TranslatorService.traducir("Siguiente ➡️", idioma), callback_data="action_next_citas_group"))
        if nav_buttons:
            keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton(TranslatorService.traducir("🔙 Volver al Menú", idioma), callback_data="action_back_menu")])

    await _send_or_edit(query, update, texto_citas, keyboard)

async def handle_prev_citas_group(query, context: ContextTypes.DEFAULT_TYPE, update=None) -> None:
    """Retrocede de grupo en la paginación."""
    bloque_actual = context.user_data.get("citas_bloque_actual", 0)
    if bloque_actual > 0:
        context.user_data["citas_bloque_actual"] = bloque_actual - 1
        await _render_bloque_citas(query, context, update, bloque_actual - 1)
    else:
        msg = TranslatorService.traducir("⚠️ Ya estás en la primera página", context.user_data.get("idioma", "es"))
        await query.answer(msg, show_alert=True)

async def handle_next_citas_group(query, context: ContextTypes.DEFAULT_TYPE, update=None) -> None:
    """Avanza de grupo en la paginación."""
    bloques = context.user_data.get("citas_bloques", [])
    bloque_actual = context.user_data.get("citas_bloque_actual", 0)
    if bloque_actual < len(bloques) - 1:
        context.user_data["citas_bloque_actual"] = bloque_actual + 1
        await _render_bloque_citas(query, context, update, bloque_actual + 1)
    else:
        msg = TranslatorService.traducir("⚠️ Ya estás en la última página", context.user_data.get("idioma", "es"))
        await query.answer(msg, show_alert=True)


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
            calendar_service.delete_reservation,
            name_and_id,
            old_fecha,
            old_hora,
            email_empleado,
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
