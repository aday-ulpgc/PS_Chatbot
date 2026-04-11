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
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from BBDD.databasecontroller import (
    actualizar_cita,
    crear_cita,
    crear_contacto,
    crear_usuario,
    eliminar_cita,
    eliminar_contacto,
    eliminar_usuario,
    get_db,
    init_db,
    obtener_cita,
    obtener_citas_eliminadas_por_usuario,
    obtener_citas_por_usuario,
    obtener_contacto,
    obtener_contactos,
    obtener_contactos_eliminados,
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
    ID_USUARIO: int
    ID_CONTACTO: Optional[int] = None
    FECHA: datetime
    DESCRIPCION: Optional[str] = None
    PRIORIDAD: int = 1


class CitaUpdate(BaseModel):
    FECHA: Optional[datetime] = None
    DESCRIPCION: Optional[str] = None
    PRIORIDAD: Optional[int] = None


class CitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID_CITA: int
    ID_USUARIO: int
    ID_CONTACTO: Optional[int]
    DESCRIPCION: Optional[str]
    FECHA: datetime
    PRIORIDAD: Optional[int]
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


# ── Endpoints: CITAS ───────────────────────────────────────────────────────────


@app.post("/citas", response_model=CitaOut, status_code=201, tags=["Citas"])
def post_cita(body: CitaCreate, db: Session = Depends(get_db)):
    """Crea una nueva cita. ID_CONTACTO es opcional."""
    try:
        return crear_cita(
            db,
            body.ID_USUARIO,
            body.FECHA,
            body.ID_CONTACTO,
            body.DESCRIPCION,
            body.PRIORIDAD,
        )
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/usuarios/{id_usuario}/citas", response_model=list[CitaOut], tags=["Citas"])
def get_citas_usuario(id_usuario: int, db: Session = Depends(get_db)):
    """Lista todas las citas activas del usuario, ordenadas por fecha."""
    try:
        return obtener_citas_por_usuario(db, id_usuario)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/usuarios/{id_usuario}/citas/eliminadas",
    response_model=list[CitaOut],
    tags=["Citas"],
)
def get_citas_eliminadas_usuario(id_usuario: int, db: Session = Depends(get_db)):
    """Lista todas las citas eliminadas (soft-delete) del usuario, ordenadas por fecha."""
    try:
        return obtener_citas_eliminadas_por_usuario(db, id_usuario)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/citas/{id_cita}", response_model=CitaOut, tags=["Citas"])
def get_cita(id_cita: int, db: Session = Depends(get_db)):
    cita = obtener_cita(db, id_cita)
    if cita is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita


@app.put("/citas/{id_cita}", response_model=CitaOut, tags=["Citas"])
def put_cita(id_cita: int, body: CitaUpdate, db: Session = Depends(get_db)):
    """Actualiza fecha, descripción o prioridad de una cita. Solo se modifican los campos enviados."""
    cita = actualizar_cita(db, id_cita, body.FECHA, body.DESCRIPCION, body.PRIORIDAD)
    if cita is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita


@app.delete("/citas/{id_cita}", status_code=204, tags=["Citas"])
def delete_cita(id_cita: int, db: Session = Depends(get_db)):
    """Soft delete: registra la fecha de baja en ELIMINADO."""
    if not eliminar_cita(db, id_cita):
        raise HTTPException(status_code=404, detail="Cita no encontrada o ya eliminada")
