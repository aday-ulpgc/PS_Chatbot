import json
import asyncio
from datetime import date, datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar
from telegram.error import BadRequest

from src.services import calendar_service
from src.services.voice_service import VoiceService
from src.bot.telegram.constants import CALENDAR_STEPS, MODO_TEXTO, MODO_AUDIO
from src.bot.telegram.keyboards import main_menu_keyboard
from src.bot.telegram.handlers.commands import handle_action_back_menu
from src.BBDD.database_service import (
    guardar_cita_en_db,
    obtener_o_crear_usuario_telegram,
    obtener_horas_ocupadas,
    obtener_citas_usuario,
    cancelar_cita_db,
    actualizar_cita_fecha_db
)


async def handle_calendar_and_time(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> bool:
    """Maneja la selección de fecha y hora del calendario."""
    if query.data.startswith("time_"):
        selected_time = query.data.split("_")[1]
        selected_data = context.user_data.get("selected_data", "Desconocida")

        if selected_data == "Desconocida":
            await query.edit_message_text(
                "❌ Error: No se ha encontrado la fecha. Inténtalo de nuevo."
            )
            return True
        
        modifying_id = context.user_data.get("modifying_id")
        
        if modifying_id:
            fecha_dt = datetime.strptime(selected_data, "%Y-%m-%d")
            hora_parts = selected_time.split(":")
            fecha_dt_con_hora = fecha_dt.replace(
                hour=int(hora_parts[0]),
                minute=int(hora_parts[1]) if len(hora_parts) > 1 else 0
            )

            await asyncio.to_thread(actualizar_cita_fecha_db, modifying_id, fecha_dt_con_hora)
            context.user_data.pop("modifying_id", None) # Limpiamos memoria
            
            await query.answer("✅ Cita modificada con éxito", show_alert=True)
            await handle_action_my_appointments(query, context)
            
            return True

        await query.edit_message_text(
            text=f"✅ ¡Resumen de tu solicitud!\n📅 Fecha: {selected_data}\n⏰ Hora: {selected_time}\n\n⏳ Procesando reserva en Google Calendar..."
        )

        name_and_id = f"{update.effective_user.full_name} ({update.effective_user.id})"
        response_message = await asyncio.to_thread(
            calendar_service.create_reservation,
            name_and_id,
            selected_data,
            selected_time,
        )

        if response_message.startswith("❌"):
            error_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↻ Elegir otro día", callback_data="action_reserve"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⫶☰ Menú Principal", callback_data="action_back_menu"
                        )
                    ],
                ]
            )
            await query.edit_message_text(
                text=response_message, reply_markup=error_keyboard
            )
        else:
            # Obtener modo del usuario (TEXTO o AUDIO)
            user_mode = context.user_data.get("pref_mode", MODO_TEXTO)

            context.user_data["last_reserva_text"] = response_message

            if user_mode == MODO_AUDIO:
                await query.edit_message_text("🎙️ Generando audio de confirmación...")

                audio_path = await VoiceService.text_to_speech(response_message)

                audio_keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📖 Ver en texto", callback_data="show_text_reserva"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⫶☰ Menú Principal", callback_data="action_back_menu"
                            )
                        ],
                    ]
                )

                with open(audio_path, "rb") as audio_file:
                    await context.bot.send_voice(
                        chat_id=update.effective_chat.id,
                        voice=audio_file,
                        reply_markup=audio_keyboard,
                    )
                await query.delete_message()
            else:
                await query.edit_message_text(
                    text=response_message, reply_markup=main_menu_keyboard()
                )

            # Guarda en la base de datos para los recordatorios diarios
            fecha_dt = datetime.strptime(selected_data, "%Y-%m-%d")

            obtener_o_crear_usuario_telegram(
                telegram_id=update.effective_user.id,
                nombre=update.effective_user.full_name,
            )

            guardar_cita_en_db(
                telegram_id=update.effective_user.id,
                fecha=fecha_dt,
                hora=selected_time,
                descripcion="Reserva desde Telegram MVP",
            )

        return True

    if DetailedTelegramCalendar.func()(query):
        current_calendar = DetailedTelegramCalendar(min_date=date.today())
        result, key, step = current_calendar.process(query.data)

        if not result and key:
            keyboard_dict = json.loads(key)
            keyboard_buttons = [
                [
                    InlineKeyboardButton(
                        text=btn["text"], callback_data=btn["callback_data"]
                    )
                    for btn in row
                ]
                for row in keyboard_dict.get("inline_keyboard", [])
            ]
            keyboard_buttons.append(
                [
                    InlineKeyboardButton("↻ Reiniciar", callback_data="action_reserve"),
                    InlineKeyboardButton("⫶☰ Menú", callback_data="action_back_menu"),
                ]
            )

            try:
                await query.edit_message_text(
                    text=f"Selecciona una fecha {CALENDAR_STEPS[step]}:",
                    reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                )
            except BadRequest:
                pass

        elif result:
            context.user_data["selected_data"] = str(result)

            now = datetime.now()
            is_today = result == date.today()

            available_hours = [
                "9:00",
                "10:00",
                "11:00",
                "12:00",
                "16:00",
                "17:00",
                "18:00",
                "19:00",
            ]

            horas_ocupadas = obtener_horas_ocupadas(str(result))

            buttons = []
            row = []

            for h in available_hours:
                hour_int = int(h.split(":")[0])
                if is_today and hour_int <= now.hour:
                    continue

                if h in horas_ocupadas:
                    continue

                row.append(InlineKeyboardButton(h, callback_data=f"time_{h}"))
                if len(row) == 2:
                    buttons.append(row)
                    row = []

            if row:
                buttons.append(row)

            buttons.append(
                [
                    InlineKeyboardButton(
                        "↻ Cambiar Fecha", callback_data="action_reserve"
                    ),
                    InlineKeyboardButton("⫶☰ Menú", callback_data="action_back_menu"),
                ]
            )

            if not buttons[:-1]:
                text_hour = (
                    f"❌ Lo siento, ya no quedan huecos libres para el día ({result})."
                )
                reply_markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "↻ Elegir otro día", callback_data="action_reserve"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⫶☰ Menú Principal", callback_data="action_back_menu"
                            )
                        ],
                    ]
                )
            else:
                text_hour = (
                    f"Fecha seleccionada: {result}\n⏰ Ahora, selecciona una hora:"
                )
                reply_markup = InlineKeyboardMarkup(buttons)

            await query.edit_message_text(text=text_hour, reply_markup=reply_markup)

        else:
            await handle_action_back_menu(query, context)
        return True

    return False


