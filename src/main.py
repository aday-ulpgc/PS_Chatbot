"""Punto de entrada del bot de Telegram.

Carga la configuración desde el archivo .env, valida que el token
de Telegram esté presente y arranca el bot en modo polling.
"""

import asyncio
import atexit
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import threading
import uvicorn
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from src.bot.telegram.handlers.commands import start_command
from src.bot.telegram.router import menu_callback_handler, message_handler
from src.bot.telegram.handlers.nlp import set_ptb_app
from src.api import app as fastapi_app
from src.bot.telegram.handlers.reminders import check_daily_reminders
from datetime import time

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# ── Lock de instancia única ───────────────────────────────────────────────────
_LOCK_FILE = os.path.join(tempfile.gettempdir(), "ps_chatbot_bot.lock")


def _is_pid_alive(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=3,
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def _acquire_lock() -> None:
    if os.path.exists(_LOCK_FILE):
        try:
            with open(_LOCK_FILE) as f:
                pid = int(f.read().strip())
            if _is_pid_alive(pid):
                print(f"❌ Ya hay una instancia del bot en ejecución (PID {pid}).")
                print("   Ciérrala o ejecuta: Get-Process python* | Stop-Process -Force")
                sys.exit(1)
        except (ValueError, OSError):
            pass
    with open(_LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(_release_lock)


def _release_lock() -> None:
    try:
        if os.path.exists(_LOCK_FILE):
            os.remove(_LOCK_FILE)
    except OSError:
        pass


# ── Loop asíncrono (compatible con Python 3.14) ───────────────────────────────
async def _run_polling(app) -> None:
    async with app:
        await app.updater.start_polling(
            poll_interval=2.0,
            timeout=10,
            allowed_updates=None,
            drop_pending_updates=True,
        )
        await app.start()
        print("Bot iniciado. Esperando mensajes...")
        try:
            await asyncio.Event().wait()  # espera indefinida hasta Ctrl+C
        finally:
            # Limpieza explícita antes de que async-with llame a shutdown()
            await app.updater.stop()
            await app.stop()


def main() -> None:
    _acquire_lock()

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

    # Compartir la instancia PTB con la API web para que los usuarios identificados
    # via Telegram Login Widget usen la misma sesión que el bot
    set_ptb_app(app)

    hora_recordatorio = time(hour=8, minute=0, second=0)
    app.job_queue.run_daily(check_daily_reminders, time=hora_recordatorio)

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(menu_callback_handler))
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.VOICE) & ~filters.COMMAND, message_handler
        )
    )

    api_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": fastapi_app, "host": "0.0.0.0", "port": 8000},
        daemon=True,
    )
    api_thread.start()
    print("API iniciada en http://localhost:8000/docs")

    try:
        asyncio.run(_run_polling(app))
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
