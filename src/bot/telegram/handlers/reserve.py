import asyncio
import json
import os
import re
from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
import os
import re
from datetime import date, datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar

from src.BBDD.database_service import (
    guardar_cita_en_db,
    obtener_o_crear_usuario_telegram,
from src.services import calendar_service
from src.services.voice_service import VoiceService
from src.services.visualization_service import generar_imagen_disponibilidad, generar_imagen_disponibilidad_semana_24h
from src.bot.telegram.constants import CALENDAR_STEPS, MODO_TEXTO, MODO_AUDIO
from src.bot.telegram.keyboards import main_menu_keyboard
from src.bot.telegram.handlers.commands import handle_action_back_menu

from src.BBDD.database_service import (
    guardar_cita_en_db,
    obtener_o_crear_usuario_telegram,
    obtener_horas_ocupadas,
    actualizar_cita_fecha_db,
    obtener_info_cita_db,
)
from src.bot.telegram.constants import CALENDAR_STEPS, MODO_AUDIO, MODO_TEXTO
from src.bot.telegram.handlers.commands import handle_action_back_menu
from src.services import calendar_service
from src.services.voice_service import VoiceService


MESES_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def formatear_fecha_para_voz(texto: str) -> str:
    """Convierte fechas YYYY-MM-DD a un formato más natural en español."""

    def reemplazo(match):
        fecha_str = match.group(0)
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        return f"{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}"

    return re.sub(r"\b\d{4}-\d{2}-\d{2}\b", reemplazo, texto)


def formatear_hora_para_voz(texto: str) -> str:
    """Convierte horas del estilo 16:00 a un formato más natural."""
    return (
        texto.replace("9:00", "9 en punto")
        .replace("10:00", "10 en punto")
        .replace("11:00", "11 en punto")
        .replace("12:00", "12 en punto")
        .replace("16:00", "4 de la tarde")
        .replace("17:00", "5 de la tarde")
        .replace("18:00", "6 de la tarde")
        .replace("19:00", "7 de la tarde")
    )


async def enviar_recordatorio_cita(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Esta función es la que el bot ejecuta cuando pasan los 2 segundos."""
    job = context.job
    try:
        await context.bot.send_message(
            chat_id=job.chat_id,
            text=f"⏰ PRUEBA\n{job.data}",
        )
    except Exception as e:
        print(f"❌ Error al enviar el mensaje: {e}")


async def send_with_optional_audio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    texto: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Envía siempre texto y, si el modo audio está activo, también audio."""
    user_mode = context.user_data.get("pref_mode", MODO_TEXTO)
    print(f"[DEBUG] pref_mode actual: {user_mode}")

    if update.callback_query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texto,
            reply_markup=reply_markup,
        )
    elif update.message:
        await update.message.reply_text(
            text=texto,
            reply_markup=reply_markup,
        )

    if user_mode == MODO_AUDIO:
        try:
            texto_para_audio = formatear_fecha_para_voz(texto)
            texto_para_audio = formatear_hora_para_voz(texto_para_audio)
            print(f"[DEBUG] Texto para audio: {texto_para_audio}")

            audio_path = await VoiceService.text_to_speech(texto_para_audio)
            print(f"[DEBUG] Audio generado en: {audio_path}")

            with open(audio_path, "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio_file,
                    title="Confirmación de reserva",
                )

            if os.path.exists(audio_path):
                os.remove(audio_path)

            print("[DEBUG] Audio enviado correctamente")

        except Exception as e:
            print(f"❌ Error al generar/enviar audio: {e}")

def parse_alternative_times(error_message: str) -> list:
    """Extrae las horas alternativas libres del mensaje de error.
    
    Busca patrones como: "Otras fechas cercanas que podrían interesarte: 12/06/2026 06:00 11/06/2026 23:00"
    Retorna lista de tuples: [(fecha, hora), (fecha, hora)]
    """
    try:
        # Buscar el patrón de fechas y horas
        pattern = r'(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})'
        matches = re.findall(pattern, error_message)
        
        if not matches or len(matches) < 2:
            return []
        
        # Convertir a datetime para validar que no sean pasadas
        now = datetime.now()
        alternatives = []
        
        for fecha_str, hora_str in matches[:2]:  # Solo tomar las primeras 2
            try:
                # Parsear fecha: formato DD/MM/YYYY
                fecha_obj = datetime.strptime(f"{fecha_str} {hora_str}", "%d/%m/%Y %H:%M")
                
                # Si ya pasó, no añadirla
                if fecha_obj > now:
                    alternatives.append((fecha_str, hora_str))
            except ValueError:
                continue
        
        return alternatives
    except Exception as e:
        print(f"Error parseando alternativas: {e}")
        return []


async def handle_alternative_time_selection(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update,
    alternatives: list, original_date: str
) -> None:
    """Muestra opciones de horas alternativas libres al usuario con opciones izquierda/derecha/otro día."""
    try:
        keyboard = []
        
        # Asumir que el primer alternativo es la hora anterior (izquierda)
        # y el segundo es la hora posterior (derecha)
        if len(alternatives) >= 1:
            # Primera alternativa (hora anterior/izquierda)
            fecha, hora = alternatives[0]
            fecha_obj = datetime.strptime(fecha, "%d/%m/%Y")
            fecha_iso = fecha_obj.strftime("%Y%m%d")
            hora_no_sep = hora.replace(":", "")
            callback_data = f"alt_time_0_{fecha_iso}_{hora_no_sep}"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"⬅️ Anterior: {hora}",
                    callback_data=callback_data
                )
            ])
        
        if len(alternatives) >= 2:
            # Segunda alternativa (hora posterior/derecha)
            fecha, hora = alternatives[1]
            fecha_obj = datetime.strptime(fecha, "%d/%m/%Y")
            fecha_iso = fecha_obj.strftime("%Y%m%d")
            hora_no_sep = hora.replace(":", "")
            callback_data = f"alt_time_1_{fecha_iso}_{hora_no_sep}"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"Posterior: {hora} ➡️",
                    callback_data=callback_data
                )
            ])
        
        # Agregar opción para elegir otro día
        keyboard.append([
            InlineKeyboardButton("📅 Otro día", callback_data="action_reserve")
        ])
        keyboard.append([
            InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = "⏰ La hora seleccionada no está disponible.\n\n"
        message_text += "Elige una de las alternativas más cercanas:\n\n"
        for idx, (fecha, hora) in enumerate(alternatives, 1):
            if idx == 1:
                message_text += f"⬅️ Anterior: {hora}\n"
            elif idx == 2:
                message_text += f"Posterior ➡️: {hora}\n"
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup
        )
        
        # Guardar las alternativas en contexto
        context.user_data["alternative_times"] = alternatives
        
    except Exception as e:
        print(f"Error en handle_alternative_time_selection: {e}")
        await query.answer(f"Error: {str(e)}", show_alert=True)


async def enviar_recordatorio_cita(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Esta función es la que el bot ejecuta cuando pasan los 2 segundos."""
    job = context.job
    try:
        # Obtener el message_id del recordatorio anterior si existe
        reminder_message_id = context.user_data.get("reminder_message_id")
        message_text = f"⏰ PRUEBA\n{job.data}"
        
        if reminder_message_id:
            # Editar el mensaje anterior en lugar de crear uno nuevo
            try:
                await context.bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=reminder_message_id,
                    text=message_text
                )
            except Exception as edit_error:
                print(f"⚠️ No se pudo editar el recordatorio anterior: {edit_error}")
                # Si no se puede editar, enviar uno nuevo
                msg = await context.bot.send_message(
                    chat_id=job.chat_id, text=message_text
                )
                context.user_data["reminder_message_id"] = msg.message_id
        else:
            # Enviar nuevo mensaje
            msg = await context.bot.send_message(
                chat_id=job.chat_id, text=message_text
            )
            context.user_data["reminder_message_id"] = msg.message_id
    except Exception as e:
        print(f"❌ Error al enviar el mensaje: {e}")


async def handle_calendar_and_time(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
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
            await query.edit_message_text(
                text="⏳ Modificando tu reserva en Google Calendar..."
            )

            cita_antigua = await asyncio.to_thread(obtener_info_cita_db, modifying_id)
            name_and_id = (
                f"{update.effective_user.full_name} ({update.effective_user.id})"
            )

            if cita_antigua:
                old_fecha = cita_antigua["FECHA"].strftime("%Y-%m-%d")
                old_hora = cita_antigua["FECHA"].strftime("%H:%M")
                await asyncio.to_thread(
                    calendar_service.delete_reservation,
                    name_and_id,
                    old_fecha,
                    old_hora,
                )

            await asyncio.to_thread(
                calendar_service.create_reservation,
                name_and_id,
                selected_data,
                selected_time,
            )

            fecha_dt = datetime.strptime(selected_data, "%Y-%m-%d")
            hora_parts = selected_time.split(":")
            fecha_dt_con_hora = fecha_dt.replace(
                hour=int(hora_parts[0]),
                minute=int(hora_parts[1]) if len(hora_parts) > 1 else 0,
            )

            await asyncio.to_thread(
                actualizar_cita_fecha_db, modifying_id, fecha_dt_con_hora
            )
            context.user_data.pop("modifying_id", None)

            await query.answer("✅ Cita modificada con éxito", show_alert=True)

            from src.bot.telegram.handlers.manage_appointments import (
                handle_action_my_appointments,
            )

            await handle_action_my_appointments(query, context)

            return True

        await query.edit_message_text(
            text=(
                f"✅ ¡Resumen de tu solicitud!\n"
                f"📅 Fecha: {selected_data}\n"
                f"⏰ Hora: {selected_time}\n\n"
                f"⏳ Procesando reserva en Google Calendar..."
            )
        )

        name_and_id = f"{update.effective_user.full_name} ({update.effective_user.id})"
        response_message = await asyncio.to_thread(
            calendar_service.create_reservation,
            name_and_id,
            selected_data,
            selected_time,
        )

        if response_message.startswith("❌"):
            # Verificar si es un error de horario ocupado con alternativas
            if "Otras fechas cercanas" in response_message or "Otras horas" in response_message:
                alternatives = parse_alternative_times(response_message)
                
                if alternatives and len(alternatives) >= 1:
                    # Mostrar opciones de horas alternativas
                    await handle_alternative_time_selection(
                        query, context, update, alternatives, selected_data
                    )
                    return True
            
            # Si no hay alternativas o es otro tipo de error, mostrar error normal
            error_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↻ Elegir otro día",
                            callback_data="action_reserve",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⫶☰ Menú Principal",
                            callback_data="action_back_menu",
                        )
                    ],
                ]
            )
            await query.edit_message_text(
                text=response_message,
                reply_markup=error_keyboard,
            )
        else:
            # Obtener modo del usuario (TEXTO o AUDIO)
            user_mode = context.user_data.get("pref_mode", MODO_TEXTO)

            context.user_data["last_reserva_text"] = response_message

            # Borrar la imagen de disponibilidad si existe
            reserve_photo_id = context.user_data.get("reserve_photo_message_id")
            if reserve_photo_id:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=reserve_photo_id
                    )
                    context.user_data["reserve_photo_message_id"] = None
                except Exception as e:
                    print(f"⚠️ Error al borrar imagen de reserva: {e}")

            if user_mode == MODO_AUDIO:
                await query.edit_message_text("🎙️ Generando audio de confirmación...")

                audio_path = await VoiceService.text_to_speech(response_message)

                audio_keyboard = InlineKeyboardMarkup(
                    [
                        InlineKeyboardButton(
                            "⫶☰ Menú Principal",
                            callback_data="action_back_menu",
                        )
                    ]
                ]
            )

            await query.delete_message()

            await send_with_optional_audio(
                update,
                context,
                response_message,
                reply_markup=menu_keyboard,
            )

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
                        text=btn["text"],
                        callback_data=btn["callback_data"],
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
                # Evitar que clicks rápidos generen imágenes simultáneas
                if context.user_data.get("reserve_photo_generating"):
                    await query.answer("⏳ Cargando imagen, espera un momento...")
                else:
                    context.user_data["reserve_photo_generating"] = True
                    try:
                        # Borrar TODAS las imágenes anteriores acumuladas
                        for old_id in context.user_data.get("reserve_photo_message_ids", []):
                            try:
                                await context.bot.delete_message(
                                    chat_id=query.from_user.id,
                                    message_id=old_id
                                )
                            except Exception:
                                pass
                        context.user_data["reserve_photo_message_ids"] = []

                        # Convertir date a datetime
                        fecha_datetime = datetime.combine(result, datetime.min.time())
                        imagen_path = await asyncio.to_thread(
                            generar_imagen_disponibilidad,
                            user_info["id_usuario"],
                            fecha_datetime
                        )

                        # Enviar imagen y guardar su message_id en la lista
                        if imagen_path:
                            await query.answer()
                            with open(imagen_path, 'rb') as img:
                                photo_message = await context.bot.send_photo(
                                    chat_id=query.from_user.id,
                                    photo=img,
                                    caption=f"📊 Disponibilidad para {result.strftime('%A, %d de %B')}"
                                )
                            context.user_data["reserve_photo_message_ids"] = [photo_message.message_id]
                            # Compatibilidad con código existente que usa el campo singular
                            context.user_data["reserve_photo_message_id"] = photo_message.message_id
                    except Exception as e:
                        print(f"⚠️ Error al generar imagen: {e}")
                    finally:
                        context.user_data["reserve_photo_generating"] = False

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
                        "↻ Cambiar Fecha",
                        callback_data="action_reserve",
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
                                "↻ Elegir otro día",
                                callback_data="action_reserve",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⫶☰ Menú Principal",
                                callback_data="action_back_menu",
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


async def handle_alternative_time_selection_callback(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Procesa la selección de una hora alternativa."""
    try:
        # Parsear el callback: alt_time_0_20260612_0600
        parts = query.data.split("_")
        if len(parts) < 4 or parts[0] != "alt":
            return
        
        idx = int(parts[2])
        fecha_yyyymmdd = parts[3]  # YYYYMMDD
        hora_str = parts[4]   # HHMM
        
        # Convertir hora de HHMM a HH:MM
        hora_formatted = f"{hora_str[:2]}:{hora_str[2:]}"
        
        # Convertir fecha de YYYYMMDD a:
        # - ISO format (YYYY-MM-DD) para el API
        # - Display format (DD/MM/YYYY) para mostrar
        fecha_obj = datetime.strptime(fecha_yyyymmdd, "%Y%m%d")
        fecha_iso = fecha_obj.strftime("%Y-%m-%d")
        fecha_display = fecha_obj.strftime("%d/%m/%Y")
        
        # Procesar la reserva con la hora alternativa seleccionada
        await query.edit_message_text(
            text=f"✅ ¡Resumen de tu solicitud!\n📅 Fecha: {fecha_display}\n⏰ Hora: {hora_formatted}\n\n⏳ Procesando reserva..."
        )
        
        name_and_id = f"{update.effective_user.full_name} ({update.effective_user.id})"
        response_message = await asyncio.to_thread(
            calendar_service.create_reservation,
            name_and_id,
            fecha_iso,
            hora_formatted,
        )
        
        if response_message.startswith("✅"):
            # Éxito en la reserva
            user_mode = context.user_data.get("pref_mode", MODO_TEXTO)
            context.user_data["last_reserva_text"] = response_message
            
            # Borrar la imagen de disponibilidad si existe
            reserve_photo_id = context.user_data.get("reserve_photo_message_id")
            if reserve_photo_id:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=reserve_photo_id
                    )
                    context.user_data["reserve_photo_message_id"] = None
                except Exception as e:
                    print(f"⚠️ Error al borrar imagen de reserva: {e}")
            
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
        else:
            # Error nuevamente
            error_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↻ Elegir otra hora", callback_data="action_reserve"
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
        
    except Exception as e:
        print(f"Error en handle_alternative_time_selection_callback: {e}")
        import traceback
        traceback.print_exc()
        await query.answer(f"Error: {str(e)}", show_alert=True)


async def handle_action_reserve(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_calendar = DetailedTelegramCalendar(min_date=date.today())
    calendar, step = current_calendar.build()

    keyboard_dict = json.loads(calendar)
    navigation_row = [
        {"text": "↻ Reiniciar", "callback_data": "action_reserve"},
        {"text": "⫶☰ Menú", "callback_data": "action_back_menu"},
    ]
    # Añadir el botón de disponibilidad
    availability_row = [
        {"text": "📅 Ver disponibilidad", "callback_data": "action_view_availability"}
    ]
    keyboard_dict["inline_keyboard"].append(availability_row)
    keyboard_dict["inline_keyboard"].append(navigation_row)

    try:
        keyboard_buttons = [
            [
                InlineKeyboardButton(
                    text=btn["text"],
                    callback_data=btn["callback_data"],
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
    """Muestra la última imagen de día o el calendario para seleccionar un día."""
    # Bloquear clicks rápidos durante la regeneración
    if context.user_data.get("day_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    try:
        # Borrar imagen de semana si existe (cambio de vista)
        week_photo_id = context.user_data.get("week_photo_message_id")
        if week_photo_id:
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=week_photo_id
                )
                context.user_data["week_photo_message_id"] = None
            except Exception:
                pass  # Mantener el ID para que back_menu pueda reintentarlo
        
        # Verificar si existe una imagen anterior de día
        current_day_date = context.user_data.get("current_day_date")
        day_photo_id = context.user_data.get("day_photo_message_id")
        
        # Solo intentar reutilizar la imagen si ambos existen y message_id es válido
        if current_day_date and day_photo_id and day_photo_id is not None:
            if not isinstance(current_day_date, date):
                current_day_date = date.fromisoformat(str(current_day_date))
            
            # Obtener usuario
            user_id = update.effective_user.id
            usuario = obtener_o_crear_usuario_telegram(user_id)
            user_db_id = usuario.get("id_usuario")
            
            if user_db_id:
                # Bloquear clicks rápidos durante la regeneración
                context.user_data["day_photo_generating"] = True
                try:
                    # Convertir a datetime
                    day_datetime = datetime.combine(current_day_date, datetime.min.time())

                    # Generar imagen del día
                    imagen_path = await asyncio.to_thread(
                        generar_imagen_disponibilidad, user_db_id, day_datetime
                    )

                    if imagen_path and os.path.exists(imagen_path):
                        try:
                            with open(imagen_path, "rb") as img_file:
                                media = InputMediaPhoto(
                                    media=img_file.read(),
                                    caption=f"📊 Tu disponibilidad el {current_day_date.strftime('%d/%m/%Y')}",
                                    parse_mode="HTML"
                                )
                                await context.bot.edit_message_media(
                                    chat_id=query.message.chat_id,
                                    message_id=day_photo_id,
                                    media=media
                                )

                            # Si funcionó, mostrar botones
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
                                text="✅ Última disponibilidad de día guardada",
                                reply_markup=reply_markup
                            )
                            return
                        except Exception as e:
                            # No se pudo editar: intentar borrar la foto huérfana y limpiar
                            print(f"No se pudo editar imagen día: {e}")
                            try:
                                await context.bot.delete_message(
                                    chat_id=query.message.chat_id,
                                    message_id=day_photo_id
                                )
                            except Exception:
                                pass
                            context.user_data["day_photo_message_id"] = None
                finally:
                    context.user_data["day_photo_generating"] = False
        
        # Si no existe imagen anterior válida, mostrar calendario
        calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
        await query.edit_message_text(
            text="📅 Selecciona un día para ver tu disponibilidad:",
            reply_markup=calendar
        )
        context.user_data["availability_calendar"] = "day"
        
    except Exception as e:
        print(f"❌ Error en handle_action_view_availability_day: {e}")
        import traceback
        traceback.print_exc()
        keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="❌ Error al mostrar calendario", reply_markup=reply_markup
        )


async def handle_action_view_availability_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la última imagen de semana o el calendario para seleccionar una semana."""
    # Bloquear clicks rápidos durante la regeneración
    if context.user_data.get("week_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    try:
        # Borrar imagen de día si existe (cambio de vista)
        day_photo_id = context.user_data.get("day_photo_message_id")
        if day_photo_id:
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=day_photo_id
                )
                context.user_data["day_photo_message_id"] = None
            except Exception:
                pass  # Mantener el ID para que back_menu pueda reintentarlo
        
        # Verificar si existe una imagen anterior de semana
        current_week_date = context.user_data.get("current_week_date")
        week_photo_id = context.user_data.get("week_photo_message_id")
        
        # Solo intentar reutilizar la imagen si ambos existen y message_id es válido
        if current_week_date and week_photo_id and week_photo_id is not None:
            if not isinstance(current_week_date, date):
                current_week_date = date.fromisoformat(str(current_week_date))
            
            # Obtener usuario
            user_id = update.effective_user.id
            usuario = obtener_o_crear_usuario_telegram(user_id)
            user_db_id = usuario.get("id_usuario")
            
            if user_db_id:
                context.user_data["week_photo_generating"] = True
                try:
                    # Convertir a datetime
                    week_datetime = datetime.combine(current_week_date, datetime.min.time())

                    # Generar imagen de la semana
                    imagen_path = await asyncio.to_thread(
                        generar_imagen_disponibilidad_semana_24h, user_db_id, week_datetime
                    )

                    if imagen_path and os.path.exists(imagen_path):
                        try:
                            # Calcular rango de fechas para el caption
                            lunes = current_week_date - timedelta(days=current_week_date.weekday())
                            domingo_fecha = lunes + timedelta(days=6)
                            caption = f"📆 Semana del {lunes.strftime('%d/%m')} al {domingo_fecha.strftime('%d/%m/%Y')}"

                            with open(imagen_path, "rb") as img_file:
                                media = InputMediaPhoto(
                                    media=img_file.read(),
                                    caption=caption,
                                    parse_mode="HTML"
                                )
                                await context.bot.edit_message_media(
                                    chat_id=query.message.chat_id,
                                    message_id=week_photo_id,
                                    media=media
                                )

                            # Si funcionó, mostrar botones
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
                            return
                        except Exception as e:
                            # No se pudo editar: intentar borrar la foto huérfana y limpiar
                            print(f"No se pudo editar imagen semana: {e}")
                            try:
                                await context.bot.delete_message(
                                    chat_id=query.message.chat_id,
                                    message_id=week_photo_id
                                )
                            except Exception:
                                pass
                            context.user_data["week_photo_message_id"] = None
                finally:
                    context.user_data["week_photo_generating"] = False
        
        # Si no existe imagen anterior válida, mostrar calendario
        calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
        await query.edit_message_text(
            text="📆 Selecciona cualquier día de la semana que deseas ver:",
            reply_markup=calendar
        )
        context.user_data["availability_calendar"] = "week"
        
    except Exception as e:
        print(f"❌ Error en handle_action_view_availability_week: {e}")
        import traceback
        traceback.print_exc()
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
                # Evitar generaciones concurrentes por clicks rápidos
                if context.user_data.get("day_photo_generating"):
                    await query.answer("⏳ Cargando imagen, espera un momento...")
                    return
                context.user_data["day_photo_generating"] = True
                try:
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

                        context.user_data["day_photo_message_id"] = photo_message.message_id
                        context.user_data["current_day_date"] = selected_date

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
                    else:
                        await query.edit_message_text("❌ Error al generar la imagen")
                finally:
                    context.user_data["availability_calendar"] = False
                    context.user_data["day_photo_generating"] = False

            elif availability_type == "week":
                # Evitar generaciones concurrentes por clicks rápidos
                if context.user_data.get("week_photo_generating"):
                    await query.answer("⏳ Cargando imagen, espera un momento...")
                    return
                context.user_data["week_photo_generating"] = True
                try:
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

                        context.user_data["week_photo_message_id"] = photo_message.message_id
                        context.user_data["current_week_date"] = selected_date

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
                    else:
                        await query.edit_message_text("❌ Error al generar la imagen")
                finally:
                    context.user_data["availability_calendar"] = False
                    context.user_data["week_photo_generating"] = False
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
    if context.user_data.get("day_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    context.user_data["day_photo_generating"] = True
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
    finally:
        context.user_data["day_photo_generating"] = False


async def handle_next_day(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el día siguiente."""
    if context.user_data.get("day_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    context.user_data["day_photo_generating"] = True
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
    finally:
        context.user_data["day_photo_generating"] = False


async def handle_prev_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la semana anterior."""
    if context.user_data.get("week_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    context.user_data["week_photo_generating"] = True
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
    finally:
        context.user_data["week_photo_generating"] = False


async def handle_next_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la semana siguiente."""
    if context.user_data.get("week_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    context.user_data["week_photo_generating"] = True
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
    finally:
        context.user_data["week_photo_generating"] = False


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
