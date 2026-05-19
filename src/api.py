"""Mini-API FastAPI para testing externo del CRUD de base de datos.

Esta API envuelve las funciones de databasecontroller en endpoints HTTP.
El bot de Telegram llama al controller directamente (sin HTTP); esta API
solo se usa para pruebas y herramientas externas.

Arrancar con:
    uvicorn api:app --reload        (desde src/)
    uvicorn src.api:app --reload    (desde la raíz del proyecto)

Documentación interactiva disponible en: http://localhost:8000/docs
"""

import math
from contextlib import asynccontextmanager
from datetime import date as date_type
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.BBDD.databasecontroller import (
    actualizar_cita_corp,
    crear_cita_corp,
    get_citas_cor_en_rango,
    crear_cliente,
    crear_empleado,
    eliminar_cita_corp,
    eliminar_cliente,
    eliminar_empleado,
    get_db,
    init_db,
    obtener_cita_corp,
    obtener_citas_cliente,
    obtener_citas_cliente_eliminadas,
    obtener_citas_empleado,
    obtener_cliente,
    obtener_cliente_por_telegram,
    obtener_clientes_por_empleado,
    obtener_empleado,
    obtener_empleado_por_nombre,
    obtener_empleados,
    obtener_o_crear_cliente_telegram,
)


PAGE_SIZE = 9

# ── Respuestas Swagger reutilizables ──────────────────────────────────────────
_R400 = {400: {"description": "Datos inválidos o regla de negocio no cumplida."}}
_R404 = {404: {"description": "Recurso no encontrado."}}
_R409 = {
    409: {
        "description": (
            "Conflicto de disponibilidad (solo `POST /citas` con `bloqueante` > 0).\n\n"
            "Posibles valores de `detail`:\n"
            "- **Slot ocupado con alternativas**: `Horario no disponible. "
            "Otras fechas cercanas que podrían interesarte: DD/MM/YYYY HH:MM  DD/MM/YYYY HH:MM` "
            "— el campo `detail` incluye hasta dos huecos libres cercanos.\n"
            "- **Sin huecos en el rango**: `Cita no guardada. Ninguna cita disponible para este periodo.`"
        ),
        "content": {
            "application/json": {
                "examples": {
                    "slot_ocupado": {
                        "summary": "Slot ocupado — con alternativas",
                        "value": {
                            "detail": (
                                "Horario no disponible. "
                                "Otras fechas cercanas que podrían interesarte: "
                                "28/04/2026 09:00  28/04/2026 11:00"
                            )
                        },
                    },
                    "sin_huecos": {
                        "summary": "Sin huecos disponibles en el rango",
                        "value": {
                            "detail": "Cita no guardada. Ninguna cita disponible para este periodo."
                        },
                    },
                }
            }
        },
    }
}
_R500 = {500: {"description": "Error interno al generar la imagen."}}
_R_PNG = {
    200: {"description": "Imagen PNG de disponibilidad.", "content": {"image/png": {}}}
}

# ── Ciclo de vida ──────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    init_db()
    yield


app = FastAPI(
    title="PS-Chatbot API",
    version="0.1.0",
    description="CRUD de usuarios, contactos y citas para el bot de Telegram.",
    lifespan=lifespan,
)


# ── Schemas Pydantic ───────────────────────────────────────────────────────────


class EmpleadoCreate(BaseModel):
    TIPO: str  # 'senior' | 'junior'
    NOMBRE: str
    EMAIL: str
    CONTRASENA: str


class EmpleadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_EMPLEADO: int
    TIPO: str
    NOMBRE: str
    EMAIL: str
    ELIMINADO: Optional[datetime]


class ClienteCreate(BaseModel):
    NOMBRE: str
    TELEGRAM_ID: Optional[int] = None
    EMAIL: Optional[str] = None
    TELEFONO: Optional[str] = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_CLIENTE: int
    NOMBRE: str
    TELEGRAM_ID: Optional[int]
    EMAIL: Optional[str]
    TELEFONO: Optional[str]
    ELIMINADO: Optional[datetime]


class CitaCorpCreate(BaseModel):
    ID_EMPLEADO: int
    ID_CLIENTE: int
    FECHA: Optional[datetime] = None  # por omisión: datetime.now()
    DESCRIPCION: Optional[str] = None
    DURACION: Optional[int] = None  # minutos
    bloqueante: int = Query(
        default=0,
        description="0 = sin comprobación de disponibilidad. N > 0 = busca hueco libre en ±N días.",
    )


class CitaCorpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_CITA: int
    ID_EMPLEADO: int
    ID_CLIENTE: int
    DESCRIPCION: Optional[str]
    FECHA: datetime
    DURACION: Optional[int]  # minutos
    ELIMINADO: Optional[datetime]
    ELIMINADO: Optional[datetime]


