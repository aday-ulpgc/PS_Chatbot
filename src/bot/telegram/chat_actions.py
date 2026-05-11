import asyncio
from contextlib import asynccontextmanager
from telegram.ext import ExtBot
from telegram.constants import ChatAction

@asynccontextmanager
async def send_action_while_thinking(bot: ExtBot, chat_id: int, action: str = ChatAction.TYPING):
    """
    Gestor de contexto asíncrono para enviar acciones de chat de Telegram (ej. escribiendo).
    Inicia una tarea en segundo plano al entrar y la cancela de forma segura al salir.
    """
    task = None
    
    async def keep_action_alive():
        try:
            while True:
                await bot.send_chat_action(chat_id=chat_id, action=action)
                await asyncio.sleep(4.5)
        except asyncio.CancelledError:
            pass

    try:
        # Iniciamos el bucle en background (__aenter__)
        task = asyncio.create_task(keep_action_alive())
        yield
    finally:
        # Aseguramos la cancelación, pase lo que pase (__aexit__)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
