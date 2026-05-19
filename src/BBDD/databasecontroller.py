"""Controlador de base de datos MySQL (Aiven) con SQLAlchemy.

Expone modelos ORM y funciones CRUD para:
    - USUARIOS (tipo="C" corporativo)
    - EMPLEADOS (senior/junior dentro de una corporación)
    - CLIENTES (clientes de los empleados)
    - CITAS_COR (citas corporativas)

Las funciones reciben una sesión SQLAlchemy como primer argumento, lo que
las hace usables tanto desde el bot (via get_session()) como desde la API
FastAPI (via get_db() dependency).

Arquitectura:
    USUARIO (Corporativo) → EMPLEADO → CLIENTE → CITA_COR

Nota: Arquitectura Individual (CitaInd, Contactos) está deprecada.
"""

import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Generator

from dotenv import load_dotenv
import bcrypt
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    BigInteger,
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


def hash_password(password: str | None) -> str | None:
    """Hash a password using bcrypt."""
    if password is None:
        return None
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


# ── Constantes ─────────────────────────────────────────────────────────────
TIPOS_EMPLEADOS: list[str] = ["senior", "junior"]


# ── Modelos ORM ────────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class CitaInd(Base):
    __tablename__ = "CITAS_IND"

    ID_CITA = Column(Integer, primary_key=True, autoincrement=True)
    ID_USUARIO = Column(Integer, ForeignKey("USUARIOS.ID_USUARIO"), nullable=False)
    ID_CONTACTO = Column(Integer, nullable=True)
    DESCRIPCION = Column(
        "DESCRIPCIÓN", String(500), nullable=False, default="Cita reservada"
    )
    FECHA = Column(DateTime, nullable=False)
    DURACION = Column(Integer, nullable=True, default=None)  # minutos
    PRIORIDAD = Column(Integer, nullable=True, default=1)
    ELIMINADO = Column(DateTime, nullable=True, default=None)

    # DEPRECATED: Usuario model was removed
    # usuario = relationship("Usuario", back_populates="citas")


class ListaEspera(Base):
    __tablename__ = "LISTA_ESPERA"

    ID_LISTA = Column(Integer, primary_key=True, autoincrement=True)
    TELEGRAM_ID = Column(BigInteger, nullable=False)
    FECHA = Column(DateTime, nullable=False)
    NOTIFICADO = Column(Integer, default=0)


class Empleado(Base):
    __tablename__ = "EMPLEADOS"

    ID_EMPLEADO = Column(Integer, primary_key=True, autoincrement=True)
    NOMBRE = Column(String(100), nullable=False)
    EMAIL = Column(String(200), nullable=False, unique=True)
    # CONTRASENA = Column("CONTRASEÑA", String(255), nullable=True)
    ELIMINADO = Column(DateTime, nullable=True, default=None)

    clientes = relationship(
        "Cliente",
        back_populates="empleado_usual",
        foreign_keys="Cliente.ID_EMPLEADO_USUAL",
    )
    citas = relationship("CitaCorp", back_populates="empleado")


class Cliente(Base):
    __tablename__ = "CLIENTES"

    ID_CLIENTE = Column(Integer, primary_key=True, autoincrement=True)
    ID_EMPLEADO_USUAL = Column(
        Integer, ForeignKey("EMPLEADOS.ID_EMPLEADO"), nullable=True
    )
    DNI = Column(String(9), nullable=False, unique=True)
    NOMBRE = Column(String(100), nullable=False)
    TELEGRAM_ID = Column(
        "ID_TELEGRAM", BigInteger, nullable=True, unique=True
    )  # Para identificar usuario del bot
    EMAIL = Column(String(200), nullable=True)
    TELEFONO = Column(String(20), nullable=True)
    ELIMINADO = Column(DateTime, nullable=True, default=None)

    empleado_usual = relationship(
        "Empleado", back_populates="clientes", foreign_keys=[ID_EMPLEADO_USUAL]
    )
    citas = relationship("CitaCorp", back_populates="cliente")


