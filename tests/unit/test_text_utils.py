"""Pruebas unitarias para las utilidades de texto y fechas."""

from app.utils.text import (
    clean_string,
    normalize_date,
    normalize_gender,
    normalize_marital_status,
    remove_accents,
)


def test_clean_string():
    assert clean_string(None) is None
    assert clean_string("") is None
    assert clean_string("   ") is None
    assert clean_string("null") is None
    assert clean_string("NONE") is None
    assert clean_string("N/A") is None
    assert clean_string("  Juan   Carlos  ") == "Juan Carlos"


def test_remove_accents():
    assert remove_accents("Álvaro José Ñúñez") == "Alvaro Jose Ñuñez"
    assert remove_accents("PÉREZ") == "PEREZ"
    assert remove_accents("") == ""


def test_normalize_date():
    assert normalize_date("15/04/1985") == "1985-04-15"
    assert normalize_date("15-04-1985") == "1985-04-15"
    assert normalize_date("1985-04-15") == "1985-04-15"
    assert normalize_date("15/04/1985 00:00:00") == "1985-04-15"
    assert normalize_date("1985-04-15T12:30:00") == "1985-04-15"
    assert normalize_date(None) is None
    assert normalize_date("fecha_invalida") == "fecha_invalida"


def test_normalize_gender():
    assert normalize_gender("M") == "MASCULINO"
    assert normalize_gender("Masculino") == "MASCULINO"
    assert normalize_gender("Varón") == "MASCULINO"
    assert normalize_gender("F") == "FEMENINO"
    assert normalize_gender("Femenino") == "FEMENINO"
    assert normalize_gender(None) is None


def test_normalize_marital_status():
    assert normalize_marital_status("Soltero") == "SOLTERO"
    assert normalize_marital_status("Casada") == "CASADA"
    assert normalize_marital_status("Divorciado(a)") == "DIVORCIADO(A)"
    assert normalize_marital_status(None) is None
