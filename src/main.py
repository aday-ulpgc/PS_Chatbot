"""Punto de entrada del bot de Telegram.

Carga la configuración desde el archivo .env, valida que el token
de Telegram esté presente y arranca el bot en modo polling.
"""

import os
import sys
import asyncio

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler

from bot.telegram_handler import start_command


def main() -> None:
    """Inicializa y arranca el bot de Telegram.

    1. Carga las variables de entorno desde ``env/.env``.
    2. Valida que ``TELEGRAM_TOKEN`` esté definido.
    3. Construye la aplicación con ``ApplicationBuilder``.
    4. Registra los handlers de comandos.
    5. Inicia el loop de polling.
    """
    dotenv_path: str = os.path.join(
        os.path.dirname(__file__), "..", "env", ".env"
    )
    load_dotenv(dotenv_path=dotenv_path)

    token: str | None = os.getenv("TELEGRAM_TOKEN")

    if not token:
        print(
            "ERROR: La variable de entorno TELEGRAM_TOKEN no está definida. "
            "Revisa el archivo env/.env"
        )
        sys.exit(1)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))

    print("Bot iniciado. Esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()
