"""Controlador de base de datos MySQL (Aiven) con SQLAlchemy.

Expone modelos ORM y funciones CRUD para USUARIOS, CONTACTOS y CITAS_IND.
Las funciones reciben una sesión SQLAlchemy como primer argumento, lo que
las hace usables tanto desde el bot (via get_session()) como desde la API
FastAPI (via get_db() dependency).

Jerarquía de acceso:
    USUARIOS (tipo="I") → CONTACTOS (profesionales) → CITAS_IND (citas)

Restricción de tipo:
    Solo usuarios con TIPO en TIPOS_INDIVIDUALES pueden operar sobre
    CONTACTOS y CITAS_IND. Ampliar TIPOS_INDIVIDUALES para nuevos tipos.
"""

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from dotenv import load_dotenv
import bcrypt
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship

# ── Configuración ──────────────────────────────────────────────────────────────

_dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", "env", ".env")
load_dotenv(dotenv_path=_dotenv_path)

_CA_PATH = os.path.join(os.path.dirname(__file__), "ca.pem")

# Usa SQLite en desarrollo si lo especificas en .env
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
if USE_SQLITE:
    _DB_URL = "sqlite:///./ps_chatbot.db"
else:
    _DB_URL = os.getenv("DB_URL", "")

if USE_SQLITE:
    engine = create_engine(
        _DB_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=False,
    )
else:
    engine = create_engine(
        _DB_URL,
        connect_args={
            "ssl": {"ca": _CA_PATH},
            "connect_timeout": 30,  # 30 segundos
        },
        pool_pre_ping=True,
        pool_recycle=3600,  # Recicla conexiones cada hora
        echo=False,
    )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    if len(password) > 72:
        password = password[:72]
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if len(plain_password) > 72:
        plain_password = plain_password[:72]
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# ── Control de acceso por tipo ─────────────────────────────────────────────────
# Añadir aquí nuevos tipos de usuario que deban acceder a contactos/citas.
TIPOS_INDIVIDUALES: list[str] = ["I"]


# ── Modelos ORM ────────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "USUARIOS"

    ID_USUARIO = Column(Integer, primary_key=True, autoincrement=True)
    TIPO = Column(String(10), nullable=False, default="I")
    NOMBRE = Column(String(100), nullable=False)
    EMAIL = Column(String(200), nullable=False, unique=True)
    CONTRASENA = Column("CONTRASEÑA", String(255), nullable=False)
    ELIMINADO = Column(DateTime, nullable=True, default=None)

    contactos = relationship("Contacto", back_populates="usuario")
    citas = relationship("CitaInd", back_populates="usuario")


class Contacto(Base):
    __tablename__ = "CONTACTOS"

    ID_CONTACTO = Column(Integer, primary_key=True, autoincrement=True)
    ID_USUARIO = Column(Integer, ForeignKey("USUARIOS.ID_USUARIO"), nullable=True)
    NOMBRE = Column(String(100), nullable=False)
    EMAIL = Column(String(200), nullable=True)
    ELIMINADO = Column(DateTime, nullable=True, default=None)

    usuario = relationship("Usuario", back_populates="contactos")


class CitaInd(Base):
    __tablename__ = "CITAS_IND"

    ID_CITA = Column(Integer, primary_key=True, autoincrement=True)
    ID_USUARIO = Column(Integer, ForeignKey("USUARIOS.ID_USUARIO"), nullable=False)
    ID_CONTACTO = Column(Integer, nullable=True)
    DESCRIPCION = Column(
        "DESCRIPCIÓN", String(500), nullable=False, default="Cita reservada"
    )
    FECHA = Column(DateTime, nullable=False)
    PRIORIDAD = Column(Integer, nullable=True, default=1)
    ELIMINADO = Column(DateTime, nullable=True, default=None)

    usuario = relationship("Usuario", back_populates="citas")


