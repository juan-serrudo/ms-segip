"""Pruebas unitarias para las validaciones y servicio de procesamiento de PDF."""

import base64
import io

import pytest
from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import (
    InvalidPdfBase64Exception,
    NotAPdfException,
    PdfTooLargeException,
)
from app.services.pdf_service import PdfService
from tests.fixtures.mock_pdfs import MOCK_NON_PDF_BYTES, create_mock_segip_pdf


@pytest.fixture
def pdf_service(test_settings: Settings) -> PdfService:
    return PdfService(settings=test_settings)


@pytest.mark.asyncio
async def test_process_uploaded_pdf_success(pdf_service: PdfService):
    pdf_bytes = create_mock_segip_pdf(include_photo=False)
    file = UploadFile(
        filename="certificado_segip.pdf",
        file=io.BytesIO(pdf_bytes),
        headers={"content-type": "application/pdf"},
    )

    result = await pdf_service.process_uploaded_pdf(file=file, extraer_fotografia=False)
    assert result.persona.numero_documento == "6842190"


@pytest.mark.asyncio
async def test_process_uploaded_pdf_invalid_extension(pdf_service: PdfService):
    file = UploadFile(
        filename="documento.docx",
        file=io.BytesIO(b"%PDF-test"),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(NotAPdfException) as exc:
        await pdf_service.process_uploaded_pdf(file=file)
    assert "Extensión no permitida" in str(exc.value.details)


@pytest.mark.asyncio
async def test_process_uploaded_pdf_invalid_mime(pdf_service: PdfService):
    file = UploadFile(
        filename="documento.pdf",
        file=io.BytesIO(b"%PDF-test"),
        headers={"content-type": "text/html"},
    )

    with pytest.raises(NotAPdfException) as exc:
        await pdf_service.process_uploaded_pdf(file=file)
    assert "MIME" in str(exc.value.details)


@pytest.mark.asyncio
async def test_process_uploaded_pdf_invalid_magic_bytes(pdf_service: PdfService):
    file = UploadFile(
        filename="archivo.pdf",
        file=io.BytesIO(MOCK_NON_PDF_BYTES),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(NotAPdfException) as exc:
        await pdf_service.process_uploaded_pdf(file=file)
    assert "firma binaria" in str(exc.value.details)


@pytest.mark.asyncio
async def test_process_uploaded_pdf_size_exceeded(test_settings: Settings):
    # Configurar un límite diminuto para probar el rechazo por tamaño
    tiny_settings = Settings(PDF_MAX_SIZE_MB=0.0001)  # ~100 bytes
    tiny_service = PdfService(settings=tiny_settings)

    pdf_bytes = create_mock_segip_pdf()
    file = UploadFile(
        filename="pesado.pdf",
        file=io.BytesIO(pdf_bytes),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(PdfTooLargeException):
        await tiny_service.process_uploaded_pdf(file=file)


def test_process_base64_pdf_success(pdf_service: PdfService):
    pdf_bytes = create_mock_segip_pdf(include_photo=False)
    b64_str = base64.b64encode(pdf_bytes).decode("ascii")

    result = pdf_service.process_base64_pdf(base64_str=b64_str, extraer_fotografia=False)
    assert result.persona.numero_documento == "6842190"


def test_process_base64_pdf_data_uri_prefix(pdf_service: PdfService):
    pdf_bytes = create_mock_segip_pdf(include_photo=False)
    b64_str = f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode('ascii')}"

    result = pdf_service.process_base64_pdf(base64_str=b64_str, extraer_fotografia=False)
    assert result.persona.numero_documento == "6842190"


def test_process_base64_invalid_string(pdf_service: PdfService):
    with pytest.raises(InvalidPdfBase64Exception):
        pdf_service.process_base64_pdf(base64_str="Esto no es un base64 valido!!!")


def test_process_base64_empty_string(pdf_service: PdfService):
    with pytest.raises(InvalidPdfBase64Exception):
        pdf_service.process_base64_pdf(base64_str="   ")
