import asyncio
import os
from uuid import uuid4

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

_DOTENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "env", ".env")
load_dotenv(dotenv_path=_DOTENV_PATH)


class VoiceService:
    """Servicio encargado de la conversión de texto a voz."""

    @staticmethod
    async def text_to_speech(text: str) -> str:
        """
        Recibe un texto y devuelve la ruta del archivo de audio generado con ElevenLabs.
        """
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
