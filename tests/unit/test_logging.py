"""Pruebas unitarias para el enmascaramiento de datos y sanitización de logs."""

import logging

from app.core.logging import (
    SensitiveDataFilter,
    mask_document_number,
    sanitize_sensitive_data,
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
    assert "Secreta456" not in record.msg
    assert "[REDACTED]" in record.msg
