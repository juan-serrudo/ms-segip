"""Pruebas unitarias de seguridad y autenticación desacoplada."""

import pytest
from httpx import AsyncClient

from app.core.config import Settings
from app.core.security import verify_api_key


@pytest.mark.asyncio
async def test_verify_api_key_when_disabled():
    settings = Settings(API_KEY=None)
    result = await verify_api_key(x_api_key=None, settings=settings)
    assert result is None


@pytest.mark.asyncio
async def test_verify_api_key_when_enabled_valid():
    settings = Settings(API_KEY="clave_secreta_institucional")
    result = await verify_api_key(x_api_key="clave_secreta_institucional", settings=settings)
    assert result == "clave_secreta_institucional"


@pytest.mark.asyncio
async def test_verify_api_key_when_enabled_invalid():
    from fastapi import HTTPException

    settings = Settings(API_KEY="clave_secreta_institucional")
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(x_api_key="clave_incorrecta", settings=settings)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_correlation_id_propagated_in_headers(async_client: AsyncClient):
    custom_id = "CUSTOM-CORRELATION-ID-12345"
    response = await async_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
    assert response.json()["request_id"] == custom_id