async def handle_action_reserve(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_calendar = DetailedTelegramCalendar(min_date=date.today())
    calendar, step = current_calendar.build()

    keyboard_dict = json.loads(calendar)
    navigation_row = [
        {"text": "↻ Reiniciar", "callback_data": "action_reserve"},
        {"text": "⫶☰ Menú", "callback_data": "action_back_menu"},
    ]
    keyboard_dict["inline_keyboard"].append(navigation_row)

    try:
        keyboard_buttons = [
            [
                InlineKeyboardButton(
                    text=btn["text"], callback_data=btn["callback_data"]
                )
                for btn in row
            ]
            for row in keyboard_dict.get("inline_keyboard", [])
        ]
        await query.edit_message_text(
            text=f"Selecciona una fecha {CALENDAR_STEPS[step]}:",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons),
        )
    except BadRequest:
        pass



async def handle_action_my_appointments(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra las citas con un formato elegante y botones de cancelación."""
    telegram_id = query.from_user.id
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


        keyboard.append([
            InlineKeyboardButton("📝 Modificar", callback_data="action_modify_menu"),
            InlineKeyboardButton("❌ Cancelar", callback_data="action_cancel_menu")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Volver al Menú", callback_data="action_back_menu")])

    try:
        await query.edit_message_text(
            text=texto_citas, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )
    except BadRequest:
        pass


async def handle_action_cancel_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra los botones específicos para elegir qué cita borrar."""
    telegram_id = query.from_user.id
    citas = await asyncio.to_thread(obtener_citas_usuario, telegram_id)

    if not citas:
        await handle_action_my_appointments(query, context)
        return

    texto = "❌ *Cancelar Cita*\n\nSelecciona la cita que deseas anular:"
    keyboard = []

    for i, cita in enumerate(citas, 1):
        dia = cita["FECHA"].day
        mes = cita["FECHA"].month
        hora_str = cita["FECHA"].strftime("%H:%M")
        btn_text = f"Cita {i} ({dia:02d}/{mes:02d} - {hora_str})"

        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"cancelcita_{cita['ID_CITA']}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Volver a Mis Citas", callback_data="action_my_appointments")])

    try:
        await query.edit_message_text(
            text=texto, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )
    except BadRequest:
        pass


async def handle_cancel_appointment(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa el clic en un botón de 'Cancelar Cita'."""
    id_cita = int(query.data.split("_")[1])
    
    exito = await asyncio.to_thread(cancelar_cita_db, id_cita)

    if exito:
        await query.answer("✅ Cita cancelada correctamente", show_alert=True)
    else:
        await query.answer("❌ Error al cancelar la cita", show_alert=True)

    await handle_action_my_appointments(query, context)


async def handle_action_modify_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra las citas para elegir cuál modificar."""
    telegram_id = query.from_user.id
    citas = await asyncio.to_thread(obtener_citas_usuario, telegram_id)

    if not citas:
        await query.answer("No tienes citas para modificar", show_alert=True)
        return

    texto = "📝 *Modificar Cita*\n\nSelecciona la cita que quieres cambiar de fecha:"
    keyboard = []

    for i, cita in enumerate(citas, 1):
        dia = cita["FECHA"].day
        mes = cita["FECHA"].month
        hora_str = cita["FECHA"].strftime("%H:%M")
        btn_text = f"✏️ Cita {i} ({dia:02d}/{mes:02d} - {hora_str})"

        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"modcita_{cita['ID_CITA']}")])

    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="action_my_appointments")])

    await query.edit_message_text(text=texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_start_modify_calendar(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Guarda el ID de la cita a modificar y lanza el calendario."""
    id_cita = int(query.data.split("_")[1])
    context.user_data["modifying_id"] = id_cita 
    
    await handle_action_reserve(query, context)