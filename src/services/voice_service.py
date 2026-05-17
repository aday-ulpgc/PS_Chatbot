import os
import re
import asyncio
from uuid import uuid4

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from gtts import gTTS

_DOTENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "env", ".env")
load_dotenv(dotenv_path=_DOTENV_PATH)

_MESES = {
    "01": "enero",
    "02": "febrero",
    "03": "marzo",
    "04": "abril",
    "05": "mayo",
    "06": "junio",
    "07": "julio",
    "08": "agosto",
    "09": "septiembre",
    "10": "octubre",
    "11": "noviembre",
    "12": "diciembre",
}


def formatear_fecha_para_voz(texto: str) -> str:
    """
    Transforma fechas en formatos cortos o ISO a lenguaje natural antes de
    enviarlas a ElevenLabs.

    Ejemplos:
        '2024-06-23'  →  '23 de junio de 2024'
        '23/06'       →  '23 de junio'
        '23-06'       →  '23 de junio'
    """

    # Formato completo ISO: YYYY-MM-DD o YYYY/MM/DD
    def _reemplazar_fecha_completa(m: re.Match) -> str:
        anyo, mes, dia = m.group(1), m.group(2), m.group(3)
        return f"{int(dia)} de {_MESES.get(mes, mes)} de {anyo}"

    texto = re.sub(
        r"\b(\d{4})[-/](\d{2})[-/](\d{2})\b",
        _reemplazar_fecha_completa,
        texto,
    )

    # Formato corto: DD/MM o DD-MM
    def _reemplazar_fecha_corta(m: re.Match) -> str:
        dia, mes = m.group(1), m.group(2)
        return f"{int(dia)} de {_MESES.get(mes, mes)}"

    texto = re.sub(
        r"\b(\d{1,2})[-/](\d{2})\b",
        _reemplazar_fecha_corta,
        texto,
    )

    return texto


def formatear_hora_para_voz(texto: str) -> str:
    """
    Transforma horas en formato HH:MM a lenguaje natural.

    Ejemplos:
        '15:00'  →  'las 15 en punto'
        '09:30'  →  'las 9 y 30'
    """

    def _reemplazar_hora(m: re.Match) -> str:
        hora = int(m.group(1))
        minutos = m.group(2)
        if minutos == "00":
            return f"las {hora} en punto"
        return f"las {hora} y {minutos}"

    return re.sub(r"\b(\d{1,2}):(\d{2})\b", _reemplazar_hora, texto)


class VoiceService:
    """Servicio encargado de la conversion de texto a voz"""

    @staticmethod
    async def text_to_speech(text: str) -> str:
        """
        Recibe un texto, lo normaliza (fechas, horas) y devuelve la ruta del
        archivo de audio generado con ElevenLabs (o fallback a gTTS).
        """
        # Normalización automática antes de enviar a la API
        text = formatear_fecha_para_voz(text)
        text = formatear_hora_para_voz(text)

        if not text or not text.strip():
            raise ValueError("El texto para generar audio está vacío")

        output_path = f"temp_reserva_{uuid4().hex}.mp3"

        # Intentar con ElevenLabs primero
        api_key = os.getenv("ELEVEN_API_KEY")
        if api_key:
            try:
                voice_id = os.getenv("ELEVEN_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
                client = ElevenLabs(api_key=api_key)
                
                def _generate_audio_elevenlabs():
                    response = client.text_to_speech.convert(
                        voice_id=voice_id,
                        text=text,
                        model_id="eleven_monolingual_v1",
                    )
                    with open(output_path, "wb") as f:
                        for chunk in response:
                            f.write(chunk)
                
                await asyncio.to_thread(_generate_audio_elevenlabs)
                
                if os.path.exists(output_path):
                    return output_path
            except Exception as e:
                print(f"⚠️ Error con ElevenLabs, usando fallback: {e}")

        # Fallback a gTTS
        def _generate_audio_gtts():
            tts = gTTS(text=text, lang="es", tld="es")
            tts.save(output_path)

        await asyncio.to_thread(_generate_audio_gtts)

        if not os.path.exists(output_path):
            raise FileNotFoundError(
                f"No se pudo generar el archivo de audio: {output_path}"
            )

        return output_path
