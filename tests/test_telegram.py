import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, InlineKeyboardMarkup
from telegram import CallbackQuery, Update, Message, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.telegram_handler import start_command
from datetime import date
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
    assert (
        "¡Hola! Soy tu asistente de reservas (SaaS-Bot del Grupo 06). ¿En qué te puedo ayudar hoy?"
        in reply["text"]
    )
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
    assert (
        reply["reply_markup"].inline_keyboard[3][0].text
        == "🔙 Volver al menú principal"
    )


@pytest.mark.asyncio
async def test_guardar_fecha_en_contexto():
    """Verifica que al elegir fecha, se guarda en la 'memoria' del bot."""
    from src.bot.telegram_handler import menu_callback_handler

    update = MagicMock()
    context = MagicMock()
    context.user_data = {}

    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = "cb_calendar_data"
    update.callback_query = query

    with patch(
        "src.bot.telegram_handler.DetailedTelegramCalendar.process"
    ) as mock_process, patch(
        "src.bot.telegram_handler.DetailedTelegramCalendar.func"
    ) as mock_func:
        mock_process.return_value = (date(2026, 6, 26), None, None)

        mock_func.return_value = lambda x: True

        await menu_callback_handler(update, context)

    assert context.user_data.get("fecha_seleccionada") == "2026-06-26"

    query.edit_message_text.assert_called_once()
    argumentos_nombrados = query.edit_message_text.call_args.kwargs
    texto_respuesta = argumentos_nombrados.get("text", "").lower()

    assert "selecciona una hora" in texto_respuesta


def test_2():
    assert True
