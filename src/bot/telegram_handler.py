"""Handlers de comandos para el bot de Telegram.

Este módulo contiene las funciones asíncronas que responden
a los comandos del usuario. Los handlers deben mantenerse
"tontos": sin lógica de negocio, solo interacción con el chat.
"""
import json
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

TEXTO_BIENVENIDA="¡Hola! Soy tu asistente de reservas (SaaS-Bot del Grupo 06). ¿En qué te puedo ayudar hoy?"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:    
    """Responde al comando /start con un mensaje de bienvenida y un menú interactivo.

    Args:
        update: Objeto con la información del mensaje entrante.
        context: Contexto del handler proporcionado por python-telegram-bot.
    """
    if update.message:
        await update.message.reply_text(
            text=TEXTO_BIENVENIDA,
            reply_markup=botones_principales()
        )

def botones_principales() -> InlineKeyboardMarkup:
    """Devuelve los botones del menú principal"""

    keyboard = [
        [InlineKeyboardButton("📅 Hacer una reserva", callback_data="action_reserve")],
        [InlineKeyboardButton("📋 Mis citas", callback_data="action_my_appointments")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="action_help")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

        await query.edit_message_text(
            text=f"✅ ¡Resumen de tu solicitud!\n📅 Fecha: {fecha_seleccionada}\n⏰ Hora: {hora_seleccionada}\n\n(Próximamente se enviará a Google Calendar...)")
        return
        

    if DetailedTelegramCalendar.func()(query):
        actual_calendar = DetailedTelegramCalendar(min_date=date.today())
        result, key, step = actual_calendar.process(query.data)
        
        if not result and key:
            teclado_dict = json.loads(key)
            btn_cancelar = [InlineKeyboardButton("❌ Cancelar / Volver", callback_data="action_cancel")]
            teclado_dict["inline_keyboard"].append(btn_cancelar)
            key_modificado = json.dumps(teclado_dict)
            
            await query.edit_message_text(text=f"Selecciona una fecha: {LSTEP[step]}", reply_markup=key_modificado)
        elif result:
            await query.edit_message_text(text=f"Fecha seleccionada: {result}")
        else:
            await volver_menu(query)

        return

    match query.data:
        case "action_reserve":
            actual_calendar = DetailedTelegramCalendar(min_date=date.today())
            calendar, step = actual_calendar.build()

            teclado_dict = json.loads(calendar)
            btn_cancelar = [InlineKeyboardButton("❌ Cancelar / Volver", callback_data="action_cancel")]
            teclado_dict["inline_keyboard"].append(btn_cancelar)
            key_modificado = json.dumps(teclado_dict)

            await query.edit_message_text(text=f"Selecciona una fecha: {LSTEP[step]}", reply_markup=key_modificado)
            return

        case "action_my_appointments":
            response_text = "Has seleccionado: 📋 Mis citas. (Funcionalidad en desarrollo)"
        case "action_help":
            await menu_ayuda(query)
            return
        case "help_faq":
            await questions(query)
            return
        case "menu_main":
            await volver_menu(query)
            return
        case _:
            response_text = "Acción no reconocida."

    await query.edit_message_text(text=response_text)


async def menu_ayuda(query) -> None:
    """Reemplaza el menú principal por el submenú de opciones de ayuda.

    Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón, 
                               usado para editar el mensaje actual.
    """
    keyboard = [
        [InlineKeyboardButton("❓ Preguntas frecuentes", callback_data="help_faq")],
        [InlineKeyboardButton("🛠️ Soporte técnico", url="https://forms.gle/Fu9HuBVJA747nW9E8")],
        [InlineKeyboardButton("📖 Guía de uso", url="https://docs.google.com/document/d/16ryO0SMthEtiy3AFTEKQJK7v4IODzlgunb8nVP7bI1Q/edit?usp=sharing")],
        [InlineKeyboardButton("🔙 Volver al menú principal", callback_data="menu_main")] 
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=f"Sección Ayuda. ¿Que necesitas?", reply_markup=reply_markup)

async def questions(query) -> None:
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
    await query.edit_message_text(text=questions, reply_markup=reply_markup,parse_mode="Markdown")

    
async def volver_menu(query) -> None:
    """Muestre el menu principal

     Args:
        query (CallbackQuery): El objeto del evento generado al pulsar el botón, 
                               usado para editar el mensaje actual.
    """
    await query.edit_message_text(
            text=TEXTO_BIENVENIDA,
            reply_markup=botones_principales()
        )


