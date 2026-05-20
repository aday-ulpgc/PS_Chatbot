from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.BBDD.database_service import obtener_o_crear_cliente_por_telegram
from src.services.translator_service import TranslatorService
from .utils import _send_or_edit


async def handle_action_my_appointments(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra las citas del cliente agrupadas en bloques de 9."""
    idioma = context.user_data.get("idioma", "es")

    try:
        # Obtener cliente de Telegram
        user_id = update.effective_user.id
        cliente_result = obtener_o_crear_cliente_por_telegram(user_id)
        cliente_id = cliente_result.get("cliente_id")

        if not cliente_id:
            msg_err = TranslatorService.traducir("Error al obtener tus datos", idioma)
            await _send_or_edit(query, update, msg_err)
            return

        from src.BBDD.databasecontroller import obtener_citas_cliente, get_session

        lbl_sin_desc = TranslatorService.traducir("Sin descripción", idioma)

        with get_session() as session:
            citas = obtener_citas_cliente(session, cliente_id, None, None)
            citas = sorted(citas, key=lambda c: c.FECHA, reverse=True)

            # Convertir a diccionarios DENTRO de la sesión para no perder datos
            citas_dict = [
                {"fecha": c.FECHA, "descripcion": c.DESCRIPCION or lbl_sin_desc}
                for c in citas
            ]

            lbl_volver = TranslatorService.traducir("⫶☰ Volver", idioma)

            if not citas_dict:
                keyboard = [
                    [InlineKeyboardButton(lbl_volver, callback_data="action_back_menu")]
                ]
                msg_vacio = TranslatorService.traducir(
                    "*Mis citas:*\n\n*No hay citas registradas*", idioma
                )
                await _send_or_edit(
                    query,
                    update,
                    text=msg_vacio,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                )
                return

            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            bloques = [citas_dict[i : i + 9] for i in range(0, len(citas_dict), 9)]

            context.user_data["citas_bloques"] = bloques
            context.user_data["citas_bloque_actual"] = 0

            # Mostrar primer bloque
            lbl_citas = TranslatorService.traducir("Mis citas", idioma)
            lbl_grupo = TranslatorService.traducir("grupo", idioma)
            lbl_de = TranslatorService.traducir("de", idioma)

            bloque_texto = f"*{lbl_citas}* ({lbl_grupo} 1 {lbl_de} {len(bloques)})\n\n"
            for idx, cita in enumerate(bloques[0]):
                fecha_str = cita["fecha"].strftime("%d/%m/%Y %H:%M")
                bloque_texto += f"{emojis[idx]} *{fecha_str}* - {cita['descripcion']}\n"

            keyboard = []
            if len(bloques) > 1:
                lbl_ant = TranslatorService.traducir("Anterior", idioma)
                lbl_sig = TranslatorService.traducir("Siguiente", idioma)
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            lbl_ant, callback_data="action_prev_citas_group"
                        ),
                        InlineKeyboardButton(
                            lbl_sig, callback_data="action_next_citas_group"
                        ),
                    ]
                )
            keyboard.append(
                [InlineKeyboardButton(lbl_volver, callback_data="action_back_menu")]
            )

            await _send_or_edit(
                query,
                update,
                text=bloque_texto,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

    except Exception as e:
        print(f"❌ Error en handle_action_my_appointments: {e}")
        lbl_volver = TranslatorService.traducir("⫶☰ Volver", idioma)
        msg_err_cargar = TranslatorService.traducir(
            "❌ Error al cargar tus citas", idioma
        )
        keyboard = [
            [InlineKeyboardButton(lbl_volver, callback_data="action_back_menu")]
        ]
        await _send_or_edit(
            query,
            update,
            text=msg_err_cargar,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def _navegar_grupo(query, context, update, direccion):
    """Función unificada para no repetir código entre anterior y siguiente"""
    idioma = context.user_data.get("idioma", "es")
    try:
        bloques = context.user_data.get("citas_bloques", [])
        bloque_actual = context.user_data.get("citas_bloque_actual", 0)

        if direccion == "prev" and (not bloques or bloque_actual == 0):
            msg = TranslatorService.traducir("⚠️ Ya estás en el primer grupo", idioma)
            await query.answer(msg, show_alert=True)
            return
        elif direccion == "next" and (not bloques or bloque_actual >= len(bloques) - 1):
            msg = TranslatorService.traducir("⚠️ Ya estás en el último grupo", idioma)
            await query.answer(msg, show_alert=True)
            return

        nuevo_bloque = bloque_actual - 1 if direccion == "prev" else bloque_actual + 1
        context.user_data["citas_bloque_actual"] = nuevo_bloque

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        lbl_citas = TranslatorService.traducir("Mis citas", idioma)
        lbl_grupo = TranslatorService.traducir("grupo", idioma)
        lbl_de = TranslatorService.traducir("de", idioma)

        bloque_texto = f"📋 *{lbl_citas}* ({lbl_grupo} {nuevo_bloque + 1} {lbl_de} {len(bloques)})\n\n"

        for idx, cita in enumerate(bloques[nuevo_bloque]):
            fecha_str = cita["fecha"].strftime("%d/%m/%Y %H:%M")
            bloque_texto += f"{emojis[idx]} *{fecha_str}* - {cita['descripcion']}\n"

        keyboard = []
        if len(bloques) > 1:
            lbl_ant = TranslatorService.traducir("⬅️ Anterior", idioma)
            lbl_sig = TranslatorService.traducir("Siguiente ➡️", idioma)
            keyboard.append(
                [
                    InlineKeyboardButton(
                        lbl_ant, callback_data="action_prev_citas_group"
                    ),
                    InlineKeyboardButton(
                        lbl_sig, callback_data="action_next_citas_group"
                    ),
                ]
            )

        lbl_disp = TranslatorService.traducir("📅 Ver disponibilidad", idioma)
        lbl_volver = TranslatorService.traducir("⫶☰ Volver", idioma)

        keyboard.extend(
            [
                [
                    InlineKeyboardButton(
                        lbl_disp, callback_data="action_view_availability"
                    )
                ],
                [InlineKeyboardButton(lbl_volver, callback_data="action_back_menu")],
            ]
        )

        await query.edit_message_text(
            text=bloque_texto,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    except Exception as e:
        print(f"❌ Error en navegación de citas: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def handle_prev_citas_group(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    await _navegar_grupo(query, context, update, "prev")


async def handle_next_citas_group(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    await _navegar_grupo(query, context, update, "next")
