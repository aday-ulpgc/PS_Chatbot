import asyncio
import os
import re
from datetime import datetime

from telegram import InlineKeyboardMarkup, Update, constants
from telegram.ext import ContextTypes

from src.bot.telegram.chat_actions import keep_action_alive
from src.bot.telegram.constants import MODO_AUDIO, MODO_TEXTO
from src.services.voice_service import VoiceService


MESES_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def formatear_fecha_para_voz(texto: str) -> str:
    """Convierte fechas YYYY-MM-DD a un formato más natural en español."""

    def reemplazo(match):
        fecha_str = match.group(0)
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        return f"{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}"

    return re.sub(r"\b\d{4}-\d{2}-\d{2}\b", reemplazo, texto)


def formatear_hora_para_voz(texto: str) -> str:
    """Convierte horas del estilo 16:00 a un formato más natural."""
    return (
        texto.replace("9:00", "9 en punto")
        .replace("10:00", "10 en punto")
        .replace("11:00", "11 en punto")
        .replace("12:00", "12 en punto")
        .replace("16:00", "4 de la tarde")
        .replace("17:00", "5 de la tarde")
        .replace("18:00", "6 de la tarde")
        .replace("19:00", "7 de la tarde")
    )


async def send_with_optional_audio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    texto: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Envía la respuesta. Si el modo audio está activo, intenta enviar solo voz (con botones).
    Si falla el audio o el modo es texto, envía el mensaje de texto tradicional.
    """
    user_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    # 1. Intentar enviar AUDIO si el modo está activo
    if user_mode == MODO_AUDIO:
        try:
            texto_para_audio = formatear_fecha_para_voz(texto)
            texto_para_audio = formatear_hora_para_voz(texto_para_audio)

            # UX: RECORD_VOICE se mantiene activo durante toda la llamada a ElevenLabs
            voice_task = asyncio.create_task(
                keep_action_alive(
                    context.bot,
                    update.effective_chat.id,
                    constants.ChatAction.RECORD_VOICE,
                )
            )
            try:
                audio_path = await VoiceService.text_to_speech(texto_para_audio)
            finally:
                voice_task.cancel()

            with open(audio_path, "rb") as audio_file:
                # Enviamos como VOICE y adjuntamos el reply_markup
                await context.bot.send_voice(
                    chat_id=update.effective_chat.id,
                    voice=audio_file,
                    reply_markup=reply_markup,
                )

            if os.path.exists(audio_path):
                os.remove(audio_path)

            # Si el envío de voz fue exitoso, terminamos para no duplicar con texto
            return

        except Exception as e:
            print(f"❌ Error al generar/enviar audio (usando fallback de texto): {e}")

    # 2. MODO TEXTO o FALLBACK por error en audio
    if update.callback_query:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texto,
            reply_markup=reply_markup,
        )
    elif update.message:
        await update.message.reply_text(
            text=texto,
            reply_markup=reply_markup,
        )


async def _send_or_edit(query, update, text, reply_markup=None, parse_mode=None):
    """Envía o edita según si venimos de un callback (query) o de un mensaje NLP directo."""
    if query is not None:
        await query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode=parse_mode
        )
    else:
        await update.message.reply_text(
            text=text, reply_markup=reply_markup, parse_mode=parse_mode
        )