class CitaCorp(Base):
    __tablename__ = "CITAS"

    ID_CITA = Column(Integer, primary_key=True, autoincrement=True)
    ID_EMPLEADO = Column(Integer, ForeignKey("EMPLEADOS.ID_EMPLEADO"), nullable=False)
    ID_CLIENTE = Column(Integer, ForeignKey("CLIENTES.ID_CLIENTE"), nullable=False)
    FECHA = Column(DateTime, nullable=False)
    DURACION = Column(Integer, nullable=True, default=None)  # minutos
    DESCRIPCION = Column(
        "DESCRIPCIÓN", String(500), nullable=True, default="Cita reservada"
    )
    ELIMINADO = Column(DateTime, nullable=True, default=None)

    empleado = relationship("Empleado", back_populates="citas")
    cliente = relationship("Cliente", back_populates="citas")


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
        print("OK: Base de datos inicializada correctamente")
    except Exception as e:
        print(f"Advertencia: No se pudo conectar a la BD durante init: {e}")
        print("  La API seguirá funcionando pero las operaciones de BD fallarán")


# ── Helpers internos ───────────────────────────────────────────────────────────


def _get_empleado_activo(session: Session, id_empleado: int) -> Empleado:
    """Devuelve el empleado activo o lanza ValueError si no existe o está eliminado."""
    empleado = session.get(Empleado, id_empleado)
    if empleado is None:
        raise ValueError(f"Empleado {id_empleado} no encontrado")
    if empleado.ELIMINADO is not None:
        raise ValueError("El empleado está dado de baja")
    return empleado


# ── CRUD USUARIOS ──────────────────────────────────────────────────────────────

# ── CRUD EMPLEADOS ─────────────────────────────────────────────────────────────


def crear_empleado(
    session: Session,
    tipo: str,
    nombre: str,
    email: str,
    contrasena: str | None = None,
    id_admin: int | None = None,
) -> Empleado:
    """Crea un empleado independiente (sin necesidad de Usuario corporativo)."""
    empleado = Empleado(
        TIPO=tipo,
        NOMBRE=nombre,
        EMAIL=email,
        CONTRASENA=hash_password(contrasena) if contrasena else None,
        ID_ADMIN=id_admin,
    )
    session.add(empleado)
    session.flush()
    return empleado


def obtener_empleados(session: Session) -> list[Empleado]:
    """Retorna todos los empleados activos."""
    return session.query(Empleado).filter(Empleado.ELIMINADO.is_(None)).all()


def obtener_empleado(session: Session, id_empleado: int) -> Empleado | None:
    empleado = session.get(Empleado, id_empleado)
    if empleado is None or empleado.ELIMINADO is not None:
        return None
    return empleado


def obtener_empleado_por_nombre(session: Session, nombre: str) -> Empleado | None:
    """Obtiene un empleado por su nombre. Retorna None si no existe o está eliminado."""
    empleado = (
        session.query(Empleado)
        .filter(
            Empleado.NOMBRE.ilike(nombre),  # ilike = case-insensitive
            Empleado.ELIMINADO.is_(None),
        )
        .first()
    )
    return empleado


def eliminar_empleado(session: Session, id_empleado: int) -> bool:
    empleado = session.get(Empleado, id_empleado)
    if empleado is None or empleado.ELIMINADO is not None:
        return False
    empleado.ELIMINADO = datetime.now(timezone.utc)
    return True


# ── CRUD CLIENTES ─────────────────────────────────────────────────────────────


def crear_cliente(
    session: Session,
    id_empleado: int,
    dni: str,
    nombre: str,
    telegram_id: int | None = None,
    email: str | None = None,
    telefono: str | None = None,
    id_empleado_usual: int | None = None,
) -> Cliente:
    """Crea un cliente directamente (sin necesidad de Usuario)."""
    _get_empleado_activo(session, id_empleado)
    cliente = Cliente(
        ID_EMPLEADO_USUAL=id_empleado_usual
        if id_empleado_usual is not None
        else id_empleado,
        DNI=dni,
        NOMBRE=nombre,
        TELEGRAM_ID=telegram_id,
        EMAIL=email,
        TELEFONO=telefono,
    )
    session.add(cliente)
    session.flush()
    return cliente


