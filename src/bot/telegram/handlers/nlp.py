# src/bot/telegram/handlers/nlp.py
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from src.nlp.gemini_service import NLPService
from src.services import calendar_service

async def handle_texto_libre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texto_usuario = update.message.text
    
    # 1. Indicador de "Escribiendo..."
    await update.message.chat.send_action(action="typing")
    
    disponibilidad_semanal = await asyncio.to_thread(calendar_service.get_weekly_availability, 7)

    # 2. Gestionar la memoria (Historial)
    if "historial" not in context.user_data:
        context.user_data["historial"] = []
    
    context.user_data["historial"].append({"rol": "usuario", "texto": texto_usuario})
    
    # Mantenemos solo los últimos 10 mensajes para no saturar el token limit
    if len(context.user_data["historial"]) > 10:
        context.user_data["historial"] = context.user_data["historial"][-10:]
    
    # 3. Procesar con la IA
    respuesta_agente = await NLPService.procesar_mensaje(context.user_data["historial"],
                                                         datos_semanal=disponibilidad_semanal)
    
    # 4. Guardar lo que dijo la IA en la memoria
    texto_respuesta = respuesta_agente.get("respuesta_usuario", "Ha habido un error de comunicación.")
    context.user_data["historial"].append({"rol": "asistente", "texto": texto_respuesta})
    
    # 5. Lógica de Ejecución
    estado = respuesta_agente.get("estado")
    datos = respuesta_agente.get("datos_extraidos", {})
    
    if estado == "recopilando":
        # Aún faltan datos, el bot solo chatea
        await update.message.reply_text(texto_respuesta)
        
    elif estado == "listo_para_reservar":
        # Gemini dice que ya tiene Fecha y Hora. ¡Atacamos Google Calendar!
        mensaje_espera = await update.message.reply_text(f"{texto_respuesta}\n\n⏳ Procesando reserva en Google Calendar...")
        
        fecha = datos.get("fecha_iso")
        hora = datos.get("hora")
        nombre_id = f"{update.effective_user.full_name} ({update.effective_user.id})"
        
        # Ejecutamos el servicio de calendario que ya tenías creado
        try:
            resultado = await asyncio.to_thread(
                calendar_service.create_reservation,
                nombre_id,
                fecha,
                hora
            )
            
            if resultado.startswith("❌"):
                await mensaje_espera.edit_text(f"{resultado}\n\n¿Quieres probar con otro día u otra hora?")
                # Si falló porque estaba ocupado, quitamos el último mensaje de la memoria para que Gemini vuelva a preguntar
                context.user_data["historial"].pop()
            else:
                await mensaje_espera.edit_text(f"✅ ¡Todo listo!\n{resultado}")
                # Reserva completada, limpiamos la memoria
                context.user_data["historial"] = []
                
        except Exception as e:
            print(f"Error al reservar: {e}")
            await mensaje_espera.edit_text("❌ Hubo un fallo interno al conectar con el calendario. Por favor, inténtalo más tarde.")
            context.user_data["historial"].pop()