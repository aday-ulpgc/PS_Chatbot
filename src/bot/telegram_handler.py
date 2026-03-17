"""Handlers de comandos para el bot de Telegram.

Este módulo contiene las funciones asíncronas que responden
a los comandos del usuario. Los handlers deben mantenerse
"tontos": sin lógica de negocio, solo interacción con el chat.
"""

from telegram import Update
from telegram.ext import ContextTypes


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Responde al comando /start con un mensaje de bienvenida.

    Args:
        update: Objeto con la información del mensaje entrante.
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    await update.message.reply_text("¡Hola! Soy tu bot de gestión de citas")
