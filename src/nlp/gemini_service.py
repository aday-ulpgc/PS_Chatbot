import os
import json
import re
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from src.bot.telegram.constants import obtener_promt_agente

# Cargar variables de entorno
env_path = Path(__file__).resolve().parent.parent.parent / "env" / ".env"
load_dotenv(env_path)


class NLPService:
    MODELOS_DISPONIBLES = [
        "gemini-3.1-flash-lite",                 
        "gemini-3-flash-preview",                   
        "gemini-3.1-pro-preview",              
    ]
    
    # 🔄 Índice del modelo actual (inicia con el mejor)
    _modelo_actual_idx = 0
    
    @classmethod
    def obtener_modelo_actual(cls) -> str:
        """Retorna el modelo actual en uso."""
        return cls.MODELOS_DISPONIBLES[cls._modelo_actual_idx]
    
    @classmethod
    def cambiar_al_siguiente_modelo(cls) -> str:
        """
        Cambia al siguiente modelo en la lista.
        Si llega al final, regresa al primero.
        Retorna el nuevo modelo.
        """
        cls._modelo_actual_idx = (cls._modelo_actual_idx + 1) % len(cls.MODELOS_DISPONIBLES)
        nuevo_modelo = cls.MODELOS_DISPONIBLES[cls._modelo_actual_idx]
        print(f"⚠️  Modelo sobrecargado. Cambiando a: {nuevo_modelo}")
        return nuevo_modelo
    
    @classmethod
    def resetear_a_modelo_preferido(cls) -> None:
        """Resetea al modelo preferido (el primero de la lista)."""
        cls._modelo_actual_idx = 0
        print(f"🔄 Reseteando a modelo preferido: {cls.obtener_modelo_actual()}")

    @staticmethod
    def _limpiar_json(texto: str) -> dict:
        """Limpia el texto por si Gemini envuelve el JSON en bloques de Markdown."""
        texto_limpio = re.sub(r"```json\n?", "", texto)
        texto_limpio = re.sub(r"```\n?", "", texto_limpio)
        try:
            print(f"JSON Limpio: {texto_limpio}")
            return json.loads(texto_limpio.strip())
        except json.JSONDecodeError:
            print(f"❌ Error decodificando JSON de Gemini: {texto}")
            return NLPService._respuesta_emergencia(
                "Uy, me he liado un poco. ¿Me repites qué querías hacer?"
            )

    @staticmethod
    def _respuesta_emergencia(texto: str) -> dict:
        """Genera un JSON seguro para no romper el bot si todo falla."""
        return {
            "estado": "recopilando",
            "datos_extraidos": {"fecha_iso": None, "hora": None},
            "respuesta_usuario": texto,
        }

    @staticmethod
    async def procesar_mensaje(
        historial_mensajes: list, datos_semanal: str, audio_b64: str = None
    ) -> dict:
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key or api_key.startswith("AIzaSy..."):
            print("\n❌ ERROR: GEMINI_API_KEY no está configurada correctamente")
            print("📝 Por favor, agrega tu API key de Gemini al archivo env/.env:")
            print("   GEMINI_API_KEY=AIzaSy_tu_api_key_real_aqui")
            print("🔗 Obtén tu API key en: https://aistudio.google.com/apikey")
            return {
                "respuesta": "❌ El servicio de IA no está configurado. Por favor, contacta al administrador.",
                "necesita_intervencion": True,
                "estado": "error"
            }
        
        import pytz
        from src.services.calendar_service import TIMEZONE

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        fecha_actual = now.strftime("%A, %d de %B de %Y")
        hora_actual = now.strftime("%H:%M")

        prompt_sistema = obtener_promt_agente(fecha_actual, hora_actual, datos_semanal)

        # Construir mensajes para Gemini
        mensajes_gemini = []
        for m in historial_mensajes:
            role = "user" if m["rol"] == "usuario" else "model"
            mensajes_gemini.append({"role": role, "parts": [{"text": m["texto"]}]})
        
        if audio_b64 and mensajes_gemini:
            mensajes_gemini[-1]["parts"].append(
                {"inlineData": {"mimeType": "audio/ogg", "data": audio_b64}}
            )
        
        # Payload para la API de Gemini
        payload = {
            "contents": mensajes_gemini,
            "systemInstruction": {"parts": [{"text": prompt_sistema}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.7,
                "maxOutputTokens": 1000
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_LOW_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_LOW_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_LOW_AND_ABOVE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_LOW_AND_ABOVE",
                },
            ],
        }

        max_reintentos = len(NLPService.MODELOS_DISPONIBLES)
        
        for intento in range(max_reintentos):
            try:
                modelo = NLPService.obtener_modelo_actual()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
                print(f"📡 Intentando con modelo: {modelo}")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload)

                    # Manejar errores de tasa (429)
                    if response.status_code == 429:
                        print(f"❌ Error 429 (Sobrecargado): {modelo}")
                        if intento < max_reintentos - 1:
                            NLPService.cambiar_al_siguiente_modelo()
                            await asyncio.sleep(2)
                            continue
                        else:
                            return NLPService._respuesta_emergencia(
                                "Todos mis asistentes están muy ocupados 🥵. ¿Lo intentamos en un minuto?"
                            )
                    
                    # Manejar errores 400 (Bad Request)
                    if response.status_code == 400:
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("error", {}).get("message", "Error desconocido")
                            print(f"❌ Error 400 (Bad Request): {error_msg}")
                            print(f"📋 Modelo usado: {modelo}")
                            print(f"📋 Respuesta completa: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                        except:
                            print(f"❌ Error 400 (Bad Request)")
                            print(f"📋 Respuesta: {response.text}")
                        
                        # Probar con siguiente modelo
                        if intento < max_reintentos - 1:
                            NLPService.cambiar_al_siguiente_modelo()
                            await asyncio.sleep(1)
                            continue
                        else:
                            return NLPService._respuesta_emergencia(
                                "No puedo procesar tu solicitud en este momento. ¿Intentamos de nuevo?"
                            )
                    
                    # Otros errores HTTP
                    if response.status_code >= 400:
                        print(f"❌ Error {response.status_code}: {response.text}")
                        if intento < max_reintentos - 1:
                            await asyncio.sleep(1)
                            continue
                        return NLPService._respuesta_emergencia(
                            "Parece que hay un problema con el servicio. ¿Intentamos de nuevo?"
                        )

                    # Éxito
                    data = response.json()
                    
                    try:
                        candidato = data.get("candidates", [{}])[0]
                        
                        # Verificar si fue bloqueado por seguridad
                        if candidato.get("finishReason") == "SAFETY":
                            return NLPService._respuesta_emergencia(
                                "Lo siento, mi configuración no me permite procesar ese lenguaje. ¿Hablamos de tu reserva? 🗓️"
                            )
                        
                        # Extraer texto de respuesta
                        texto_respuesta = candidato.get("content", {}).get("parts", [{}])[0].get("text", "")
                        
                        if not texto_respuesta:
                            print(f"⚠️  Respuesta vacía de Gemini")
                            return NLPService._respuesta_emergencia(
                                "Hmm, no entendí bien. ¿Puedes repetirlo?"
                            )
                        
                        # ✅ Éxito - resetear al modelo preferido para siguiente llamada
                        NLPService.resetear_a_modelo_preferido()
                        return NLPService._limpiar_json(texto_respuesta)

                    except (KeyError, IndexError, TypeError) as e:
                        print(f"❌ Error procesando respuesta de Gemini: {e}")
                        print(f"📋 Estructura recibida: {json.dumps(data, indent=2, ensure_ascii=False)}")
                        return NLPService._respuesta_emergencia(
                            "Tuve un pequeño cruce de cables 🤖. ¿Puedes volver a decírmelo?"
                        )

            except asyncio.TimeoutError:
                print(f"⏱️ Timeout con modelo: {NLPService.obtener_modelo_actual()}")
                if intento < max_reintentos - 1:
                    NLPService.cambiar_al_siguiente_modelo()
                    await asyncio.sleep(1)
                    continue
                return NLPService._respuesta_emergencia(
                    "La respuesta tardó demasiado. ¿Intentamos de nuevo?"
                )
            
            except Exception as e:
                print(f"❌ Error inesperado: {type(e).__name__}: {e}")
                if intento == max_reintentos - 1:
                    return NLPService._respuesta_emergencia(
                        "Parece que mi conexión falló 🔌. ¿Lo intentamos de nuevo?"
                    )
                await asyncio.sleep(1)
