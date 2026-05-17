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
            
            # Duración por defecto 1 hora si no está especificada
            duracion = cita['duracion']
            
            # Calcular hora de fin
            minutos_totales = minuto_inicio + duracion
            horas_ocupadas_por_cita = minutos_totales // 60
            
            # Marcar todas las horas que ocupan
            for h in range(hora_inicio, min(hora_inicio + horas_ocupadas_por_cita + 1, HORAS_FIN)):
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


def generar_imagen_disponibilidad_semana(user_id: int, fecha_inicio: datetime) -> str:
    """
    Genera una imagen de disponibilidad para 7 días a partir de una fecha.
    
    Args:
        user_id: ID del usuario
        fecha_inicio: Fecha de inicio de la semana (datetime)
        
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
        
        # Crear figura con subplots (7 días)
        fig, axes = plt.subplots(7, 1, figsize=(20, 12))
        fig.patch.set_facecolor('#f8f9fa')
        
        titulo = f"Disponibilidad - Semana del {fecha_inicio.strftime('%d de %B')}"
        fig.suptitle(titulo, fontsize=16, fontweight='bold')
        
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        for idx in range(7):
            fecha_dia = fecha_inicio + timedelta(days=idx)
            ax = axes[idx]
            
            # Filtrar citas del día
            fecha_inicio_dia = fecha_dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin_dia = fecha_dia.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            citas_del_dia = [
                c for c in citas_data
                if fecha_inicio_dia <= c['fecha'] <= fecha_fin_dia
            ]
            
            # Configurar ejes
            ax.set_title(f"{dias_semana[fecha_dia.weekday()]} - {fecha_dia.strftime('%d/%m/%Y')}", 
                        fontsize=11, fontweight='bold', loc='left')
            ax.set_ylim(0, 1)
            ax.set_xlim(HORAS_INICIO - 0.5, HORAS_FIN + 0.5)
            ax.set_yticks([])
            
            horas = list(range(HORAS_INICIO, HORAS_FIN + 1))
            ax.set_xticks(horas)
            ax.set_xticklabels([f"{h:02d}:00" for h in horas], fontsize=8)
            ax.grid(axis='x', alpha=0.3, linestyle='--')
            
            # Crear matriz de horas ocupadas
            horas_ocupadas = {h: False for h in range(HORAS_INICIO, HORAS_FIN)}
            
            # Marcar horas ocupadas
            for cita in citas_del_dia:
                hora_inicio = cita['fecha'].hour
                duracion = cita['duracion']
                minutos_totales = cita.FECHA.minute + duracion
                horas_ocupadas_por_cita = minutos_totales // 60
                
                for h in range(hora_inicio, min(hora_inicio + horas_ocupadas_por_cita + 1, HORAS_FIN)):
                    horas_ocupadas[h] = True
            
            # Dibujar bloques
            for hora in range(HORAS_INICIO, HORAS_FIN):
                x_start = hora
                x_width = 0.8
                
                color = '#e74c3c' if horas_ocupadas.get(hora, False) else '#27ae60'
                
                rect = patches.Rectangle(
                    (x_start - x_width/2, 0.2),
                    x_width,
                    0.6,
                    linewidth=1.5,
                    edgecolor='#2c3e50',
                    facecolor=color,
                    alpha=0.8
                )
                ax.add_patch(rect)
        
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
