# src/bot/telegram/handlers/nlp.py
import base64
import asyncio
import os
from telegram import Update, constants
from telegram.ext import ContextTypes
from src.bot.telegram.chat_actions import send_action_while_thinking
from src.nlp.gemini_service import NLPService
from src.services import calendar_service
from src.services.voice_service import VoiceService
from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO, TRABAJADORES
from src.bot.telegram.handlers.manage_appointments import (
    handle_action_cancel_menu,
    handle_action_modify_menu,
    handle_action_my_appointments,
)


async def _reply_to_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE, texto_respuesta: str
):
    """Envía la respuesta como audio o texto según las preferencias del usuario."""
    user_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    if user_mode == MODO_AUDIO:
        async with send_action_while_thinking(
            context.bot, update.effective_chat.id, constants.ChatAction.RECORD_VOICE
        ):
            try:
                audio_path = await VoiceService.text_to_speech(texto_respuesta)
                with open(audio_path, "rb") as audio_file:
                    await update.message.reply_voice(voice=audio_file)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                print(f"Error al generar audio (fallback texto): {e}")
                await update.message.reply_text(texto_respuesta)
    else:
        await update.message.reply_text(texto_respuesta)


async def _handle_settings_intent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    agente: dict,
    texto_respuesta: str,
):
    accion = agente.get("accion")
    if accion == "activar_audio":
        context.user_data["pref_mode"] = MODO_AUDIO
        context.user_data["modo_respuesta"] = MODO_AUDIO
        await _reply_to_user(update, context, texto_respuesta)
    elif accion == "desactivar_audio":
        context.user_data["pref_mode"] = MODO_TEXTO
        context.user_data["modo_respuesta"] = MODO_TEXTO
        await _reply_to_user(update, context, texto_respuesta)
    elif accion == "abrir_ajustes":
        from src.bot.telegram.keyboards import settings_menu_keyboard

        modo_interaccion = context.user_data.get("modo_interaccion", "botones")
        modo_respuesta = context.user_data.get("modo_respuesta", "texto")
        await update.message.reply_text(
            text="⚙️ *Ajustes*\n\nConfigura cómo quieres interactuar con Calia:",
            parse_mode="Markdown",
            reply_markup=settings_menu_keyboard(modo_interaccion, modo_respuesta),
        )


async def _handle_booking_intent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    agente: dict,
    texto_respuesta: str,
):
    estado = agente.get("estado")
    if estado != "listo_para_reservar":
        await _reply_to_user(update, context, texto_respuesta)
        return

    user_mode = context.user_data.get("pref_mode", MODO_TEXTO)
    mensaje_espera = await update.message.reply_text(
        f"{texto_respuesta}\n\n⏳ Procesando reserva en Google Calendar..."
    )

    datos = agente.get("datos_extraidos", {})
    fecha = datos.get("fecha_iso")
    hora = datos.get("hora")
    nombre_id = f"{update.effective_user.full_name} ({update.effective_user.id})"
    nombre_ia = datos.get("nombre_trabajador") or ""
    gmail_trabajador = TRABAJADORES.get(nombre_ia.lower())

    try:
        resultado = await asyncio.to_thread(
            calendar_service.create_reservation,
            nombre_id,
            fecha,
            hora,
            gmail_trabajador,
        )

        final_text = ""
        if resultado.startswith("❌"):
            final_text = f"{resultado}\n\n¿Quieres probar con otro día u otra hora?"
            context.user_data["historial"].pop()
        else:
            final_text = f"✅ ¡Todo listo!\n{resultado}"
            context.user_data["historial"] = []

        if user_mode == MODO_AUDIO:
            await mensaje_espera.edit_text("🎙️ Generando audio de confirmación...")
            async with send_action_while_thinking(
                context.bot, update.effective_chat.id, constants.ChatAction.RECORD_VOICE
            ):
                try:
                    audio_path = await VoiceService.text_to_speech(final_text)
                    with open(audio_path, "rb") as audio_file:
                        await update.message.reply_voice(voice=audio_file)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                    await mensaje_espera.delete()
                except Exception as e:
                    print(f"Error al generar audio final en NLP (fallback texto): {e}")
                    await mensaje_espera.edit_text(final_text)
        else:
            await mensaje_espera.edit_text(final_text)

    except Exception as e:
        print(f"Error al reservar: {e}")
        await mensaje_espera.edit_text(
            "❌ Hubo un fallo interno al conectar con el calendario. Por favor, inténtalo más tarde."
        )
        context.user_data["historial"].pop()


async def _handle_availability_intent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    agente: dict,
    texto_respuesta: str,
):
    if agente.get("estado") == "listo_para_consultar_disponibilidad":
        await _reply_to_user(update, context, texto_respuesta)
    else:
        await _reply_to_user(update, context, texto_respuesta)


