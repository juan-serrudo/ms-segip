"""Pruebas unitarias para endpoints de salud y probes de Kubernetes según Convenciones UOIT."""

import httpx
import pytest
from httpx import AsyncClient

from app.api.dependencies import get_segip_client
from app.integrations.segip.client import SegipSoapClient
from app.main import app
from tests.fixtures.soap_responses import MOCK_VERSION_RESPONSE_XML


@pytest.mark.asyncio
async def test_k8s_liveness_probe(async_client: AsyncClient):
    """Prueba el endpoint de liveness para Kubernetes (UOIT Sección 29)."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


@pytest.mark.asyncio
async def test_k8s_readiness_probe_segip_up(async_client: AsyncClient, test_settings):
    """Prueba el endpoint de readiness para Kubernetes cuando SEGIP responde (UOIT Sección 29)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_VERSION_RESPONSE_XML.encode("utf-8"))

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "UP"}
    finally:
        app.dependency_overrides.pop(get_segip_client, None)


@pytest.mark.asyncio
async def test_k8s_readiness_probe_segip_down(async_client: AsyncClient, test_settings):
    """Prueba el endpoint de readiness para Kubernetes cuando SEGIP falla (UOIT Sección 29)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        response = await async_client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "DOWN"}
    finally:
        app.dependency_overrides.pop(get_segip_client, None)


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    """Prueba el endpoint informativo /api/v1/health con estructura ApiResponse UOIT."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Microservicio operativo"
    assert body["data"]["status"] == "healthy"
    assert body["data"]["appName"] == "ms-segip"
    assert body["meta"] is None
    assert body["error"] is None


@pytest.mark.asyncio
async def test_readiness_check_endpoint_segip_up(async_client: AsyncClient, test_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_VERSION_RESPONSE_XML.encode("utf-8"))

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 200

        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "ready"
        assert body["data"]["components"]["application"]["status"] == "up"
        assert body["data"]["components"]["segipSoap"]["status"] == "up"
    finally:
        app.dependency_overrides.pop(get_segip_client, None)


@pytest.mark.asyncio
async def test_readiness_check_endpoint_segip_down(async_client: AsyncClient, test_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 503

        body = response.json()
        assert body["success"] is False
        assert body["data"]["status"] == "degraded"
        assert body["data"]["components"]["segipSoap"]["status"] == "down"
    finally:
        app.dependency_overrides.pop(get_segip_client, None)
