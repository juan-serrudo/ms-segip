"""Configuración y fixtures compartidas de pytest."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provee configuración optimizada para pruebas unitarias."""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["SEGIP_SERVICE_URL"] = (
        "https://segip-api.fiscalia.gob.bo/ServicioExternoInstitucion.svc"
    )
    os.environ["SEGIP_INSTITUTION_CODE"] = "999"
    os.environ["SEGIP_USERNAME"] = "usuario_test"
    os.environ["SEGIP_PASSWORD"] = "password_test"
    os.environ["PDF_MAX_SIZE_MB"] = "5.0"
    os.environ["SEGIP_MAX_RETRIES"] = "1"
    os.environ["SEGIP_CONNECT_TIMEOUT"] = "1.0"
    os.environ["SEGIP_READ_TIMEOUT"] = "1.0"

    get_settings.cache_clear()
    return get_settings()


@pytest_asyncio.fixture
async def async_client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """Provee un cliente HTTP asíncrono para probar los endpoints de FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
