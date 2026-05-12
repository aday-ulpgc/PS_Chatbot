import os
import json
import re
import asyncio
import httpx
from datetime import datetime
from src.bot.telegram.constants import obtener_promt_agente


class NLPService:
    # 📋 Lista de modelos ordenados por rendimiento (mejor → peor)
    MODELOS_DISPONIBLES = [
        "gemini-3-flash",                    # Gemini 3.1 Flash (mejor rendimiento)
        "gemini-3-flash-lite",               # Gemini 3.1 Flash-Lite
        "gemini-3-flash-live",               # Gemini 3.1 Flash Live
        "gemini-2-5-flash",                  # Gemini 2.5 Flash
        "gemini-2-5-flash-lite",             # Gemini 2.5 Flash-Lite
        "gemini-nano",                       # Gemini Nano (respaldo final)
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
        modelo = NLPService.obtener_modelo_actual()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"

        import pytz
        from src.services.calendar_service import TIMEZONE

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        fecha_actual = now.strftime("%A, %d de %B de %Y")
        hora_actual = now.strftime("%H:%M")

        prompt_sistema = obtener_promt_agente(fecha_actual, hora_actual, datos_semanal)

        mensajes_gemini = []
        for m in historial_mensajes:
            role = "user" if m["rol"] == "usuario" else "model"
            mensajes_gemini.append({"role": role, "parts": [{"text": m["texto"]}]})
        if audio_b64:
            mensajes_gemini[-1]["parts"].append(
                {"inlineData": {"mimeType": "audio/ogg", "data": audio_b64}}
            )
        payload = {
            "contents": mensajes_gemini,
            "systemInstruction": {"parts": [{"text": prompt_sistema}]},
            "generationConfig": {"responseMimeType": "application/json"},
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

        max_reintentos = 3
        intentos_fallidos = 0
        
        for intento in range(max_reintentos):
            try:
                # 🔄 Actualizar URL con modelo actual si cambiamos
                modelo = NLPService.obtener_modelo_actual()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
                print(f"📡 Intentando con modelo: {modelo}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=payload, timeout=15.0)

                    if response.status_code == 429:
                        # ⚠️ Modelo sobrecargado - cambiar al siguiente
                        print(f"❌ Error 429 (Sobrecargado) con modelo: {modelo}")
                        NLPService.cambiar_al_siguiente_modelo()
                        intentos_fallidos += 1
                        
                        if intentos_fallidos < len(NLPService.MODELOS_DISPONIBLES):
                            # Esperar y reintentar con siguiente modelo
                            await asyncio.sleep(1)
                            continue
                        else:
                            # Se agotaron todos los modelos
                            return NLPService._respuesta_emergencia(
                                "Todos mis asistentes están muy ocupados 🥵. ¿Lo intentamos en un minuto?"
                            )

                    response.raise_for_status()

                    data = response.json()

                    try:
                        candidato = data["candidates"][0]
                        if candidato.get("finishReason") == "SAFETY":
                            return NLPService._respuesta_emergencia(
                                "Lo siento, mi configuración no me permite procesar ese lenguaje. ¿Hablamos de tu reserva? 🗓️"
                            )

                        texto_respuesta = candidato["content"]["parts"][0]["text"]
                        
                        # ✅ Éxito - resetear al modelo preferido para siguiente llamada
                        NLPService.resetear_a_modelo_preferido()
                        return NLPService._limpiar_json(texto_respuesta)

                    except (KeyError, IndexError):
                        print(f"❌ Estructura inesperada de Gemini: {data}")
                        return NLPService._respuesta_emergencia(
                            "Tuve un pequeño cruce de cables 🤖. ¿Puedes volver a decírmelo?"
                        )

            except Exception as e:
                print(f"❌ Error de red HTTP: {e}")
                if intento == max_reintentos - 1:
                    return NLPService._respuesta_emergencia(
                        "Parece que mi conexión a internet falló 🔌. ¿Lo intentamos de nuevo?"
                    )

                    data = response.json()

                    try:
                        candidato = data["candidates"][0]
                        if candidato.get("finishReason") == "SAFETY":
                            return NLPService._respuesta_emergencia(
                                "Lo siento, mi configuración no me permite procesar ese lenguaje. ¿Hablamos de tu reserva? 🗓️"
                            )

                        texto_respuesta = candidato["content"]["parts"][0]["text"]
                        return NLPService._limpiar_json(texto_respuesta)

                    except (KeyError, IndexError):
                        print(f"❌ Estructura inesperada de Gemini: {data}")
                        return NLPService._respuesta_emergencia(
                            "Tuve un pequeño cruce de cables 🤖. ¿Puedes volver a decírmelo?"
                        )

            except Exception as e:
                print(f"❌ Error de red HTTP: {e}")
                if intento == max_reintentos - 1:
                    return NLPService._respuesta_emergencia(
                        "Parece que mi conexión a internet falló 🔌. ¿Lo intentamos de nuevo?"
                    )
