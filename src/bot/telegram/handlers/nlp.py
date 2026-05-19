# src/bot/telegram/handlers/nlp.py
import base64
import asyncio
import os
from typing import Optional

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

# ── Estado de sesiones Web (in-memory) ───────────────────────────────────────
# Clave: user_id (str), Valor: dict con "historial", "pref_mode", "trabajador_actual"
WEB_SESSIONS: dict[str, dict] = {}

# ── Referencia al bot PTB para compartir sesiones con usuarios de Telegram ────
_ptb_app = None


def set_ptb_app(app) -> None:
    """Registra la instancia PTB para que los usuarios web identificados via Telegram
    compartan el mismo estado de sesión que al usar el bot directamente."""
    global _ptb_app
    _ptb_app = app


def _get_user_data(user_id: str, es_web: bool, context=None) -> dict:
    """Devuelve el diccionario de datos de usuario correcto según la plataforma.

    Para usuarios web autenticados con Telegram (user_id = 'tg_NNNNN'), reutiliza
    el user_data de PTB para que la sesión sea la misma que en el bot.
    """
    if es_web:
        # Usuario identificado via Telegram Login Widget → sesión compartida con el bot
        if user_id.startswith("tg_") and _ptb_app is not None:
            try:
                tg_numeric_id = int(user_id[3:])
                return _ptb_app.user_data[tg_numeric_id]
            except (ValueError, AttributeError):
                pass
        # Visitante anónimo → sesión in-memory exclusiva de la web
        if user_id not in WEB_SESSIONS:
            WEB_SESSIONS[user_id] = {}
        return WEB_SESSIONS[user_id]
    return context.user_data


# ── Helpers de respuesta (solo Telegram) ─────────────────────────────────────

async def _reply_to_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE, texto_respuesta: str
):
    """Envía la respuesta como audio o texto según las preferencias del usuario (Telegram)."""
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


# ── Handlers de intención (solo Telegram) ────────────────────────────────────

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


# ── Núcleo universal de procesamiento ────────────────────────────────────────

