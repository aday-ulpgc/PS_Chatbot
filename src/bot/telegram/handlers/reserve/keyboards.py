import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.services.translator_service import TranslatorService


def calendar_step_markup(key: str, idioma: str = "es") -> InlineKeyboardMarkup:
    """Reconstruye el teclado del calendario y añade botones de reinicio/menú."""
    keyboard_dict = json.loads(key)
    keyboard_buttons = [
        [
            InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])
            for btn in row
        ]
        for row in keyboard_dict.get("inline_keyboard", [])
    ]
    keyboard_buttons.append(
        [
            InlineKeyboardButton(
                TranslatorService.traducir("↻ Reiniciar", idioma),
                callback_data="action_view_availability",
            ),
            InlineKeyboardButton(
                TranslatorService.traducir("⫶☰ Menú", idioma),
                callback_data="action_back_menu",
            ),
        ]
    )
    return InlineKeyboardMarkup(keyboard_buttons)


def back_menu_markup(label: str = "Volver", idioma: str = "es") -> InlineKeyboardMarkup:
    lbl_traducida = TranslatorService.traducir(label, idioma)
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(lbl_traducida, callback_data="action_back_menu")]]
    )


def availability_type_markup(idioma: str = "es") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    TranslatorService.traducir(
                        "📅 Ver disponibilidad de un DÍA", idioma
                    ),
                    callback_data="action_view_availability_day",
                )
            ],
            [
                InlineKeyboardButton(
                    TranslatorService.traducir(
                        "📆 Ver disponibilidad de una SEMANA", idioma
                    ),
                    callback_data="action_view_availability_week",
                )
            ],
            [
                InlineKeyboardButton(
                    TranslatorService.traducir("⫶☰ Volver", idioma),
                    callback_data="action_back_menu",
                )
            ],
        ]
    )


def day_navigation_markup(idioma: str = "es") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    TranslatorService.traducir("⬅️ Día anterior", idioma),
                    callback_data="action_prev_day",
                ),
                InlineKeyboardButton(
                    TranslatorService.traducir("Día siguiente ➡️", idioma),
                    callback_data="action_next_day",
                ),
            ],
            [
                InlineKeyboardButton(
                    TranslatorService.traducir("📅 Otro día", idioma),
                    callback_data="action_view_availability_day",
                )
            ],
            [
                InlineKeyboardButton(
                    TranslatorService.traducir("⫶☰ Menú Principal", idioma),
                    callback_data="action_back_menu",
                )
            ],
        ]
    )


def week_navigation_markup(idioma: str = "es") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    TranslatorService.traducir("⬅️ Semana anterior", idioma),
                    callback_data="action_prev_week",
                ),
                InlineKeyboardButton(
                    TranslatorService.traducir("Semana siguiente ➡️", idioma),
                    callback_data="action_next_week",
                ),
            ],
            [
                InlineKeyboardButton(
                    TranslatorService.traducir("📆 Otra semana", idioma),
                    callback_data="action_view_availability_week",
                )
            ],
            [
                InlineKeyboardButton(
                    TranslatorService.traducir("⫶☰ Menú Principal", idioma),
                    callback_data="action_back_menu",
                )
            ],
        ]
    )
