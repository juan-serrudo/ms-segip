"""Pruebas unitarias para el endpoint REST POST /api/v1/segip/certificaciones/consultar-persona (UOIT 1.0)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_persona_certificada_service
from app.core.exceptions import PersonaDuplicadaException
from app.main import app
from app.schemas.pdf import DatosCertificadoPdf
from app.schemas.persona_certificada import (
    ArchivosCertificacion,
    MetadatosConsultaPersona,
    PersonaCertificadaResponseData,
)
from app.schemas.segip import DatosNacimiento, DatosPersona
from app.services.persona_certificada_service import PersonaCertificadaService


@pytest.mark.asyncio
async def test_endpoint_consultar_persona_certificada_success(async_client: AsyncClient):
    """Verifica que el endpoint responda 200 con el sobre genérico ApiResponse en camelCase."""
    mock_service = MagicMock(spec=PersonaCertificadaService)

    mock_resp = PersonaCertificadaResponseData(
        persona=DatosPersona(
            numero_documento="6842190",
            complemento="1B",
            nombres="ROBERTO CARLOS",
            primer_apellido="FLORES",
            segundo_apellido="CONDORI",
            estado_civil="CASADO",
            sexo="MASCULINO",
        ),
        nacimiento=DatosNacimiento(
            pais="BOLIVIA",
            departamento="COCHABAMBA",
            provincia="CERCADO",
            localidad="COCHABAMBA",
        ),
        certificado=DatosCertificadoPdf(
            numero_emision="CERT-2026-00452",
            codigo_segip="SEG-778899",
            fecha_emision="15/02/2026 10:15:30",
            motivo_consulta="TRAMITE",
            paginas=1,
        ),
        archivos=ArchivosCertificacion(
            url_presignada_pdf="http://localhost:9000/segip-archivos/cert.pdf?exp=300",
            url_presignada_imagen="http://localhost:9000/segip-archivos/foto.jpg?exp=300",
            vigencia_segundos=300,
            fecha_expiracion=datetime.now(UTC),
        ),
        metadatos=MetadatosConsultaPersona(
            origen_datos="CACHE_BD",
            es_refrescado=False,
            aviso=None,
            fecha_ultima_consulta_segip=datetime.now(UTC),
            total_certificaciones_registradas=1,
        ),
    )

    mock_service.consultar_o_certificar_persona = AsyncMock(return_value=mock_resp)
    app.dependency_overrides[get_persona_certificada_service] = lambda: mock_service

    try:
        payload = {
            "numeroDocumento": "6842190",
            "complemento": "1B",
            "forzarActualizacion": False,
            "generarUrlPdf": True,
            "generarUrlImagen": True,
            "tiempoExpiracionUrlSegundos": 300,
        }

        response = await async_client.post(
            "/api/v1/segip/certificaciones/consultar-persona",
            json=payload,
        )

        assert response.status_code == 200
        body = response.json()

        # Estándar UOIT
        assert body["success"] is True
        assert body["error"] is None
        assert body["message"] == "Consulta de persona y certificación procesada exitosamente"

        data = body["data"]
        # Serialización camelCase
        assert data["persona"]["numeroDocumento"] == "6842190"
        assert data["persona"]["primerApellido"] == "FLORES"
        assert (
            data["archivos"]["urlPresignadaPdf"]
            == "http://localhost:9000/segip-archivos/cert.pdf?exp=300"
        )
        assert data["archivos"]["vigenciaSegundos"] == 300
        assert data["metadatos"]["origenDatos"] == "CACHE_BD"
        assert data["metadatos"]["esRefrescado"] is False

    finally:
        app.dependency_overrides.pop(get_persona_certificada_service, None)


@pytest.mark.asyncio
async def test_endpoint_consultar_persona_certificada_error_homonimia_409(
    async_client: AsyncClient,
):
    """Verifica el manejo de error 409 cuando existen múltiples registros / homónimos."""
    mock_service = MagicMock(spec=PersonaCertificadaService)
    mock_service.consultar_o_certificar_persona = AsyncMock(
        side_effect=PersonaDuplicadaException(
            message="Múltiples registros detectados. Especifique complemento.",
            details={"total": 2},
        )
    )
    app.dependency_overrides[get_persona_certificada_service] = lambda: mock_service

    try:
        payload = {
            "numeroDocumento": "4892341",
            "complemento": "",
        }

        response = await async_client.post(
            "/api/v1/segip/certificaciones/consultar-persona",
            json=payload,
        )

        assert response.status_code == 409
        body = response.json()
        assert body["success"] is False
        assert body["data"] is None
        assert body["error"]["code"] == "PERSONA_DUPLICADA_HOMONIMIA"
        assert "Múltiples registros detectados" in body["message"]

    finally:
        app.dependency_overrides.pop(get_persona_certificada_service, None)


@pytest.mark.asyncio
async def test_endpoint_consultar_persona_certificada_validation_error_422(
    async_client: AsyncClient,
):
    """Verifica que si no se provee el número de documento se retorne error 422."""
    payload = {
        "complemento": "1B",
    }
    response = await async_client.post(
        "/api/v1/segip/certificaciones/consultar-persona",
        json=payload,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
