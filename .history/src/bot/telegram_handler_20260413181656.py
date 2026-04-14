"""Handlers de comandos para el bot de Telegram.

Este módulo contiene las funciones asíncronas que responden
a los comandos del usuario. Los handlers deben mantenerse
"tontos": sin lógica de negocio, solo interacción con el chat.
"""

import json
import asyncio
from src.services import calendar_service
from datetime import date, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar
from telegram.error import BadRequest

# Importar servicios de BD
from services.database_service import obtener_o_crear_usuario_telegram, guardar_cita_en_db

WELCOME_TEXT = "¡Hola! Soy tu asistente de reservas (SaaS-Bot del Grupo 06).\n¿En qué te puedo ayudar hoy?"
WELCOME_TEXT = (
    "¡Hola! Soy Calia, tu asistente de reservas.\n¿En qué te puedo ayudar hoy?"
)

CALENDAR_STEPS = {
    "y": "(año)",
    "m": "(mes)",
    "d": "(día)",
}



async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /start con un mensaje de bienvenida y un menú interactivo.

    Args:
        update: Objeto con la información del mensaje entrante.
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    if update.message:
        await update.message.reply_text(
            text=WELCOME_TEXT, reply_markup=main_menu_keyboard()
        )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Devuelve los botones del menú principal"""

    keyboard = [
        [InlineKeyboardButton("📅 Hacer una reserva", callback_data="action_reserve")],
        [InlineKeyboardButton("📋 Mis citas", callback_data="action_my_appointments")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="action_help")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def enviar_recordatorio_cita(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Esta función es la que el bot ejecuta cuando pasan los 2 segundos."""

    job = context.job

    try:
        await context.bot.send_message(
            chat_id=job.chat_id, text=f"⏰ PRUEBA\n{job.data}"
        )
    except Exception as e:
        print(f"❌ Error al enviar el mensaje: {e}")


async def menu_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Procesa los eventos de los botones del menú interactivo.

    Args:
        update: Objeto con la información del evento (CallbackQuery).
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    if query.data.startswith("time_"):
        selected_time = query.data.split("_")[1]
        selected_data = context.user_data.get("selected_data", "Desconocida")




        if selected_data == "Desconocida":
            await query.edit_message_text(
                "❌ Error: No se ha encontrado la fecha. Inténtalo de nuevo."
            )
            return

        # 🔐 GUARDAR CITA EN LA BASE DE DATOS
        telegram_id = update.effective_user.id
        nombre_usuario = update.effective_user.first_name

        # Asegurar que el usuario existe en BD
        obtener_o_crear_usuario_telegram(telegram_id, nombre_usuario)

        # Convertir fecha a datetime
        try:
            fecha_obj = datetime.strptime(selected_data, "%Y-%m-%d")
        except:
            fecha_obj = datetime.now()

        # Guardar cita en BD
        exito = guardar_cita_en_db(
            telegram_id=telegram_id,
            fecha=fecha_obj,
            hora=selected_time,
            descripcion=f"Cita de {nombre_usuario}"
        )

        if exito:
            mensaje = f"✅ ¡Resumen de tu solicitud!\n📅 Fecha: {selected_data}\n⏰ Hora: {selected_time}\n\n✔️ Cita guardada en tu perfil"
        else:
            mensaje = f"⚠️ La cita se confirmó pero hubo un problema al guardarla en el sistema"

        await query.edit_message_text(text=mensaje, reply_markup=main_menu_keyboard())





        if selected_data == "Desconocida":
            await query.edit_message_text(
                "❌ Error: No se ha encontrado la fecha. Inténtalo de nuevo."
            )
            return

        await query.edit_message_text(
            text=f"✅ ¡Resumen de tu solicitud!\n📅 Fecha: {selected_data}\n⏰ Hora: {selected_time}\n\n⏳ Procesando reserva en Google Calendar..."
        )

        name_and_id = f"{update.effective_user.full_name} ({update.effective_user.id})"

        response_message = await asyncio.to_thread(
            calendar_service.create_reservation,
            name_and_id,
            selected_data,
            selected_time,
        )

        if response_message.startswith("❌"):
            error_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↻ Elegir otro día", callback_data="action_reserve"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⫶☰ Menú Principal", callback_data="action_back_menu"
                        )
                    ],
                ]
            )
            await query.edit_message_text(
                text=response_message, reply_markup=error_keyboard
            )
        else:
            await query.edit_message_text(
                text=response_message, reply_markup=main_menu_keyboard()
            )

            context.job_queue.run_once(
                enviar_recordatorio_cita,
                when=2,
                chat_id=update.effective_chat.id,
                data=f"Cita el {selected_data} a las {selected_time}",
                name=f"remind_{update.effective_chat.id}",
            )





        return

    if DetailedTelegramCalendar.func()(query):
        current_calendar = DetailedTelegramCalendar(min_date=date.today())
        result, key, step = current_calendar.process(query.data)

        if not result and key:
            keyboard_dict = json.loads(key)
            # Convertir diccionario a lista de listas de botones
            keyboard_buttons = [[InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]) 
                                 for btn in row] for row in keyboard_dict.get("inline_keyboard", [])]
            
            # Añadir botones de navegación
            fila_navegacion = [
                InlineKeyboardButton("↻ Reiniciar", callback_data="action_reserve"),
                InlineKeyboardButton("⫶☰ Menú", callback_data="action_back_menu")
            ]
            keyboard_buttons.append(fila_navegacion)
            navigation_row = [
                {"text": "↻ Reiniciar", "callback_data": "action_reserve"},
                {"text": "⫶☰ Menú", "callback_data": "action_back_menu"},
            ]
            keyboard_dict["inline_keyboard"].append(navigation_row)
            modified_key = json.dumps(keyboard_dict)

            try:
                await query.edit_message_text(
                    text=f"Selecciona una fecha {CALENDAR_STEPS[step]}:",
                    reply_markup=InlineKeyboardMarkup(keyboard_buttons),
                    reply_markup=modified_key,
                )
            except BadRequest:
                pass

        elif result:
            context.user_data["selected_data"] = str(result)

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
            buttons = []
            row = []

            for h in available_hours:
                hour_int = int(h.split(":")[0])
                if is_today and hour_int <= now.hour:
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
                        "↻ Cambiar Fecha", callback_data="action_reserve"
                    ),
                    InlineKeyboardButton("⫶☰ Menú", callback_data="action_back_menu"),
                ]
            )

            text_hour = f"Fecha seleccionada: {result}\n⏰ Ahora, selecciona una hora:"
            if is_today and not buttons[:-1]:
                text_hour = f"❌ Lo siento, ya no quedan huecos disponibles para hoy ({result})."
                reply_markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "↻ Elegir otro día", callback_data="action_reserve"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⫶☰ Menú Principal", callback_data="action_back_menu"
                            )
                        ],
                    ]
                )
            else:
                reply_markup = InlineKeyboardMarkup(buttons)

            await query.edit_message_text(text=text_hour, reply_markup=reply_markup)

        else:
            await handle_action_back_menu(query)

        return

    function = CALLBACK_ROUTES.get(query.data)
    if function:
        await function(query)
        return
    else:
        await query.edit_message_text(text="Acción no reconocida.")