async def procesar_flujo_completo(
    user_id: str,
    texto: str,
    es_web: bool = False,
    update: Optional[Update] = None,
    context: Optional[ContextTypes.DEFAULT_TYPE] = None,
    user_name: str = "",
) -> dict:
    """Núcleo agnóstico del chatbot. Procesa un mensaje y devuelve el dict de respuesta.

    Funciona tanto desde Telegram (es_web=False) como desde la API REST (es_web=True).
    Cuando es_web=True, no accede a ningún objeto de Telegram (update/context).

    Args:
        user_id:    Identificador único del usuario (telegram_id str o UUID web).
        texto:      Texto del mensaje del usuario.
        es_web:     True si la petición viene de la API web.
        update:     Objeto Update de Telegram (None si es_web=True).
        context:    ContextTypes de Telegram (None si es_web=True).
        user_name:  Nombre del usuario (solo se usa en el flujo web para Telegram Login).

    Returns:
        El dict completo de respuesta del agente (respuesta_agente).
    """
    user_data = _get_user_data(user_id, es_web, context)

    # ── Contexto de disponibilidad semanal ────────────────────────────────────
    nombre_trabajador_sesion = user_data.get("trabajador_actual")
    gmail_consulta = (
        TRABAJADORES.get(nombre_trabajador_sesion) if nombre_trabajador_sesion else None
    )

    datos_semanal = await asyncio.to_thread(
        calendar_service.get_weekly_availability, 7, gmail_consulta
    )

    # ── Historial ─────────────────────────────────────────────────────────────
    if "historial" not in user_data:
        user_data["historial"] = []

    user_data["historial"].append({"rol": "usuario", "texto": texto})

    if len(user_data["historial"]) > 10:
        user_data["historial"] = user_data["historial"][-10:]

    # ── Llamada al LLM ────────────────────────────────────────────────────────
    if not es_web:
        async with send_action_while_thinking(
            context.bot, update.effective_chat.id, constants.ChatAction.TYPING
        ):
            respuesta_agente = await NLPService.procesar_mensaje(
                user_data["historial"],
                datos_semanal=datos_semanal,
            )
    else:
        respuesta_agente = await NLPService.procesar_mensaje(
            user_data["historial"],
            datos_semanal=datos_semanal,
        )

    # ── Actualizar historial con la respuesta ─────────────────────────────────
    texto_respuesta = respuesta_agente.get(
        "respuesta_usuario", "Ha habido un error de comunicación."
    )
    user_data["historial"].append({"rol": "asistente", "texto": texto_respuesta})

    estado = respuesta_agente.get("estado")
    accion = respuesta_agente.get("accion")
    datos = respuesta_agente.get("datos_extraidos", {})

    # ── Actualizar trabajador en sesión ───────────────────────────────────────
    nuevo_trabajador = datos.get("nombre_trabajador")
    if nuevo_trabajador:
        user_data["trabajador_actual"] = nuevo_trabajador.lower()

    # ── Dispatch de intenciones (solo Telegram) ───────────────────────────────
    if not es_web:
        # Vista semanal con imagen
        if (
            accion == "consultar_disponibilidad_semana"
            and estado == "listo_para_consultar_disponibilidad_semana"
        ):
            await _reply_to_user(update, context, texto_respuesta)

            try:
                from src.services.visualization_service import (
                    generar_imagen_disponibilidad_semana,
                )
                from datetime import datetime

                fecha_iso = datos.get("fecha_inicio_iso") or datos.get("fecha_iso")
                if fecha_iso:
                    fecha_inicio = datetime.fromisoformat(fecha_iso)
                    img_path = await asyncio.to_thread(
                        generar_imagen_disponibilidad_semana,
                        update.effective_user.id,
                        fecha_inicio,
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
            await _reply_to_user(update, context, texto_respuesta)

    # ── Dispatch web: reserva real ────────────────────────────────────────────
    if es_web and accion == "reservar" and estado == "listo_para_reservar":
        nombre_ia = datos.get("nombre_trabajador") or ""
        gmail_trabajador = TRABAJADORES.get(nombre_ia.lower())
        # Formato de nombre igual que en Telegram: "Nombre (ID)"
        # El nombre se obtiene de la BD (autoritativo) igual que el bot usa
        # update.effective_user.full_name — no depende del cliente web.
        if user_id.startswith("tg_"):
            tg_numeric_id = user_id[3:]
            try:
                from src.BBDD.database_service import obtener_o_crear_usuario_telegram
                db_result = await asyncio.to_thread(
                    obtener_o_crear_usuario_telegram,
                    int(tg_numeric_id),
                    user_name or None,
                )
                nombre_db = db_result.get("nombre") or user_name or f"Usuario Web"
            except Exception as e:
                print(f"[WARN] No se pudo obtener nombre desde DB: {e}")
                nombre_db = user_name or f"Usuario Web"
            nombre_reserva = f"{nombre_db} ({tg_numeric_id})"
        else:
            nombre_reserva = user_id
        try:
            resultado = await asyncio.to_thread(
                calendar_service.create_reservation,
                nombre_reserva,
                datos.get("fecha_iso"),
                datos.get("hora"),
                gmail_trabajador,
            )
            if resultado.startswith("❌"):
                respuesta_agente["respuesta_usuario"] = (
                    resultado + "\n\n¿Quieres probar con otro día u otra hora?"
                )
                user_data["historial"].pop()
            else:
                respuesta_agente["respuesta_usuario"] = f"✅ ¡Todo listo!\n{resultado}"
                user_data["historial"] = []
        except Exception as e:
            print(f"Error al reservar (web): {e}")
            respuesta_agente["respuesta_usuario"] = (
                "❌ Fallo interno al conectar con el calendario. Inténtalo más tarde."
            )
            user_data["historial"].pop()

    # ── Dispatch web: ajustes (audio) ─────────────────────────────────────────
    if es_web and accion in ["activar_audio", "desactivar_audio"]:
        if accion == "activar_audio":
            user_data["pref_mode"] = MODO_AUDIO
        else:
            user_data["pref_mode"] = MODO_TEXTO

    # ── Audio web ─────────────────────────────────────────────────────────────
    audio_url = None
    if es_web and user_data.get("pref_mode") == MODO_AUDIO:
        import uuid
        import os as _os

        _static_dir = "static"
        _os.makedirs(_static_dir, exist_ok=True)
        try:
            audio_path = await VoiceService.text_to_speech(
                respuesta_agente.get("respuesta_usuario", "")
            )
            audio_filename = f"calia_{uuid.uuid4().hex}.mp3"
            dest = _os.path.join(_static_dir, audio_filename)
            _os.rename(audio_path, dest)
            # URL absoluta para el cliente web
            audio_url = f"http://localhost:8000/static/{audio_filename}"
        except Exception as e:
            print(f"Error al generar audio web: {e}")

    respuesta_agente["audio_url"] = audio_url

    # ── Devolver siempre el dict completo (útil para la API web) ─────────────
    return respuesta_agente


# ── Adaptador Telegram ────────────────────────────────────────────────────────

async def handle_texto_libre(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler de Telegram. Thin adapter sobre procesar_flujo_completo."""
    texto_usuario = ""
    audio_b64 = None

    if update.message.voice:
        voice_file = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        texto_usuario = "[El usuario ha enviado una nota de voz. Escúchala para extraer la intención]"
    else:
        texto_usuario = update.message.text

    user_id = str(update.effective_user.id)
    await procesar_flujo_completo(
        user_id=user_id,
        texto=texto_usuario,
        es_web=False,
        update=update,
        context=context,
    )
