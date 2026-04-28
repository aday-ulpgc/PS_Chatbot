"""Servicio de visualización para mostrar disponibilidad de horas."""

import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from src.BBDD.databasecontroller import obtener_citas_por_usuario, get_session


HORAS_INICIO = 0
HORAS_FIN = 24
TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "temp")


def _asegurar_temp_dir():
    """Crea el directorio temporal si no existe."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)


def generar_imagen_disponibilidad(user_id: int, fecha: datetime) -> str:
    """
    Genera una imagen de disponibilidad de horas para un día específico.
    
    Args:
        user_id: ID del usuario
        fecha: Fecha para la cual generar la imagen (datetime)
        
    Returns:
        Ruta a la imagen generada
    """
    _asegurar_temp_dir()
    
    try:
        # Obtener citas del usuario para ese día - DENTRO de la sesión
        with get_session() as session:
            citas = obtener_citas_por_usuario(session, user_id)
            
            # Convertir a diccionarios para no perder datos después de cerrar sesión
            citas_data = [
                {
                    'fecha': c.FECHA,
                    'duracion': c.DURACION if c.DURACION else 60,
                    'descripcion': c.DESCRIPCION
                }
                for c in citas
            ]
        
        # Filtrar citas del día específico
        fecha_inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        citas_del_dia = [
            c for c in citas_data
            if fecha_inicio <= c['fecha'] <= fecha_fin
        ]
        
        # Crear figura
        fig, ax = plt.subplots(figsize=(20, 6))
        fig.patch.set_facecolor('#f8f9fa')
        
        # Configurar título y labels
        titulo = f"Disponibilidad de horas - {fecha.strftime('%A, %d de %B de %Y')}"
        ax.set_title(titulo, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Hora del día', fontsize=12, fontweight='bold')
        ax.set_ylim(0, 1)
        ax.set_xlim(HORAS_INICIO - 0.5, HORAS_FIN - 0.5)
        
        # Remover ejes Y innecesarios
        ax.set_yticks([])
        
        # Establecer horas en el eje X
        horas = list(range(HORAS_INICIO, HORAS_FIN))
        ax.set_xticks(horas)
        ax.set_xticklabels([f"{h:02d}:00" for h in horas], fontsize=9)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        # Crear matriz de horas ocupadas
        horas_ocupadas = {}
        for hora in range(HORAS_INICIO, HORAS_FIN):
            horas_ocupadas[hora] = False
        
        # Marcar horas ocupadas según las citas
        for cita in citas_del_dia:
            hora_inicio = cita['fecha'].hour
            minuto_inicio = cita['fecha'].minute
            duracion = cita['duracion']
            
            # Calcular hora y minuto de fin correctamente
            minutos_totales = minuto_inicio + duracion
            horas_fin = minutos_totales // 60
            minutos_fin = minutos_totales % 60
            
            hora_fin = hora_inicio + horas_fin
            
            # Si terminamos exacto en la hora, no incluir esa hora
            if minutos_fin == 0:
                # La cita termina exacto, p.ej. 07:00-13:00
                horas_a_marcar = range(hora_inicio, min(hora_fin, HORAS_FIN))
            else:
                # La cita termina entre horas, p.ej. 07:00-13:15, hay que marcar hora 13
                horas_a_marcar = range(hora_inicio, min(hora_fin + 1, HORAS_FIN))
            
            for h in horas_a_marcar:
                horas_ocupadas[h] = True
        
        # Dibujar bloques de horas
        for idx, hora in enumerate(range(HORAS_INICIO, HORAS_FIN)):
            x_start = hora
            x_width = 0.8
            
            if horas_ocupadas.get(hora, False):
                # Rojo para horas ocupadas
                color = '#e74c3c'
                label = '❌ Ocupado' if idx == 0 else ""
            else:
                # Verde para horas disponibles
                color = '#27ae60'
                label = '✅ Disponible' if idx == 0 else ""
            
            rect = patches.Rectangle(
                (x_start - x_width/2, 0.2),
                x_width,
                0.6,
                linewidth=2,
                edgecolor='#2c3e50',
                facecolor=color,
                alpha=0.8
            )
            ax.add_patch(rect)
        
        # Agregar leyenda
        ocupado = patches.Patch(facecolor='#e74c3c', edgecolor='#2c3e50', label='❌ Ocupado')
        disponible = patches.Patch(facecolor='#27ae60', edgecolor='#2c3e50', label='✅ Disponible')
        ax.legend(handles=[disponible, ocupado], loc='upper right', fontsize=11)
        
        # Ajustar layout
        plt.tight_layout()
        
        # Guardar imagen
        fecha_str = fecha.strftime("%Y%m%d")
        filename = f"disponibilidad_{user_id}_{fecha_str}.png"
        filepath = os.path.join(TEMP_DIR, filename)
        
        fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='#f8f9fa')
        plt.close(fig)
        
        return filepath
        
    except Exception as e:
        print(f"❌ Error al generar imagen de disponibilidad: {e}")
        return None


def generar_imagen_disponibilidad_semana(user_id: int, fecha_inicio: datetime, citas_data: list) -> str:
    """
    Genera una imagen de disponibilidad para 7 días a partir de una fecha.
    Una columna por día, eje Y = horas del día. Verde = disponible, Rojo = ocupado.

    Args:
        user_id: ID del usuario
        fecha_inicio: Fecha de inicio de la semana (datetime)
        citas_data: Lista de dicts con claves 'fecha', 'duracion'

    Returns:
        Ruta a la imagen generada
    """
    _asegurar_temp_dir()

    try:
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

        fig, axes = plt.subplots(1, 7, sharey=True, figsize=(14, 10))
        fig.patch.set_facecolor('#f8f9fa')
        fig.subplots_adjust(wspace=0.12)

        titulo = f"Disponibilidad - Semana del {fecha_inicio.strftime('%d de %B')}"
        fig.suptitle(titulo, fontsize=14, fontweight='bold', y=1.01)

        for idx in range(7):
            fecha_dia = fecha_inicio + timedelta(days=idx)
            ax = axes[idx]

            fecha_inicio_dia = fecha_dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin_dia = fecha_dia.replace(hour=23, minute=59, second=59, microsecond=999999)

            citas_del_dia = [
                c for c in citas_data
                if fecha_inicio_dia <= c['fecha'] <= fecha_fin_dia
            ]

            horas_ocupadas = {h: False for h in range(HORAS_INICIO, HORAS_FIN)}
            for cita in citas_del_dia:
                hora_ini = cita['fecha'].hour
                minuto_ini = cita['fecha'].minute
                duracion = cita['duracion']
                minutos_totales = minuto_ini + duracion
                horas_extra = minutos_totales // 60
                minutos_fin = minutos_totales % 60
                hora_fin = hora_ini + horas_extra
                if minutos_fin == 0:
                    horas_a_marcar = range(hora_ini, min(hora_fin, HORAS_FIN))
                else:
                    horas_a_marcar = range(hora_ini, min(hora_fin + 1, HORAS_FIN))
                for h in horas_a_marcar:
                    horas_ocupadas[h] = True

            # Dibujar una barra por hora (barh: eje Y = horas, eje X = ancho fijo)
            for hora in range(HORAS_INICIO, HORAS_FIN):
                color = '#e74c3c' if horas_ocupadas[hora] else '#27ae60'
                ax.barh(hora, 1, height=1, color=color, align='edge', edgecolor='none')

            # Líneas blancas finas entre horas
            for h in range(HORAS_INICIO + 1, HORAS_FIN):
                ax.axhline(h, color='white', linewidth=0.6)

            # Configuración del subplot
            ax.set_xlim(0, 1)
            ax.set_ylim(HORAS_FIN, HORAS_INICIO)  # 00:00 arriba, 24:00 abajo
            ax.set_xticks([])
            ax.set_facecolor('#f8f9fa')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            if idx > 0:
                ax.spines['left'].set_visible(False)

            ax.set_title(
                f"{dias_semana[fecha_dia.weekday()]}\n{fecha_dia.strftime('%d/%m')}",
                fontsize=10, fontweight='bold', pad=6
            )

            # Ticks Y sólo en la primera columna, cada 2 horas
            if idx == 0:
                tick_horas = list(range(HORAS_INICIO, HORAS_FIN + 1, 2))
                ax.set_yticks(tick_horas)
                ax.set_yticklabels([f"{h:02d}:00" for h in tick_horas], fontsize=8)
            else:
                ax.set_yticks([])

        # Leyenda centrada abajo
        disponible = patches.Patch(facecolor='#27ae60', label='✅ Disponible')
        ocupado = patches.Patch(facecolor='#e74c3c', label='❌ Ocupado')
        fig.legend(handles=[disponible, ocupado], loc='lower center',
                   ncol=2, fontsize=10, bbox_to_anchor=(0.5, -0.03))

        plt.tight_layout()

        fecha_str = fecha_inicio.strftime("%Y%m%d")
        filename = f"disponibilidad_semana_{user_id}_{fecha_str}.png"
        filepath = os.path.join(TEMP_DIR, filename)

        fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='#f8f9fa')
        plt.close(fig)

        return filepath

    except Exception as e:
        print(f"❌ Error al generar imagen de disponibilidad semanal: {e}")
        return None


def generar_imagen_disponibilidad_semana_24h(user_id: int, fecha_cualquiera: datetime) -> str:
    """
    Genera una imagen de disponibilidad para una semana completa (24h cada día).
    Si se pasa viernes 12 de Junio, muestra lunes 8 de Junio a domingo 14 de Junio.

    Args:
        user_id: ID del usuario
        fecha_cualquiera: Cualquier fecha de la semana que quieras ver (datetime)

    Returns:
        Ruta a la imagen generada
    """
    _asegurar_temp_dir()

    try:
        # Obtener citas del usuario - DENTRO de la sesión
        with get_session() as session:
            citas = obtener_citas_por_usuario(session, user_id)
            
            # Convertir a diccionarios
            citas_data = [
                {
                    'fecha': c.FECHA,
                    'duracion': c.DURACION if c.DURACION else 60,
                    'descripcion': c.DESCRIPCION
                }
                for c in citas
            ]
        
        # Calcular el lunes de la semana de esa fecha
        dias_desde_lunes = fecha_cualquiera.weekday()
        fecha_lunes = fecha_cualquiera - timedelta(days=dias_desde_lunes)
        fecha_lunes = fecha_lunes.replace(hour=0, minute=0, second=0, microsecond=0)
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

        fig, axes = plt.subplots(1, 7, sharey=True, figsize=(14, 10))
        fig.patch.set_facecolor('#f8f9fa')
        fig.subplots_adjust(wspace=0.12)

        titulo = (
            f"Disponibilidad Semanal - Semana del {fecha_lunes.strftime('%d de %B')} "
            f"al {(fecha_lunes + timedelta(days=6)).strftime('%d de %B')}"
        )
        fig.suptitle(titulo, fontsize=14, fontweight='bold', y=1.01)

        for idx in range(7):
            fecha_dia = fecha_lunes + timedelta(days=idx)
            ax = axes[idx]

            fecha_inicio_dia = fecha_dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin_dia = fecha_dia.replace(hour=23, minute=59, second=59, microsecond=999999)

            citas_del_dia = [
                c for c in citas_data
                if fecha_inicio_dia <= c['fecha'] <= fecha_fin_dia
            ]

            horas_ocupadas = {h: False for h in range(HORAS_INICIO, HORAS_FIN)}
            for cita in citas_del_dia:
                hora_ini = cita['fecha'].hour
                minuto_ini = cita['fecha'].minute
                duracion = cita['duracion']
                minutos_totales = minuto_ini + duracion
                horas_extra = minutos_totales // 60
                minutos_fin = minutos_totales % 60
                hora_fin = hora_ini + horas_extra
                if minutos_fin == 0:
                    horas_a_marcar = range(hora_ini, min(hora_fin, HORAS_FIN))
                else:
                    horas_a_marcar = range(hora_ini, min(hora_fin + 1, HORAS_FIN))
                for h in horas_a_marcar:
                    horas_ocupadas[h] = True

            # Dibujar una barra por hora (barh: eje Y = horas, eje X = ancho fijo)
            for hora in range(HORAS_INICIO, HORAS_FIN):
                color = '#e74c3c' if horas_ocupadas[hora] else '#27ae60'
                ax.barh(hora, 1, height=1, color=color, align='edge', edgecolor='none')

            # Líneas blancas finas entre horas
            for h in range(HORAS_INICIO + 1, HORAS_FIN):
                ax.axhline(h, color='white', linewidth=0.6)

            # Configuración del subplot
            ax.set_xlim(0, 1)
            ax.set_ylim(HORAS_FIN, HORAS_INICIO)  # 00:00 arriba, 24:00 abajo
            ax.set_xticks([])
            ax.set_facecolor('#f8f9fa')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            if idx > 0:
                ax.spines['left'].set_visible(False)

            ax.set_title(
                f"{dias_semana[idx]}\n{fecha_dia.strftime('%d/%m')}",
                fontsize=10, fontweight='bold', pad=6
            )

            # Ticks Y sólo en la primera columna, cada 2 horas
            if idx == 0:
                tick_horas = list(range(HORAS_INICIO, HORAS_FIN + 1, 2))
                ax.set_yticks(tick_horas)
                ax.set_yticklabels([f"{h:02d}:00" for h in tick_horas], fontsize=8)
            else:
                ax.set_yticks([])

        # Leyenda centrada abajo
        disponible = patches.Patch(facecolor='#27ae60', label='✅ Disponible')
        ocupado = patches.Patch(facecolor='#e74c3c', label='❌ Ocupado')
        fig.legend(handles=[disponible, ocupado], loc='lower center',
                   ncol=2, fontsize=10, bbox_to_anchor=(0.5, -0.03))

        plt.tight_layout()

        fecha_str = fecha_lunes.strftime("%Y%m%d")
        filename = f"disponibilidad_semana_24h_{user_id}_{fecha_str}.png"
        filepath = os.path.join(TEMP_DIR, filename)

        fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='#f8f9fa')
        plt.close(fig)

        return filepath

    except Exception as e:
        print(f"❌ Error al generar imagen de disponibilidad semanal 24h: {e}")
        import traceback
        traceback.print_exc()
        return None