async def handle_action_reserve(query) -> None:
    """Inicia el proceso de reserva mostrando un calendario para seleccionar la fecha.

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                               usado para editar el mensaje actual.
    """
    current_calendar = DetailedTelegramCalendar(min_date=date.today())
    calendar, step = current_calendar.build()

    keyboard_dict = json.loads(calendar)
    navigation_row = [
        {"text": "↻ Reiniciar", "callback_data": "action_reserve"},
        {"text": "⫶☰ Menú", "callback_data": "action_back_menu"},
    ]
    keyboard_dict["inline_keyboard"].append(navigation_row)
    modified_calendar = json.dumps(keyboard_dict)

    try:
        # Convertir diccionario a lista de listas de botones
        keyboard_buttons = [[InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]) 
                             for btn in row] for row in keyboard_dict.get("inline_keyboard", [])]
        
        await query.edit_message_text(
            text=f"Selecciona una fecha {CALENDAR_STEPS[step]}:",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
        await query.edit_message_text(
            text=f"Selecciona una fecha {CALENDAR_STEPS[step]}:",
            reply_markup=modified_calendar,
        )
    except BadRequest:
        pass


async def handle_action_my_appointments(query) -> None:
    """Muestra un mensaje de que la funcionalidad de 'Mis citas' está en desarrollo.

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                               usado para editar el mensaje actual.
    """
    questions = (
        " *Mis citas*\n\n"
        "1️⃣ *20/03/2023* Fisio Juan\n"
        "2️⃣ *21/03/2023* Fisio Daniel\n"
        "3️⃣ *3/04/2023* Fisio Juan\n"
        "4️⃣ *4/04/2023* Fisio Daniel\n"
    )

    keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=questions, reply_markup=reply_markup, parse_mode="Markdown"
    )


async def handle_action_menu_help(query) -> None:
    """Reemplaza el menú principal por el submenú de opciones de ayuda.

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                               usado para editar el mensaje actual.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "❓ Preguntas frecuentes", callback_data="action_help_faq"
            )
        ],
        [
            InlineKeyboardButton(
                "🛠️ Soporte técnico", url="https://forms.gle/Fu9HuBVJA747nW9E8"
            )
        ],
        [
            InlineKeyboardButton(
                "📖 Guía de uso",
                url="https://docs.google.com/document/d/16ryO0SMthEtiy3AFTEKQJK7v4IODzlgunb8nVP7bI1Q/edit?usp=sharing",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Volver al menú principal", callback_data="action_back_menu"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Sección Ayuda. ¿Que necesitas?", reply_markup=reply_markup
    )


async def handle_action_faq(query) -> None:
    """Reemplaza el submenú de opciones de ayuda por las preguntas frecuentes

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                               usado para editar el mensaje actual.
    """
    questions = (
        "❓ *Preguntas Frecuentes*\n\n"
        "1️⃣ *¿Cómo cancelo una cita?*\n"
        "Ve a 'Mis citas' y pulsa anular.\n\n"
        "2️⃣ *¿Qué pasa si llego tarde?*\n"
        "Tienes 10 minutos de cortesía."
    )

    keyboard = [[InlineKeyboardButton("Volver", callback_data="action_help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=questions, reply_markup=reply_markup, parse_mode="Markdown"
    )


async def handle_action_back_menu(query) -> None:
    """Muestra el menu principal

    Args:
       query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                              usado para editar el mensaje actual.
    """
    await query.edit_message_text(text=WELCOME_TEXT, reply_markup=main_menu_keyboard())


CALLBACK_ROUTES = {
    "action_reserve": handle_action_reserve,
    "action_my_appointments": handle_action_my_appointments,
    "action_help": handle_action_menu_help,
    "action_help_faq": handle_action_faq,
    "action_back_menu": handle_action_back_menu,
}
