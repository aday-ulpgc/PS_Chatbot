from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO


def main_menu_keyboard(current_mode: str = MODO_TEXTO) -> InlineKeyboardMarkup:
    """Devuelve los botones del menú principal."""
    audio_label = (
        "🎤 Audio activado" if current_mode == MODO_AUDIO else "🔇 Audio desactivado"
    )

    keyboard = [
        [InlineKeyboardButton(audio_label, callback_data="toggle_audio_main")],
        [InlineKeyboardButton("📅 Hacer una reserva", callback_data="action_reserve")],
        [InlineKeyboardButton("📋 Mis citas", callback_data="action_my_appointments")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="action_help")],
    ]
    return InlineKeyboardMarkup(keyboard)
