"""Pruebas unitarias para los endpoints de extracción de datos de PDFs."""

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

    response = await async_client.post("/api/v1/pdfs/extraer", files=files, data=data)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["persona"]["numero_documento"] == "6842190"
    assert body["data"]["persona"]["nombres"] == "ROBERTO CARLOS"
    assert body["data"]["persona"]["fotografia_base64"] is not None


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_multipart_corrupted(async_client: AsyncClient):
    files = {"file": ("corrupto.pdf", MOCK_CORRUPTED_PDF_BYTES, "application/pdf")}

    response = await async_client.post("/api/v1/pdfs/extraer", files=files)
    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["errors"][0]["code"] == "PDF_CORRUPTED"


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_multipart_non_pdf(async_client: AsyncClient):
    files = {"file": ("falso.pdf", MOCK_NON_PDF_BYTES, "application/pdf")}

    response = await async_client.post("/api/v1/pdfs/extraer", files=files)
    assert response.status_code == 400

    body = response.json()
    assert body["success"] is False
    assert body["errors"][0]["code"] == "NOT_A_PDF"


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_base64_success(async_client: AsyncClient):
    pdf_bytes = create_mock_segip_pdf(include_photo=False)
    b64_str = base64.b64encode(pdf_bytes).decode("ascii")

    payload = {
        "pdf_base64": b64_str,
        "extraer_fotografia": False,
    }
    response = await async_client.post("/api/v1/pdfs/extraer-base64", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["persona"]["numero_documento"] == "6842190"
    assert body["data"]["persona"]["fotografia_base64"] is None


@pytest.mark.asyncio
async def test_endpoint_extraer_pdf_base64_invalid(async_client: AsyncClient):
    payload = {
        "pdf_base64": "invalid_base64_string!!!",
        "extraer_fotografia": False,
    }
    response = await async_client.post("/api/v1/pdfs/extraer-base64", json=payload)
    assert response.status_code == 400

    body = response.json()
    assert body["success"] is False
    assert body["errors"][0]["code"] == "INVALID_PDF_BASE64"
