from telegram.ext import ContextTypes

from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO, WELCOME_TEXT
from src.bot.telegram.keyboards import main_menu_keyboard


async def handle_toggle_audio_main(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activa o desactiva rápidamente el audio desde el menú principal."""
    current_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    if current_mode == MODO_AUDIO:
        context.user_data["pref_mode"] = MODO_TEXTO
        await query.answer(text="Audio desactivado 🔇")
    else:
        context.user_data["pref_mode"] = MODO_AUDIO
        await query.answer(text="Audio activado 🎤")

    new_mode = context.user_data["pref_mode"]

    await query.edit_message_text(
        text=WELCOME_TEXT,
        reply_markup=main_menu_keyboard(new_mode),
    )


async def handle_show_text_reserva(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botón de emergencia: Muestra el texto del audio en un popup."""
    texto = context.user_data.get(
        "last_reserva_text", "No hay detalles de reserva recientes."
    )
    await query.answer(text=texto, show_alert=True)