# ── Endpoints: CITAS (compartidos, dispatch por TIPO de usuario) ───────────────


def _buscar_disponibilidad(
    citas: list,
    fecha_ref: datetime,
    duracion_min: int,
    range_start: datetime,
    range_end: datetime,
) -> tuple[str, Optional[datetime], Optional[datetime]]:
    """Busca disponibilidad para una cita de `duracion_min` minutos en `fecha_ref`.

    Devuelve una tupla (estado, antes, después):
    - ("available", None, None): el slot original está libre, se puede insertar.
    - ("unavailable", dt_antes, dt_después): slot ocupado; dt_* son los huecos
      alternativos más cercanos (pueden ser None si no existe en esa dirección).
    - ("no_space", None, None): no hay ningún hueco válido en el rango.
    """
    dur = timedelta(minutes=duracion_min)

    # Construir intervalos ocupados (datetime naive)
    intervals: list[tuple[datetime, datetime]] = []
    for c in citas:
        start = c.FECHA.replace(tzinfo=None) if c.FECHA.tzinfo is not None else c.FECHA
        end = start + timedelta(minutes=c.DURACION if c.DURACION is not None else 60)
        intervals.append((start, end))

    intervals.sort(key=lambda x: x[0])

    # Mergear intervalos solapados
    merged: list[list[datetime]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # Calcular huecos libres dentro de [range_start, range_end]
    free_gaps: list[tuple[datetime, datetime]] = []
    cursor = range_start
    for busy_start, busy_end in merged:
        if busy_start >= range_end:
            break
        if busy_end <= range_start:
            continue
        gap_end = min(busy_start, range_end)
        if gap_end > cursor:
            free_gaps.append((cursor, gap_end))
        cursor = max(cursor, busy_end)
    if cursor < range_end:
        free_gaps.append((cursor, range_end))

    # Filtrar huecos que pueden albergar la cita
    viable = [(gs, ge) for gs, ge in free_gaps if ge - gs >= dur]

    # ¿El slot original está libre?
    slot_end = fecha_ref + dur
    for gs, ge in viable:
        if gs <= fecha_ref and ge >= slot_end:
            return ("available", None, None)

    # Buscar candidatos antes y después
    before_candidate: Optional[datetime] = None
    after_candidate: Optional[datetime] = None

    for gs, ge in viable:
        latest_start = ge - dur
        if latest_start < fecha_ref:  # hueco está antes de fecha_ref
            if before_candidate is None or latest_start > before_candidate:
                before_candidate = latest_start
        elif gs > fecha_ref:  # hueco está después de fecha_ref
            if after_candidate is None or gs < after_candidate:
                after_candidate = gs

    if before_candidate is None and after_candidate is None:
        return ("no_space", None, None)

    return ("unavailable", before_candidate, after_candidate)


@app.post(
    "/citas",
    response_model=CitaCorpOut,
    status_code=201,
    tags=["Citas"],
    responses={**_R400, **_R404, **_R409},
)
def post_cita(
    body: CitaCorpCreate,
    bloqueante: int = Query(
        default=0,
        description="0 = sin comprobación de disponibilidad. N > 0 = busca hueco libre en ±N días.",
    ),
    db: Session = Depends(get_db),
):
    """Crea una cita corporativa (Empleado ↔ Cliente).

    Si `bloqueante` es 0 (valor por defecto) se inserta sin comprobación de disponibilidad.
    Si `bloqueante` es N > 0 se verifica que el slot esté libre en el calendario;
    si está ocupado se devuelven alternativas dentro de ±N días.
    """
    fecha_ref = body.FECHA if body.FECHA is not None else datetime.now()
    # Asegurar datetime naive para consistencia con la BD
    if fecha_ref.tzinfo is not None:
        fecha_ref = fecha_ref.replace(tzinfo=None)

    try:
        # Validar que empleado y cliente existan
        empleado = obtener_empleado(db, body.ID_EMPLEADO)
        if empleado is None:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        cliente = obtener_cliente(db, body.ID_CLIENTE)
        if cliente is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # ── Comprobación de disponibilidad (solo si bloqueante != 0) ─────────────────
        if bloqueante != 0:
            duracion_efectiva = body.DURACION if body.DURACION is not None else 60
            range_start = (fecha_ref - timedelta(days=bloqueante)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            range_end = (fecha_ref + timedelta(days=bloqueante)).replace(
                hour=23, minute=59, second=59, microsecond=0
            )

            citas = get_citas_cor_en_rango(db, body.ID_EMPLEADO, range_start, range_end)

            estado, antes, despues = _buscar_disponibilidad(
                citas, fecha_ref, duracion_efectiva, range_start, range_end
            )

            if estado == "no_space":
                raise HTTPException(
                    status_code=409,
                    detail="Cita no guardada. Ninguna cita disponible para este periodo.",
                )

            if estado == "unavailable":
                fmt = "%d/%m/%Y %H:%M"
                alternativas = [
                    (abs((dt - fecha_ref).total_seconds()), dt)
                    for dt in (antes, despues)
                    if dt is not None
                ]
                alternativas.sort(key=lambda x: x[0])
                fechas_str = "  ".join(dt.strftime(fmt) for _, dt in alternativas)
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Horario no disponible. "
                        f"Otras fechas cercanas que podrían interesarte: {fechas_str}"
                    ),
                )

        # ── Inserción ──────────────────────────────────────────────────
        return crear_cita_corp(
            db,
            body.ID_EMPLEADO,
            body.ID_CLIENTE,
            body.FECHA,
            body.DESCRIPCION,
            body.DURACION,
        )
    except HTTPException:
        raise
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


