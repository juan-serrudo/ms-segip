"""Pruebas unitarias para el mapeador de respuestas SOAP de SEGIP."""

import json

import pytest

from app.core.exceptions import SegipInvalidJsonException
from app.integrations.segip.mapper import SegipResponseMapper
from tests.fixtures.soap_responses import (
    MOCK_FOTO_BASE64,
    MOCK_PERSONA_JSON,
)


def test_map_to_persona_normalizada_success():
    raw_soap_result = {
        "CodigoRespuesta": "1",
        "CodigoUnico": "UNIQ-998877",
        "DescripcionRespuesta": "CONSULTA CORRECTA",
        "EsValido": "true",
        "DatosPersonaEnFormatoJson": json.dumps(MOCK_PERSONA_JSON),
        "Fotografia": MOCK_FOTO_BASE64,
    }

    normalized = SegipResponseMapper.map_to_persona_normalizada(raw_soap_result)

    assert normalized.persona.numero_documento == "4892341"
    assert normalized.persona.complemento == "1A"
    assert normalized.persona.nombres == "CARLOS ANDRES"
    assert normalized.persona.primer_apellido == "MAMANI"
    assert normalized.persona.segundo_apellido == "QUISPE"
    assert normalized.persona.fecha_nacimiento == "1990-05-15"
    assert normalized.persona.sexo == "MASCULINO"
    assert normalized.persona.estado_civil == "SOLTERO"
    assert normalized.persona.fotografia_base64 == MOCK_FOTO_BASE64

    assert normalized.nacimiento.pais == "BOLIVIA"
    assert normalized.nacimiento.departamento == "LA PAZ"
    assert normalized.nacimiento.provincia == "MURILLO"
    assert normalized.nacimiento.localidad == "NUESTRA SEÑORA DE LA PAZ"

    assert normalized.consulta.codigo_unico == "UNIQ-998877"
    assert normalized.consulta.codigo_respuesta == 1
    assert normalized.consulta.descripcion == "CONSULTA CORRECTA"
    assert normalized.consulta.fecha_consulta is not None


def test_map_to_persona_normalizada_invalid_internal_json():
    raw_soap_result = {
        "CodigoRespuesta": "1",
        "CodigoUnico": "UNIQ-ERR",
        "DatosPersonaEnFormatoJson": "{ESTO NO ES UN JSON",
    }

    with pytest.raises(SegipInvalidJsonException):
        SegipResponseMapper.map_to_persona_normalizada(raw_soap_result)


def test_map_to_certificacion():
    raw_soap_result = {
        "CodigoRespuesta": 1,
        "CodigoUnico": "CERT-1122",
        "DescripcionRespuesta": "OK",
        "EsValido": True,
        "Mensaje": "EMITIDO",
        "ReporteCertificacion": "BASE64_PDF_DUMMY",
    }

    cert = SegipResponseMapper.map_to_certificacion(raw_soap_result)
    assert cert.es_valido is True
    assert cert.codigo_unico == "CERT-1122"
    assert cert.reporte_certificacion_base64 == "BASE64_PDF_DUMMY"


def test_map_to_qr_verificacion():
    raw_soap_result = {
        "CodigoRespuesta": 1,
        "CodigoUnico": "QR-99",
        "DescripcionRespuesta": "AUTENTICO",
        "EsValido": "1",
        "Mensaje": "VALIDO",
        "ReporteCertificacion": "BASE64_PDF_DUMMY",
    }

    qr = SegipResponseMapper.map_to_qr_verificacion(raw_soap_result)
    assert qr.es_valido is True
    assert qr.codigo_unico == "QR-99"


def test_map_to_contrastacion():
    raw_soap_result = {
        "CodigoRespuesta": 1,
        "CodigoUnico": "CONTRAST-01",
        "EsValido": True,
        "ContrastacionEnFormatoJson": '{"CI": true}',
    }

    contrast = SegipResponseMapper.map_to_contrastacion(raw_soap_result)
    assert contrast.es_valido is True
    assert contrast.contrastacion_json == '{"CI": true}'
