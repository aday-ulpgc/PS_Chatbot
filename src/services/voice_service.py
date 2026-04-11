import os
import asyncio
from gtts import gTTS

class VoiceService:
    """Servicio encargado de la conversion de texto a voz"""
    @staticmethod
    async def text_to_speech(text: str) -> str:
        """
        Recibe un texto y devuelve la ruta del archivo de audio generado.
        mediante [elegir cual usar]
        """
        output_path = "temp_reserva.mp3"

        def _generate_audio():
            tts = gTTS(text=text, lang='es', tld="es")
            tts.save(output_path)
        
        await asyncio.to_thread(_generate_audio)

        if not os.path.exists(output_path):
            raise FileNotFoundError(f"No se pudo generar el archivo de audio: {output_path}")

        return output_path
        
        