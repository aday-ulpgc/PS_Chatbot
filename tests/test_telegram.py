
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, Message, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.telegram_handler import start_command


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
    
    mensaje,reply = update.message.reply_text.call_args

    assert "¡Hola! Soy tu asistente de reservas" in mensaje[0]
    assert "reply_markup" in reply
    assert isinstance(reply["reply_markup"], InlineKeyboardMarkup)

def test_2():
    assert True
