"""Mini-API FastAPI para testing externo del CRUD de base de datos.

Esta API envuelve las funciones de databasecontroller en endpoints HTTP.
El bot de Telegram llama al controller directamente (sin HTTP); esta API
solo se usa para pruebas y herramientas externas.

Arrancar con:
    uvicorn api:app --reload        (desde src/)
    uvicorn src.api:app --reload    (desde la raíz del proyecto)

Documentación interactiva disponible en: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from datetime import date as date_type
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.BBDD.databasecontroller import (
    actualizar_cita,
    actualizar_cita_corp,
    crear_cita,
    crear_cita_corp,
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
    FECHA: datetime
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


@app.post("/usuarios", response_model=UsuarioOut, status_code=201, tags=["Usuarios"])
def post_usuario(body: UsuarioCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario. La contraseña se almacena con hash bcrypt."""
    try:
        return crear_usuario(db, body.TIPO, body.NOMBRE, body.EMAIL, body.CONTRASENA)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/usuarios/{id_usuario}", response_model=UsuarioOut, tags=["Usuarios"])
def get_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = obtener_usuario(db, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@app.delete("/usuarios/{id_usuario}", status_code=204, tags=["Usuarios"])
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
)
def get_contactos_eliminados(id_usuario: int, db: Session = Depends(get_db)):
    """Lista los contactos eliminados (soft-delete) del usuario."""
    try:
        return obtener_contactos_eliminados(db, id_usuario)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/contactos/{id_contacto}", response_model=ContactoOut, tags=["Contactos"])
def get_contacto(id_contacto: int, db: Session = Depends(get_db)):
    contacto = obtener_contacto(db, id_contacto)
    if contacto is None:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contacto


@app.delete("/contactos/{id_contacto}", status_code=204, tags=["Contactos"])
def delete_contacto(id_contacto: int, db: Session = Depends(get_db)):
    """Soft delete: registra la fecha de baja en ELIMINADO."""
    if not eliminar_contacto(db, id_contacto):
        raise HTTPException(
            status_code=404, detail="Contacto no encontrado o ya eliminado"
        )


# ── Endpoints: CITAS (compartidos, dispatch por TIPO de usuario) ───────────────


@app.post("/citas", response_model=CitaOut, status_code=201, tags=["Citas"])
def post_cita(body: CitaCreate, db: Session = Depends(get_db)):
    """Crea una cita.
    - Tipo I: usa ID_USUARIO + FECHA (+ ID_CONTACTO, DESCRIPCION, PRIORIDAD opcionales).
    - Tipo C: usa ID_EMPLEADO + ID_CLIENTE + FECHA (+ DESCRIPCION opcional).
    """
    try:
        usuario = obtener_usuario(db, body.ID_USUARIO)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if usuario.TIPO == "C":
            if body.ID_EMPLEADO is None or body.ID_CLIENTE is None:
                raise HTTPException(
                    status_code=400,
                    detail="Tipo C requiere ID_EMPLEADO e ID_CLIENTE",
                )
            return crear_cita_corp(
                db, body.ID_EMPLEADO, body.ID_CLIENTE, body.FECHA, body.DESCRIPCION, body.DURACION
            )
        return crear_cita(
            db,
            body.ID_USUARIO,
            body.FECHA,
            body.ID_CONTACTO,
            body.DESCRIPCION,
            body.PRIORIDAD,
            body.DURACION,
        )
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


@app.get("/usuarios/{id_usuario}/citas", response_model=list[CitaOut], tags=["Citas"])
def get_citas_usuario(
    id_usuario: int,
    anterior: bool = Query(default=False, description="false → próximas citas desde la fecha dada; true → citas anteriores a la fecha dada"),
    fecha: Optional[str] = Query(default=None, description="Fecha de referencia en ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS). Por defecto: ahora. Si solo se indica fecha, se asume 00:00."),
    db: Session = Depends(get_db),
):
    """Lista las citas activas del usuario filtradas por fecha de referencia.
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
            return obtener_citas_corp_por_usuario(db, id_usuario, fecha_dt, anterior)
        return obtener_citas_por_usuario(db, id_usuario, fecha_dt, anterior)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/usuarios/{id_usuario}/citas/eliminadas",
    response_model=list[CitaOut],
    tags=["Citas"],
)
def get_citas_eliminadas_usuario(
    id_usuario: int,
    anterior: bool = Query(default=False, description="false → próximas citas desde la fecha dada; true → citas anteriores a la fecha dada"),
    fecha: Optional[str] = Query(default=None, description="Fecha de referencia en ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS). Por defecto: ahora. Si solo se indica fecha, se asume 00:00."),
    db: Session = Depends(get_db),
):
    """Lista las citas eliminadas del usuario filtradas por fecha de referencia.
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
            return obtener_citas_corp_eliminadas_por_usuario(db, id_usuario, fecha_dt, anterior)
        return obtener_citas_eliminadas_por_usuario(db, id_usuario, fecha_dt, anterior)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/citas/{id_cita}", response_model=CitaOut, tags=["Citas"])
def get_cita(id_cita: int, db: Session = Depends(get_db)):
    """Obtiene una cita por ID. Busca primero en CITAS_IND, luego en CITAS_COR."""
    cita = obtener_cita(db, id_cita)
    if cita is not None:
        return cita
    cita = obtener_cita_corp(db, id_cita)
    if cita is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita


@app.put("/citas/{id_cita}", response_model=CitaOut, tags=["Citas"])
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


@app.delete("/citas/{id_cita}", status_code=204, tags=["Citas"])
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
)
def get_empleados(id_usuario: int, db: Session = Depends(get_db)):
    """Lista los empleados activos de la corporación."""
    try:
        return obtener_empleados(db, id_usuario)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/empleados/{id_empleado}", response_model=EmpleadoOut, tags=["Empleados"])
def get_empleado(id_empleado: int, db: Session = Depends(get_db)):
    empleado = obtener_empleado(db, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado


@app.delete("/empleados/{id_empleado}", status_code=204, tags=["Empleados"])
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
)
def get_clientes(id_empleado: int, db: Session = Depends(get_db)):
    """Lista los clientes activos del empleado."""
    try:
        return obtener_clientes_por_empleado(db, id_empleado)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/clientes/{id_cliente}", response_model=ClienteOut, tags=["Clientes"])
def get_cliente(id_cliente: int, db: Session = Depends(get_db)):
    cliente = obtener_cliente(db, id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@app.delete("/clientes/{id_cliente}", status_code=204, tags=["Clientes"])
def delete_cliente(id_cliente: int, db: Session = Depends(get_db)):
    """Soft delete del cliente."""
    if not eliminar_cliente(db, id_cliente):
        raise HTTPException(
            status_code=404, detail="Cliente no encontrado o ya eliminado"
        )

