from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from src.bot.telegram.constants import WELCOME_TEXT
from src.bot.telegram.keyboards import main_menu_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /start con un mensaje de bienvenida y un menú interactivo.

    Args:
        update: Objeto con la información del mensaje entrante.
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    if update.message:
        await update.message.reply_text(
            text=WELCOME_TEXT, reply_markup=main_menu_keyboard()
        )


async def handle_action_back_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el menú principal, manejando correctamente mensajes de texto y audio."""
    if query.message.text:
        try:
            await query.edit_message_text(
                text=WELCOME_TEXT, reply_markup=main_menu_keyboard()
            )
        except BadRequest:
            pass
    else:
        await query.delete_message()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=WELCOME_TEXT,
            reply_markup=main_menu_keyboard(),
        )
