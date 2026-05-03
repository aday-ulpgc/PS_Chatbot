import asyncio
import os
import re
from uuid import uuid4

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

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
    """Servicio encargado de la conversión de texto a voz."""

    @staticmethod
    async def text_to_speech(text: str) -> str:
        """
        Recibe un texto, lo normaliza (fechas, horas) y devuelve la ruta del
        archivo de audio generado con ElevenLabs.
        """
        # Normalización automática antes de enviar a la API
        text = formatear_fecha_para_voz(text)
        text = formatear_hora_para_voz(text)

        api_key = os.getenv("ELEVEN_API_KEY")
        if not api_key:
            raise ValueError("No se encontró ELEVEN_API_KEY en el archivo .env")

        voice_id = os.getenv("ELEVEN_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

        if not text or not text.strip():
            raise ValueError("El texto para generar audio está vacío")

        output_path = f"temp_reserva_{uuid4().hex}.mp3"

        def _generate_audio():
            client = ElevenLabs(api_key=api_key)

            audio_stream = client.text_to_speech.convert(
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                text=text,
            )

            audio_bytes = b"".join(audio_stream)

            with open(output_path, "wb") as f:
                f.write(audio_bytes)

        await asyncio.to_thread(_generate_audio)

        if not os.path.exists(output_path):
            raise FileNotFoundError(
                f"No se pudo generar el archivo de audio: {output_path}"
            )

        return output_path
