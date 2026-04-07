import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import CallbackQuery, Update, Message, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.telegram_handler import handle_action_menu_help, start_command


def test_sprint_zero_environment():
    """Verifica que el entorno de testing de pytest funciona en CI/CD."""
    assert True


@pytest.mark.asyncio
async def test_start():
    update = MagicMock(spec=Update)

    update.message = AsyncMock(spec=Message)

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await start_command(update, context)

    update.message.reply_text.assert_called_once()

    reply = update.message.reply_text.call_args.kwargs
    print("Reply:", reply)
    print("CNODSNONDC")
    print(reply)
    assert "¡Hola! Soy tu asistente de reservas (SaaS-Bot del Grupo 06). ¿En qué te puedo ayudar hoy?" in reply["text"]
    assert "reply_markup" in reply
    assert isinstance(reply["reply_markup"], InlineKeyboardMarkup)
    assert len(reply["reply_markup"].inline_keyboard) == 3
    assert reply["reply_markup"].inline_keyboard[0][0].text == "📅 Hacer una reserva"
    assert reply["reply_markup"].inline_keyboard[1][0].text == "📋 Mis citas"
    assert reply["reply_markup"].inline_keyboard[2][0].text == "❓ Ayuda"


@pytest.mark.asyncio
async def test_handle_action_menu_help():
    query = AsyncMock(spec=CallbackQuery)
    query.data = "action_help"
    await handle_action_menu_help(query)
    query.edit_message_text.assert_called_once()
    reply = query.edit_message_text.call_args.kwargs
    print("Reply:", reply)
    assert "Sección Ayuda. ¿Que necesitas?" in reply["text"]
    assert reply["reply_markup"].inline_keyboard[0][0].text == "❓ Preguntas frecuentes"
    assert reply["reply_markup"].inline_keyboard[1][0].text == "🛠️ Soporte técnico"
    assert reply["reply_markup"].inline_keyboard[2][0].text == "📖 Guía de uso"
    assert reply["reply_markup"].inline_keyboard[3][0].text == "🔙 Volver al menú principal"

    
