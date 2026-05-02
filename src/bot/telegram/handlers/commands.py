from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from src.bot.telegram.constants import WELCOME_TEXT, MODO_TEXTO
from src.bot.telegram.keyboards import main_menu_keyboard, menu_eleccion


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /start con un mensaje de bienvenida y un menú interactivo.

    Args:
        update: Objeto con la información del mensaje entrante.
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    current_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    if update.message:
        await update.message.reply_text(
            text=WELCOME_TEXT,
            reply_markup=menu_eleccion(),
        )


async def handle_action_back_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el menú principal, manejando correctamente mensajes de texto y audio."""
    current_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    # Eliminar imágenes de disponibilidad si existen
    try:
        day_photo_id = context.user_data.get("day_photo_message_id")
        if day_photo_id:
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=day_photo_id
                )
            except Exception:
                pass  # Si no se puede borrar, continuar
            # Limpiar el ID para que no intente reutilizarlo
            context.user_data["day_photo_message_id"] = None
        
        week_photo_id = context.user_data.get("week_photo_message_id")
        if week_photo_id:
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=week_photo_id
                )
            except Exception:
                pass  # Si no se puede borrar, continuar
            # Limpiar el ID para que no intente reutilizarlo
            context.user_data["week_photo_message_id"] = None
        
        # También borrar TODAS las imágenes de disponibilidad del flujo de reserva
        for reserve_photo_id in context.user_data.get("reserve_photo_message_ids", []):
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=reserve_photo_id
                )
            except Exception:
                pass
        context.user_data["reserve_photo_message_ids"] = []
        context.user_data["reserve_photo_message_id"] = None
        context.user_data["reserve_photo_generating"] = False
        context.user_data["day_photo_generating"] = False
        context.user_data["week_photo_generating"] = False
    except Exception:
        pass
    
    if query.message.text:
        try:
            await query.edit_message_text(
                text=WELCOME_TEXT,
                reply_markup=main_menu_keyboard(current_mode),
            )
        except BadRequest:
            pass
    else:
        await query.delete_message()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=WELCOME_TEXT,
            reply_markup=main_menu_keyboard(current_mode),
        )