def obtener_clientes_por_empleado(session: Session, id_empleado: int) -> list[Cliente]:
    _get_empleado_activo(session, id_empleado)
    return (
        session.query(Cliente)
        .filter(Cliente.ID_EMPLEADO_USUAL == id_empleado, Cliente.ELIMINADO.is_(None))
        .all()
    )


def obtener_cliente(session: Session, id_cliente: int) -> Cliente | None:
    cliente = session.get(Cliente, id_cliente)
    if cliente is None or cliente.ELIMINADO is not None:
        return None
    return cliente


def obtener_cliente_por_telegram(session: Session, telegram_id: int) -> Cliente | None:
    """Obtiene un cliente por su telegram_id (para el bot)."""
    cliente = (
        session.query(Cliente)
        .filter(Cliente.TELEGRAM_ID == telegram_id, Cliente.ELIMINADO.is_(None))
        .first()
    )
    return cliente


def obtener_o_crear_cliente_telegram(
    session: Session,
    telegram_id: int,
    id_empleado_default: int,
    nombre: str | None = None,
    dni: str | None = None,
) -> Cliente:
    """Obtiene o crea un cliente para el bot usando telegram_id.

    Si no existe, crea un nuevo cliente asignado al empleado por defecto.
    """
    cliente = obtener_cliente_por_telegram(session, telegram_id)
    if cliente:
        return cliente

    # Crear nuevo cliente
    empleado = _get_empleado_activo(session, id_empleado_default)
    # DNI: usar los últimos 9 dígitos del telegram_id (para caber en VARCHAR(9))
    dni_default = str(telegram_id)[-9:] if telegram_id else "000000000"

    cliente = crear_cliente(
        session,
        id_empleado=id_empleado_default,
        dni=dni or dni_default,
        nombre=nombre or f"Usuario Telegram {telegram_id}",
        telegram_id=telegram_id,
        id_empleado_usual=id_empleado_default,
    )
    session.flush()
    return cliente


def eliminar_cliente(session: Session, id_cliente: int) -> bool:
    cliente = session.get(Cliente, id_cliente)
    if cliente is None or cliente.ELIMINADO is not None:
        return False
    cliente.ELIMINADO = datetime.now(timezone.utc)
    return True


# ── CRUD CITAS_COR ────────────────────────────────────────────────────────────


def crear_cita_corp(
    session: Session,
    id_empleado: int,
    id_cliente: int,
    fecha: datetime,
    descripcion: str | None = None,
    duracion: int | None = None,
) -> CitaCorp:
    _get_empleado_activo(session, id_empleado)
    cliente = session.get(Cliente, id_cliente)
    if cliente is None or cliente.ELIMINADO is not None:
        raise ValueError(f"Cliente {id_cliente} no encontrado o dado de baja")
    cita = CitaCorp(
        ID_EMPLEADO=id_empleado,
        ID_CLIENTE=id_cliente,
        FECHA=fecha,
        DESCRIPCION=descripcion,
        DURACION=duracion,
    )
    session.add(cita)
    session.commit()
    return cita


def obtener_citas_cliente(
    session: Session,
    id_cliente: int,
    fecha: datetime | None = None,
    anterior: bool = False,
) -> list[CitaCorp]:
    """Devuelve todas las citas corporativas activas de un cliente."""
    if fecha is None:
        fecha = datetime.now()
    cliente = session.get(Cliente, id_cliente)
    if cliente is None or cliente.ELIMINADO is not None:
        raise ValueError(f"Cliente {id_cliente} no encontrado")
    q = session.query(CitaCorp).filter(
        CitaCorp.ID_CLIENTE == id_cliente, CitaCorp.ELIMINADO.is_(None)
    )
    if anterior:
        q = q.filter(CitaCorp.FECHA < fecha).order_by(CitaCorp.FECHA.desc())
    else:
        q = q.filter(CitaCorp.FECHA >= fecha).order_by(CitaCorp.FECHA.asc())
    return q.all()


