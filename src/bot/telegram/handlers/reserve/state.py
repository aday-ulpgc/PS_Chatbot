from telegram.ext import ContextTypes


def limpiar_estado_reserva(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Elimina todas las claves volátiles de user_data relacionadas con el flujo
    de reserva. Llamar al inicio de cada nueva reserva para evitar fugas de estado.
    """
    claves_a_limpiar = [
        "reserve_photo_message_id",
        "reserve_photo_message_ids",
        "reserve_photo_generating",
        "last_reserva_text",
        "citas_bloques",
        "citas_bloque_actual",
        "day_photo_message_id",
        "week_photo_message_id",
        "day_photo_generating",
        "week_photo_generating",
        "current_day_date",
        "current_week_date",
        "availability_calendar",
        "modifying_id",
    ]
    for clave in claves_a_limpiar:
        context.user_data.pop(clave, None)
