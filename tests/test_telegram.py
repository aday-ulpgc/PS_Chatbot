import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.telegram_handler import start_command
from datetime import date


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
    print("cosas del reply\n")
    print(reply)
    assert "¡Hola! Soy tu asistente de reservas" in reply["text"]
    assert "reply_markup" in reply
    assert isinstance(reply["reply_markup"], InlineKeyboardMarkup)


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
