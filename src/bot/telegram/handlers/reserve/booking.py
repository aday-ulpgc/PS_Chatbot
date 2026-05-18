import asyncio
import json
from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar

from src.BBDD.database_service import (
    actualizar_cita_fecha_db,
    obtener_horas_ocupadas,
    obtener_info_cita_db,
    obtener_o_crear_cliente_por_telegram,
    obtener_empleados_activos,
)
from src.bot.telegram.constants import CALENDAR_STEPS, MODO_AUDIO, MODO_TEXTO
from src.bot.telegram.handlers.commands import handle_action_back_menu
from src.bot.telegram.keyboards import main_menu_keyboard
from src.services import calendar_service
from src.services.translator_service import TranslatorService

from .alternatives import handle_alternative_time_selection, parse_alternative_times
from .utils import send_with_optional_audio, limpiar_estado_reserva


async def enviar_recordatorio_cita(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Esta función es la que el bot ejecuta cuando pasan los 2 segundos."""
    job = context.job
    try:
        reminder_message_id = context.user_data.get("reminder_message_id")
        message_text = f"⏰ PRUEBA\n{job.data}"

        if reminder_message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=reminder_message_id,
                    text=message_text,
                )
            except Exception as edit_error:
                print(f"⚠️ No se pudo editar el recordatorio anterior: {edit_error}")
                # Si no se puede editar, enviar uno nuevo
                msg = await context.bot.send_message(
                    chat_id=job.chat_id, text=message_text
                )
                context.user_data["reminder_message_id"] = msg.message_id
        else:
            msg = await context.bot.send_message(chat_id=job.chat_id, text=message_text)
            context.user_data["reminder_message_id"] = msg.message_id
    except Exception as e:
        print(f"❌ Error al enviar el mensaje: {e}")


async def handle_select_employee(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra los empleados disponibles para que el usuario seleccione uno."""
    try:
        # Obtener empleados activos
        empleados = await asyncio.to_thread(obtener_empleados_activos)
        
        if not empleados:
            await query.edit_message_text(
                "❌ Lo siento, no hay empleados disponibles en este momento."
            )
            return
        
        # Crear botones para cada empleado
        keyboard = []
        for emp in empleados:
            btn = InlineKeyboardButton(
                text=f"👤 {emp['NOMBRE']} ({emp['EMAIL']})",
                callback_data=f"select_emp_{emp['ID_EMPLEADO']}"
            )
            keyboard.append([btn])
        
        # Agregar botón para volver
        keyboard.append([
            InlineKeyboardButton("🔙 Volver", callback_data="action_back_menu")
        ])
        
        await query.edit_message_text(
            text="👤 *Selecciona con cuál empleado deseas agendar tu cita:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"❌ Error en handle_select_employee: {e}")
        await query.edit_message_text("❌ Error al cargar los empleados")


async def handle_calendar_and_time(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
) -> bool:
    """Maneja la selección de fecha y hora del calendario."""
    idioma = context.user_data.get("idioma", "es")

    if query.data.startswith("time_"):
        selected_time = query.data.split("_")[1]
        selected_data = context.user_data.get("selected_data", "Desconocida")

        if selected_data == "Desconocida":
            msg = TranslatorService.traducir(
                "❌ Error: No se ha encontrado la fecha. Inténtalo de nuevo.", idioma
            )
            await query.edit_message_text(msg)
            return True

        modifying_id = context.user_data.get("modifying_id")

        if modifying_id:
            await query.answer()
            msg = TranslatorService.traducir(
                "⏳ Modificando tu reserva en Google Calendar...", idioma
            )
            await query.edit_message_text(text=msg)

            cita_antigua = await asyncio.to_thread(obtener_info_cita_db, modifying_id)
            name_and_id = (
                f"{update.effective_user.full_name} ({update.effective_user.id})"
            )

            if cita_antigua:
                old_fecha = cita_antigua["FECHA"].strftime("%Y-%m-%d")
                old_hora = cita_antigua["FECHA"].strftime("%H:%M")
                await asyncio.to_thread(
                    calendar_service.delete_reservation,
                    name_and_id,
                    old_fecha,
                    old_hora,
                    True,
                )

            await asyncio.to_thread(
                calendar_service.create_reservation,
                name_and_id,
                selected_data,
                selected_time,
                None,
                True,
            )

            fecha_dt = datetime.strptime(selected_data, "%Y-%m-%d")
            hora_parts = selected_time.split(":")
            fecha_dt_con_hora = fecha_dt.replace(
                hour=int(hora_parts[0]),
                minute=int(hora_parts[1]) if len(hora_parts) > 1 else 0,
            )

            await asyncio.to_thread(
                actualizar_cita_fecha_db, modifying_id, fecha_dt_con_hora
            )
            context.user_data.pop("modifying_id", None)

            msg = TranslatorService.traducir(
                "✅ Cita modificada con éxito. Actualizando agenda...", idioma
            )
            await query.edit_message_text(msg)

            from src.bot.telegram.handlers.manage_appointments import (
                handle_action_my_appointments,
            )

            await handle_action_my_appointments(query, context)

            return True

        texto_resumen = (
            f"✅ ¡Resumen de tu solicitud!\n"
            f"📅 Fecha: {selected_data}\n"
            f"⏰ Hora: {selected_time}\n\n"
            f"⏳ Procesando reserva en Google Calendar..."
        )
        msg_resumen = TranslatorService.traducir(texto_resumen, idioma)
        await query.edit_message_text(text=msg_resumen)

        telegram_id = update.effective_user.id
        user_info = await asyncio.to_thread(
            obtener_o_crear_cliente_por_telegram,
            telegram_id,
            update.effective_user.full_name,
        )

        if user_info.get("error"):
            error_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            TranslatorService.traducir("↻ Elegir otro día", idioma),
                            callback_data="action_reserve",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            TranslatorService.traducir("⫶☰ Menú Principal", idioma),
                            callback_data="action_back_menu",
                        )
                    ],
                ]
            )
            msg_error = TranslatorService.traducir(
                "❌ Error al obtener tus datos de usuario", idioma
            )
            await query.edit_message_text(
                text=msg_error,
                reply_markup=error_keyboard,
            )
            return True

        response_message = await calendar_service.create_reservation_via_api(
            telegram_id=telegram_id,
            date=selected_data,
            hour=selected_time,
            nombre=update.effective_user.full_name,
            id_empleado=selected_emp_id,
        )

        if response_message.startswith("❌"):
            if "Otras fechas cercanas" in response_message:
                alternatives = parse_alternative_times(response_message)

                if alternatives and len(alternatives) >= 1:
                    # Mostrar opciones de horas alternativas
                    await handle_alternative_time_selection(
                        query, context, update, alternatives, selected_data
                    )
                    return True

            error_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            TranslatorService.traducir("↻ Elegir otro día", idioma),
                            callback_data="action_reserve",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            TranslatorService.traducir("⫶☰ Menú Principal", idioma),
                            callback_data="action_back_menu",
                        )
                    ],
                ]
            )
            msg_error_api = TranslatorService.traducir(response_message, idioma)
            await query.edit_message_text(
                text=msg_error_api,
                reply_markup=error_keyboard,
            )
        else:
            user_mode = context.user_data.get("pref_mode", MODO_TEXTO)

            response_traducida = TranslatorService.traducir(response_message, idioma)
            context.user_data["last_reserva_text"] = response_traducida

            reserve_photo_id = context.user_data.get("reserve_photo_message_id")
            if reserve_photo_id:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id, message_id=reserve_photo_id
                    )
                    context.user_data["reserve_photo_message_id"] = None
                except Exception as e:
                    print(f"⚠️ Error al borrar imagen de reserva: {e}")

            if user_mode == MODO_AUDIO:
                msg_audio = TranslatorService.traducir(
                    "🎙️ Generando audio de confirmación...", idioma
                )
                await query.edit_message_text(msg_audio)

            await query.delete_message()

            await send_with_optional_audio(
                update,
                context,
                response_traducida,
                reply_markup=main_menu_keyboard(current_mode=user_mode, idioma=idioma),
            )

        return True

    if DetailedTelegramCalendar.func()(query):
        current_calendar = DetailedTelegramCalendar(min_date=date.today())
        result, key, step = current_calendar.process(query.data)

        if not result and key:
            keyboard_dict = json.loads(key)
            keyboard_buttons = [
                [
                    InlineKeyboardButton(
                        text=btn["text"],
                        callback_data=btn["callback_data"],
                    )
                    for btn in row
                ]
                for row in keyboard_dict.get("inline_keyboard", [])
            ]
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        TranslatorService.traducir("↻ Reiniciar", idioma),
                        callback_data="action_reserve",
                    ),
                    InlineKeyboardButton(
                        TranslatorService.traducir("⫶☰ Menú", idioma),
                        callback_data="action_back_menu",
                    ),
                ]
            )

            try:
                texto_step = f"Selecciona una fecha {CALENDAR_STEPS[step]}:"
                msg_step = TranslatorService.traducir(texto_step, idioma)
                await query.edit_message_text(
                    text=msg_step,
                    reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                )
            except BadRequest:
                pass

        elif result:
            context.user_data["selected_data"] = str(result)

            telegram_id = query.from_user.id
            await asyncio.to_thread(
                obtener_o_crear_cliente_por_telegram,
                telegram_id,
                query.from_user.first_name,
            )

            now = datetime.now()
            is_today = result == date.today()

            available_hours = [
                "9:00",
                "10:00",
                "11:00",
                "12:00",
                "16:00",
                "17:00",
                "18:00",
                "19:00",
            ]

            horas_ocupadas = await asyncio.to_thread(
                obtener_horas_ocupadas, str(result)
            )

            buttons = []
            row = []

            for h in available_hours:
                hour_int = int(h.split(":")[0])

                if is_today and hour_int <= now.hour:
                    continue

                if h in horas_ocupadas:
                    continue

                row.append(InlineKeyboardButton(h, callback_data=f"time_{h}"))

                if len(row) == 2:
                    buttons.append(row)
                    row = []

            if row:
                buttons.append(row)

            buttons.append(
                [
                    InlineKeyboardButton(
                        TranslatorService.traducir("↻ Cambiar Fecha", idioma),
                        callback_data="action_reserve",
                    ),
                    InlineKeyboardButton(
                        TranslatorService.traducir("⫶☰ Menú", idioma),
                        callback_data="action_back_menu",
                    ),
                ]
            )

            if not buttons[:-1]:
                texto_hora = (
                    f"❌ Lo siento, ya no quedan huecos libres para el día ({result})."
                )
                reply_markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                TranslatorService.traducir("↻ Elegir otro día", idioma),
                                callback_data="action_reserve",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                TranslatorService.traducir("⫶☰ Menú Principal", idioma),
                                callback_data="action_back_menu",
                            )
                        ],
                    ]
                )
            else:
                texto_hora = (
                    f"Fecha seleccionada: {result}\n⏰ Ahora, selecciona una hora:"
                )
                reply_markup = InlineKeyboardMarkup(buttons)

            msg_hora = TranslatorService.traducir(texto_hora, idioma)
            await query.edit_message_text(text=msg_hora, reply_markup=reply_markup)

        else:
            await handle_action_back_menu(query, context)

        return True

    return False


