from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO

MODO_BOTONES = "botones"
MODO_NLP = "nlp"


def main_menu_keyboard(current_mode: str = MODO_TEXTO) -> InlineKeyboardMarkup:
    """Devuelve los botones del menú principal."""
    audio_label = (
        "🎤 Audio activado" if current_mode == MODO_AUDIO else "🔇 Audio desactivado"
    )

    keyboard = [
        [InlineKeyboardButton("📅 Hacer una reserva", callback_data="action_reserve")],
        [InlineKeyboardButton("📋 Mis citas", callback_data="action_my_appointments")],
        [
            InlineKeyboardButton("❓ Ayuda", callback_data="action_help"),
            InlineKeyboardButton(audio_label, callback_data="toggle_audio_main"),
        ],
        [InlineKeyboardButton("⚙️ Ajustes", callback_data="action_settings")],
    ]
    return InlineKeyboardMarkup(keyboard)


def menu_eleccion() -> InlineKeyboardMarkup:
    """Devuelve los botones para elegir entre botones o texto libre."""
    keyboard = [
        [
            InlineKeyboardButton(
                "📋 Cita mediante Botones", callback_data="eleccion_botones"
            )
        ],
        [
            InlineKeyboardButton(
                "📝 Cita mediante IA", callback_data="eleccion_texto_libre"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_menu_keyboard(
    modo_interaccion: str, modo_respuesta: str
) -> InlineKeyboardMarkup:
    """
    Devuelve el teclado del menú de ajustes con toggles dinámicos según el
    estado actual del usuario.
    """
    # Toggle de modo de interacción
    if modo_interaccion == MODO_BOTONES:
        btn_interaccion = InlineKeyboardButton(
            "🤖 Cambiar a Modo IA", callback_data="toggle_modo_interaccion"
        )
    else:
        btn_interaccion = InlineKeyboardButton(
            "📋 Cambiar a Modo Botones", callback_data="toggle_modo_interaccion"
        )

    # Toggle de modo de respuesta (audio/texto)
    if modo_respuesta == MODO_AUDIO:
        btn_respuesta = InlineKeyboardButton(
            "🔇 Desactivar Audio", callback_data="toggle_modo_respuesta"
        )
    else:
        btn_respuesta = InlineKeyboardButton(
            "🎤 Activar Audio", callback_data="toggle_modo_respuesta"
        )

    keyboard = [
        [btn_interaccion],
        [btn_respuesta],
        [
            InlineKeyboardButton(
                "🔙 Volver al Menú Principal", callback_data="action_back_main"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
