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
    actualizar_cita,
    actualizar_cita_corp,
    crear_cita,
    crear_cita_corp,
    get_citas_cor_en_rango,
    get_citas_ind_en_rango,
    crear_cliente,
    crear_contacto,
    crear_empleado,
    crear_usuario,
    eliminar_cita,
    eliminar_cita_corp,
    eliminar_cliente,
    eliminar_contacto,
    eliminar_empleado,
    eliminar_usuario,
    get_db,
    init_db,
    obtener_cita,
    obtener_cita_corp,
    obtener_citas_corp_eliminadas_por_usuario,
    obtener_citas_corp_por_usuario,
    obtener_citas_eliminadas_por_usuario,
    obtener_citas_por_usuario,
    obtener_cliente,
    obtener_clientes_por_empleado,
    obtener_contacto,
    obtener_contactos,
    obtener_contactos_eliminados,
    obtener_empleado,
    obtener_empleados,
    obtener_usuario,
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
_R_PNG = {200: {"description": "Imagen PNG de disponibilidad.", "content": {"image/png": {}}}}

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


class UsuarioCreate(BaseModel):
    TIPO: str = "I"
    NOMBRE: str
    EMAIL: str
    CONTRASENA: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_USUARIO: int
    TIPO: str
    NOMBRE: str
    EMAIL: str
    ELIMINADO: Optional[datetime]


class ContactoCreate(BaseModel):
    NOMBRE: str
    EMAIL: Optional[str] = None


class ContactoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_CONTACTO: int
    ID_USUARIO: Optional[int]
    NOMBRE: str
    EMAIL: Optional[str]
    ELIMINADO: Optional[datetime]


class CitaCreate(BaseModel):
    # Tipo I: requiere ID_USUARIO; ID_CONTACTO opcional
    ID_USUARIO: int
    ID_CONTACTO: Optional[int] = None
    FECHA: Optional[datetime] = None  # por omisión: datetime.now()
    DESCRIPCION: Optional[str] = None
    PRIORIDAD: int = 1
    # Tipo C: requiere ID_EMPLEADO + ID_CLIENTE
    ID_EMPLEADO: Optional[int] = None
    ID_CLIENTE: Optional[int] = None
    # Ambos tipos
    DURACION: Optional[int] = None  # minutos


class CitaUpdate(BaseModel):
    FECHA: Optional[datetime] = None
    DESCRIPCION: Optional[str] = None
    PRIORIDAD: Optional[int] = None  # solo tipo I
    DURACION: Optional[int] = None   # ambos tipos, minutos


class CitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_CITA: int
    # Tipo I
    ID_USUARIO: Optional[int] = None
    ID_CONTACTO: Optional[int] = None
    PRIORIDAD: Optional[int] = None
    # Tipo C
    ID_EMPLEADO: Optional[int] = None
    ID_CLIENTE: Optional[int] = None
    # Comunes
    DESCRIPCION: Optional[str]
    FECHA: datetime
    DURACION: Optional[int] = None  # minutos
    ELIMINADO: Optional[datetime]


class CitaPage(BaseModel):
    items: list[CitaOut]
    lastpage: int


class EmpleadoCreate(BaseModel):
    TIPO: str = "E"  # 'A' = Admin | 'E' = Empleado
    NOMBRE: str
    CONTRASENA_CORP: str | None = None
    ID_ADMIN: Optional[int] = None


class EmpleadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_EMPLEADO: int
    ID_USUARIO: Optional[int]
    ID_ADMIN: Optional[int]
    TIPO: str
    NOMBRE: str
    ELIMINADO: Optional[datetime]


class ClienteCreate(BaseModel):
    DNI: str
    NOMBRE: str
    ID_EMPLEADO_USUAL: Optional[int] = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_CLIENTE: int
    ID_EMPLEADO_USUAL: Optional[int]
    DNI: str
    NOMBRE: str
    ELIMINADO: Optional[datetime]


# ── Endpoints: USUARIOS ────────────────────────────────────────────────────────


