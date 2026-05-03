import os
from telegram.ext import ContextTypes
from src.bot.telegram.handlers.commands import handle_action_back_menu

from src.bot.telegram.constants import MODO_TEXTO, MODO_AUDIO, WELCOME_TEXT
from src.bot.telegram.keyboards import (
    main_menu_keyboard,
    settings_menu_keyboard,
    MODO_BOTONES,
    MODO_NLP,
)
from src.services.voice_service import VoiceService


async def handle_toggle_audio_main(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activa o desactiva rápidamente el audio desde el menú principal."""
    current_mode = context.user_data.get("pref_mode", MODO_TEXTO)

    if current_mode == MODO_AUDIO:
        context.user_data["pref_mode"] = MODO_TEXTO
        context.user_data["modo_respuesta"] = MODO_TEXTO
        await query.answer(text="Audio desactivado 🔇")

        await query.edit_message_text(
            text=WELCOME_TEXT,
            reply_markup=main_menu_keyboard(MODO_TEXTO),
        )
    else:
        context.user_data["pref_mode"] = MODO_AUDIO
        context.user_data["modo_respuesta"] = MODO_AUDIO
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


async def handle_eleccion_texto_libre(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Maneja la elección de texto libre, mostrando un mensaje de confirmación."""
    context.user_data["modo_interaccion"] = MODO_NLP
    await query.edit_message_text(
        text="Has elegido el modo Texto Libre. A partir de ahora, podrás escribir tus reservas en formato libre. ¡Prueba a escribir una reserva ahora! 📝",
    )


async def handle_eleccion_botones(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Establece el modo interacción a botones y vuelve al menú principal."""
    context.user_data["modo_interaccion"] = MODO_BOTONES
    await handle_action_back_menu(query, context)


async def handle_show_settings(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el menú de ajustes con los toggles dinámicos actuales del usuario."""
    modo_interaccion = context.user_data.get("modo_interaccion", MODO_BOTONES)
    modo_respuesta = context.user_data.get("modo_respuesta", MODO_TEXTO)
    await query.edit_message_text(
        text="⚙️ *Ajustes*\n\nConfigura cómo quieres interactuar con Calia:",
        parse_mode="Markdown",
        reply_markup=settings_menu_keyboard(modo_interaccion, modo_respuesta),
    )


async def handle_toggle_modo_interaccion(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Alterna entre el modo Botones y el modo NLP, actualizando el teclado al instante."""
    # TODO: Persistir este estado en MySQL usando la conexión MCP (Model Context Protocol).
    modo_actual = context.user_data.get("modo_interaccion", MODO_BOTONES)

    if modo_actual == MODO_BOTONES:
        context.user_data["modo_interaccion"] = MODO_NLP
        await query.answer(text="Modo NLP activado 🤖")
    else:
        context.user_data["modo_interaccion"] = MODO_BOTONES
        await query.answer(text="Modo Botones activado 📋")

    modo_respuesta = context.user_data.get("modo_respuesta", MODO_TEXTO)
    await query.edit_message_reply_markup(
        reply_markup=settings_menu_keyboard(
            context.user_data["modo_interaccion"], modo_respuesta
        )
    )


async def handle_toggle_modo_respuesta(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Alterna entre respuesta en texto y audio, actualizando el teclado al instante."""
    # TODO: Persistir este estado en MySQL usando la conexión MCP (Model Context Protocol).
    modo_actual = context.user_data.get("modo_respuesta", MODO_TEXTO)

    if modo_actual == MODO_AUDIO:
        context.user_data["modo_respuesta"] = MODO_TEXTO
        context.user_data["pref_mode"] = MODO_TEXTO
        await query.answer(text="Audio desactivado 🔇")
    else:
        context.user_data["modo_respuesta"] = MODO_AUDIO
        context.user_data["pref_mode"] = MODO_AUDIO
        await query.answer(text="Audio activado 🎤")

    modo_interaccion = context.user_data.get("modo_interaccion", MODO_BOTONES)
    await query.edit_message_reply_markup(
        reply_markup=settings_menu_keyboard(
            modo_interaccion, context.user_data["modo_respuesta"]
        )
    )
