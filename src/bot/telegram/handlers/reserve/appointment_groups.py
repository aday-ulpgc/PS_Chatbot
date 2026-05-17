from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.BBDD.database_service import obtener_o_crear_usuario_telegram

from .utils import _send_or_edit


async def handle_action_my_appointments(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra las citas del usuario agrupadas en bloques de 9."""
    try:
        # Obtener usuario de Telegram
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")

        if not user_db_id:
            await _send_or_edit(
                query, update, "❌ Error al obtener tus datos de usuario"
            )
            return

        # Obtener citas del usuario de la BD
        from src.BBDD.databasecontroller import obtener_citas_por_usuario, get_session

        with get_session() as session:
            citas = obtener_citas_por_usuario(session, user_db_id)
            # Invertir para mostrar más recientes primero
            citas = sorted(citas, key=lambda c: c.FECHA, reverse=True)

            # Convertir a diccionarios DENTRO de la sesión para no perder datos
            citas_dict = [
                {"fecha": c.FECHA, "descripcion": c.DESCRIPCION or "Sin descripción"}
                for c in citas
            ]

            if not citas_dict:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📅 Ver disponibilidad",
                            callback_data="action_view_availability",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⫶☰ Volver", callback_data="action_back_menu"
                        )
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await _send_or_edit(
                    query,
                    update,
                    text="📋 *Mis citas:*\n\n*No hay citas registradas*",
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )
                return

            # Agrupar citas en bloques de 9
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            bloques = []
            for i in range(0, len(citas_dict), 9):
                bloque = citas_dict[i : i + 9]
                bloques.append(bloque)

            # Guardar bloques en contexto para navegación
            context.user_data["citas_bloques"] = bloques
            context.user_data["citas_bloque_actual"] = 0

            # Mostrar primer bloque
            bloque_texto = f"📋 *Mis citas* (grupo 1 de {len(bloques)})\n\n"
            for idx, cita in enumerate(bloques[0]):
                fecha_str = cita["fecha"].strftime("%d/%m/%Y %H:%M")
                bloque_texto += f"{emojis[idx]} *{fecha_str}* - {cita['descripcion']}\n"

            # Crear botones de navegación
            keyboard = []
            if len(bloques) > 1:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "⬅️ Anterior", callback_data="action_prev_citas_group"
                        ),
                        InlineKeyboardButton(
                            "Siguiente ➡️", callback_data="action_next_citas_group"
                        ),
                    ]
                )
            keyboard.extend(
                [
                    [
                        InlineKeyboardButton(
                            "📅 Ver disponibilidad",
                            callback_data="action_view_availability",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⫶☰ Volver", callback_data="action_back_menu"
                        )
                    ],
                ]
            )
            reply_markup = InlineKeyboardMarkup(keyboard)

            await _send_or_edit(
                query,
                update,
                text=bloque_texto,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

    except Exception as e:
        print(f"❌ Error en handle_action_my_appointments: {e}")
        keyboard = [[InlineKeyboardButton("Volver", callback_data="action_back_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _send_or_edit(
            query,
            update,
            text="❌ Error al cargar tus citas",
            reply_markup=reply_markup,
        )


async def handle_prev_citas_group(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el grupo anterior de citas."""
    try:
        bloques = context.user_data.get("citas_bloques", [])
        bloque_actual = context.user_data.get("citas_bloque_actual", 0)

        if not bloques or bloque_actual == 0:
            await query.answer("⚠️ Ya estás en el primer grupo", show_alert=True)
            return

        # Retroceder un grupo
        nuevo_bloque = bloque_actual - 1
        context.user_data["citas_bloque_actual"] = nuevo_bloque

        # Generar texto del nuevo grupo
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        bloque_texto = (
            f"📋 *Mis citas* (grupo {nuevo_bloque + 1} de {len(bloques)})\n\n"
        )

        for idx, cita in enumerate(bloques[nuevo_bloque]):
            fecha_str = cita["fecha"].strftime("%d/%m/%Y %H:%M")
            bloque_texto += f"{emojis[idx]} *{fecha_str}* - {cita['descripcion']}\n"

        # Crear botones de navegación
        keyboard = []
        if len(bloques) > 1:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "⬅️ Anterior", callback_data="action_prev_citas_group"
                    ),
                    InlineKeyboardButton(
                        "Siguiente ➡️", callback_data="action_next_citas_group"
                    ),
                ]
            )
        keyboard.extend(
            [
                [
                    InlineKeyboardButton(
                        "📅 Ver disponibilidad",
                        callback_data="action_view_availability",
                    )
                ],
                [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")],
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=bloque_texto, reply_markup=reply_markup, parse_mode="Markdown"
        )

    except Exception as e:
        print(f"❌ Error en handle_prev_citas_group: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def handle_next_citas_group(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el siguiente grupo de citas."""
    try:
        bloques = context.user_data.get("citas_bloques", [])
        bloque_actual = context.user_data.get("citas_bloque_actual", 0)

        if not bloques or bloque_actual >= len(bloques) - 1:
            await query.answer("⚠️ Ya estás en el último grupo", show_alert=True)
            return

        # Avanzar un grupo
        nuevo_bloque = bloque_actual + 1
        context.user_data["citas_bloque_actual"] = nuevo_bloque

        # Generar texto del nuevo grupo
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        bloque_texto = (
            f"📋 *Mis citas* (grupo {nuevo_bloque + 1} de {len(bloques)})\n\n"
        )

        for idx, cita in enumerate(bloques[nuevo_bloque]):
            fecha_str = cita["fecha"].strftime("%d/%m/%Y %H:%M")
            bloque_texto += f"{emojis[idx]} *{fecha_str}* - {cita['descripcion']}\n"

        # Crear botones de navegación
        keyboard = []
        if len(bloques) > 1:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "⬅️ Anterior", callback_data="action_prev_citas_group"
                    ),
                    InlineKeyboardButton(
                        "Siguiente ➡️", callback_data="action_next_citas_group"
                    ),
                ]
            )
        keyboard.extend(
            [
                [
                    InlineKeyboardButton(
                        "📅 Ver disponibilidad",
                        callback_data="action_view_availability",
                    )
                ],
                [InlineKeyboardButton("⫶☰ Volver", callback_data="action_back_menu")],
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=bloque_texto, reply_markup=reply_markup, parse_mode="Markdown"
        )

    except Exception as e:
        print(f"❌ Error en handle_next_citas_group: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
