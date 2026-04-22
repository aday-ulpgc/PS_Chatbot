import json
import asyncio
from datetime import date, datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar
from telegram.error import BadRequest

from src.services import calendar_service
from src.services.voice_service import VoiceService
from src.bot.telegram.constants import CALENDAR_STEPS, MODO_TEXTO, MODO_AUDIO
from src.bot.telegram.keyboards import main_menu_keyboard
from src.bot.telegram.handlers.commands import handle_action_back_menu
from src.BBDD.database_service import guardar_cita_en_db, obtener_o_crear_usuario_telegram, obtener_horas_ocupadas

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
                nombre=update.effective_user.full_name
            )
            
            guardar_cita_en_db(
                telegram_id=update.effective_user.id,
                fecha=fecha_dt,
                hora=selected_time,
                descripcion="Reserva desde Telegram MVP"
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
                "9:00", "10:00", "11:00", "12:00", 
                "16:00", "17:00", "18:00", "19:00",
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
                    InlineKeyboardButton("↻ Cambiar Fecha", callback_data="action_reserve"),
                    InlineKeyboardButton("⫶☰ Menú", callback_data="action_back_menu"),
                ]
            )
           
            if not buttons[:-1]:
                text_hour = f"❌ Lo siento, ya no quedan huecos libres para el día ({result})."
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
                text_hour = f"Fecha seleccionada: {result}\n⏰ Ahora, selecciona una hora:"
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


async def handle_action_my_appointments(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    questions = (
        " *Mis citas*\n\n"
        "1️⃣ *20/03/2023* Fisio Juan\n"
        "2️⃣ *21/03/2023* Fisio Daniel\n"
        "3️⃣ *3/04/2023* Fisio Juan\n"
        "4️⃣ *4/04/2023* Fisio Daniel\n"
    )

    keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=questions, reply_markup=reply_markup, parse_mode="Markdown"
    )
