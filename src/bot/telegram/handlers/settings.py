from telegram.ext import ContextTypes
from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO
from src.bot.telegram.keyboards import settings_menu_keyboard


async def handle_action_settings(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_mode = context.user_data.get("pref_mode", MODO_TEXTO)
    await query.edit_message_text(
        text="⚙️ *Ajustes de Chat*\n¿Cómo prefieres que Calia confirme tus reservas?",
        reply_markup=settings_menu_keyboard(current_mode),
        parse_mode="Markdown",
    )


async def handle_set_mode_texto(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    if current_mode == MODO_TEXTO:
        await query.answer(text="Ya tienes seleccionado el Modo Texto 📝.")
        return
    context.user_data["pref_mode"] = MODO_TEXTO
    await handle_action_settings(query, context)


async def handle_set_mode_audio(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    if current_mode == MODO_AUDIO:
        await query.answer(text="Ya tienes seleccionado el Modo Audio 🎙️.")
        return
    context.user_data["pref_mode"] = MODO_AUDIO
    await handle_action_settings(query, context)


async def handle_show_text_reserva(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botón de emergencia: Muestra el texto del audio en un popup."""
    texto = context.user_data.get(
        "last_reserva_text", "No hay detalles de reserva recientes."
    )
    await query.answer(text=texto, show_alert=True)
