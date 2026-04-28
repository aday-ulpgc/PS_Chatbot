import json
import asyncio
import os
from datetime import date, datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar
from telegram.error import BadRequest

from src.services import calendar_service
from src.services.voice_service import VoiceService
from src.services.visualization_service import generar_imagen_disponibilidad, generar_imagen_disponibilidad_semana_24h
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
    """Muestra las citas del usuario agrupadas en bloques de 9."""
    try:
        # Obtener usuario de Telegram
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")
        
        if not user_db_id:
            await query.edit_message_text("❌ Error al obtener tus datos de usuario")
            return
        
        # Obtener citas del usuario de la BD
        from src.BBDD.databasecontroller import obtener_citas_por_usuario, get_session
        with get_session() as session:
            citas = obtener_citas_por_usuario(session, user_db_id)
            # Invertir para mostrar más recientes primero
            citas = sorted(citas, key=lambda c: c.FECHA, reverse=True)
            
            # Convertir a diccionarios DENTRO de la sesión para no perder datos
            citas_dict = [
                {
                    'fecha': c.FECHA,
                    'descripcion': c.DESCRIPCION or 'Sin descripción'
                }
                for c in citas
            ]
            
            if not citas_dict:
                keyboard = [
                    [InlineKeyboardButton("📅 Ver disponibilidad", callback_data="action_view_availability")],
                    [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text="📋 *Mis citas:*\n\n*No hay citas registradas*",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            # Agrupar citas en bloques de 9
            emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
            bloques = []
            for i in range(0, len(citas_dict), 9):
                bloque = citas_dict[i:i+9]
                bloques.append(bloque)
            
            # Guardar bloques en contexto para navegación
            context.user_data["citas_bloques"] = bloques
            context.user_data["citas_bloque_actual"] = 0
            
            # Mostrar primer bloque
            bloque_texto = f"📋 *Mis citas* (grupo 1 de {len(bloques)})\n\n"
            for idx, cita in enumerate(bloques[0]):
                fecha_str = cita['fecha'].strftime("%d/%m/%Y %H:%M")
                bloque_texto += f"{emojis[idx]} *{fecha_str}* - {cita['descripcion']}\n"
            
            # Crear botones de navegación
            keyboard = []
            if len(bloques) > 1:
                keyboard.append([
                    InlineKeyboardButton("⬅️ Anterior", callback_data="action_prev_citas_group"),
                    InlineKeyboardButton("Siguiente ➡️", callback_data="action_next_citas_group")
                ])
            keyboard.extend([
                [InlineKeyboardButton("📅 Ver disponibilidad", callback_data="action_view_availability")],
                [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")]
            ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=bloque_texto,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        
    except Exception as e:
        print(f"❌ Error en handle_action_my_appointments: {e}")
        keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="❌ Error al cargar tus citas", reply_markup=reply_markup
        )


async def handle_action_view_availability(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Permite elegir si ver disponibilidad de un día o una semana."""
    try:
        keyboard = [
            [InlineKeyboardButton("📅 Ver disponibilidad de un DÍA", callback_data="action_view_availability_day")],
            [InlineKeyboardButton("📆 Ver disponibilidad de una SEMANA", callback_data="action_view_availability_week")],
            [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="¿Qué tipo de disponibilidad deseas ver?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        print(f"❌ Error en handle_action_view_availability: {e}")
        keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="❌ Error al mostrar opciones", reply_markup=reply_markup
        )


async def handle_action_view_availability_day(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el calendario para seleccionar un día."""
    try:
        calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
        await query.edit_message_text(
            text="📅 Selecciona un día para ver tu disponibilidad:",
            reply_markup=calendar
        )
        context.user_data["availability_calendar"] = "day"
        
    except Exception as e:
        print(f"❌ Error en handle_action_view_availability_day: {e}")
        keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="❌ Error al mostrar calendario", reply_markup=reply_markup
        )


async def handle_action_view_availability_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el calendario para seleccionar una semana."""
    try:
        calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
        await query.edit_message_text(
            text="📆 Selecciona cualquier día de la semana que deseas ver:",
            reply_markup=calendar
        )
        context.user_data["availability_calendar"] = "week"
        
    except Exception as e:
        print(f"❌ Error en handle_action_view_availability_week: {e}")
        keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="❌ Error al mostrar calendario", reply_markup=reply_markup
        )

async def handle_availability_calendar_selection(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Genera y envía la imagen de disponibilidad cuando se selecciona una fecha."""
    try:
        # Verificar si es un evento del calendario
        if not DetailedTelegramCalendar.func()(query):
            return
        
        # Procesar la selección del calendario
        current_calendar = DetailedTelegramCalendar(min_date=date.today())
        result, key, step = current_calendar.process(query.data)
        
        if not result and key:
            # Mostrar siguiente paso del calendario
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
                    InlineKeyboardButton("↻ Reiniciar", callback_data="action_view_availability"),
                    InlineKeyboardButton("⫶☰ Menú", callback_data="action_back_menu"),
                ]
            )
            
            try:
                await query.edit_message_text(
                    text="Selecciona una fecha:",
                    reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                )
            except BadRequest:
                pass
                
        elif result:
            # Fecha seleccionada
            selected_date = result
            availability_type = context.user_data.get("availability_calendar", "day")
            
            # Obtener usuario de Telegram
            user_id = update.effective_user.id
            usuario = obtener_o_crear_usuario_telegram(user_id)
            user_db_id = usuario.get("id_usuario")
            
            if not user_db_id:
                await query.edit_message_text("❌ Error al obtener tus datos de usuario")
                return
            
            # Convertir a datetime
            selected_datetime = datetime.combine(selected_date, datetime.min.time())
            
            if availability_type == "day":
                # Vista de día
                await query.edit_message_text("🎨 Generando imagen de disponibilidad del día...")
                
                imagen_path = await asyncio.to_thread(
                    generar_imagen_disponibilidad, user_db_id, selected_datetime
                )
                
                if imagen_path and os.path.exists(imagen_path):
                    with open(imagen_path, "rb") as img_file:
                        photo_message = await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=img_file,
                            caption=f"📊 Tu disponibilidad el {selected_date.strftime('%d/%m/%Y')}"
                        )
                    
                    # Guardar el message_id de la foto para poder editarla después
                    context.user_data["day_photo_message_id"] = photo_message.message_id
                    
                    # Guardar la fecha actual del día para navegar
                    context.user_data["current_day_date"] = selected_date
                    
                    # Mostrar botones para opciones con navegación
                    keyboard = [
                        [
                            InlineKeyboardButton("⬅️ Día anterior", callback_data="action_prev_day"),
                            InlineKeyboardButton("Día siguiente ➡️", callback_data="action_next_day")
                        ],
                        [InlineKeyboardButton("📅 Otro día", callback_data="action_view_availability_day")],
                        [InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text="✅ Imagen enviada",
                        reply_markup=reply_markup
                    )
                    # Limpiar el flag del calendario para permitir navegación
                    context.user_data["availability_calendar"] = False
                else:
                    await query.edit_message_text("❌ Error al generar la imagen")
                    # Limpiar el flag del calendario
                    context.user_data["availability_calendar"] = False
                    
            elif availability_type == "week":
                # Vista de semana
                await query.edit_message_text("🎨 Generando imagen de disponibilidad de la semana...")
                
                imagen_path = await asyncio.to_thread(
                    generar_imagen_disponibilidad_semana_24h, user_db_id, selected_datetime
                )
                
                if imagen_path and os.path.exists(imagen_path):
                    with open(imagen_path, "rb") as img_file:
                        photo_message = await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=img_file,
                            caption=f"📆 Disponibilidad de la semana"
                        )
                    
                    # Guardar el message_id de la foto para poder editarla después
                    context.user_data["week_photo_message_id"] = photo_message.message_id
                    
                    # Guardar la fecha actual de la semana para navegar
                    context.user_data["current_week_date"] = selected_date
                    
                    # Mostrar botones de navegación semanal
                    keyboard = [
                        [
                            InlineKeyboardButton("⬅️ Semana anterior", callback_data="action_prev_week"),
                            InlineKeyboardButton("Semana siguiente ➡️", callback_data="action_next_week")
                        ],
                        [InlineKeyboardButton("📆 Otra semana", callback_data="action_view_availability_week")],
                        [InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text="✅ Imagen enviada",
                        reply_markup=reply_markup
                    )
                    # Limpiar el flag del calendario
                    context.user_data["availability_calendar"] = False
                else:
                    await query.edit_message_text("❌ Error al generar la imagen")
                    # Limpiar el flag del calendario
                    context.user_data["availability_calendar"] = False
            else:
                await query.edit_message_text("❌ Error al generar la imagen")
                
    except Exception as e:
        print(f"❌ Error en handle_availability_calendar_selection: {e}")
        keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"❌ Error: {str(e)}", reply_markup=reply_markup
        )


async def handle_prev_day(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el día anterior."""
    try:
        # Obtener la fecha actual del día
        current_day_date = context.user_data.get("current_day_date")
        if not current_day_date:
            current_day_date = date.today()
        else:
            current_day_date = current_day_date if isinstance(current_day_date, date) else date.fromisoformat(str(current_day_date))
        
        # Restar 1 día
        prev_day_date = current_day_date - timedelta(days=1)
        
        # No permitir ir a días pasados
        if prev_day_date < date.today():
            await query.answer("⚠️ No puedes ver días pasados", show_alert=True)
            return
        
        # Obtener usuario
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")
        
        if not user_db_id:
            await query.answer("❌ Error al obtener datos del usuario", show_alert=True)
            return
        
        # Convertir a datetime
        prev_day_datetime = datetime.combine(prev_day_date, datetime.min.time())
        
        # Generar imagen del día anterior
        imagen_path = await asyncio.to_thread(
            generar_imagen_disponibilidad, user_db_id, prev_day_datetime
        )
        
        if imagen_path and os.path.exists(imagen_path):
            # Actualizar la fecha guardada
            context.user_data["current_day_date"] = prev_day_date
            
            # Obtener el message_id de la foto anterior
            photo_message_id = context.user_data.get("day_photo_message_id")
            
            if photo_message_id:
                # Reemplazar la imagen existente
                with open(imagen_path, "rb") as img_file:
                    media = InputMediaPhoto(
                        media=img_file.read(),
                        caption=f"📊 Tu disponibilidad el {prev_day_date.strftime('%d/%m/%Y')}",
                        parse_mode="HTML"
                    )
                    await context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=photo_message_id,
                        media=media
                    )
            
            # Actualizar botones
            keyboard = [
                [
                    InlineKeyboardButton("⬅️ Día anterior", callback_data="action_prev_day"),
                    InlineKeyboardButton("Día siguiente ➡️", callback_data="action_next_day")
                ],
                [InlineKeyboardButton("📅 Otro día", callback_data="action_view_availability_day")],
                [InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"✅ Día anterior",
                reply_markup=reply_markup
            )
        else:
            await query.answer("❌ Error al generar la imagen", show_alert=True)
            
    except Exception as e:
        print(f"❌ Error en handle_prev_day: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def handle_next_day(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el día siguiente."""
    try:
        # Obtener la fecha actual del día
        current_day_date = context.user_data.get("current_day_date")
        if not current_day_date:
            current_day_date = date.today()
        else:
            current_day_date = current_day_date if isinstance(current_day_date, date) else date.fromisoformat(str(current_day_date))
        
        # Sumar 1 día
        next_day_date = current_day_date + timedelta(days=1)
        
        # Obtener usuario
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")
        
        if not user_db_id:
            await query.answer("❌ Error al obtener datos del usuario", show_alert=True)
            return
        
        # Convertir a datetime
        next_day_datetime = datetime.combine(next_day_date, datetime.min.time())
        
        # Generar imagen del día siguiente
        imagen_path = await asyncio.to_thread(
            generar_imagen_disponibilidad, user_db_id, next_day_datetime
        )
        
        if imagen_path and os.path.exists(imagen_path):
            # Actualizar la fecha guardada
            context.user_data["current_day_date"] = next_day_date
            
            # Obtener el message_id de la foto anterior
            photo_message_id = context.user_data.get("day_photo_message_id")
            
            if photo_message_id:
                # Reemplazar la imagen existente
                with open(imagen_path, "rb") as img_file:
                    media = InputMediaPhoto(
                        media=img_file.read(),
                        caption=f"📊 Tu disponibilidad el {next_day_date.strftime('%d/%m/%Y')}",
                        parse_mode="HTML"
                    )
                    await context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=photo_message_id,
                        media=media
                    )
            
            # Actualizar botones
            keyboard = [
                [
                    InlineKeyboardButton("⬅️ Día anterior", callback_data="action_prev_day"),
                    InlineKeyboardButton("Día siguiente ➡️", callback_data="action_next_day")
                ],
                [InlineKeyboardButton("📅 Otro día", callback_data="action_view_availability_day")],
                [InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"✅ Día siguiente",
                reply_markup=reply_markup
            )
        else:
            await query.answer("❌ Error al generar la imagen", show_alert=True)
            
    except Exception as e:
        print(f"❌ Error en handle_next_day: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def handle_prev_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la semana anterior."""
    try:
        # Obtener la fecha actual de la semana
        current_week_date = context.user_data.get("current_week_date")
        if not current_week_date:
            current_week_date = date.today()
        else:
            current_week_date = current_week_date if isinstance(current_week_date, date) else date.fromisoformat(str(current_week_date))
        
        # Restar 7 días
        prev_week_date = current_week_date - timedelta(days=7)
        
        # No permitir ir a semanas pasadas (si el lunes de la semana anterior sería antes de hoy)
        lunes = prev_week_date - timedelta(days=prev_week_date.weekday())
        if lunes < date.today():
            await query.answer("⚠️ No puedes ver semanas pasadas", show_alert=True)
            return
        
        # Obtener usuario
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")
        
        if not user_db_id:
            await query.answer("❌ Error al obtener datos del usuario", show_alert=True)
            return
        
        # Convertir a datetime
        prev_week_datetime = datetime.combine(prev_week_date, datetime.min.time())
        
        # Generar imagen de la semana anterior
        imagen_path = await asyncio.to_thread(
            generar_imagen_disponibilidad_semana_24h, user_db_id, prev_week_datetime
        )
        
        if imagen_path and os.path.exists(imagen_path):
            # Actualizar la fecha guardada
            context.user_data["current_week_date"] = prev_week_date
            
            # Calcular rango de fechas para el caption
            lunes = prev_week_date - timedelta(days=prev_week_date.weekday())
            domingo_fecha = lunes + timedelta(days=6)
            caption = f"📆 Semana del {lunes.strftime('%d/%m')} al {domingo_fecha.strftime('%d/%m/%Y')}"
            
            # Obtener el message_id de la foto anterior
            photo_message_id = context.user_data.get("week_photo_message_id")
            
            if photo_message_id:
                # Reemplazar la imagen existente
                with open(imagen_path, "rb") as img_file:
                    media = InputMediaPhoto(
                        media=img_file.read(),
                        caption=caption,
                        parse_mode="HTML"
                    )
                    await context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=photo_message_id,
                        media=media
                    )
            
            # Actualizar botones
            keyboard = [
                [
                    InlineKeyboardButton("⬅️ Semana anterior", callback_data="action_prev_week"),
                    InlineKeyboardButton("Semana siguiente ➡️", callback_data="action_next_week")
                ],
                [InlineKeyboardButton("📆 Otra semana", callback_data="action_view_availability_week")],
                [InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"✅ {caption}",
                reply_markup=reply_markup
            )
        else:
            await query.answer("❌ Error al generar la imagen", show_alert=True)
            
    except Exception as e:
        print(f"❌ Error en handle_prev_week: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def handle_next_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la semana siguiente."""
    try:
        # Obtener la fecha actual de la semana
        current_week_date = context.user_data.get("current_week_date")
        if not current_week_date:
            current_week_date = date.today()
        else:
            current_week_date = current_week_date if isinstance(current_week_date, date) else date.fromisoformat(str(current_week_date))
        
        # Sumar 7 días
        next_week_date = current_week_date + timedelta(days=7)
        
        # Obtener usuario
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")
        
        if not user_db_id:
            await query.answer("❌ Error al obtener datos del usuario", show_alert=True)
            return
        
        # Convertir a datetime
        next_week_datetime = datetime.combine(next_week_date, datetime.min.time())
        
        # Generar imagen de la semana siguiente
        imagen_path = await asyncio.to_thread(
            generar_imagen_disponibilidad_semana_24h, user_db_id, next_week_datetime
        )
        
        if imagen_path and os.path.exists(imagen_path):
            # Actualizar la fecha guardada
            context.user_data["current_week_date"] = next_week_date
            
            # Calcular rango de fechas para el caption
            lunes = next_week_date - timedelta(days=next_week_date.weekday())
            domingo_fecha = lunes + timedelta(days=6)
            caption = f"📆 Semana del {lunes.strftime('%d/%m')} al {domingo_fecha.strftime('%d/%m/%Y')}"
            
            # Obtener el message_id de la foto anterior
            photo_message_id = context.user_data.get("week_photo_message_id")
            
            if photo_message_id:
                # Reemplazar la imagen existente
                with open(imagen_path, "rb") as img_file:
                    media = InputMediaPhoto(
                        media=img_file.read(),
                        caption=caption,
                        parse_mode="HTML"
                    )
                    await context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=photo_message_id,
                        media=media
                    )
            
            # Actualizar botones
            keyboard = [
                [
                    InlineKeyboardButton("⬅️ Semana anterior", callback_data="action_prev_week"),
                    InlineKeyboardButton("Semana siguiente ➡️", callback_data="action_next_week")
                ],
                [InlineKeyboardButton("📆 Otra semana", callback_data="action_view_availability_week")],
                [InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"✅ {caption}",
                reply_markup=reply_markup
            )
        else:
            await query.answer("❌ Error al generar la imagen", show_alert=True)
            
    except Exception as e:
        print(f"❌ Error en handle_next_week: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def handle_prev_citas_group(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el grupo anterior de citas."""
    try:
        bloques = context.user_data.get("citas_bloques", [])
        bloque_actual = context.user_data.get("citas_bloque_actual", 0)
        
        if not bloques or bloque_actual == 0:
            await query.answer("⚠️ Ya estás en el primer grupo", show_alert=True)
            return
        
        # Retroceder un grupo
        nuevo_bloque = bloque_actual - 1
        context.user_data["citas_bloque_actual"] = nuevo_bloque
        
        # Generar texto del nuevo grupo
        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
        bloque_texto = f"📋 *Mis citas* (grupo {nuevo_bloque + 1} de {len(bloques)})\n\n"
        
        for idx, cita in enumerate(bloques[nuevo_bloque]):
            fecha_str = cita['fecha'].strftime("%d/%m/%Y %H:%M")
            bloque_texto += f"{emojis[idx]} *{fecha_str}* - {cita['descripcion']}\n"
        
        # Crear botones de navegación
        keyboard = []
        if len(bloques) > 1:
            keyboard.append([
                InlineKeyboardButton("⬅️ Anterior", callback_data="action_prev_citas_group"),
                InlineKeyboardButton("Siguiente ➡️", callback_data="action_next_citas_group")
            ])
        keyboard.extend([
            [InlineKeyboardButton("📅 Ver disponibilidad", callback_data="action_view_availability")],
            [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=bloque_texto,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        print(f"❌ Error en handle_prev_citas_group: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def handle_next_citas_group(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el siguiente grupo de citas."""
    try:
        bloques = context.user_data.get("citas_bloques", [])
        bloque_actual = context.user_data.get("citas_bloque_actual", 0)
        
        if not bloques or bloque_actual >= len(bloques) - 1:
            await query.answer("⚠️ Ya estás en el último grupo", show_alert=True)
            return
        
        # Avanzar un grupo
        nuevo_bloque = bloque_actual + 1
        context.user_data["citas_bloque_actual"] = nuevo_bloque
        
        # Generar texto del nuevo grupo
        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
        bloque_texto = f"📋 *Mis citas* (grupo {nuevo_bloque + 1} de {len(bloques)})\n\n"
        
        for idx, cita in enumerate(bloques[nuevo_bloque]):
            fecha_str = cita['fecha'].strftime("%d/%m/%Y %H:%M")
            bloque_texto += f"{emojis[idx]} *{fecha_str}* - {cita['descripcion']}\n"
        
        # Crear botones de navegación
        keyboard = []
        if len(bloques) > 1:
            keyboard.append([
                InlineKeyboardButton("⬅️ Anterior", callback_data="action_prev_citas_group"),
                InlineKeyboardButton("Siguiente ➡️", callback_data="action_next_citas_group")
            ])
        keyboard.extend([
            [InlineKeyboardButton("📅 Ver disponibilidad", callback_data="action_view_availability")],
            [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=bloque_texto,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        print(f"❌ Error en handle_next_citas_group: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
