"""Handlers de comandos para el bot de Telegram.

Este módulo contiene las funciones asíncronas que responden
a los comandos del usuario. Los handlers deben mantenerse
"tontos": sin lógica de negocio, solo interacción con el chat.
"""

import json
import asyncio
from services import calendar_service
from datetime import date, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

TEXTO_BIENVENIDA = "¡Hola! Soy tu asistente de reservas (SaaS-Bot del Grupo 06). ¿En qué te puedo ayudar hoy?"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /start con un mensaje de bienvenida y un menú interactivo.

    Args:
        update: Objeto con la información del mensaje entrante.
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    if update.message:
        await update.message.reply_text(
            text=TEXTO_BIENVENIDA, reply_markup=botones_principales()
        )


def botones_principales() -> InlineKeyboardMarkup:
    """Devuelve los botones del menú principal"""

    keyboard = [
        [InlineKeyboardButton("📅 Hacer una reserva", callback_data="action_reserve")],
        [InlineKeyboardButton("📋 Mis citas", callback_data="action_my_appointments")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="action_help")],
    ]
    return InlineKeyboardMarkup(keyboard)


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
        hora_seleccionada = query.data.split("_")[1]
        fecha_seleccionada = context.user_data.get("fecha_seleccionada", "Desconocida")

        if fecha_seleccionada == "Desconocida":
            await query.edit_message_text("❌ Error: No se ha encontrado la fecha. Inténtalo de nuevo.")
            return

        await query.edit_message_text(
            text=f"✅ ¡Resumen de tu solicitud!\n📅 Fecha: {fecha_seleccionada}\n⏰ Hora: {hora_seleccionada}\n\n⏳ Procesando reserva en Google Calendar..."
        )

        nombre_y_id = f"{update.effective_user.full_name} ({update.effective_user.id})"

        mensaje_respuesta = await asyncio.to_thread(
            calendar_service.crear_reserva,
            nombre_y_id,
            fecha_seleccionada,
            hora_seleccionada
        )

        if mensaje_respuesta.startswith("❌"):
            teclado_error = InlineKeyboardMarkup([
                [InlineKeyboardButton("↻ Elegir otro día", callback_data="action_reserve")],
                [InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")]
            ])
            await query.edit_message_text(
                text=mensaje_respuesta, 
                reply_markup=teclado_error
            )
        else:
            await query.edit_message_text(
                text=mensaje_respuesta,
                reply_markup=botones_principales()
            )

        return

    if DetailedTelegramCalendar.func()(query):
        actual_calendar = DetailedTelegramCalendar(min_date=date.today())
        result, key, step = actual_calendar.process(query.data)

        if not result and key:
            teclado_dict = json.loads(key)
            fila_navegacion = [
                {"text": "↻ Reiniciar", "callback_data": "action_reserve"},
                {"text": "⫶☰ Menú", "callback_data": "action_back_menu"},
            ]
            teclado_dict["inline_keyboard"].append(fila_navegacion)
            key_modificado = json.dumps(teclado_dict)

            await query.edit_message_text(
                text=f"Selecciona una fecha: {LSTEP[step]}", reply_markup=key_modificado
            )

        elif result:
            context.user_data["fecha_seleccionada"] = str(result)
            
            ahora = datetime.now()
            es_hoy = (result == date.today())

            horas_disponibles = ["10:00", "11:00", "16:00", "17:00"]
            botones = []
            fila = []

            for h in horas_disponibles:
                hora_int = int(h.split(":")[0])
                if es_hoy and hora_int <= ahora.hour:
                    continue
                
                fila.append(InlineKeyboardButton(h, callback_data=f"time_{h}"))
                if len(fila) == 2:
                    botones.append(fila)
                    fila = []
            
            if fila: 
                botones.append(fila) 

            botones.append([
                InlineKeyboardButton("↻ Cambiar Fecha", callback_data="action_reserve"),
                InlineKeyboardButton("⫶☰ Menú", callback_data="action_back_menu")
            ])

            texto_hora = f"Fecha seleccionada: {result}\n⏰ Ahora, selecciona una hora:"
            if es_hoy and not botones[:-1]:
                texto_hora = f"❌ Lo siento, ya no quedan huecos disponibles para hoy ({result})."
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("↻ Elegir otro día", callback_data="action_reserve")],
                    [InlineKeyboardButton("⫶☰ Menú Principal", callback_data="action_back_menu")]
                ])
            else:
                reply_markup = InlineKeyboardMarkup(botones)

            await query.edit_message_text(text=texto_hora, reply_markup=reply_markup)

        else:
            await handle_action_back_menu(query)

        return

    function = RUTAS_CALLBACKS.get(query.data)
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
    actual_calendar = DetailedTelegramCalendar(min_date=date.today())
    calendar, step = actual_calendar.build()

    teclado_dict = json.loads(calendar)
    fila_navegacion = [
        {"text": "↻ Reiniciar", "callback_data": "action_reserve"},
        {"text": "⫶☰ Menú", "callback_data": "action_back_menu"},
    ]
    teclado_dict["inline_keyboard"].append(fila_navegacion)
    calendar_modificado = json.dumps(teclado_dict)

    await query.edit_message_text(
        text=f"Selecciona una fecha: {LSTEP[step]}", reply_markup=calendar_modificado
    )


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
    """Muestre el menu principal

    Args:
       query (CallbackQuery): El objeto del evento generado al pulsar el botón,
                              usado para editar el mensaje actual.
    """
    await query.edit_message_text(
        text=TEXTO_BIENVENIDA, reply_markup=botones_principales()
    )


RUTAS_CALLBACKS = {
    "action_reserve": handle_action_reserve,
    "action_my_appointments": handle_action_my_appointments,
    "action_help": handle_action_menu_help,
    "action_help_faq": handle_action_faq,
    "action_back_menu": handle_action_back_menu,
}
