from telegram import Update
from telegram.ext import ContextTypes

from src.bot.telegram.handlers.reserve import (
    handle_action_reserve,
    handle_action_my_appointments,
    handle_calendar_and_time,
)
from src.bot.telegram.handlers.settings import (
    handle_toggle_audio_main,
    handle_action_settings,
    handle_eleccion_texto_libre,
    handle_set_mode_texto,
    handle_set_mode_audio,
    handle_show_text_reserva,
)
from src.bot.telegram.handlers.help_menu import (
    handle_action_menu_help,
    handle_action_faq,
)
from src.bot.telegram.handlers.commands import handle_action_back_menu

CALLBACK_ROUTES = {
    "action_reserve": handle_action_reserve,
    "action_my_appointments": handle_action_my_appointments,
    "toggle_audio_main": handle_toggle_audio_main,
    "show_text_reserva": handle_show_text_reserva,
    "action_help": handle_action_menu_help,
    "action_help_faq": handle_action_faq,
    "action_back_menu": handle_action_back_menu,
    "eleccion_botones": handle_action_back_menu,  # Reutilizamos el mismo handler para mostrar el menú principal
    "eleccion_texto_libre": handle_eleccion_texto_libre
}


async def menu_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Procesa los eventos de los botones del menú interactivo."""
    query = update.callback_query
    if query is None:
        return

    if query.data != "show_text_reserva":
        await query.answer()

    if await handle_calendar_and_time(query, context, update):
        return

    function = CALLBACK_ROUTES.get(query.data)
    if function:
        await function(query, context)
        return
    else:
        await query.edit_message_text(text="Acción no reconocida.")
