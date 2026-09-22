"""Pruebas de integración reales contra el servicio SOAP institucional de SEGIP.

Estas pruebas ÚNICAMENTE se ejecutan si la variable de entorno RUN_SEGIP_INTEGRATION_TESTS=true
y solo ejecutan la comprobación de conectividad inocua ObtieneVersionSistema sin datos personales.
"""

import os

import pytest

from app.core.config import Settings
from app.integrations.segip.client import SegipSoapClient

RUN_LIVE = os.getenv("RUN_SEGIP_INTEGRATION_TESTS", "false").lower() in ("true", "1", "yes")


@pytest.mark.integration
@pytest.mark.skipif(not RUN_LIVE, reason="Pruebas de integración SEGIP desactivadas por defecto")
@pytest.mark.asyncio
async def test_live_segip_connectivity_obtiene_version():
    """Comprueba conectividad real contra el endpoint institucional en intranet."""
    settings = Settings(RUN_SEGIP_INTEGRATION_TESTS=True)
    async with SegipSoapClient(settings=settings) as client:
        version = await client.obtiene_version_sistema()
        assert version is not None
        assert len(version) > 0
        assert version == "8.0.0.0"
