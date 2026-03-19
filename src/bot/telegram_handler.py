"""Handlers de comandos para el bot de Telegram.

Este módulo contiene las funciones asíncronas que responden
a los comandos del usuario. Los handlers deben mantenerse
"tontos": sin lógica de negocio, solo interacción con el chat.
"""

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:    
    """Responde al comando /start con un mensaje de bienvenida y un menú interactivo.

    Args:
        update: Objeto con la información del mensaje entrante.
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    keyboard = [
        [InlineKeyboardButton("📅 Hacer una reserva", callback_data="action_reserve")],
        [InlineKeyboardButton("📋 Mis citas", callback_data="action_my_appointments")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="action_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            "¡Hola! Soy tu asistente de reservas (SaaS-Bot del Grupo 06). ¿En qué te puedo ayudar hoy?",
            reply_markup=reply_markup
        )


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa los eventos de los botones del menú interactivo.

    Args:
        update: Objeto con la información del evento (CallbackQuery).
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    match query.data:
        case "action_reserve":
            calendar, step = DetailedTelegramCalendar().build()
            await query.edit_message_text(text=f"Selecciona una fecha: {LSTEP[step]}", reply_markup=calendar)
        case "action_my_appointments":
            response_text = "Has seleccionado: 📋 Mis citas. (Funcionalidad en desarrollo)"
        case "action_help":
            response_text = "Has seleccionado: ❓ Ayuda. (Funcionalidad en desarrollo)"
        case _:
            response_text = "Acción no reconocida."

    await query.edit_message_text(text=response_text)
