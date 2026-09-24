"""Inyección de dependencias para los endpoints de la API."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session_factory
from app.integrations.segip.client import SegipSoapClient
from app.repositories.persona_repository import PersonaRepository
from app.services.pdf_service import PdfService
from app.services.persona_certificada_service import PersonaCertificadaService
from app.services.segip_service import SegipService
from app.services.storage_service import StorageService


async def get_segip_client(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[SegipSoapClient, None]:
    """Provee una instancia del cliente SOAP de SEGIP y gestiona su ciclo de vida."""
    client = SegipSoapClient(settings=settings)
    try:
        yield client
    finally:
        await client.close()


def get_segip_service(
    client: SegipSoapClient = Depends(get_segip_client),
    settings: Settings = Depends(get_settings),
) -> SegipService:
    """Provee una instancia del servicio de dominio SEGIP."""
    return SegipService(client=client, settings=settings)


def get_pdf_service(
    settings: Settings = Depends(get_settings),
) -> PdfService:
    """Provee una instancia del servicio de procesamiento de documentos PDF."""
    return PdfService(settings=settings)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión asíncrona de base de datos con manejo transaccional automático (commit/rollback)."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_persona_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PersonaRepository:
    """Provee una instancia de PersonaRepository ligada a la sesión activa."""
    return PersonaRepository(session=session)


def get_storage_service(
    settings: Settings = Depends(get_settings),
) -> StorageService:
    """Provee una instancia del servicio de almacenamiento RustFS / S3."""
    return StorageService(settings=settings)


def get_persona_certificada_service(
    persona_repo: PersonaRepository = Depends(get_persona_repository),
    segip_service: SegipService = Depends(get_segip_service),
    storage_service: StorageService = Depends(get_storage_service),
    settings: Settings = Depends(get_settings),
) -> PersonaCertificadaService:
    """Provee el servicio orquestador para consulta y certificación de personas."""
    return PersonaCertificadaService(
        persona_repo=persona_repo,
        segip_service=segip_service,
        storage_service=storage_service,
        settings=settings,
    )