# ── Gestión de sesión ──────────────────────────────────────────────────────────


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager para uso directo desde el bot u otros módulos."""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_db() -> Generator[Session, None, None]:
    """Generador para inyección de dependencias en FastAPI."""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


# ── Inicialización / migración ─────────────────────────────────────────────────


def init_db() -> None:
    """Aplica migraciones pendientes y crea tablas inexistentes.

    Migración v1: añade ID_USUARIO y su FK a CONTACTOS si no existen.
    """
    try:
        with engine.connect() as conn:
            try:
                conn.execute(
                    text("ALTER TABLE CONTACTOS ADD COLUMN ID_USUARIO INT NULL")
                )
                conn.execute(
                    text(
                        "ALTER TABLE CONTACTOS ADD CONSTRAINT fk_contactos_usuario "
                        "FOREIGN KEY (ID_USUARIO) REFERENCES USUARIOS(ID_USUARIO)"
                    )
                )
                conn.commit()
            except Exception:
                conn.rollback()  # Columna/FK ya existe, se ignora

        Base.metadata.create_all(engine)
        print("✓ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"⚠ Advertencia: No se pudo conectar a la BD durante init: {e}")
        print("  La API seguirá funcionando pero las operaciones de BD fallarán")


# ── Helpers internos ───────────────────────────────────────────────────────────


def _verificar_acceso(usuario: Usuario, tipos_permitidos: list[str]) -> None:
    """Lanza PermissionError si el tipo de usuario no está en la lista permitida."""
    if usuario.TIPO not in tipos_permitidos:
        raise PermissionError(
            f"El tipo de usuario '{usuario.TIPO}' no tiene acceso a esta operación"
        )


def _get_usuario_activo(session: Session, id_usuario: int) -> Usuario:
    """Devuelve el usuario activo o lanza ValueError si no existe o está eliminado."""
    usuario = session.get(Usuario, id_usuario)
    if usuario is None:
        raise ValueError(f"Usuario {id_usuario} no encontrado")
    if usuario.ELIMINADO is not None:
        raise ValueError("El usuario está dado de baja")
    return usuario


# ── CRUD USUARIOS ──────────────────────────────────────────────────────────────


def crear_usuario(
    session: Session,
    tipo: str,
    nombre: str,
    email: str,
    contrasena: str,
) -> Usuario:
    usuario = Usuario(
        TIPO=tipo,
        NOMBRE=nombre,
        EMAIL=email,
        CONTRASENA=hash_password(contrasena),
    )
    session.add(usuario)
    session.flush()
    return usuario


def obtener_usuario(session: Session, id_usuario: int) -> Usuario | None:
    usuario = session.get(Usuario, id_usuario)
    if usuario is None or usuario.ELIMINADO is not None:
        return None
    return usuario


def eliminar_usuario(session: Session, id_usuario: int) -> bool:
    usuario = session.get(Usuario, id_usuario)
    if usuario is None or usuario.ELIMINADO is not None:
        return False
    usuario.ELIMINADO = datetime.now(timezone.utc)
    return True


# ── CRUD CONTACTOS ─────────────────────────────────────────────────────────────


def crear_contacto(
    session: Session,
    id_usuario: int,
    nombre: str,
    email: str | None = None,
) -> Contacto:
    usuario = _get_usuario_activo(session, id_usuario)
    _verificar_acceso(usuario, TIPOS_INDIVIDUALES)
    contacto = Contacto(ID_USUARIO=id_usuario, NOMBRE=nombre, EMAIL=email)
    session.add(contacto)
    session.flush()
    return contacto


def obtener_contactos(session: Session, id_usuario: int) -> list[Contacto]:
    usuario = _get_usuario_activo(session, id_usuario)
    _verificar_acceso(usuario, TIPOS_INDIVIDUALES)
    return (
        session.query(Contacto)
        .filter(Contacto.ID_USUARIO == id_usuario, Contacto.ELIMINADO is None)
        .all()
    )


def obtener_contacto(session: Session, id_contacto: int) -> Contacto | None:
    contacto = session.get(Contacto, id_contacto)
    if contacto is None or contacto.ELIMINADO is not None:
        return None
    return contacto


def obtener_contactos_eliminados(session: Session, id_usuario: int) -> list[Contacto]:
    usuario = _get_usuario_activo(session, id_usuario)
    _verificar_acceso(usuario, TIPOS_INDIVIDUALES)
    return (
        session.query(Contacto)
        .filter(Contacto.ID_USUARIO == id_usuario, Contacto.ELIMINADO is not None)
        .all()
    )


def eliminar_contacto(session: Session, id_contacto: int) -> bool:
    contacto = session.get(Contacto, id_contacto)
    if contacto is None or contacto.ELIMINADO is not None:
        return False
    contacto.ELIMINADO = datetime.now(timezone.utc)
    return True


# ── CRUD CITAS_IND ─────────────────────────────────────────────────────────────


def crear_cita(
    session: Session,
    id_usuario: int,
    fecha: datetime,
    id_contacto: int | None = None,
    descripcion: str | None = None,
    prioridad: int = 1,
) -> CitaInd:
    usuario = _get_usuario_activo(session, id_usuario)
    _verificar_acceso(usuario, TIPOS_INDIVIDUALES)
    cita = CitaInd(
        ID_USUARIO=id_usuario,
        ID_CONTACTO=id_contacto,
        FECHA=fecha,
        DESCRIPCION=descripcion,
        PRIORIDAD=prioridad,
    )
    session.add(cita)
    session.flush()
    return cita


def obtener_citas_por_usuario(session: Session, id_usuario: int) -> list[CitaInd]:
    usuario = _get_usuario_activo(session, id_usuario)
    _verificar_acceso(usuario, TIPOS_INDIVIDUALES)
    return (
        session.query(CitaInd)
        .filter(CitaInd.ID_USUARIO == id_usuario, CitaInd.ELIMINADO is None)
        .order_by(CitaInd.FECHA)
        .all()
    )


def obtener_cita(session: Session, id_cita: int) -> CitaInd | None:
    cita = session.get(CitaInd, id_cita)
    if cita is None or cita.ELIMINADO is not None:
        return None
    return cita


def obtener_citas_eliminadas_por_usuario(
    session: Session, id_usuario: int
) -> list[CitaInd]:
    usuario = _get_usuario_activo(session, id_usuario)
    _verificar_acceso(usuario, TIPOS_INDIVIDUALES)
    return (
        session.query(CitaInd)
        .filter(CitaInd.ID_USUARIO == id_usuario, CitaInd.ELIMINADO is not None)
        .order_by(CitaInd.FECHA)
        .all()
    )


def actualizar_cita(
    session: Session,
    id_cita: int,
    fecha: datetime | None = None,
    descripcion: str | None = None,
    prioridad: int | None = None,
) -> CitaInd | None:
    cita = session.get(CitaInd, id_cita)
    if cita is None or cita.ELIMINADO is not None:
        return None
    if fecha is not None:
        cita.FECHA = fecha
    if descripcion is not None:
        cita.DESCRIPCION = descripcion
    if prioridad is not None:
        cita.PRIORIDAD = prioridad
    return cita


def eliminar_cita(session: Session, id_cita: int) -> bool:
    cita = session.get(CitaInd, id_cita)
    if cita is None or cita.ELIMINADO is not None:
        return False
    cita.ELIMINADO = datetime.now(timezone.utc)
    return True
