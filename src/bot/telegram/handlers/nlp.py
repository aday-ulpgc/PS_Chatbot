# src/bot/telegram/handlers/nlp.py
import base64
import asyncio
import os
from telegram import Update, constants
from telegram.ext import ContextTypes
from src.nlp.gemini_service import NLPService
from src.services import calendar_service
from src.services.voice_service import VoiceService
from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO
from src.bot.telegram.handlers.manage_appointments import (
    handle_action_cancel_menu,
    handle_action_modify_menu,
    handle_action_my_appointments,
)

TRABAJADORES = {"paco": "paco42538@gmail.com", "maría": "maria42538@gmail.com"}


async def keep_action_alive(bot, chat_id: int, action) -> None:
    """Mantiene activo un indicador de Telegram en bucle cada 4.5 s.
    Genérica: acepta cualquier ChatAction (TYPING, RECORD_VOICE, etc.).
    Diseñada para usarse con asyncio.create_task y cancelarse en un finally.
    """
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=action)
            await asyncio.sleep(4.5)
    except asyncio.CancelledError:
        pass  # Cancelación limpia esperada


async def handle_texto_libre(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    # UX: El indicador se enviará justo antes de la llamada a NLPService

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

    # UX: keep_action_alive mantiene el indicador activo durante toda la llamada a Gemini
    typing_task = asyncio.create_task(
        keep_action_alive(
            context.bot, update.effective_chat.id, constants.ChatAction.TYPING
        )
    )
    try:
        respuesta_agente = await NLPService.procesar_mensaje(
            context.user_data["historial"],
            datos_semanal=datos_semanal,
            audio_b64=audio_b64,
        )
    finally:
        typing_task.cancel()

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
        gmail_consulta = TRABAJADORES.get(nuevo_trabajador)

    # ── Acciones de control de preferencias (cortocircuito inmediato) ──────────
    if accion == "activar_audio":
        context.user_data["pref_mode"] = MODO_AUDIO
        context.user_data["modo_respuesta"] = MODO_AUDIO
        await update.message.reply_text(texto_respuesta)
        return

    elif accion == "desactivar_audio":
        context.user_data["pref_mode"] = MODO_TEXTO
        context.user_data["modo_respuesta"] = MODO_TEXTO
        await update.message.reply_text(texto_respuesta)
        return

    elif accion == "abrir_ajustes":
        from src.bot.telegram.keyboards import settings_menu_keyboard

        modo_interaccion = context.user_data.get("modo_interaccion", "botones")
        modo_respuesta = context.user_data.get("modo_respuesta", "texto")
        await update.message.reply_text(
            text="⚙️ *Ajustes*\n\nConfigura cómo quieres interactuar con Calia:",
            parse_mode="Markdown",
            reply_markup=settings_menu_keyboard(modo_interaccion, modo_respuesta),
        )
        return
    # ──────────────────────────────────────────────────────────────────────────

    # Verificamos si el usuario tiene activo el modo audio
    user_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    if estado == "recopilando":
        # Si el modo audio está activo, enviamos SOLO voz
        if user_mode == MODO_AUDIO:
            voice_task = asyncio.create_task(
                keep_action_alive(
                    context.bot,
                    update.effective_chat.id,
                    constants.ChatAction.RECORD_VOICE,
                )
            )
            try:
                audio_path = await VoiceService.text_to_speech(texto_respuesta)
                with open(audio_path, "rb") as audio_file:
                    await update.message.reply_voice(voice=audio_file)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                print(f"Error al generar audio en NLP (fallback texto): {e}")
                await update.message.reply_text(texto_respuesta)
            finally:
                voice_task.cancel()
        else:
            await update.message.reply_text(texto_respuesta)

    elif estado == "listo_para_reservar":
        mensaje_espera = await update.message.reply_text(
            f"{texto_respuesta}\n\n⏳ Procesando reserva en Google Calendar..."
        )

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
                voice_task = asyncio.create_task(
                    keep_action_alive(
                        context.bot,
                        update.effective_chat.id,
                        constants.ChatAction.RECORD_VOICE,
                    )
                )
                try:
                    audio_path = await VoiceService.text_to_speech(final_text)
                    with open(audio_path, "rb") as audio_file:
                        await update.message.reply_voice(voice=audio_file)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                    await mensaje_espera.delete()  # Borramos el texto para no duplicar
                except Exception as e:
                    print(f"Error al generar audio final en NLP (fallback texto): {e}")
                    await mensaje_espera.edit_text(final_text)
                finally:
                    voice_task.cancel()
            else:
                await mensaje_espera.edit_text(final_text)

        except Exception as e:
            print(f"Error al reservar: {e}")
            await mensaje_espera.edit_text(
                "❌ Hubo un fallo interno al conectar con el calendario. Por favor, inténtalo más tarde."
            )
            context.user_data["historial"].pop()

    elif accion == "consultar" and estado == "listo_para_consultar":
        if user_mode == MODO_AUDIO:
            voice_task = asyncio.create_task(
                keep_action_alive(
                    context.bot,
                    update.effective_chat.id,
                    constants.ChatAction.RECORD_VOICE,
                )
            )
            try:
                audio_path = await VoiceService.text_to_speech(texto_respuesta)
                with open(audio_path, "rb") as audio_file:
                    await update.message.reply_voice(voice=audio_file)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                print(f"Error al generar audio en consulta NLP (fallback texto): {e}")
                await update.message.reply_text(texto_respuesta)
            finally:
                voice_task.cancel()
        else:
            await update.message.reply_text(texto_respuesta)

        # Reutilizamos handle_action_my_appointments para mostrar la lista de citas
        await handle_action_my_appointments(None, context, update)

    elif accion == "cancelar" and estado == "listo_para_cancelar":
        if user_mode == MODO_AUDIO:
            voice_task = asyncio.create_task(
                keep_action_alive(
                    context.bot,
                    update.effective_chat.id,
                    constants.ChatAction.RECORD_VOICE,
                )
            )
            try:
                audio_path = await VoiceService.text_to_speech(texto_respuesta)
                with open(audio_path, "rb") as audio_file:
                    await update.message.reply_voice(voice=audio_file)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                print(f"Error al generar audio en cancelar NLP (fallback texto): {e}")
                await update.message.reply_text(texto_respuesta)
            finally:
                voice_task.cancel()
        else:
            await update.message.reply_text(texto_respuesta)

        await handle_action_cancel_menu(None, context, update)

    elif accion == "modificar" and estado == "listo_para_modificar":
        if user_mode == MODO_AUDIO:
            voice_task = asyncio.create_task(
                keep_action_alive(
                    context.bot,
                    update.effective_chat.id,
                    constants.ChatAction.RECORD_VOICE,
                )
            )
            try:
                audio_path = await VoiceService.text_to_speech(texto_respuesta)
                with open(audio_path, "rb") as audio_file:
                    await update.message.reply_voice(voice=audio_file)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                print(f"Error al generar audio en modificar NLP (fallback texto): {e}")
                await update.message.reply_text(texto_respuesta)
            finally:
                voice_task.cancel()
        else:
            await update.message.reply_text(texto_respuesta)

        await handle_action_modify_menu(None, context, update)
