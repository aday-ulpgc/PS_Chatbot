from telegram import Update
from telegram.ext import ContextTypes

from src.bot.telegram.handlers.reserve import (
    handle_action_reserve,
    handle_calendar_and_time,
)

from src.bot.telegram.handlers.manage_appointments import (
    handle_action_my_appointments,
    handle_cancel_appointment,
    handle_action_cancel_menu,
    handle_action_modify_menu,
    handle_start_modify_calendar,
)

from src.bot.telegram.handlers.settings import (
    handle_action_settings,
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
    "action_settings": handle_action_settings,
    "set_mode_texto": handle_set_mode_texto,
    "set_mode_audio": handle_set_mode_audio,
    "show_text_reserva": handle_show_text_reserva,
    "action_help": handle_action_menu_help,
    "action_help_faq": handle_action_faq,
    "action_back_menu": handle_action_back_menu,
    "action_cancel_menu": handle_action_cancel_menu,
    "action_modify_menu": handle_action_modify_menu,
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

    if query.data.startswith("cancelcita_"):
        await handle_cancel_appointment(query, context)
        return

    elif query.data.startswith("modcita_"):
        await handle_start_modify_calendar(query, context)
        return

    function = CALLBACK_ROUTES.get(query.data)
    if function:
        await function(query, context)
        return
    else:
        await query.edit_message_text(text="Acción no reconocida.")