def _parse_fecha(fecha_str: Optional[str]) -> datetime:
    """Parsea un string de fecha ISO 8601. Si solo se indica fecha sin hora, asume 00:00.
    Si no se indica nada, devuelve la fecha y hora actuales.
    """
    if fecha_str is None:
        return datetime.now()
    try:
        return datetime.fromisoformat(fecha_str)
    except ValueError:
        pass
    try:
        d = date_type.fromisoformat(fecha_str)
        return datetime(d.year, d.month, d.day, 0, 0, 0)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Formato de fecha inválido. Use ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)",
        )


@app.get(
    "/empleados",
    response_model=list[EmpleadoOut],
    tags=["Empleados"],
    responses={**_R404},
)
def get_empleados_list(db: Session = Depends(get_db)):
    """Lista todos los empleados activos."""
    return obtener_empleados(db)


@app.get(
    "/empleados/by-nombre/{nombre}",
    response_model=EmpleadoOut,
    tags=["Empleados"],
    responses={**_R404},
)
def get_empleado_por_nombre(nombre: str, db: Session = Depends(get_db)):
    """Busca un empleado por nombre (búsqueda case-insensitive)."""
    empleado = obtener_empleado_por_nombre(db, nombre)
    if empleado is None:
        raise HTTPException(
            status_code=404, detail=f"Empleado con nombre '{nombre}' no encontrado"
        )
    return empleado


@app.get(
    "/empleados/{id_empleado}",
    response_model=EmpleadoOut,
    tags=["Empleados"],
    responses={**_R404},
)
def get_empleado(id_empleado: int, db: Session = Depends(get_db)):
    empleado = obtener_empleado(db, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado


@app.delete(
    "/empleados/{id_empleado}", status_code=204, tags=["Empleados"], responses={**_R404}
)
def delete_empleado(id_empleado: int, db: Session = Depends(get_db)):
    """Soft delete del empleado."""
    if not eliminar_empleado(db, id_empleado):
        raise HTTPException(
            status_code=404, detail="Empleado no encontrado o ya eliminado"
        )


# ── Endpoints: CLIENTES ────────────────────────────────────────────────────────


@app.post(
    "/clientes",
    response_model=ClienteOut,
    status_code=201,
    tags=["Clientes"],
    responses={**_R400},
)
def post_cliente(body: ClienteCreate, db: Session = Depends(get_db)):
    """Registra un nuevo cliente."""
    try:
        return crear_cliente(
            db, body.NOMBRE, body.TELEGRAM_ID, body.EMAIL, body.TELEFONO
        )
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/clientes",
    response_model=list[ClienteOut],
    tags=["Clientes"],
    responses={**_R404},
)
def get_clientes_list(db: Session = Depends(get_db)):
    """Lista todos los clientes activos."""
    # Esta función necesita ser creada en databasecontroller
    from sqlalchemy import func

    with db:
        from src.BBDD.databasecontroller import Cliente

        return db.query(Cliente).filter(Cliente.ELIMINADO.is_(None)).all()


@app.get(
    "/clientes/{id_cliente}",
    response_model=ClienteOut,
    tags=["Clientes"],
    responses={**_R404},
)
def get_cliente(id_cliente: int, db: Session = Depends(get_db)):
    cliente = obtener_cliente(db, id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@app.delete(
    "/clientes/{id_cliente}", status_code=204, tags=["Clientes"], responses={**_R404}
)
def delete_cliente(id_cliente: int, db: Session = Depends(get_db)):
    """Soft delete del cliente."""
    if not eliminar_cliente(db, id_cliente):
        raise HTTPException(
            status_code=404, detail="Cliente no encontrado o ya eliminado"
        )
