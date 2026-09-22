"""Inyección de dependencias para los endpoints de la API."""

from collections.abc import AsyncGenerator

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.integrations.segip.client import SegipSoapClient
from app.services.pdf_service import PdfService
from app.services.segip_service import SegipService


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
