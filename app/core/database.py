"""Gestión centralizada del motor asíncrono y sesiones de SQLAlchemy 2.0 (UOIT 1.0).

Este módulo provee la configuración del pool de conexiones para PostgreSQL con el driver
asyncpg, diseñado específicamente para operar de manera resiliente bajo autoescalado (HPA)
en clústeres de Kubernetes y permitir un cierre de conexiones ordenado (graceful shutdown).
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Referencias globales singleton para el motor y la fábrica de sesiones
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine(settings: Settings | None = None) -> AsyncEngine:
    """Retorna la instancia singleton de AsyncEngine configurada según los parámetros de entorno.

    Aplica pool_pre_ping=True para validar conexiones antes de entregarlas del pool
    y acota el tamaño del pool para evitar saturar el servidor PostgreSQL cuando
    el microservicio escala horizontalmente en Kubernetes.
    """
    global _engine
    if _engine is not None:
        return _engine

    cfg = settings or get_settings()
    db_url = cfg.async_database_url

    engine_kwargs: dict[str, Any] = {
        "echo": cfg.DB_ECHO,
    }

    # Motores basados en SQLite (usados en pruebas) no soportan argumentos de QueuePool
    if "sqlite" in db_url.lower():
        logger.info("Inicializando AsyncEngine para SQLite: %s", db_url)
    else:
        logger.info(
            "Inicializando AsyncEngine PostgreSQL [host=%s, port=%s, db=%s, pool_size=%d, max_overflow=%d, pre_ping=%s]",
            cfg.DB_HOST,
            cfg.DB_PORT,
            cfg.DB_NAME,
            cfg.DB_POOL_SIZE,
            cfg.DB_MAX_OVERFLOW,
            cfg.DB_POOL_PRE_PING,
        )
        engine_kwargs.update(
            {
                "pool_size": cfg.DB_POOL_SIZE,
                "max_overflow": cfg.DB_MAX_OVERFLOW,
                "pool_timeout": cfg.DB_POOL_TIMEOUT,
                "pool_recycle": cfg.DB_POOL_RECYCLE,
                "pool_pre_ping": cfg.DB_POOL_PRE_PING,
            }
        )

    _engine = create_async_engine(db_url, **engine_kwargs)
    return _engine


def get_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Retorna la fábrica singleton de sesiones asíncronas de SQLAlchemy."""
    global _session_factory
    if _session_factory is not None and engine is None:
        return _session_factory

    active_engine = engine or get_async_engine()
    _session_factory = async_sessionmaker(
        bind=active_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _session_factory


async def close_database_engine() -> None:
    """Cierra el pool de conexiones de manera ordenada (Graceful Shutdown).

    Invocado durante el evento shutdown del lifespan de FastAPI cuando
    Kubernetes envía SIGTERM a un pod.
    """
    global _engine, _session_factory
    if _engine is not None:
        logger.info("Cerrando pool de conexiones de PostgreSQL (await engine.dispose())...")
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Pool de conexiones de base de datos liberado exitosamente.")


async def check_database_health(engine: AsyncEngine | None = None) -> tuple[bool, str]:
    """Ejecuta una consulta liviana (SELECT 1) para verificar la conectividad de la base de datos."""
    active_engine = engine or get_async_engine()
    try:
        async with active_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "Base de datos PostgreSQL disponible"
    except Exception as exc:
        logger.warning("Fallo en healthcheck de base de datos: %s", str(exc))
        return False, f"Error de conexión a base de datos: {exc}"