async def handle_action_reserve(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    idioma = context.user_data.get("idioma", "es")

    limpiar_estado_reserva(context)

    current_calendar = DetailedTelegramCalendar(min_date=date.today())
    calendar, step = current_calendar.build()

    keyboard_dict = json.loads(calendar)
    navigation_row = [
        {
            "text": TranslatorService.traducir("↻ Reiniciar", idioma),
            "callback_data": "action_reserve",
        },
        {
            "text": TranslatorService.traducir("⫶☰ Menú", idioma),
            "callback_data": "action_back_menu",
        },
    ]

    availability_row = [
        {
            "text": TranslatorService.traducir("📅 Ver disponibilidad", idioma),
            "callback_data": "action_view_availability",
        }
    ]

    keyboard_dict["inline_keyboard"].append(availability_row)
    keyboard_dict["inline_keyboard"].append(navigation_row)

    try:
        keyboard_buttons = [
            [
                InlineKeyboardButton(
                    text=btn["text"],
                    callback_data=btn["callback_data"],
                )
                for btn in row
            ]
            for row in keyboard_dict.get("inline_keyboard", [])
        ]
        texto_step = f"Selecciona una fecha {CALENDAR_STEPS[step]}:"
        msg_step = TranslatorService.traducir(texto_step, idioma)

        await query.edit_message_text(
            text=msg_step,
            reply_markup=InlineKeyboardMarkup(keyboard_buttons),
        )
    except BadRequest:
        pass


async def handle_action_reserve(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia el flujo de reserva: primero selecciona empleado, luego calendario."""
    # Limpiamos cualquier estado residual de flujos anteriores
    limpiar_estado_reserva(context)
    
    # Mostrar selector de empleados
    await handle_select_employee(query, context)
