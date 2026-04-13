from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


async def handle_action_menu_help(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reemplaza el menú principal por el submenú de opciones de ayuda.

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                               usado para editar el mensaje actual.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "❓ Preguntas frecuentes", callback_data="action_help_faq"
            )
        ],
        [
            InlineKeyboardButton(
                "🛠️ Soporte técnico", url="https://forms.gle/Fu9HuBVJA747nW9E8"
            )
        ],
        [
            InlineKeyboardButton(
                "📖 Guía de uso",
                url="https://docs.google.com/document/d/16ryO0SMthEtiy3AFTEKQJK7v4IODzlgunb8nVP7bI1Q/edit?usp=sharing",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Volver al menú principal", callback_data="action_back_menu"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Sección Ayuda. ¿Que necesitas?", reply_markup=reply_markup
    )


async def handle_action_faq(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reemplaza el submenú de opciones de ayuda por las preguntas frecuentes

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                               usado para editar el mensaje actual.
    """
    questions = (
        "❓ *Preguntas Frecuentes*\n\n"
        "1️⃣ *¿Cómo cancelo una cita?*\n"
        "Ve a 'Mis citas' y pulsa anular.\n\n"
        "2️⃣ *¿Qué pasa si llego tarde?*\n"
        "Tienes 10 minutos de cortesía."
    )

    keyboard = [[InlineKeyboardButton("Volver", callback_data="action_help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=questions, reply_markup=reply_markup, parse_mode="Markdown"
    )
