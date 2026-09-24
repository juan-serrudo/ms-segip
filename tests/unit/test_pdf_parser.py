"""Pruebas unitarias para el parser de documentos PDF de SEGIP."""

import pymupdf
import pytest

from app.core.exceptions import (
    PdfCorruptedException,
    UnrecognizedSegipPdfException,
)
from app.parsers.segip_pdf_parser import SegipPdfParser
from tests.fixtures.mock_pdfs import (
    MOCK_CORRUPTED_PDF_BYTES,
    create_mock_segip_pdf,
)


def test_parse_standard_segip_pdf_with_photo():
    pdf_bytes = create_mock_segip_pdf(include_photo=True, layout_variant="standard")

    parser = SegipPdfParser(pdf_bytes=pdf_bytes, extraer_fotografia=True)
    result = parser.parse()

    # Verificar persona
    assert result.persona.numero_documento == "6842190"
    assert result.persona.complemento == "1B"
    assert result.persona.nombres == "ROBERTO CARLOS"
    assert result.persona.primer_apellido == "FLORES"
    assert result.persona.segundo_apellido == "CONDORI"
    assert result.persona.fecha_nacimiento == "1988-09-24"
    assert result.persona.sexo == "MASCULINO"
    assert result.persona.estado_civil == "CASADO"
    assert result.persona.profesion_ocupacion == "ARQUITECTO"
    assert result.persona.domicilio == "CALLE LOS PINOS NRO. 450"
    assert result.persona.fotografia_base64 is not None

    # Verificar nacimiento
    assert result.nacimiento.pais == "BOLIVIA"
    assert result.nacimiento.departamento == "COCHABAMBA"
    assert result.nacimiento.provincia == "CERCADO"
    assert result.nacimiento.localidad == "COCHABAMBA"

    # Verificar certificado
    assert result.certificado.numero_emision == "CERT-2026-00452"
    assert result.certificado.codigo_segip == "SEG-778899"
    assert result.certificado.paginas == 1


def test_parse_standard_segip_pdf_without_photo():
    pdf_bytes = create_mock_segip_pdf(include_photo=True, layout_variant="standard")

    # Extraer sin solicitar fotografía
    parser = SegipPdfParser(pdf_bytes=pdf_bytes, extraer_fotografia=False)
    result = parser.parse()

    assert result.persona.numero_documento == "6842190"
    assert result.persona.fotografia_base64 is None


def test_parse_segip_pdf_variant_layout():
    pdf_bytes = create_mock_segip_pdf(include_photo=False, layout_variant="composite_birth")

    parser = SegipPdfParser(pdf_bytes=pdf_bytes, extraer_fotografia=False)
    result = parser.parse()

    assert result.persona.numero_documento == "7654321"
    assert result.persona.complemento == "LP"
    assert result.persona.nombres == "MARIA ELENA"
    assert result.persona.primer_apellido == "MAMANI"
    assert result.persona.segundo_apellido == "GOMEZ"
    assert result.persona.fecha_nacimiento == "1992-11-05"
    assert result.persona.sexo == "FEMENINO"
    assert result.persona.estado_civil == "SOLTERA"

    assert result.nacimiento.pais == "BOLIVIA"
    assert result.nacimiento.departamento == "LA PAZ"


def test_parse_segip_pdf_validation_report():
    pdf_bytes = create_mock_segip_pdf(include_photo=True, layout_variant="validation_report")

    parser = SegipPdfParser(pdf_bytes=pdf_bytes, extraer_fotografia=True)
    result = parser.parse()

    assert result.persona.numero_documento == "1146351"
    assert result.persona.nombres == "JUAN VICTOR"
    assert result.persona.primer_apellido == "SERRUDO"
    assert result.persona.segundo_apellido == "CHAVEZ"
    assert result.persona.fecha_nacimiento == "1986-10-16"
    assert result.persona.sexo == "MASCULINO"
    assert result.persona.estado_civil == "CASADO"
    assert result.persona.profesion_ocupacion == "ING. DE SISTEMAS"
    assert result.persona.domicilio == "CLL/INDEPENDENCIA N° 120 ZONA YURAC YURAC-SUCRE"
    assert result.persona.fotografia_base64 is not None

    assert result.nacimiento.pais == "BOLIVIA"
    assert result.nacimiento.departamento == "CHUQUISACA"
    assert result.nacimiento.provincia == "OROPEZA"
    assert result.nacimiento.localidad == "SUCRE"

    assert result.certificado.codigo_segip == "c4CAXTej-4774047"
    assert (
        result.certificado.motivo_consulta
        == "CONVENIO - FISCALIA GENERAL DEL ESTADO MINISTERIO PUBLICO"
    )


def test_parse_segip_pdf_convenio_brackets():
    pdf_bytes = create_mock_segip_pdf(include_photo=False, layout_variant="convenio_brackets")

    parser = SegipPdfParser(pdf_bytes=pdf_bytes, extraer_fotografia=False)
    result = parser.parse()

    assert result.persona.numero_documento == "7560566"
    assert result.persona.complemento == "1F"
    assert result.persona.nombres == "NOEMI JHUSTIN"
    assert result.persona.primer_apellido == "MENCHACA"
    assert result.persona.segundo_apellido == "ROMERO"
    assert result.persona.fecha_nacimiento == "1993-10-29"
    assert result.persona.sexo == "FEMENINO"
    assert result.persona.estado_civil == "SOLTERA"
    assert result.persona.profesion_ocupacion == "ESTUDIANTE"
    assert result.persona.domicilio == "CLL/NUEVA ESPERANZA- N°50- Z/ALTO TUCSUPAYA-SUCRE"

    assert result.nacimiento.pais == "BOLIVIA"
    assert result.nacimiento.departamento == "CHUQUISACA"
    assert result.nacimiento.provincia == "OROPEZA"
    assert result.nacimiento.localidad == "SUCRE"

    assert result.certificado.codigo_segip == "BzxPgh8Y-0347041"


def test_parse_unrecognized_pdf():
    # PDF válido pero sin palabras clave de SEGIP
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        pymupdf.Point(50, 50), "Este es un documento corporativo cualquiera de facturación."
    )
    generic_pdf_bytes = doc.tobytes()
    doc.close()

    parser = SegipPdfParser(pdf_bytes=generic_pdf_bytes)
    with pytest.raises(UnrecognizedSegipPdfException):
        parser.parse()


def test_parse_corrupted_pdf():
    parser = SegipPdfParser(pdf_bytes=MOCK_CORRUPTED_PDF_BYTES)
    with pytest.raises(PdfCorruptedException):
        parser.parse()
