import os
import json
import re
import asyncio
import httpx
import pytz
from datetime import datetime
from src.bot.telegram.constants import obtener_promt_agente
from src.services.translator_service import TranslatorService


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
        historial_mensajes: list,
        datos_semanal: str,
        audio_b64: str = None,
        idioma_usuario: str = "es",
    ) -> dict:
        api_key = os.getenv("GEMINI_API_KEY")
        modelo = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"

        from src.services.calendar_service import TIMEZONE

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        fecha_actual = now.strftime("%A, %d de %B de %Y")
        hora_actual = now.strftime("%H:%M")

        prompt_sistema = obtener_promt_agente(fecha_actual, hora_actual, datos_semanal)

        mensajes_gemini = []
        for m in historial_mensajes:
            role = "user" if m["rol"] == "usuario" else "model"
            texto_original = m["texto"]

            if role == "user":
                texto_para_gemini, _ = TranslatorService.traducir_a_es(texto_original)
            else:
                texto_para_gemini = texto_original

            mensajes_gemini.append(
                {"role": role, "parts": [{"text": texto_para_gemini}]}
            )

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
                    response = await client.post(url, json=payload, timeout=30.0)

                    if response.status_code == 429:
                        if intento < max_reintentos - 1:
                            await asyncio.sleep(2**intento)
                            continue
                        else:
                            msg_error = TranslatorService.traducir(
                                "Estoy un poco saturada ahora mismo 🥵. ¿Me lo repites en un minutito?",
                                idioma_usuario,
                            )
                            return NLPService._respuesta_emergencia(msg_error)

                    response.raise_for_status()

                    data = response.json()

                    try:
                        candidato = data["candidates"][0]
                        if candidato.get("finishReason") == "SAFETY":
                            msg_seguridad = TranslatorService.traducir(
                                "Lo siento, mi configuración no me permite procesar ese lenguaje. ¿Hablamos de tu reserva? 🗓️",
                                idioma_usuario,
                            )
                            return NLPService._respuesta_emergencia(msg_seguridad)

                        texto_respuesta = candidato["content"]["parts"][0]["text"]
                        respuesta_json = NLPService._limpiar_json(texto_respuesta)

                        if respuesta_json and respuesta_json.get("respuesta_usuario"):
                            respuesta_json["respuesta_original"] = respuesta_json[
                                "respuesta_usuario"
                            ]
                            texto_traducido = TranslatorService.traducir(
                                respuesta_json["respuesta_usuario"], idioma_usuario
                            )
                            respuesta_json["respuesta_usuario"] = texto_traducido

                        return respuesta_json

                    except (KeyError, IndexError):
                        print(f"❌ Estructura inesperada de Gemini: {data}")
                        msg_estructura = TranslatorService.traducir(
                            "Tuve un pequeño cruce de cables 🤖. ¿Puedes volver a decírmelo?",
                            idioma_usuario,
                        )
                        return NLPService._respuesta_emergencia(msg_estructura)

            except Exception as e:
                print(f"❌ Error de red HTTP: {e}")
                if intento == max_reintentos - 1:
                    msg_red = TranslatorService.traducir(
                        "Parece que mi conexión a internet falló 🔌. ¿Lo intentamos de nuevo?",
                        idioma_usuario,
                    )
                    return NLPService._respuesta_emergencia(msg_red)
