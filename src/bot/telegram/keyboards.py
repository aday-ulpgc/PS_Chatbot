from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Devuelve los botones del menú principal"""
    keyboard = [
        [InlineKeyboardButton("📅 Hacer una reserva", callback_data="action_reserve")],
        [InlineKeyboardButton("📋 Mis citas", callback_data="action_my_appointments")],
        [InlineKeyboardButton("⚙️ Ajustes de Chat", callback_data="action_settings")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="action_help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_menu_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    """Devuelve los botones del menú de configuración"""
    label_texto = f"{'✅ ' if current_mode == MODO_TEXTO else ''}Modo Texto 📝"
    label_audio = f"{'✅ ' if current_mode == MODO_AUDIO else ''}Modo Audio 🎙️"

    keyboard = [
        [InlineKeyboardButton(label_texto, callback_data="set_mode_texto")],
        [InlineKeyboardButton(label_audio, callback_data="set_mode_audio")],
        [InlineKeyboardButton("🔙 Volver", callback_data="action_back_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_eleccion() -> InlineKeyboardMarkup:
    """Devuelve los botones para elegir entre botones o texto libre"""
    keyboard = [
        [InlineKeyboardButton("📋 Botones", callback_data="eleccion_botones")],
        [InlineKeyboardButton("📝 Texto Libre", callback_data="eleccion_texto_libre")],
    ]
    return InlineKeyboardMarkup(keyboard)
