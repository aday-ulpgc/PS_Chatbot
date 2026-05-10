from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def back_menu_markup(label: str = "Volver") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data="action_back_menu")]]
    )


def availability_type_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📅 Ver disponibilidad de un DÍA",
                    callback_data="action_view_availability_day",
                )
            ],
            [
                InlineKeyboardButton(
                    "📆 Ver disponibilidad de una SEMANA",
                    callback_data="action_view_availability_week",
                )
            ],
            [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")],
        ]
    )


def day_navigation_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⬅️ Día anterior", callback_data="action_prev_day"),
                InlineKeyboardButton(
                    "Día siguiente ➡️", callback_data="action_next_day"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📅 Otro día", callback_data="action_view_availability_day"
                )
            ],
            [
                InlineKeyboardButton(
                    "⫶☰ Menú Principal", callback_data="action_back_menu"
                )
            ],
        ]
    )


def week_navigation_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ Semana anterior", callback_data="action_prev_week"
                ),
                InlineKeyboardButton(
                    "Semana siguiente ➡️", callback_data="action_next_week"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📆 Otra semana", callback_data="action_view_availability_week"
                )
            ],
            [
                InlineKeyboardButton(
                    "⫶☰ Menú Principal", callback_data="action_back_menu"
                )
            ],
        ]
    )
