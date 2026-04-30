from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO


def main_menu_keyboard(current_mode: str = MODO_TEXTO) -> InlineKeyboardMarkup:
    """Devuelve los botones del menú principal con exactamente 4 filas."""
    audio_label = (
        "🎤 Audio activado" if current_mode == MODO_AUDIO else "🔇 Audio desactivado"
    )

    keyboard = [
        [InlineKeyboardButton("📅 Hacer una reserva", callback_data="action_reserve")],
        [InlineKeyboardButton("📋 Mis citas", callback_data="action_my_appointments")],
        [InlineKeyboardButton("⚙️ Ajustes de Chat", callback_data="action_settings")],
        [
            InlineKeyboardButton("❓ Ayuda", callback_data="action_help"),
            InlineKeyboardButton(audio_label, callback_data="toggle_audio_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_eleccion() -> InlineKeyboardMarkup:
    """Devuelve los botones para elegir entre botones o texto libre"""
    keyboard = [
        [InlineKeyboardButton("📋 Botones", callback_data="eleccion_botones")],
        [InlineKeyboardButton("📝 Texto Libre", callback_data="eleccion_texto_libre")],
    ]
    return InlineKeyboardMarkup(keyboard)
