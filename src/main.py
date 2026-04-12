"""Punto de entrada del bot de Telegram.

Carga la configuración desde el archivo .env, valida que el token
de Telegram esté presente y arranca el bot en modo polling.
"""

import os
import sys
import subprocess
import threading

# Aseguramos que la raíz del proyecto esté en el path para que los imports desde 'src.' funcionen correctamente
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uvicorn
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from src.bot.telegram.handlers.commands import start_command
from src.bot.telegram.router import menu_callback_handler
from src.api import app as fastapi_app


def check_and_install_requirements() -> None:
    """Pregunta al usuario si desea instalar/actualizar los requerimientos."""
    response = input("Descargar requerimientos (y/n): ").strip().lower()
    
    while response not in ("y", "n"):
        response = input("Opción inválida. Por favor ingresa 'y' o 'n': ").strip().lower()
    if response == "y":
        print("Instalando requerimientos...")
        requirements_path = os.path.join(
            os.path.dirname(__file__), "..", "requirements.txt"
        )
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", requirements_path],
                check=True,
            )
            print("Requerimientos actualizados")
        except subprocess.CalledProcessError as e:
            print(f"Error al instalar requerimientos: {e}")
            sys.exit(1)
    elif response == "n":
        print("Continuando sin instalar requerimientos...")

def main() -> None:
    """Inicializa y arranca el bot de Telegram.

    1. Pregunta al usuario si desea instalar requerimientos.
    2. Carga las variables de entorno desde ``env/.env``.
    3. Valida que ``TELEGRAM_TOKEN`` esté definido.
    4. Construye la aplicación con ``ApplicationBuilder``.
    5. Registra los handlers de comandos.
    6. Inicia el loop de polling.
    """
    # Pregunta al usuario si desea instalar/actualizar requerimientos
    check_and_install_requirements()
    
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
    app.run_polling()


if __name__ == "__main__":
    main()
