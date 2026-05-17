"""Punto de entrada del bot de Telegram.

Carga la configuración desde el archivo .env, valida que el token
de Telegram esté presente y arranca el bot en modo polling.
"""

import os
import sys
import threading

# Aseguramos que la raíz del proyecto esté en el path para que los imports desde 'src.' funcionen correctamente
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uvicorn
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from src.bot.telegram.handlers.commands import start_command
from src.bot.telegram.router import menu_callback_handler
from src.api import app as fastapi_app


def main() -> None:
    """Inicializa y arranca el bot de Telegram.

    1. Carga las variables de entorno desde ``env/.env``.
    2. Valida que ``TELEGRAM_TOKEN`` esté definido.
    3. Construye la aplicación con ``ApplicationBuilder``.
    4. Registra los handlers de comandos.
    5. Inicia el loop de polling.
    """
    dotenv_path: str = os.path.join(os.path.dirname(__file__), "..", "env", ".env")
    load_dotenv(dotenv_path=dotenv_path)

    token: str | None = os.getenv("TELEGRAM_TOKEN")

    if not token:
        print(
            "ERROR: La variable de entorno TELEGRAM_TOKEN no está definida. "
            "Revisa el archivo env/.env"
        )
        sys.exit(1)

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(menu_callback_handler))

    api_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": fastapi_app, "host": "0.0.0.0", "port": 8000},
        daemon=True,
    )
    api_thread.start()
    print("API iniciada en http://localhost:8000/docs")

    print("Bot iniciado. Esperando mensajes...")
    # Aumentar timeouts para conectividad débil/lenta
    app.run_polling(
        poll_interval=2.0,  # Esperar 2 segundos entre polls
        timeout=10,         # Timeout de 10 segundos (por defecto es 5)
        allowed_updates=None,
        drop_pending_updates=True,  # Ignorar mensajes antiguos al reiniciar
    )


if __name__ == "__main__":
    main()
