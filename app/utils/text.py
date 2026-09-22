"""Utilidades para normalización de texto, fechas y formatos."""

import re
import unicodedata
from datetime import datetime


def clean_string(val: str | None) -> str | None:
    """Limpia cadenas de texto, elimina espacios redundantes y retorna None si está vacía.

    Convierte valores como '', 'null', 'None', 'N/A' en None.
    """
    if val is None:
        return None
    cleaned = str(val).strip()
    if not cleaned or cleaned.lower() in ("null", "none", "n/a", "undefined"):
        return None
    # Colapsar espacios múltiples internos
    return re.sub(r"\s+", " ", cleaned)


def remove_accents(text: str) -> str:
    """Elimina tildes y diacríticos preservando la letra Ñ y ñ (ej. 'Ángel' -> 'Angel')."""
    if not text:
        return ""
    # Proteger temporalmente la letra Ñ y ñ para no descomponerlas en N + tilde
    safe_text = text.replace("ñ", "\u0001").replace("Ñ", "\u0002")
    normalized = unicodedata.normalize("NFD", safe_text)
    stripped = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return stripped.replace("\u0001", "ñ").replace("\u0002", "Ñ")


def normalize_date(date_raw: str | None) -> str | None:
    """Normaliza representaciones de fecha a formato ISO YYYY-MM-DD.

    Formatos reconocidos:
      - DD/MM/YYYY
      - DD-MM-YYYY
      - YYYY-MM-DD
      - YYYY/MM/DD
      - DD/MM/YYYY HH:MM:SS
      - YYYY-MM-DDTHH:MM:SS
    """
    cleaned = clean_string(date_raw)
    if not cleaned:
        return None

    # Si contiene hora, extraer solo la porción de fecha
    date_part = cleaned.split("T")[0].split(" ")[0].strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_part, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Si no coincide con ningún formato conocido, devolver limpio
    return date_part


def normalize_gender(raw_gender: str | None) -> str | None:
    """Normaliza el sexo o género a 'MASCULINO', 'FEMENINO' o el valor limpio."""
    cleaned = clean_string(raw_gender)
    if not cleaned:
        return None
    val_upper = remove_accents(cleaned).upper()
    if val_upper in ("M", "MASCULINO", "VARON", "HOMBRE"):
        return "MASCULINO"
    if val_upper in ("F", "FEMENINO", "MUJER"):
        return "FEMENINO"
    return cleaned.upper()


def normalize_marital_status(raw_status: str | None) -> str | None:
    """Normaliza el estado civil a mayúsculas estándar."""
    cleaned = clean_string(raw_status)
    if not cleaned:
        return None
    return remove_accents(cleaned).upper()
