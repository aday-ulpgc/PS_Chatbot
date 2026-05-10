import asyncio


async def keep_action_alive(bot, chat_id: int, action) -> None:
    """Mantiene activo un indicador de Telegram en bucle hasta que se cancele."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=action)
            await asyncio.sleep(4.5)
    except asyncio.CancelledError:
        pass
