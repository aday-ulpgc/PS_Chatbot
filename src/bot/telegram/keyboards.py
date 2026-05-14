from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO
from src.services.translator_service import TranslatorService

MODO_BOTONES = "botones"
MODO_NLP = "nlp"


def main_menu_keyboard(
    current_mode: str = MODO_TEXTO, idioma: str = "es"
) -> InlineKeyboardMarkup:
    """Devuelve los botones del menú principal."""
    audio_label = (
        "🎤 Audio activado" if current_mode == MODO_AUDIO else "🔇 Audio desactivado"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                TranslatorService.traducir("📅 Hacer una reserva", idioma),
                callback_data="action_reserve",
            )
        ],
        [
            InlineKeyboardButton(
                TranslatorService.traducir("📋 Mis citas", idioma),
                callback_data="action_my_appointments",
            )
        ],
        [
            InlineKeyboardButton(
                TranslatorService.traducir("❓ Ayuda", idioma),
                callback_data="action_help",
            ),
            InlineKeyboardButton(
                TranslatorService.traducir(audio_label, idioma),
                callback_data="toggle_audio_main",
            ),
        ],
        [
            InlineKeyboardButton(
                TranslatorService.traducir("⚙️ Ajustes", idioma),
                callback_data="action_settings",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def menu_eleccion(idioma: str = "es") -> InlineKeyboardMarkup:
    """Devuelve los botones para elegir entre botones o texto libre."""
    keyboard = [
        [
            InlineKeyboardButton(
                TranslatorService.traducir("📋 Cita mediante Botones", idioma),
                callback_data="eleccion_botones",
            )
        ],
        [
            InlineKeyboardButton(
                TranslatorService.traducir("📝 Cita mediante IA", idioma),
                callback_data="eleccion_texto_libre",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_menu_keyboard(
    modo_interaccion: str, modo_respuesta: str, idioma: str = "es"
) -> InlineKeyboardMarkup:
    """
    Devuelve el teclado del menú de ajustes con toggles dinámicos según el
    estado actual del usuario.
    """
    if modo_interaccion == MODO_BOTONES:
        lbl_interaccion = "🤖 Cambiar a Modo IA"
    else:
        lbl_interaccion = "📋 Cambiar a Modo Botones"

    btn_interaccion = InlineKeyboardButton(
        TranslatorService.traducir(lbl_interaccion, idioma),
        callback_data="toggle_modo_interaccion",
    )

    if modo_respuesta == MODO_AUDIO:
        lbl_respuesta = "🔇 Desactivar Audio"
    else:
        lbl_respuesta = "🎤 Activar Audio"

    btn_respuesta = InlineKeyboardButton(
        TranslatorService.traducir(lbl_respuesta, idioma),
        callback_data="toggle_modo_respuesta",
    )

    keyboard = [
        [btn_interaccion],
        [btn_respuesta],
        [
            InlineKeyboardButton(
                TranslatorService.traducir("🔙 Volver al Menú Principal", idioma),
                callback_data="action_back_main",
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)
