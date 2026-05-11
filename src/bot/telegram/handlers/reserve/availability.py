import asyncio
import os
from datetime import date, datetime, timedelta

from telegram import InputMediaPhoto, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar

from src.BBDD.database_service import obtener_o_crear_usuario_telegram
from src.services.visualization_service import (
    generar_imagen_disponibilidad,
    generar_imagen_disponibilidad_semana_24h,
)

from .keyboards import (
    availability_type_markup,
    back_menu_markup,
    calendar_step_markup,
    day_navigation_markup,
    week_navigation_markup,
)


async def handle_action_view_availability(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Permite elegir si ver disponibilidad de un día o una semana."""
    try:
        await query.edit_message_text(
            text="¿Qué tipo de disponibilidad deseas ver?",
            reply_markup=availability_type_markup(),
        )

    except Exception as e:
        print(f"❌ Error en handle_action_view_availability: {e}")
        await query.edit_message_text(
            text="❌ Error al mostrar opciones", reply_markup=back_menu_markup()
        )


async def handle_action_view_availability_day(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la última imagen de día o el calendario para seleccionar un día."""
    # Bloquear clicks rápidos durante la regeneración
    if context.user_data.get("day_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    try:
        # Borrar imagen de semana si existe (cambio de vista)
        week_photo_id = context.user_data.get("week_photo_message_id")
        if week_photo_id:
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id, message_id=week_photo_id
                )
                context.user_data["week_photo_message_id"] = None
            except Exception:
                pass  # Mantener el ID para que back_menu pueda reintentarlo

        # Verificar si existe una imagen anterior de día
        current_day_date = context.user_data.get("current_day_date")
        day_photo_id = context.user_data.get("day_photo_message_id")

        # Solo intentar reutilizar la imagen si ambos existen y message_id es válido
        if current_day_date and day_photo_id and day_photo_id is not None:
            if not isinstance(current_day_date, date):
                current_day_date = date.fromisoformat(str(current_day_date))

            # Obtener usuario
            user_id = update.effective_user.id
            usuario = obtener_o_crear_usuario_telegram(user_id)
            user_db_id = usuario.get("id_usuario")

            if user_db_id:
                # Bloquear clicks rápidos durante la regeneración
                context.user_data["day_photo_generating"] = True
                try:
                    # Convertir a datetime
                    day_datetime = datetime.combine(
                        current_day_date, datetime.min.time()
                    )

                    # Generar imagen del día
                    imagen_path = await asyncio.to_thread(
                        generar_imagen_disponibilidad, user_db_id, day_datetime
                    )

                    if imagen_path and os.path.exists(imagen_path):
                        try:
                            with open(imagen_path, "rb") as img_file:
                                media = InputMediaPhoto(
                                    media=img_file.read(),
                                    caption=f"📊 Tu disponibilidad el {current_day_date.strftime('%d/%m/%Y')}",
                                    parse_mode="HTML",
                                )
                                await context.bot.edit_message_media(
                                    chat_id=query.message.chat_id,
                                    message_id=day_photo_id,
                                    media=media,
                                )

                            reply_markup = day_navigation_markup()
                            await query.edit_message_text(
                                text="✅ Última disponibilidad de día guardada",
                                reply_markup=reply_markup,
                            )
                            return
                        except Exception as e:
                            # No se pudo editar: intentar borrar la foto huérfana y limpiar
                            print(f"No se pudo editar imagen día: {e}")
                            try:
                                await context.bot.delete_message(
                                    chat_id=query.message.chat_id,
                                    message_id=day_photo_id,
                                )
                            except Exception:
                                pass
                            context.user_data["day_photo_message_id"] = None
                finally:
                    context.user_data["day_photo_generating"] = False

        # Si no existe imagen anterior válida, mostrar calendario
        calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
        await query.edit_message_text(
            text="📅 Selecciona un día para ver tu disponibilidad:",
            reply_markup=calendar,
        )
        context.user_data["availability_calendar"] = "day"

    except Exception as e:
        print(f"❌ Error en handle_action_view_availability_day: {e}")
        import traceback

        traceback.print_exc()
        await query.edit_message_text(
            text="❌ Error al mostrar calendario", reply_markup=back_menu_markup()
        )


async def handle_action_view_availability_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la última imagen de semana o el calendario para seleccionar una semana."""
    # Bloquear clicks rápidos durante la regeneración
    if context.user_data.get("week_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    try:
        # Borrar imagen de día si existe (cambio de vista)
        day_photo_id = context.user_data.get("day_photo_message_id")
        if day_photo_id:
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id, message_id=day_photo_id
                )
                context.user_data["day_photo_message_id"] = None
            except Exception:
                pass  # Mantener el ID para que back_menu pueda reintentarlo

        # Verificar si existe una imagen anterior de semana
        current_week_date = context.user_data.get("current_week_date")
        week_photo_id = context.user_data.get("week_photo_message_id")

        # Solo intentar reutilizar la imagen si ambos existen y message_id es válido
        if current_week_date and week_photo_id and week_photo_id is not None:
            if not isinstance(current_week_date, date):
                current_week_date = date.fromisoformat(str(current_week_date))

            # Obtener usuario
            user_id = update.effective_user.id
            usuario = obtener_o_crear_usuario_telegram(user_id)
            user_db_id = usuario.get("id_usuario")

            if user_db_id:
                context.user_data["week_photo_generating"] = True
                try:
                    # Convertir a datetime
                    week_datetime = datetime.combine(
                        current_week_date, datetime.min.time()
                    )

                    # Generar imagen de la semana
                    imagen_path = await asyncio.to_thread(
                        generar_imagen_disponibilidad_semana_24h,
                        user_db_id,
                        week_datetime,
                    )

                    if imagen_path and os.path.exists(imagen_path):
                        try:
                            # Calcular rango de fechas para el caption
                            lunes = current_week_date - timedelta(
                                days=current_week_date.weekday()
                            )
                            domingo_fecha = lunes + timedelta(days=6)
                            caption = f"📆 Semana del {lunes.strftime('%d/%m')} al {domingo_fecha.strftime('%d/%m/%Y')}"

                            with open(imagen_path, "rb") as img_file:
                                media = InputMediaPhoto(
                                    media=img_file.read(),
                                    caption=caption,
                                    parse_mode="HTML",
                                )
                                await context.bot.edit_message_media(
                                    chat_id=query.message.chat_id,
                                    message_id=week_photo_id,
                                    media=media,
                                )

                            reply_markup = week_navigation_markup()
                            await query.edit_message_text(
                                text=f"✅ {caption}", reply_markup=reply_markup
                            )
                            return
                        except Exception as e:
                            # No se pudo editar: intentar borrar la foto huérfana y limpiar
                            print(f"No se pudo editar imagen semana: {e}")
                            try:
                                await context.bot.delete_message(
                                    chat_id=query.message.chat_id,
                                    message_id=week_photo_id,
                                )
                            except Exception:
                                pass
                            context.user_data["week_photo_message_id"] = None
                finally:
                    context.user_data["week_photo_generating"] = False

        # Si no existe imagen anterior válida, mostrar calendario
        calendar, step = DetailedTelegramCalendar(min_date=date.today()).build()
        await query.edit_message_text(
            text="📆 Selecciona cualquier día de la semana que deseas ver:",
            reply_markup=calendar,
        )
        context.user_data["availability_calendar"] = "week"

    except Exception as e:
        print(f"❌ Error en handle_action_view_availability_week: {e}")
        import traceback

        traceback.print_exc()
        await query.edit_message_text(
            text="❌ Error al mostrar calendario", reply_markup=back_menu_markup()
        )


async def handle_availability_calendar_selection(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Genera y envía la imagen de disponibilidad cuando se selecciona una fecha."""
    try:
        # Verificar si es un evento del calendario
        if not DetailedTelegramCalendar.func()(query):
            return

        # Procesar la selección del calendario
        current_calendar = DetailedTelegramCalendar(min_date=date.today())
        result, key, step = current_calendar.process(query.data)

        if not result and key:
            # Mostrar siguiente paso del calendario
            try:
                await query.edit_message_text(
                    text="Selecciona una fecha:",
                    reply_markup=calendar_step_markup(key),
                )
            except BadRequest:
                pass

        elif result:
            # Fecha seleccionada
            selected_date = result
            availability_type = context.user_data.get("availability_calendar", "day")

            # Obtener usuario de Telegram
            user_id = update.effective_user.id
            usuario = obtener_o_crear_usuario_telegram(user_id)
            user_db_id = usuario.get("id_usuario")

            if not user_db_id:
                await query.edit_message_text(
                    "❌ Error al obtener tus datos de usuario"
                )
                return

            # Convertir a datetime
            selected_datetime = datetime.combine(selected_date, datetime.min.time())

            if availability_type == "day":
                # Evitar generaciones concurrentes por clicks rápidos
                if context.user_data.get("day_photo_generating"):
                    await query.answer("⏳ Cargando imagen, espera un momento...")
                    return
                context.user_data["day_photo_generating"] = True
                try:
                    # Vista de día
                    await query.edit_message_text(
                        "🎨 Generando imagen de disponibilidad del día..."
                    )

                    imagen_path = await asyncio.to_thread(
                        generar_imagen_disponibilidad, user_db_id, selected_datetime
                    )

                    if imagen_path and os.path.exists(imagen_path):
                        with open(imagen_path, "rb") as img_file:
                            photo_message = await context.bot.send_photo(
                                chat_id=query.message.chat_id,
                                photo=img_file,
                                caption=f"📊 Tu disponibilidad el {selected_date.strftime('%d/%m/%Y')}",
                            )

                        context.user_data["day_photo_message_id"] = (
                            photo_message.message_id
                        )
                        context.user_data["current_day_date"] = selected_date

                        await query.edit_message_text(
                            text="✅ Imagen enviada",
                            reply_markup=day_navigation_markup(),
                        )
                    else:
                        await query.edit_message_text("❌ Error al generar la imagen")
                finally:
                    context.user_data["availability_calendar"] = False
                    context.user_data["day_photo_generating"] = False

            elif availability_type == "week":
                # Evitar generaciones concurrentes por clicks rápidos
                if context.user_data.get("week_photo_generating"):
                    await query.answer("⏳ Cargando imagen, espera un momento...")
                    return
                context.user_data["week_photo_generating"] = True
                try:
                    # Vista de semana
                    await query.edit_message_text(
                        "🎨 Generando imagen de disponibilidad de la semana..."
                    )

                    imagen_path = await asyncio.to_thread(
                        generar_imagen_disponibilidad_semana_24h,
                        user_db_id,
                        selected_datetime,
                    )

                    if imagen_path and os.path.exists(imagen_path):
                        with open(imagen_path, "rb") as img_file:
                            photo_message = await context.bot.send_photo(
                                chat_id=query.message.chat_id,
                                photo=img_file,
                                caption="📆 Disponibilidad de la semana",
                            )

                        context.user_data["week_photo_message_id"] = (
                            photo_message.message_id
                        )
                        context.user_data["current_week_date"] = selected_date

                        await query.edit_message_text(
                            text="✅ Imagen enviada",
                            reply_markup=week_navigation_markup(),
                        )
                    else:
                        await query.edit_message_text("❌ Error al generar la imagen")
                finally:
                    context.user_data["availability_calendar"] = False
                    context.user_data["week_photo_generating"] = False
            else:
                await query.edit_message_text("❌ Error al generar la imagen")

    except Exception as e:
        print(f"❌ Error en handle_availability_calendar_selection: {e}")
        await query.edit_message_text(
            text=f"❌ Error: {str(e)}", reply_markup=back_menu_markup()
        )


async def handle_prev_day(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el día anterior."""
    if context.user_data.get("day_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    context.user_data["day_photo_generating"] = True
    try:
        # Obtener la fecha actual del día
        current_day_date = context.user_data.get("current_day_date")
        if not current_day_date:
            current_day_date = date.today()
        else:
            current_day_date = (
                current_day_date
                if isinstance(current_day_date, date)
                else date.fromisoformat(str(current_day_date))
            )

        # Restar 1 día
        prev_day_date = current_day_date - timedelta(days=1)

        # No permitir ir a días pasados
        if prev_day_date < date.today():
            await query.answer("⚠️ No puedes ver días pasados", show_alert=True)
            return

        # Obtener usuario
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")

        if not user_db_id:
            await query.answer("❌ Error al obtener datos del usuario", show_alert=True)
            return

        # Convertir a datetime
        prev_day_datetime = datetime.combine(prev_day_date, datetime.min.time())

        # Generar imagen del día anterior
        imagen_path = await asyncio.to_thread(
            generar_imagen_disponibilidad, user_db_id, prev_day_datetime
        )

        if imagen_path and os.path.exists(imagen_path):
            # Actualizar la fecha guardada
            context.user_data["current_day_date"] = prev_day_date

            # Obtener el message_id de la foto anterior
            photo_message_id = context.user_data.get("day_photo_message_id")

            if photo_message_id:
                # Reemplazar la imagen existente
                with open(imagen_path, "rb") as img_file:
                    media = InputMediaPhoto(
                        media=img_file.read(),
                        caption=f"📊 Tu disponibilidad el {prev_day_date.strftime('%d/%m/%Y')}",
                        parse_mode="HTML",
                    )
                    await context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=photo_message_id,
                        media=media,
                    )

            # Actualizar botones
            await query.edit_message_text(
                text="✅ Día anterior", reply_markup=day_navigation_markup()
            )
        else:
            await query.answer("❌ Error al generar la imagen", show_alert=True)

    except Exception as e:
        print(f"❌ Error en handle_prev_day: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        context.user_data["day_photo_generating"] = False


async def handle_next_day(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra el día siguiente."""
    if context.user_data.get("day_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    context.user_data["day_photo_generating"] = True
    try:
        # Obtener la fecha actual del día
        current_day_date = context.user_data.get("current_day_date")
        if not current_day_date:
            current_day_date = date.today()
        else:
            current_day_date = (
                current_day_date
                if isinstance(current_day_date, date)
                else date.fromisoformat(str(current_day_date))
            )

        # Sumar 1 día
        next_day_date = current_day_date + timedelta(days=1)

        # Obtener usuario
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")

        if not user_db_id:
            await query.answer("❌ Error al obtener datos del usuario", show_alert=True)
            return

        # Convertir a datetime
        next_day_datetime = datetime.combine(next_day_date, datetime.min.time())

        # Generar imagen del día siguiente
        imagen_path = await asyncio.to_thread(
            generar_imagen_disponibilidad, user_db_id, next_day_datetime
        )

        if imagen_path and os.path.exists(imagen_path):
            # Actualizar la fecha guardada
            context.user_data["current_day_date"] = next_day_date

            # Obtener el message_id de la foto anterior
            photo_message_id = context.user_data.get("day_photo_message_id")

            if photo_message_id:
                # Reemplazar la imagen existente
                with open(imagen_path, "rb") as img_file:
                    media = InputMediaPhoto(
                        media=img_file.read(),
                        caption=f"📊 Tu disponibilidad el {next_day_date.strftime('%d/%m/%Y')}",
                        parse_mode="HTML",
                    )
                    await context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=photo_message_id,
                        media=media,
                    )

            # Actualizar botones
            await query.edit_message_text(
                text="✅ Día siguiente", reply_markup=day_navigation_markup()
            )
        else:
            await query.answer("❌ Error al generar la imagen", show_alert=True)

    except Exception as e:
        print(f"❌ Error en handle_next_day: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        context.user_data["day_photo_generating"] = False


async def handle_prev_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la semana anterior."""
    if context.user_data.get("week_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    context.user_data["week_photo_generating"] = True
    try:
        # Obtener la fecha actual de la semana
        current_week_date = context.user_data.get("current_week_date")
        if not current_week_date:
            current_week_date = date.today()
        else:
            current_week_date = (
                current_week_date
                if isinstance(current_week_date, date)
                else date.fromisoformat(str(current_week_date))
            )

        # Restar 7 días
        prev_week_date = current_week_date - timedelta(days=7)

        # No permitir ir a semanas pasadas (si el lunes de la semana anterior sería antes de hoy)
        lunes = prev_week_date - timedelta(days=prev_week_date.weekday())
        if lunes < date.today():
            await query.answer("⚠️ No puedes ver semanas pasadas", show_alert=True)
            return

        # Obtener usuario
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")

        if not user_db_id:
            await query.answer("❌ Error al obtener datos del usuario", show_alert=True)
            return

        # Convertir a datetime
        prev_week_datetime = datetime.combine(prev_week_date, datetime.min.time())

        # Generar imagen de la semana anterior
        imagen_path = await asyncio.to_thread(
            generar_imagen_disponibilidad_semana_24h, user_db_id, prev_week_datetime
        )

        if imagen_path and os.path.exists(imagen_path):
            # Actualizar la fecha guardada
            context.user_data["current_week_date"] = prev_week_date

            # Calcular rango de fechas para el caption
            lunes = prev_week_date - timedelta(days=prev_week_date.weekday())
            domingo_fecha = lunes + timedelta(days=6)
            caption = f"📆 Semana del {lunes.strftime('%d/%m')} al {domingo_fecha.strftime('%d/%m/%Y')}"

            # Obtener el message_id de la foto anterior
            photo_message_id = context.user_data.get("week_photo_message_id")

            if photo_message_id:
                # Reemplazar la imagen existente
                with open(imagen_path, "rb") as img_file:
                    media = InputMediaPhoto(
                        media=img_file.read(), caption=caption, parse_mode="HTML"
                    )
                    await context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=photo_message_id,
                        media=media,
                    )

            # Actualizar botones
            await query.edit_message_text(
                text=f"✅ {caption}", reply_markup=week_navigation_markup()
            )
        else:
            await query.answer("❌ Error al generar la imagen", show_alert=True)

    except Exception as e:
        print(f"❌ Error en handle_prev_week: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        context.user_data["week_photo_generating"] = False


async def handle_next_week(
    query, context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    """Muestra la semana siguiente."""
    if context.user_data.get("week_photo_generating"):
        await query.answer("⏳ Cargando imagen, espera un momento...")
        return
    context.user_data["week_photo_generating"] = True
    try:
        # Obtener la fecha actual de la semana
        current_week_date = context.user_data.get("current_week_date")
        if not current_week_date:
            current_week_date = date.today()
        else:
            current_week_date = (
                current_week_date
                if isinstance(current_week_date, date)
                else date.fromisoformat(str(current_week_date))
            )

        # Sumar 7 días
        next_week_date = current_week_date + timedelta(days=7)

        # Obtener usuario
        user_id = update.effective_user.id
        usuario = obtener_o_crear_usuario_telegram(user_id)
        user_db_id = usuario.get("id_usuario")

        if not user_db_id:
            await query.answer("❌ Error al obtener datos del usuario", show_alert=True)
            return

        # Convertir a datetime
        next_week_datetime = datetime.combine(next_week_date, datetime.min.time())

        # Generar imagen de la semana siguiente
        imagen_path = await asyncio.to_thread(
            generar_imagen_disponibilidad_semana_24h, user_db_id, next_week_datetime
        )

        if imagen_path and os.path.exists(imagen_path):
            # Actualizar la fecha guardada
            context.user_data["current_week_date"] = next_week_date

            # Calcular rango de fechas para el caption
            lunes = next_week_date - timedelta(days=next_week_date.weekday())
            domingo_fecha = lunes + timedelta(days=6)
            caption = f"📆 Semana del {lunes.strftime('%d/%m')} al {domingo_fecha.strftime('%d/%m/%Y')}"

            # Obtener el message_id de la foto anterior
            photo_message_id = context.user_data.get("week_photo_message_id")

            if photo_message_id:
                # Reemplazar la imagen existente
                with open(imagen_path, "rb") as img_file:
                    media = InputMediaPhoto(
                        media=img_file.read(), caption=caption, parse_mode="HTML"
                    )
                    await context.bot.edit_message_media(
                        chat_id=query.message.chat_id,
                        message_id=photo_message_id,
                        media=media,
                    )

            # Actualizar botones
            await query.edit_message_text(
                text=f"✅ {caption}", reply_markup=week_navigation_markup()
            )
        else:
            await query.answer("❌ Error al generar la imagen", show_alert=True)

    except Exception as e:
        print(f"❌ Error en handle_next_week: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        context.user_data["week_photo_generating"] = False
