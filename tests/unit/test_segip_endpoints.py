"""Pruebas unitarias para los endpoints de integración con SEGIP según Convenciones UOIT 1.0."""

import httpx
import pytest
from httpx import AsyncClient

from app.api.dependencies import get_segip_client
from app.integrations.segip.client import SegipSoapClient
from app.main import app
from tests.fixtures.soap_responses import (
    MOCK_CERTIFICACION_RESPONSE_XML,
    MOCK_CONTRASTACION_RESPONSE_XML,
    MOCK_NO_RESULTS_XML,
    MOCK_PERSONA_RESPONSE_XML,
    MOCK_QR_RESPONSE_XML,
    MOCK_VERSION_RESPONSE_XML,
)


@pytest.mark.asyncio
async def test_endpoint_get_version(async_client: AsyncClient, test_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_VERSION_RESPONSE_XML.encode("utf-8"))

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        response = await async_client.get("/api/v1/segip/version")
        assert response.status_code == 200

        body = response.json()
        assert body["success"] is True
        assert body["data"]["version"] == "8.0.0.0"
        assert body["error"] is None
    finally:
        app.dependency_overrides.pop(get_segip_client, None)


@pytest.mark.asyncio
async def test_endpoint_consultar_persona_success(async_client: AsyncClient, test_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_PERSONA_RESPONSE_XML.encode("utf-8"))

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        payload = {
            "numeroDocumento": "4892341",
            "complemento": "1A",
            "nombre": "CARLOS",
            "primerApellido": "MAMANI",
        }
        # Probar endpoint sustantivo UOIT
        response = await async_client.post("/api/v1/segip/personas", json=payload)
        assert response.status_code == 200

        body = response.json()
        assert body["success"] is True
        assert body["data"]["persona"]["numeroDocumento"] == "4892341"
        assert body["data"]["persona"]["nombres"] == "CARLOS ANDRES"
        assert body["data"]["nacimiento"]["departamento"] == "LA PAZ"
        assert body["error"] is None

        # Probar endpoint alias /personas/consultar
        alias_resp = await async_client.post("/api/v1/segip/personas/consultar", json=payload)
        assert alias_resp.status_code == 200
        assert alias_resp.json()["data"]["persona"]["numeroDocumento"] == "4892341"
    finally:
        app.dependency_overrides.pop(get_segip_client, None)


@pytest.mark.asyncio
async def test_endpoint_consultar_persona_no_results(async_client: AsyncClient, test_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_NO_RESULTS_XML.encode("utf-8"))

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        payload = {"numeroDocumento": "9999999"}
        response = await async_client.post("/api/v1/segip/personas", json=payload)
        assert response.status_code == 404

        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "SEGIP_NO_RESULTS"
        assert body["error"]["traceId"] is not None
    finally:
        app.dependency_overrides.pop(get_segip_client, None)


@pytest.mark.asyncio
async def test_endpoint_consultar_persona_validation_error(async_client: AsyncClient):
    # Número de documento muy corto (mínimo 4 caracteres en schema)
    payload = {"numeroDocumento": "12"}
    response = await async_client.post("/api/v1/segip/personas", json=payload)
    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


@pytest.mark.asyncio
async def test_endpoint_solicitar_certificacion(async_client: AsyncClient, test_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_CERTIFICACION_RESPONSE_XML.encode("utf-8"))

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        payload = {"numeroDocumento": "4892341"}
        response = await async_client.post("/api/v1/segip/certificaciones", json=payload)
        assert response.status_code == 200

        body = response.json()
        assert body["success"] is True
        assert body["data"]["esValido"] is True
        assert body["data"]["reporteCertificacionBase64"] is not None
        assert body["error"] is None
    finally:
        app.dependency_overrides.pop(get_segip_client, None)


@pytest.mark.asyncio
async def test_endpoint_verificar_qr(async_client: AsyncClient, test_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_QR_RESPONSE_XML.encode("utf-8"))

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        payload = {"codigoQr": "https://segip.gob.bo/validador/qr/123"}
        response = await async_client.post("/api/v1/segip/certificaciones/qr", json=payload)
        assert response.status_code == 200

        body = response.json()
        assert body["success"] is True
        assert body["data"]["codigoUnico"] == "QR-VERIF-112233"
        assert body["error"] is None

        # Probar alias
        alias_resp = await async_client.post(
            "/api/v1/segip/certificaciones/verificar-qr", json=payload
        )
        assert alias_resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_segip_client, None)


@pytest.mark.asyncio
async def test_endpoint_contrastaciones(async_client: AsyncClient, test_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_CONTRASTACION_RESPONSE_XML.encode("utf-8"))

    mock_client = SegipSoapClient(settings=test_settings, transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_segip_client] = lambda: mock_client

    try:
        payload = {"listaCampos": "CI=4892341", "tipoPersona": 1}
        response = await async_client.post("/api/v1/segip/contrastaciones", json=payload)
        assert response.status_code == 200

        body = response.json()
        assert body["success"] is True
        assert body["data"]["contrastacionJson"] is not None
        assert body["error"] is None
    finally:
        app.dependency_overrides.pop(get_segip_client, None)
