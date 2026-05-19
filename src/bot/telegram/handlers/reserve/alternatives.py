import asyncio
import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.ext import ContextTypes

from src.BBDD.database_service import obtener_o_crear_cliente_por_telegram
from src.bot.telegram.chat_actions import send_action_while_thinking
from src.bot.telegram.constants import MODO_AUDIO, MODO_TEXTO
from src.bot.telegram.keyboards import main_menu_keyboard
from src.services import calendar_service
from src.services.voice_service import VoiceService


def parse_alternative_times(error_message: str) -> list:
    """Extrae las horas alternativas libres del mensaje de error.

    Busca patrones como: "Otras fechas cercanas que podrían interesarte: 12/06/2026 06:00 11/06/2026 23:00"
    Retorna lista de tuples: [(fecha, hora), (fecha, hora)]
    """
    try:
        # Buscar el patrón de fechas y horas
        pattern = r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})"
        matches = re.findall(pattern, error_message)

        if not matches or len(matches) < 2:
            return []

        # Convertir a datetime para validar que no sean pasadas
        now = datetime.now()
        alternatives = []

        for fecha_str, hora_str in matches[:2]:  # Solo tomar las primeras 2
            try:
                # Parsear fecha: formato DD/MM/YYYY
                fecha_obj = datetime.strptime(
                    f"{fecha_str} {hora_str}", "%d/%m/%Y %H:%M"
                )

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
    query,
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    alternatives: list,
    original_date: str,
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

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"⬅️ Anterior: {hora}", callback_data=callback_data
                    )
                ]
            )

        if len(alternatives) >= 2:
            # Segunda alternativa (hora posterior/derecha)
            fecha, hora = alternatives[1]
            fecha_obj = datetime.strptime(fecha, "%d/%m/%Y")
            fecha_iso = fecha_obj.strftime("%Y%m%d")
            hora_no_sep = hora.replace(":", "")
            callback_data = f"alt_time_1_{fecha_iso}_{hora_no_sep}"

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"Posterior: {hora} ➡️", callback_data=callback_data
                    )
                ]
            )

        # Agregar opción para elegir otro día
        keyboard.append(
            [InlineKeyboardButton("📅 Otro día", callback_data="action_reserve")]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "⫶☰ Menú Principal", callback_data="action_back_menu"
                )
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = "⏰ La hora seleccionada no está disponible.\n\n"
        message_text += "Elige una de las alternativas más cercanas:\n\n"
        for idx, (fecha, hora) in enumerate(alternatives, 1):
            if idx == 1:
                message_text += f"⬅️ Anterior: {hora}\n"
            elif idx == 2:
                message_text += f"Posterior ➡️: {hora}\n"

        await query.edit_message_text(text=message_text, reply_markup=reply_markup)

        # Guardar las alternativas en contexto
        context.user_data["alternative_times"] = alternatives

    except Exception as e:
        print(f"Error en handle_alternative_time_selection: {e}")
        await query.answer(f"Error: {str(e)}", show_alert=True)


async def handle_alternative_time_selection_callback(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Procesa la selección de una hora alternativa."""
    try:
        # Parsear el callback: alt_time_0_20260612_0600
        parts = query.data.split("_")
        if len(parts) < 4 or parts[0] != "alt":
            return

        # parts[2] is idx, currently unused
        fecha_yyyymmdd = parts[3]  # YYYYMMDD
        hora_str = parts[4]  # HHMM

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

        # Obtener o crear cliente de la BD
        telegram_id = update.effective_user.id
        user_info = await asyncio.to_thread(
            obtener_o_crear_cliente_por_telegram,
            telegram_id,
            update.effective_user.full_name,
        )

        if user_info.get("error"):
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
                text="❌ Error al obtener tus datos de usuario",
                reply_markup=error_keyboard,
            )
            return

        # Llamar a la API para crear la cita
        response_message = await calendar_service.create_reservation_via_api(
            telegram_id=telegram_id,
            date=fecha_iso,
            hour=hora_formatted,
            usuario_id=user_info["usuario_id"],
            contacto_id=user_info["contacto_id"],
            bloqueante=7,
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
                        chat_id=update.effective_chat.id, message_id=reserve_photo_id
                    )
                    context.user_data["reserve_photo_message_id"] = None
                except Exception as e:
                    print(f"⚠️ Error al borrar imagen de reserva: {e}")

            if user_mode == MODO_AUDIO:
                await query.edit_message_text("🎙️ Generando audio de confirmación...")

                async with send_action_while_thinking(
                    context.bot,
                    update.effective_chat.id,
                    constants.ChatAction.RECORD_VOICE,
                ):
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
