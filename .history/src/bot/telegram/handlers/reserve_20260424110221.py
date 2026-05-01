import json
import asyncio
from datetime import date, datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar
from telegram.error import BadRequest

from src.services import calendar_service
from src.services.voice_service import VoiceService
from src.services.visualization_service import generar_imagen_disponibilidad
from src.bot.telegram.constants import CALENDAR_STEPS, MODO_TEXTO, MODO_AUDIO
from src.bot.telegram.keyboards import main_menu_keyboard
from src.bot.telegram.handlers.commands import handle_action_back_menu
from src.BBDD.database_service import obtener_o_crear_usuario_telegram


async def enviar_recordatorio_cita(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Esta función es la que el bot ejecuta cuando pasan los 2 segundos."""
    job = context.job
    try:
        await context.bot.send_message(
            chat_id=job.chat_id, text=f"⏰ PRUEBA\n{job.data}"
        )
    except Exception as e:
        print(f"❌ Error al enviar el mensaje: {e}")


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

            context.job_queue.run_once(
                enviar_recordatorio_cita,
                when=2,
                chat_id=update.effective_chat.id,
                data=f"Cita el {selected_data} a las {selected_time}",
                name=f"remind_{update.effective_chat.id}",
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

            # Obtener o crear usuario en BD
            telegram_id = query.from_user.id
            user_info = obtener_o_crear_usuario_telegram(
                telegram_id,
                query.from_user.first_name
            )
            
            # Generar imagen de disponibilidad
            if user_info.get("id_usuario"):
                try:
                    # Convertir date a datetime
                    fecha_datetime = datetime.combine(result, datetime.min.time())
                    imagen_path = await asyncio.to_thread(
                        generar_imagen_disponibilidad,
                        user_info["id_usuario"],
                        fecha_datetime
                    )
                    
                    # Enviar imagen
                    if imagen_path:
                        await query.answer()
                        with open(imagen_path, 'rb') as img:
                            await context.bot.send_photo(
                                chat_id=query.from_user.id,
                                photo=img,
                                caption=f"📊 Disponibilidad para {result.strftime('%A, %d de %B')}"
                            )
                except Exception as e:
                    print(f"⚠️ Error al generar imagen: {e}")

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
            buttons = []
            row = []

            for h in available_hours:
                hour_int = int(h.split(":")[0])
                if is_today and hour_int <= now.hour:
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

            text_hour = f"Fecha seleccionada: {result}\n⏰ Ahora, selecciona una hora:"
            if is_today and not buttons[:-1]:
                text_hour = f"❌ Lo siento, ya no quedan huecos disponibles para hoy ({result})."
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
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra las citas del usuario y luego permite ver disponibilidad."""
    try:
        # Obtener usuario de Telegram
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.ID
        
        # Obtener citas del usuario de la BD
        from src.BBDD.databasecontroller import obtener_citas_por_usuario_reverse, get_session
        with get_session() as session:
            citas = obtener_citas_por_usuario_reverse(session, user_db_id)
            citas_texto = " *📋 Mis citas:*\n\n"
            
            if not citas:
                citas_texto = " *📋 Mis citas:*\n\n*No hay citas registradas*\n\n"
            else:
                for i, cita in enumerate(citas, 1):
                    fecha_str = cita.FECHA.strftime("%d/%m/%Y %H:%M")
                    citas_texto += f"{i}️⃣ *{fecha_str}* - {cita.DESCRIPCION or 'Sin descripción'}\n"
        
        # Mostrar citas y opciones
        message = citas_texto + "\n✅ ¿Deseas ver tu disponibilidad?"
        
        keyboard = [
            [InlineKeyboardButton("📅 Ver disponibilidad", callback_data="action_view_availability")],
            [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=message, reply_markup=reply_markup, parse_mode="Markdown"
        )
        
    except Exception as e:
        print(f"❌ Error en handle_action_my_appointments: {e}")
        keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="❌ Error al cargar tus citas", reply_markup=reply_markup
        )
