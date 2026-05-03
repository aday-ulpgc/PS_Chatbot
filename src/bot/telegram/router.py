from telegram import Update
from telegram.ext import ContextTypes

from src.bot.telegram.handlers.reserve import (
    handle_action_reserve,
    handle_action_my_appointments,
    handle_action_view_availability,
    handle_action_view_availability_day,
    handle_action_view_availability_week,
    handle_availability_calendar_selection,
    handle_prev_day,
    handle_next_day,
    handle_prev_week,
    handle_next_week,
    handle_prev_citas_group,
    handle_next_citas_group,
    handle_calendar_and_time,
    handle_alternative_time_selection_callback,
)

from src.bot.telegram.handlers.manage_appointments import (
    handle_action_my_appointments,
    handle_cancel_appointment,
    handle_action_cancel_menu,
    handle_action_modify_menu,
    handle_start_modify_calendar,
)

from src.bot.telegram.handlers.settings import (
    handle_toggle_audio_main,
    handle_eleccion_texto_libre,
    handle_eleccion_botones,
    handle_show_text_reserva,
    handle_show_settings,
    handle_toggle_modo_interaccion,
    handle_toggle_modo_respuesta,
)
from src.bot.telegram.handlers.nlp import handle_texto_libre
from src.bot.telegram.keyboards import MODO_BOTONES, MODO_NLP, main_menu_keyboard
from src.bot.telegram.handlers.help_menu import (
    handle_action_menu_help,
    handle_action_faq,
)
from src.bot.telegram.handlers.commands import handle_action_back_menu

CALLBACK_ROUTES = {
    # Menú principal
    "action_reserve": handle_action_reserve,
    "action_my_appointments": handle_action_my_appointments,
    "toggle_audio_main": handle_toggle_audio_main,
    "action_view_availability": handle_action_view_availability,
    "action_view_availability_day": handle_action_view_availability_day,
    "action_view_availability_week": handle_action_view_availability_week,
    "action_prev_day": handle_prev_day,
    "action_next_day": handle_next_day,
    "action_prev_week": handle_prev_week,
    "action_next_week": handle_next_week,
    "action_prev_citas_group": handle_prev_citas_group,
    "action_next_citas_group": handle_next_citas_group,
    "show_text_reserva": handle_show_text_reserva,
    "action_help": handle_action_menu_help,
    "action_help_faq": handle_action_faq,
    "action_back_menu": handle_action_back_menu,
    "action_back_main": handle_action_back_menu,
    "eleccion_botones": handle_eleccion_botones,
    "eleccion_texto_libre": handle_eleccion_texto_libre,
    "action_cancel_menu": handle_action_cancel_menu,
    "action_modify_menu": handle_action_modify_menu,
    # Ajustes
    "action_settings": handle_show_settings,
    "toggle_modo_interaccion": handle_toggle_modo_interaccion,
    "toggle_modo_respuesta": handle_toggle_modo_respuesta,
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

    # Manejar selección de hora alternativa
    if query.data.startswith("alt_time_"):
        await handle_alternative_time_selection_callback(query, context, update)
        return

    # Los botones de acción directa (menú, reiniciar, etc.) tienen prioridad
    # sobre el estado del calendario para que nunca queden bloqueados.
    if query.data in CALLBACK_ROUTES:
        function = CALLBACK_ROUTES[query.data]
        try:
            await function(query, context, update)
        except TypeError:
            await function(query, context)
        return

    # Manejar calendario de disponibilidad
    if context.user_data.get("availability_calendar"):
        await handle_availability_calendar_selection(query, context, update)
        return

    # Manejar calendario de reserva
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


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Intercepta mensajes de texto/voz y los enruta según el modo de interacción:
    - 'botones': recuerda al usuario que use el menú de botones.
    - 'nlp'    : delega directamente a handle_texto_libre.
    """
    modo = context.user_data.get("modo_interaccion", MODO_BOTONES)

    if modo == MODO_NLP:
        await handle_texto_libre(update, context)
    else:
        await update.message.reply_text(
            "Para interactuar conmigo usa el menú de botones\n"
            "Si prefieres escribir libremente, ve a ⚙️ *Ajustes* y activa el Modo IA.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
