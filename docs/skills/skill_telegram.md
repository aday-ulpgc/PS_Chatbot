# SKILL: Telegram Bot Handler (v21.0+)
**Descripción:** Cómo implementar la interfaz de Telegram en nuestro proyecto usando `python-telegram-bot`.
## Reglas de Implementación
1. **Librería:** Usa EXCLUSIVAMENTE `python-telegram-bot` en su versión 21.0 o superior (interfaz asíncrona `async`/`await`).
2. **Arquitectura:** Todo el código relacionado con Telegram debe vivir dentro de la carpeta `src/bot/`.
3. **Seguridad:** El token del bot NUNCA debe estar hardcodeado. Debe leerse desde las variables de entorno (`os.getenv("TELEGRAM_TOKEN")`).
4. **Patrón de Diseño:** - Usa `ApplicationBuilder` para inicializar el bot.
   - Crea funciones asíncronas separadas para los comandos (ej. `async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):`).
   - Mantén los handlers lo más "tontos" posible: si hay lógica compleja, deben llamar a `src/services/`.
