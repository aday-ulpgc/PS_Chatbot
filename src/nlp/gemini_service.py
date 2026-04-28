# src/nlp/gemini_service.py
import os
import json
import re
import asyncio
import httpx  # Usamos httpx (que ya viene con telegram) para hacer peticiones directas
from datetime import datetime
from src.bot.telegram.constants import obtener_promt_agente


class NLPService:
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
        modelo = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"

        hoy = datetime.now().strftime("%A, %d de %B de %Y a las %H:%M")

        prompt_sistema = obtener_promt_agente(hoy, datos_semanal)

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
        for intento in range(max_reintentos):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=payload, timeout=15.0)

                    if response.status_code == 429:
                        if intento < max_reintentos - 1:
                            await asyncio.sleep(2**intento)
                            continue
                        else:
                            return NLPService._respuesta_emergencia(
                                "Estoy un poco saturada ahora mismo 🥵. ¿Me lo repites en un minutito?"
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
