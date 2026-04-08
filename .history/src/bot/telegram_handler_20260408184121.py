"""Handlers de comandos para el bot de Telegram.

Este módulo contiene las funciones asíncronas que responden
a los comandos del usuario. Los handlers deben mantenerse
"tontos": sin lógica de negocio, solo interacción con el chat.
"""
import json
from datetime import date, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

# Importar servicios de BD
from services.database_service import obtener_o_crear_usuario_telegram, guardar_cita_en_db

TEXTO_BIENVENIDA = "¡Hola! Soy tu asistente de reservas (SaaS-Bot del Grupo 06). ¿En qué te puedo ayudar hoy?"



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

        # 🔐 GUARDAR CITA EN LA BASE DE DATOS
        telegram_id = update.effective_user.id  # ID único del usuario en Telegram
        nombre_usuario = update.effective_user.first_name

        # Asegurar que el usuario existe en BD
        obtener_o_crear_usuario_telegram(telegram_id, nombre_usuario)

        # Convertir fecha a datetime
        try:
            fecha_obj = datetime.strptime(fecha_seleccionada, "%Y-%m-%d")
        except:
            fecha_obj = datetime.now()

        # Guardar cita en DB
        exito = guardar_cita_en_db(
            telegram_id=telegram_id,
            fecha=fecha_obj,
            hora=hora_seleccionada,
            descripcion=f"Cita de {nombre_usuario}"
        )

        if exito:
            mensaje = f"✅ ¡Resumen de tu solicitud!\n📅 Fecha: {fecha_seleccionada}\n⏰ Hora: {hora_seleccionada}\n\n✔️ Cita guardada en tu perfil"
        else:
            mensaje = f"⚠️ La cita se confirmó pero hubo un problema al guardarla en el sistema"

        await query.edit_message_text(text=mensaje)
        return

    if DetailedTelegramCalendar.func()(query):
        actual_calendar = DetailedTelegramCalendar(min_date=date.today())
        result, key, step = actual_calendar.process(query.data)

        if not result and key:
            teclado_dict = json.loads(key)
            fila_navegacion = [
                {"text": "🔄 Reiniciar", "callback_data": "action_reserve"},
                {"text": "❌ Menú", "callback_data": "action_back_menu"}
            ]
            teclado_dict["inline_keyboard"].append(fila_navegacion)
            key_modificado = json.dumps(teclado_dict)

            await query.edit_message_text(text=f"Selecciona una fecha: {LSTEP[step]}", reply_markup=key_modificado)

        elif result:
            context.user_data["fecha_seleccionada"] = str(result)

            teclado_horas = [
                [
                    InlineKeyboardButton("10:00", callback_data="time_10:00"),
                    InlineKeyboardButton("11:00", callback_data="time_11:00")
                ],
                [
                    InlineKeyboardButton("16:00", callback_data="time_16:00"),
                    InlineKeyboardButton("17:00", callback_data="time_17:00")
                ],
                [
                    InlineKeyboardButton("🔄 Cambiar Fecha", callback_data="action_reserve"),
                    InlineKeyboardButton("❌ Menú", callback_data="action_back_menu")
                ]
            ]
            await query.edit_message_text(text=f"Fecha seleccionada: {result}\n⏰ Ahora, selecciona una hora:",
                                          reply_markup=InlineKeyboardMarkup(teclado_horas)
                                          )
        else:
            await handle_action_back_menu(query)

        return

    function = RUTAS_CALLBACKS.get(query.data)
    if function:
        await function(query)
        return
    else:
        await query.edit_message_text(text="Acción no reconocida.")