@app.post("/usuarios", response_model=UsuarioOut, status_code=201, tags=["Usuarios"], responses={**_R400})
def post_usuario(body: UsuarioCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario. La contraseña se almacena con hash bcrypt."""
    try:
        return crear_usuario(db, body.TIPO, body.NOMBRE, body.EMAIL, body.CONTRASENA)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/usuarios/{id_usuario}", response_model=UsuarioOut, tags=["Usuarios"], responses={**_R404})
def get_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = obtener_usuario(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@app.delete("/usuarios/{id_usuario}", status_code=204, tags=["Usuarios"], responses={**_R404})
def delete_usuario(id_usuario: int, db: Session = Depends(get_db)):
    """Soft delete: registra la fecha de baja en ELIMINADO."""
    if not eliminar_usuario(db, id_usuario):
        raise HTTPException(
            status_code=404, detail="Usuario no encontrado o ya eliminado"
        )


# ── Endpoints: CONTACTOS ───────────────────────────────────────────────────────


@app.post(
    "/usuarios/{id_usuario}/contactos",
    response_model=ContactoOut,
    status_code=201,
    tags=["Contactos"],
    responses={**_R400, **_R404},
)
def post_contacto(id_usuario: int, body: ContactoCreate, db: Session = Depends(get_db)):
    """Añade un profesional (contacto) a la agenda del usuario."""
    try:
        return crear_contacto(db, id_usuario, body.NOMBRE, body.EMAIL)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/usuarios/{id_usuario}/contactos",
    response_model=list[ContactoOut],
    tags=["Contactos"],
    responses={**_R400, **_R404},
)
def get_contactos(id_usuario: int, db: Session = Depends(get_db)):
    """Lista los contactos activos del usuario."""
    try:
        return obtener_contactos(db, id_usuario)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/usuarios/{id_usuario}/contactos/eliminados",
    response_model=list[ContactoOut],
    tags=["Contactos"],
    responses={**_R400, **_R404},
)
def get_contactos_eliminados(id_usuario: int, db: Session = Depends(get_db)):
    """Lista los contactos eliminados (soft-delete) del usuario."""
    try:
        return obtener_contactos_eliminados(db, id_usuario)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/contactos/{id_contacto}", response_model=ContactoOut, tags=["Contactos"], responses={**_R404})
def get_contacto(id_contacto: int, db: Session = Depends(get_db)):
    contacto = obtener_contacto(db, id_contacto)
    if contacto is None:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contacto


@app.delete("/contactos/{id_contacto}", status_code=204, tags=["Contactos"], responses={**_R404})
def delete_contacto(id_contacto: int, db: Session = Depends(get_db)):
    """Soft delete: registra la fecha de baja en ELIMINADO."""
    if not eliminar_contacto(db, id_contacto):
        raise HTTPException(
            status_code=404, detail="Contacto no encontrado o ya eliminado"
        )


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


@app.post("/citas", response_model=CitaOut, status_code=201, tags=["Citas"], responses={**_R400, **_R404, **_R409})
def post_cita(
    body: CitaCreate,
    bloqueante: int = Query(
        default=0,
        description="0 = sin comprobación de disponibilidad. N > 0 = busca hueco libre en ±N días.",
    ),
    db: Session = Depends(get_db),
):
    """Crea una cita.
    - Tipo I: usa ID_USUARIO en el body + FECHA (+ ID_CONTACTO, DESCRIPCION, PRIORIDAD opcionales).
    - Tipo C: usa ID_EMPLEADO + ID_CLIENTE en el body + FECHA (+ DESCRIPCION opcional).

    Si `bloqueante` es 0 (valor por defecto) se inserta sin comprobación de disponibilidad.
    Si `bloqueante` es N > 0 se verifica que el slot esté libre en el calendario;
    si está ocupado se devuelven alternativas dentro de ±N días.
    """
    fecha_ref = body.FECHA if body.FECHA is not None else datetime.now()
    # Asegurar datetime naive para consistencia con la BD
    if fecha_ref.tzinfo is not None:
        fecha_ref = fecha_ref.replace(tzinfo=None)

    try:
        usuario = obtener_usuario(db, body.ID_USUARIO)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        es_corp = usuario.TIPO == "C"

        if es_corp and (body.ID_EMPLEADO is None or body.ID_CLIENTE is None):
            raise HTTPException(
                status_code=400,
                detail="Tipo C requiere ID_EMPLEADO e ID_CLIENTE",
            )

        # ── Comprobación de disponibilidad (solo si bloqueante != 0) ─────────────────
        if bloqueante != 0:
            duracion_efectiva = body.DURACION if body.DURACION is not None else 60
            range_start = (fecha_ref - timedelta(days=bloqueante)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            range_end = (fecha_ref + timedelta(days=bloqueante)).replace(
                hour=23, minute=59, second=59, microsecond=0
            )

            if es_corp:
                citas = get_citas_cor_en_rango(db, body.ID_EMPLEADO, range_start, range_end)
            else:
                citas = get_citas_ind_en_rango(db, range_start, range_end)

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
            # estado == "available" → continuar con la inserción normal

        # ── Inserción ──────────────────────────────────────────────────
        if es_corp:
            return crear_cita_corp(
                db, body.ID_EMPLEADO, body.ID_CLIENTE, fecha_ref, body.DESCRIPCION, body.DURACION
            )
        return crear_cita(
            db,
            body.ID_USUARIO,
            fecha_ref,
            body.ID_CONTACTO,
            body.DESCRIPCION,
            body.PRIORIDAD,
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


@app.get("/usuarios/{id_usuario}/citas", response_model=CitaPage, tags=["Citas"], responses={**_R400, **_R404})
def get_citas_usuario(
    id_usuario: int,
    anterior: bool = Query(default=False, description="false → próximas citas desde la fecha dada; true → citas anteriores a la fecha dada"),
    fecha: Optional[str] = Query(default=None, description="Fecha de referencia en ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS). Por defecto: ahora. Si solo se indica fecha, se asume 00:00."),
    page: int = Query(default=0, description="Página a devolver (1-indexado). 0 = sin paginación, devuelve todos. Tamaño fijo de 9 elementos por página."),
    db: Session = Depends(get_db),
):
    """Lista las citas activas del usuario filtradas por fecha de referencia, con paginación.
    - anterior=false (defecto): citas desde 'fecha' en adelante, más cercanas primero.
    - anterior=true: citas anteriores a 'fecha', más cercanas primero.
    Tipo I: citas individuales. Tipo C: citas de todos sus empleados.
    """
    fecha_dt = _parse_fecha(fecha)
    try:
        usuario = obtener_usuario(db, id_usuario)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if usuario.TIPO == "C":
            citas = obtener_citas_corp_por_usuario(db, id_usuario, fecha_dt, anterior)
        else:
            citas = obtener_citas_por_usuario(db, id_usuario, fecha_dt, anterior)
        total = len(citas)
        lastpage = math.ceil(total / PAGE_SIZE) if total > 0 else 1
        if page == 0:
            return CitaPage(items=citas, lastpage=lastpage)
        offset = (page - 1) * PAGE_SIZE
        return CitaPage(items=citas[offset:offset + PAGE_SIZE], lastpage=lastpage)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/usuarios/{id_usuario}/citas/eliminadas",
    response_model=CitaPage,
    tags=["Citas"],
    responses={**_R400, **_R404},
)
def get_citas_eliminadas_usuario(
    id_usuario: int,
    anterior: bool = Query(default=False, description="false → próximas citas desde la fecha dada; true → citas anteriores a la fecha dada"),
    fecha: Optional[str] = Query(default=None, description="Fecha de referencia en ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS). Por defecto: ahora. Si solo se indica fecha, se asume 00:00."),
    page: int = Query(default=0, description="Página a devolver (1-indexado). 0 = sin paginación, devuelve todos. Tamaño fijo de 9 elementos por página."),
    db: Session = Depends(get_db),
):
    """Lista las citas eliminadas del usuario filtradas por fecha de referencia, con paginación.
    - anterior=false (defecto): citas desde 'fecha' en adelante, más cercanas primero.
    - anterior=true: citas anteriores a 'fecha', más cercanas primero.
    Tipo I: citas individuales eliminadas. Tipo C: citas corp eliminadas.
    """
    fecha_dt = _parse_fecha(fecha)
    try:
        usuario = obtener_usuario(db, id_usuario)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if usuario.TIPO == "C":
            citas = obtener_citas_corp_eliminadas_por_usuario(db, id_usuario, fecha_dt, anterior)
        else:
            citas = obtener_citas_eliminadas_por_usuario(db, id_usuario, fecha_dt, anterior)
        total = len(citas)
        lastpage = math.ceil(total / PAGE_SIZE) if total > 0 else 1
        if page == 0:
            return CitaPage(items=citas, lastpage=lastpage)
        offset = (page - 1) * PAGE_SIZE
        return CitaPage(items=citas[offset:offset + PAGE_SIZE], lastpage=lastpage)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/citas/{id_cita}", response_model=CitaOut, tags=["Citas"], responses={**_R404})
def get_cita(id_cita: int, db: Session = Depends(get_db)):
    """Obtiene una cita por ID. Busca primero en CITAS_IND, luego en CITAS_COR."""
    cita = obtener_cita(db, id_cita)
    if cita is not None:
        return cita
    cita = obtener_cita_corp(db, id_cita)
    if cita is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita


@app.put("/citas/{id_cita}", response_model=CitaOut, tags=["Citas"], responses={**_R400, **_R404})
def put_cita(id_cita: int, body: CitaUpdate, db: Session = Depends(get_db)):
    """Actualiza una cita. Busca primero en CITAS_IND, luego en CITAS_COR.
    PRIORIDAD solo aplica a citas individuales.
    """
    cita = actualizar_cita(db, id_cita, body.FECHA, body.DESCRIPCION, body.PRIORIDAD, body.DURACION)
    if cita is not None:
        return cita
    cita = actualizar_cita_corp(db, id_cita, body.FECHA, body.DESCRIPCION, body.DURACION)
    if cita is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita


@app.delete("/citas/{id_cita}", status_code=204, tags=["Citas"], responses={**_R404})
def delete_cita(id_cita: int, db: Session = Depends(get_db)):
    """Soft delete. Busca primero en CITAS_IND, luego en CITAS_COR."""
    if eliminar_cita(db, id_cita):
        return
    if eliminar_cita_corp(db, id_cita):
        return
    raise HTTPException(status_code=404, detail="Cita no encontrada o ya eliminada")


# ── Endpoints: EMPLEADOS ───────────────────────────────────────────────────────


@app.post(
    "/usuarios/{id_usuario}/empleados",
    response_model=EmpleadoOut,
    status_code=201,
    tags=["Empleados"],
    responses={**_R400, **_R404},
)
def post_empleado(id_usuario: int, body: EmpleadoCreate, db: Session = Depends(get_db)):
    """Añade un empleado a la corporación. Solo para usuarios TIPO='C'."""
    try:
        return crear_empleado(
            db, id_usuario, body.TIPO, body.NOMBRE, body.CONTRASENA_CORP, body.ID_ADMIN
        )
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/usuarios/{id_usuario}/empleados",
    response_model=list[EmpleadoOut],
    tags=["Empleados"],
    responses={**_R400, **_R404},
)
def get_empleados(id_usuario: int, db: Session = Depends(get_db)):
    """Lista los empleados activos de la corporación."""
    try:
        return obtener_empleados(db, id_usuario)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/empleados/{id_empleado}", response_model=EmpleadoOut, tags=["Empleados"], responses={**_R404})
def get_empleado(id_empleado: int, db: Session = Depends(get_db)):
    empleado = obtener_empleado(db, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado


@app.delete("/empleados/{id_empleado}", status_code=204, tags=["Empleados"], responses={**_R404})
def delete_empleado(id_empleado: int, db: Session = Depends(get_db)):
    """Soft delete del empleado."""
    if not eliminar_empleado(db, id_empleado):
        raise HTTPException(
            status_code=404, detail="Empleado no encontrado o ya eliminado"
        )


# ── Endpoints: CLIENTES ────────────────────────────────────────────────────────


@app.post(
    "/empleados/{id_empleado}/clientes",
    response_model=ClienteOut,
    status_code=201,
    tags=["Clientes"],
    responses={**_R400, **_R404},
)
def post_cliente(id_empleado: int, body: ClienteCreate, db: Session = Depends(get_db)):
    """Registra un nuevo cliente asignado a un empleado."""
    try:
        return crear_cliente(
            db, id_empleado, body.DNI, body.NOMBRE, body.ID_EMPLEADO_USUAL
        )
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/empleados/{id_empleado}/clientes",
    response_model=list[ClienteOut],
    tags=["Clientes"],
    responses={**_R400, **_R404},
)
def get_clientes(id_empleado: int, db: Session = Depends(get_db)):
    """Lista los clientes activos del empleado."""
    try:
        return obtener_clientes_por_empleado(db, id_empleado)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/clientes/{id_cliente}", response_model=ClienteOut, tags=["Clientes"], responses={**_R404})
def get_cliente(id_cliente: int, db: Session = Depends(get_db)):
    cliente = obtener_cliente(db, id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@app.delete("/clientes/{id_cliente}", status_code=204, tags=["Clientes"], responses={**_R404})
def delete_cliente(id_cliente: int, db: Session = Depends(get_db)):
    """Soft delete del cliente."""
    if not eliminar_cliente(db, id_cliente):
        raise HTTPException(
            status_code=404, detail="Cliente no encontrado o ya eliminado"
        )


# ── Endpoints: VISUALIZACIÓN ─────────────────────────────────────────────────────


@app.get(
    "/usuarios/{id_usuario}/disponibilidad/dia",
    response_class=FileResponse,
    tags=["Visualización"],
    responses={**_R_PNG, **_R404, **_R500},
)
def get_disponibilidad_dia(
    id_usuario: int,
    fecha: Optional[str] = Query(default=None, description="Fecha en ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS). Por defecto: hoy."),
    db: Session = Depends(get_db),
):
    """Devuelve una imagen PNG con la disponibilidad horaria del usuario para un día."""
    from src.services.visualization_service import generar_imagen_disponibilidad
    fecha_dt = _parse_fecha(fecha)
    usuario = obtener_usuario(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    citas = obtener_citas_por_usuario(db, id_usuario)
    citas_data = [
        {'fecha': c.FECHA, 'duracion': c.DURACION if c.DURACION else 60, 'descripcion': c.DESCRIPCION}
        for c in citas
    ]
    filepath = generar_imagen_disponibilidad(id_usuario, fecha_dt, citas_data)
    if filepath is None:
        raise HTTPException(status_code=500, detail="Error al generar la imagen")
    return FileResponse(filepath, media_type="image/png", filename="disponibilidad_dia.png")


@app.get(
    "/usuarios/{id_usuario}/disponibilidad/semana",
    response_class=FileResponse,
    tags=["Visualización"],
    responses={**_R_PNG, **_R404, **_R500},
)
def get_disponibilidad_semana(
    id_usuario: int,
    fecha: Optional[str] = Query(default=None, description="Fecha de inicio de semana en ISO 8601. Por defecto: hoy."),
    db: Session = Depends(get_db),
):
    """Devuelve una imagen PNG con la disponibilidad para 7 días a partir de la fecha."""
    from src.services.visualization_service import generar_imagen_disponibilidad_semana
    fecha_dt = _parse_fecha(fecha)
    usuario = obtener_usuario(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    citas = obtener_citas_por_usuario(db, id_usuario)
    citas_data = [
        {'fecha': c.FECHA, 'duracion': c.DURACION if c.DURACION else 60}
        for c in citas
    ]
    filepath = generar_imagen_disponibilidad_semana(id_usuario, fecha_dt, citas_data)
    if filepath is None:
        raise HTTPException(status_code=500, detail="Error al generar la imagen")
    return FileResponse(filepath, media_type="image/png", filename="disponibilidad_semana.png")


@app.get(
    "/usuarios/{id_usuario}/disponibilidad/semana-completa",
    response_class=FileResponse,
    tags=["Visualización"],
    responses={**_R_PNG, **_R404, **_R500},
)
def get_disponibilidad_semana_completa(
    id_usuario: int,
    fecha: Optional[str] = Query(default=None, description="Cualquier fecha de la semana en ISO 8601. Por defecto: hoy."),
    db: Session = Depends(get_db),
):
    """Devuelve una imagen PNG con la disponibilidad de la semana completa (lunes–domingo) que contiene la fecha."""
    from src.services.visualization_service import generar_imagen_disponibilidad_semana_24h
    fecha_dt = _parse_fecha(fecha)
    usuario = obtener_usuario(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    citas = obtener_citas_por_usuario(db, id_usuario)
    citas_data = [
        {'fecha': c.FECHA, 'duracion': c.DURACION if c.DURACION else 60}
        for c in citas
    ]
    filepath = generar_imagen_disponibilidad_semana_24h(id_usuario, fecha_dt, citas_data)
    if filepath is None:
        raise HTTPException(status_code=500, detail="Error al generar la imagen")
    return FileResponse(filepath, media_type="image/png", filename="disponibilidad_semana_completa.png")

