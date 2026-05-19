"""Script para reparar availability.py"""

content = '''"""Handlers para visualizar disponibilidad - DESHABILITADO TEMPORALMENTE."""

from telegram import Update
from telegram.ext import ContextTypes
from .keyboards import back_menu_markup


async def handle_action_view_availability(query, context, update):
    try:
        await query.edit_message_text(
            text="Visualization being updated.",
            reply_markup=back_menu_markup(),
        )
    except Exception as e:
        print(f"Error: {e}")


async def handle_action_view_availability_day(query, context, update):
    try:
        await query.edit_message_text(
            text="Feature temporarily disabled.",
            reply_markup=back_menu_markup(),
        )
    except Exception as e:
        print(f"Error: {e}")


async def handle_action_view_availability_week(query, context, update):
    try:
        await query.edit_message_text(
            text="Feature temporarily disabled.",
            reply_markup=back_menu_markup(),
        )
    except Exception as e:
        print(f"Error: {e}")


async def handle_availability_calendar_selection(query, context, update):
    pass


async def handle_prev_day(query, context, update):
    pass


async def handle_next_day(query, context, update):
    pass


async def handle_prev_week(query, context, update):
    pass


async def handle_next_week(query, context, update):
    pass
'''

with open(
    "src/bot/telegram/handlers/reserve/availability.py", "w", encoding="utf-8"
) as f:
    f.write(content)

print("OK availability.py fixed")
