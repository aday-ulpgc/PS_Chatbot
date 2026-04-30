import os
from telegram.ext import ContextTypes

from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO, WELCOME_TEXT
from src.bot.telegram.keyboards import main_menu_keyboard
from src.services.voice_service import VoiceService


async def handle_toggle_audio_main(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activa o desactiva rápidamente el audio desde el menú principal."""
    current_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    if current_mode == MODO_AUDIO:
        context.user_data["pref_mode"] = MODO_TEXTO
        await query.answer(text="Audio desactivado 🔇")

        await query.edit_message_text(
            text=WELCOME_TEXT,
            reply_markup=main_menu_keyboard(MODO_TEXTO),
        )
    else:
        context.user_data["pref_mode"] = MODO_AUDIO
        await query.answer(text="Audio activado 🎤")

        await query.edit_message_text(
            text=WELCOME_TEXT,
            reply_markup=main_menu_keyboard(MODO_AUDIO),
        )

        try:
            texto_bienvenida_audio = (
                "Hola, soy Calia, tu asistente de reservas. "
                "El modo audio ha sido activado. "
                "Puedes hacer una reserva, consultar tus citas o pedir ayuda."
            )

            audio_path = await VoiceService.text_to_speech(texto_bienvenida_audio)

            with open(audio_path, "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=audio_file,
                    title="Bienvenida de Calia",
                )

            if os.path.exists(audio_path):
                os.remove(audio_path)

        except Exception as e:
            print(f"❌ Error al generar/enviar audio de activación: {e}")


async def handle_show_text_reserva(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botón de emergencia: Muestra el texto del audio en un popup."""
    texto = context.user_data.get(
        "last_reserva_text", "No hay detalles de reserva recientes."
    )
    await query.answer(text=texto, show_alert=True)

async def handle_eleccion_texto_libre(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja la elección de texto libre, mostrando un mensaje de confirmación."""
    await query.edit_message_text(
        text="Has elegido el modo Texto Libre. A partir de ahora, podrás escribir tus reservas en formato libre. ¡Prueba a escribir una reserva ahora! 📝",
    )