async def _handle_appointments_intent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    agente: dict,
    texto_respuesta: str,
):
    if agente.get("estado") == "listo_para_consultar_citas":
        await _reply_to_user(update, context, texto_respuesta)
        await handle_action_my_appointments(None, context, update=update)
    else:
        await _reply_to_user(update, context, texto_respuesta)


async def _handle_cancel_intent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    agente: dict,
    texto_respuesta: str,
):
    if agente.get("estado") == "listo_para_cancelar":
        await _reply_to_user(update, context, texto_respuesta)
        await handle_action_cancel_menu(None, context, update)
    else:
        await _reply_to_user(update, context, texto_respuesta)


async def _handle_modify_intent(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    agente: dict,
    texto_respuesta: str,
):
    if agente.get("estado") == "listo_para_modificar":
        await _reply_to_user(update, context, texto_respuesta)
        await handle_action_modify_menu(None, context, update)
    else:
        await _reply_to_user(update, context, texto_respuesta)


INTENT_HANDLERS = {
    "activar_audio": _handle_settings_intent,
    "desactivar_audio": _handle_settings_intent,
    "abrir_ajustes": _handle_settings_intent,
    "reservar": _handle_booking_intent,
    "consultar_disponibilidad": _handle_availability_intent,
    "consultar_citas": _handle_appointments_intent,
    "cancelar": _handle_cancel_intent,
    "modificar": _handle_modify_intent,
}


async def handle_texto_libre(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    nombre_trabajador_sesion = context.user_data.get("trabajador_actual")
    gmail_consulta = (
        TRABAJADORES.get(nombre_trabajador_sesion) if nombre_trabajador_sesion else None
    )

    datos_semanal = await asyncio.to_thread(
        calendar_service.get_weekly_availability, 7, gmail_consulta
    )
    texto_usuario = ""
    audio_b64 = None

    if update.message.voice:
        voice_file = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        texto_usuario = "[El usuario ha enviado una nota de voz. Escúchala para extraer la intención]"
    else:
        texto_usuario = update.message.text

    if "historial" not in context.user_data:
        context.user_data["historial"] = []

    context.user_data["historial"].append({"rol": "usuario", "texto": texto_usuario})

    if len(context.user_data["historial"]) > 10:
        context.user_data["historial"] = context.user_data["historial"][-10:]

    # UX: send_action_while_thinking mantiene el indicador activo durante toda la llamada a Gemini
    async with send_action_while_thinking(
        context.bot, update.effective_chat.id, constants.ChatAction.TYPING
    ):
        respuesta_agente = await NLPService.procesar_mensaje(
            context.user_data["historial"],
            datos_semanal=datos_semanal,
            audio_b64=audio_b64,
        )

    texto_respuesta = respuesta_agente.get(
        "respuesta_usuario", "Ha habido un error de comunicación."
    )
    context.user_data["historial"].append(
        {"rol": "asistente", "texto": texto_respuesta}
    )

    estado = respuesta_agente.get("estado")
    accion = respuesta_agente.get("accion")
    datos = respuesta_agente.get("datos_extraidos", {})

    nuevo_trabajador = datos.get("nombre_trabajador")
    if nuevo_trabajador:
        nuevo_trabajador = nuevo_trabajador.lower()
        context.user_data["trabajador_actual"] = nuevo_trabajador

    if (
        accion == "consultar_disponibilidad_semana"
        and estado == "listo_para_consultar_disponibilidad_semana"
    ):
        # Enviar respuesta en modo voz o texto
        await _reply_to_user(update, context, texto_respuesta)

        # Enviar imagen de disponibilidad semanal si hay datos suficientes
        try:
            from src.services.visualization_service import (
                generar_imagen_disponibilidad_semana,
            )

            user_id = update.effective_user.id
            from datetime import datetime

            # Buscar la fecha de inicio en los datos extraídos
            fecha_iso = datos.get("fecha_inicio_iso") or datos.get("fecha_iso")
            if fecha_iso:
                fecha_inicio = datetime.fromisoformat(fecha_iso)
                img_path = await asyncio.to_thread(
                    generar_imagen_disponibilidad_semana, user_id, fecha_inicio
                )
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as img_file:
                        await update.message.reply_photo(photo=img_file)
        except Exception as e:
            print(f"Error al generar imagen de disponibilidad semanal: {e}")

    handler = INTENT_HANDLERS.get(accion)

    if accion in ["activar_audio", "desactivar_audio", "abrir_ajustes"]:
        await handler(update, context, respuesta_agente, texto_respuesta)
    elif estado == "recopilando" or accion == "desconocida":
        await _reply_to_user(update, context, texto_respuesta)
    elif handler:
        await handler(update, context, respuesta_agente, texto_respuesta)
    else:
        # Fallback
        await _reply_to_user(update, context, texto_respuesta)
