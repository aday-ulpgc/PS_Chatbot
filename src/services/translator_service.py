from functools import lru_cache
from deep_translator import GoogleTranslator
from langdetect import detect


class TranslatorService:
    @staticmethod
    def detectar_idioma(texto: str) -> str:
        """Detecta el idioma del texto del usuario."""
        if not texto or len(texto) < 3:
            return "es"  # Por defecto español
        try:
            det = detect(texto)
            if det not in ["es", "en", "fr", "it", "de", "pt"]:
                return "en"
            return det
        except Exception:
            return "es"

    @staticmethod
    @lru_cache(maxsize=1000)
    def traducir(texto: str, idioma_destino: str) -> str:
        """
        Traduce un texto y lo guarda en caché.
        Si ya se tradujo antes, lo devuelve al instante de la memoria.
        """
        if idioma_destino == "es" or not texto:
            return texto

        try:
            traductor = GoogleTranslator(source="es", target=idioma_destino)
            return traductor.translate(texto)
        except Exception as e:
            print(f"⚠️ Error traduciendo '{texto}': {e}")
            return texto

    @staticmethod
    def traducir_a_es(texto: str) -> tuple[str, str]:
        """Traduce al español y devuelve también el idioma original."""
        idioma_origen = TranslatorService.detectar_idioma(texto)
        if idioma_origen == "es":
            return texto, "es"

        try:
            traductor = GoogleTranslator(source=idioma_origen, target="es")
            texto_es = traductor.translate(texto)

            return texto_es, idioma_origen
        except Exception:
            return texto, "es"
