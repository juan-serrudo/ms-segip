"""Pruebas unitarias para el enmascaramiento de datos y sanitización de logs según Convenciones UOIT."""

import json
import logging

from app.core.logging import (
    JsonFormatter,
    SensitiveDataFilter,
    mask_document_number,
    sanitize_sensitive_data,
    set_correlation_id,
    set_request_id,
)


def test_mask_document_number():
    assert mask_document_number(None) == "N/A"
    assert mask_document_number("") == "N/A"
    assert mask_document_number("12") == "***"
    assert mask_document_number("123") == "***"
    assert mask_document_number("12345") == "1***5"
    assert mask_document_number("1234567") == "12***67"
    assert mask_document_number("10293847") == "10***47"


def test_sanitize_sensitive_xml_passwords():
    xml_input = (
        "<tem:ConsultaDatoPersonaEnJson>"
        "<tem:pUsuario>test_user</tem:pUsuario>"
        "<tem:pContrasenia>MiPasswordSuperSecreto123!</tem:pContrasenia>"
        "<tem:pClaveAccesoUsuarioFinal>ClaveOperador999</tem:pClaveAccesoUsuarioFinal>"
        "</tem:ConsultaDatoPersonaEnJson>"
    )
    sanitized = sanitize_sensitive_data(xml_input)

    assert "MiPasswordSuperSecreto123!" not in sanitized
    assert "ClaveOperador999" not in sanitized
    assert "[REDACTED]" in sanitized
    assert "test_user" in sanitized


def test_sanitize_large_base64_strings():
    huge_base64 = "A" * 120
    xml_with_photo = f"<tem:Fotografia>{huge_base64}</tem:Fotografia>"
    sanitized = sanitize_sensitive_data(xml_with_photo)

    assert huge_base64 not in sanitized
    assert "[BASE64_IMAGE_SUPPRESSED]" in sanitized


def test_sensitive_data_filter_record():
    set_request_id("REQ-TEST-1234")
    set_correlation_id("CORR-TEST-5678")
    filt = SensitiveDataFilter()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Invocando con pContrasenia='Secreta456'",
        args=(),
        exc_info=None,
    )

    result = filt.filter(record)
    assert result is True
    assert record.request_id == "REQ-TEST-1234"
    assert record.correlation_id == "CORR-TEST-5678"
    assert "Secreta456" not in record.msg
    assert "[REDACTED]" in record.msg


def test_json_formatter_uoit():
    """Prueba el formato de log estructurado en JSON según UOIT Sección 18."""
    set_request_id("REQ-JSON-1122")
    set_correlation_id("CORR-JSON-3344")

    formatter = JsonFormatter(service_name="ms-segip", environment="testing")
    filt = SensitiveDataFilter()

    record = logging.LogRecord(
        name="test_service",
        level=logging.INFO,
        pathname="service.py",
        lineno=25,
        msg="Operación ejecutada con éxito",
        args=(),
        exc_info=None,
    )
    filt.filter(record)

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["service"] == "ms-segip"
    assert parsed["environment"] == "testing"
    assert parsed["level"] == "INFO"
    assert parsed["requestId"] == "REQ-JSON-1122"
    assert parsed["correlationId"] == "CORR-JSON-3344"
    assert parsed["message"] == "Operación ejecutada con éxito"
    assert "timestamp" in parsed