def obtener_citas_cliente_eliminadas(
    session: Session,
    id_cliente: int,
    fecha: datetime | None = None,
    anterior: bool = False,
) -> list[CitaCorp]:
    """Devuelve todas las citas corporativas eliminadas de un cliente."""
    if fecha is None:
        fecha = datetime.now()
    cliente = session.get(Cliente, id_cliente)
    if cliente is None or cliente.ELIMINADO is not None:
        raise ValueError(f"Cliente {id_cliente} no encontrado")
    q = session.query(CitaCorp).filter(
        CitaCorp.ID_CLIENTE == id_cliente, CitaCorp.ELIMINADO.isnot(None)
    )
    if anterior:
        q = q.filter(CitaCorp.FECHA < fecha).order_by(CitaCorp.FECHA.desc())
    else:
        q = q.filter(CitaCorp.FECHA >= fecha).order_by(CitaCorp.FECHA.asc())
    return q.all()


def obtener_citas_empleado(
    session: Session,
    id_empleado: int,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
) -> list[CitaCorp]:
    """Devuelve todas las citas corporativas activas de un empleado en un rango de fechas."""
    if fecha_inicio is None:
        fecha_inicio = datetime.now()
    if fecha_fin is None:
        fecha_fin = fecha_inicio + timedelta(days=30)
    empleado = _get_empleado_activo(session, id_empleado)
    return (
        session.query(CitaCorp)
        .filter(
            CitaCorp.ID_EMPLEADO == id_empleado,
            CitaCorp.ELIMINADO.is_(None),
            CitaCorp.FECHA >= fecha_inicio,
            CitaCorp.FECHA < fecha_fin,
        )
        .all()
    )


# Aliases para compatibilidad (deprecated)
def obtener_citas_corp_por_usuario(
    session: Session,
    id_usuario: int,
    fecha: datetime | None = None,
    anterior: bool = False,
) -> list[CitaCorp]:
    raise NotImplementedError(
        "obtener_citas_corp_por_usuario() está deprecated. Use obtener_citas_cliente() o obtener_citas_empleado()."
    )


def obtener_citas_corp_eliminadas_por_usuario(
    session: Session,
    id_usuario: int,
    fecha: datetime | None = None,
    anterior: bool = False,
) -> list[CitaCorp]:
    raise NotImplementedError(
        "obtener_citas_corp_eliminadas_por_usuario() está deprecated. Use obtener_citas_cliente_eliminadas()."
    )


def obtener_cita_corp(session: Session, id_cita: int) -> CitaCorp | None:
    cita = session.get(CitaCorp, id_cita)
    if cita is None or cita.ELIMINADO is not None:
        return None
    return cita


def actualizar_cita_corp(
    session: Session,
    id_cita: int,
    fecha: datetime | None = None,
    descripcion: str | None = None,
    duracion: int | None = None,
) -> CitaCorp | None:
    cita = session.get(CitaCorp, id_cita)
    if cita is None or cita.ELIMINADO is not None:
        return None
    if fecha is not None:
        cita.FECHA = fecha
    if descripcion is not None:
        cita.DESCRIPCION = descripcion
    if duracion is not None:
        cita.DURACION = duracion
    return cita


def eliminar_cita_corp(session: Session, id_cita: int) -> bool:
    cita = session.get(CitaCorp, id_cita)
    if cita is None or cita.ELIMINADO is not None:
        return False
    cita.ELIMINADO = datetime.now(timezone.utc)
    return True


def get_citas_cor_en_rango(
    session: Session,
    id_empleado: int,
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> list[CitaCorp]:
    """Devuelve las CITAS_COR activas de un empleado en el rango [fecha_inicio, fecha_fin).
    Se amplía 1 día hacia atrás para capturar citas que empezaron antes pero
    podrían solapar con el inicio del rango.
    """
    return (
        session.query(CitaCorp)
        .filter(
            CitaCorp.ID_EMPLEADO == id_empleado,
            CitaCorp.ELIMINADO.is_(None),
            CitaCorp.FECHA >= fecha_inicio - timedelta(days=1),
            CitaCorp.FECHA < fecha_fin,
        )
        .all()
    )
