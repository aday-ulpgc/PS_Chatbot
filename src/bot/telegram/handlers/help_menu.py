from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.services.translator_service import TranslatorService


async def handle_action_menu_help(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reemplaza el menú principal por el submenú de opciones de ayuda.

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                               usado para editar el mensaje actual.
    """
    idioma = context.user_data.get("idioma", "es")

    keyboard = [
        [
            InlineKeyboardButton(
                TranslatorService.traducir("❓ Preguntas frecuentes", idioma),
                callback_data="action_help_faq",
            )
        ],
        [
            InlineKeyboardButton(
                TranslatorService.traducir("🛠️ Soporte técnico", idioma),
                url="https://forms.gle/Fu9HuBVJA747nW9E8",
            )
        ],
        [
            InlineKeyboardButton(
                TranslatorService.traducir("📖 Guía de uso", idioma),
                url="https://docs.google.com/document/d/16ryO0SMthEtiy3AFTEKQJK7v4IODzlgunb8nVP7bI1Q/edit?usp=sharing",
            )
        ],
        [
            InlineKeyboardButton(
                TranslatorService.traducir("🔙 Volver al menú principal", idioma),
                callback_data="action_back_menu",
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg_ayuda = TranslatorService.traducir("Sección Ayuda. ¿Que necesitas?", idioma)
    await query.edit_message_text(text=msg_ayuda, reply_markup=reply_markup)


async def handle_action_faq(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reemplaza el submenú de opciones de ayuda por las preguntas frecuentes

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                               usado para editar el mensaje actual.
    """
    idioma = context.user_data.get("idioma", "es")

    questions = (
        "❓ *Preguntas Frecuentes*\n\n"
        "1️⃣ *¿Cómo cancelo una cita?*\n"
        "Ve a 'Mis citas' y pulsa anular.\n\n"
        "2️⃣ *¿Qué pasa si llego tarde?*\n"
        "Tienes 10 minutos de cortesía."
    )

    msg_questions = TranslatorService.traducir(questions, idioma)

    btn_volver = TranslatorService.traducir("Volver", idioma)
    keyboard = [[InlineKeyboardButton(btn_volver, callback_data="action_help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=msg_questions, reply_markup=reply_markup, parse_mode="Markdown"
    )
