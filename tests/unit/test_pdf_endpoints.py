"""Pruebas unitarias para los endpoints de extracción de datos de PDFs según Convenciones UOIT 1.0."""

import base64

import pytest
from httpx import AsyncClient

from tests.fixtures.mock_pdfs import (
    MOCK_CORRUPTED_PDF_BYTES,
    MOCK_NON_PDF_BYTES,
    create_mock_segip_pdf,
)


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_multipart_success(async_client: AsyncClient):
    pdf_bytes = create_mock_segip_pdf(include_photo=True)

    files = {"file": ("certificado.pdf", pdf_bytes, "application/pdf")}
    data = {"extraer_fotografia": "true"}

    # Probar endpoint sustantivo UOIT /pdfs
    response = await async_client.post("/api/v1/pdfs", files=files, data=data)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["persona"]["numeroDocumento"] == "6842190"
    assert body["data"]["persona"]["nombres"] == "ROBERTO CARLOS"
    assert body["data"]["persona"]["fotografiaBase64"] is not None
    assert body["error"] is None

    # Probar alias /pdfs/extraer
    alias_resp = await async_client.post("/api/v1/pdfs/extraer", files=files, data=data)
    assert alias_resp.status_code == 200
    assert alias_resp.json()["data"]["persona"]["numeroDocumento"] == "6842190"


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_multipart_corrupted(async_client: AsyncClient):
    files = {"file": ("corrupto.pdf", MOCK_CORRUPTED_PDF_BYTES, "application/pdf")}

    response = await async_client.post("/api/v1/pdfs", files=files)
    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PDF_CORRUPTED"
    assert body["error"]["traceId"] is not None


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_multipart_non_pdf(async_client: AsyncClient):
    files = {"file": ("falso.pdf", MOCK_NON_PDF_BYTES, "application/pdf")}

    response = await async_client.post("/api/v1/pdfs", files=files)
    assert response.status_code == 400

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_A_PDF"


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_base64_success(async_client: AsyncClient):
    pdf_bytes = create_mock_segip_pdf(include_photo=False)
    b64_str = base64.b64encode(pdf_bytes).decode("ascii")

    payload = {
        "pdfBase64": b64_str,
        "extraerFotografia": False,
    }
    # Probar endpoint sustantivo UOIT /pdfs/base64
    response = await async_client.post("/api/v1/pdfs/base64", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["persona"]["numeroDocumento"] == "6842190"
    assert body["data"]["persona"]["fotografiaBase64"] is None
    assert body["error"] is None

    # Probar alias /pdfs/extraer-base64
    alias_resp = await async_client.post("/api/v1/pdfs/extraer-base64", json=payload)
    assert alias_resp.status_code == 200


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_base64_invalid(async_client: AsyncClient):
    payload = {
        "pdfBase64": "invalid_base64_string!!!",
        "extraerFotografia": False,
    }
    response = await async_client.post("/api/v1/pdfs/base64", json=payload)
    assert response.status_code == 400

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_PDF_BASE64"
