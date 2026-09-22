"""Pruebas unitarias para el cliente SOAP 1.1 de SEGIP."""

import httpx
import pytest

from app.core.config import Settings
from app.integrations.segip.client import SegipSoapClient
from app.integrations.segip.exceptions import (
    SegipAuthError,
    SegipCommunicationError,
    SegipSoapFaultError,
    SegipTimeoutError,
)
from tests.fixtures.soap_responses import (
    MOCK_CERTIFICACION_RESPONSE_XML,
    MOCK_CONTRASTACION_RESPONSE_XML,
    MOCK_PERSONA_RESPONSE_XML,
    MOCK_QR_RESPONSE_XML,
    MOCK_SOAP_FAULT_XML,
    MOCK_VERSION_RESPONSE_XML,
)


@pytest.mark.asyncio
async def test_obtiene_version_sistema_success(test_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert (
            request.headers.get("SOAPAction")
            == '"http://tempuri.org/IServicioExternoInstitucion/ObtieneVersionSistema"'
        )
        assert b"ObtieneVersionSistema" in request.content
        return httpx.Response(200, content=MOCK_VERSION_RESPONSE_XML.encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        version = await client.obtiene_version_sistema()
        assert version == "8.0.0.0"


@pytest.mark.asyncio
async def test_consulta_dato_persona_en_json_success(test_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert b"ConsultaDatoPersonaEnJson" in request.content
        assert b"4892341" in request.content
        return httpx.Response(200, content=MOCK_PERSONA_RESPONSE_XML.encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        result = await client.consulta_dato_persona_en_json(
            numero_documento="4892341",
            complemento="1A",
            nombre="CARLOS",
        )
        assert result["CodigoRespuesta"] == "1"
        assert result["CodigoUnico"] == "UNIQ-123456789"
        assert "DatosPersonaEnFormatoJson" in result


@pytest.mark.asyncio
async def test_consulta_certificacion_pdf_success(test_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_CERTIFICACION_RESPONSE_XML.encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        result = await client.consulta_dato_persona_certificacion(numero_documento="4892341")
        assert result["CodigoRespuesta"] == "1"
        assert "ReporteCertificacion" in result


@pytest.mark.asyncio
async def test_consulta_qr_success(test_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert b"ConsultaVerificacionCertificacionCodigoQr" in request.content
        assert b"pIdInstitucion" in request.content
        return httpx.Response(200, content=MOCK_QR_RESPONSE_XML.encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        result = await client.consulta_verificacion_certificacion_codigo_qr(
            codigo_qr="QR_CODE_DATA"
        )
        assert result["CodigoRespuesta"] == "1"
        assert result["CodigoUnico"] == "QR-VERIF-112233"


@pytest.mark.asyncio
async def test_consulta_contrastacion_success(test_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=MOCK_CONTRASTACION_RESPONSE_XML.encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        result = await client.consulta_dato_persona_contrastacion(lista_campo="Campos")
        assert result["CodigoRespuesta"] == "1"
        assert "ContrastacionEnFormatoJson" in result


@pytest.mark.asyncio
async def test_soap_fault_detection(test_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=MOCK_SOAP_FAULT_XML.encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        with pytest.raises(SegipSoapFaultError) as exc_info:
            await client.obtiene_version_sistema()
        assert "Error interno del servidor" in str(exc_info.value)


@pytest.mark.asyncio
async def test_soap_client_auth_error_401(test_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized")

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        with pytest.raises(SegipAuthError):
            await client.obtiene_version_sistema()


@pytest.mark.asyncio
async def test_soap_client_timeout_error(test_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timeout en lectura")

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        with pytest.raises(SegipTimeoutError):
            await client.obtiene_version_sistema()


@pytest.mark.asyncio
async def test_soap_client_transient_retry_and_fail(test_settings: Settings):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(handler)
    async with SegipSoapClient(settings=test_settings, transport=transport) as client:
        with pytest.raises(SegipCommunicationError):
            await client.obtiene_version_sistema()
    # Con max_retries=1, se realizan 2 intentos
    assert call_count == 2
