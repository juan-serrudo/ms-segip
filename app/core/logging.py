"""Configuración de logging estructurado y filtros de seguridad según Convenciones UOIT 1.0 (Sección 17 y 18)."""

import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

# ContextVars para propagar Request ID y Correlation ID de forma asíncrona (UOIT Sección 12 y 17)
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def get_request_id() -> str:
    """Obtiene el Request ID del contexto actual."""
    return request_id_ctx.get()


def set_request_id(req_id: str) -> contextvars.Token[str]:
    """Establece el Request ID en el contexto actual."""
    return request_id_ctx.set(req_id)


def get_correlation_id() -> str:
    """Obtiene el Correlation ID del contexto actual (UOIT Sección 12.4 y 17.2)."""
    return correlation_id_ctx.get()


def set_correlation_id(corr_id: str) -> contextvars.Token[str]:
    """Establece el Correlation ID en el contexto actual."""
    return correlation_id_ctx.set(corr_id)


def mask_document_number(doc: str | None) -> str:
    """Enmascara un número de documento de identidad para proteger datos personales.

    Ejemplos:
        '1234567' -> '12***67'
        '45678'   -> '4***8'
        '123'     -> '***'
    """
    if not doc:
        return "N/A"
    clean_doc = str(doc).strip()
    length = len(clean_doc)
    if length <= 3:
        return "***"
    if length <= 5:
        return f"{clean_doc[0]}***{clean_doc[-1]}"
    return f"{clean_doc[:2]}***{clean_doc[-2:]}"


# Patrones regex para sanitización de logs
_SENSITIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Contraseñas en XML SOAP
    (
        re.compile(r"(<(?:tem:)?pContrasenia[^>]*>)(.*?)(</(?:tem:)?pContrasenia>)", re.IGNORECASE),
        r"\1[REDACTED]\3",
    ),
    (
        re.compile(
            r"(<(?:tem:)?pClaveAccesoUsuarioFinal[^>]*>)(.*?)(</(?:tem:)?pClaveAccesoUsuarioFinal>)",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]\3",
    ),
    # Contraseñas en JSON, query params o asignaciones key=val
    (
        re.compile(
            r"""(["']?(?:password|contrasenia|pContrasenia)["']?\s*[:=]\s*["']?)([^"' \n\r>]+)(["']?)""",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]\3",
    ),
    (
        re.compile(
            r"""(["']?(?:clave_acceso|pClaveAccesoUsuarioFinal)["']?\s*[:=]\s*["']?)([^"' \n\r>]+)(["']?)""",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]\3",
    ),
    # Supresión de Base64 extensos en XML (Fotografía, ReporteCertificacion)
    (
        re.compile(
            r"(<(?:tem:)?Fotografia[^>]*>)[A-Za-z0-9+/=]{60,}(</(?:tem:)?Fotografia>)",
            re.IGNORECASE,
        ),
        r"\1[BASE64_IMAGE_SUPPRESSED]\2",
    ),
    (
        re.compile(
            r"(<(?:tem:)?ReporteCertificacion[^>]*>)[A-Za-z0-9+/=]{60,}(</(?:tem:)?ReporteCertificacion>)",
            re.IGNORECASE,
        ),
        r"\1[BASE64_PDF_SUPPRESSED]\2",
    ),
    # Supresión de Base64 extensos en JSON
    (
        re.compile(
            r'("?(?:fotografia|fotografiaBase64|fotografia_base64|reporte_certificacion|reporteCertificacion)"?\s*:\s*")[A-Za-z0-9+/=]{60,}(")',
            re.IGNORECASE,
        ),
        r"\1[BASE64_SUPPRESSED]\2",
    ),
]


def sanitize_sensitive_data(message: str) -> str:
    """Elimina contraseñas, claves y payloads Base64 voluminosos del texto de registro."""
    if not isinstance(message, str):
        return str(message)
    sanitized = message
    for pattern, replacement in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class SensitiveDataFilter(logging.Filter):
    """Filtro de logging que enmascara información sensible e inyecta identificadores de trazabilidad."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.correlation_id = get_correlation_id()

        # Sanitizar mensaje principal si es cadena
        if isinstance(record.msg, str):
            record.msg = sanitize_sensitive_data(record.msg)

        # Sanitizar argumentos posicionales si los hay
        if record.args:
            sanitized_args: list[Any] = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(sanitize_sensitive_data(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)

        return True


class StructuredFormatter(logging.Formatter):
    """Formateador de texto consistente con timestamp, nivel, requestId y correlationId."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = getattr(record, "request_id", "-")
        corr_id = getattr(record, "correlation_id", "-")
        record.request_id = req_id if req_id else "-"
        record.correlation_id = corr_id if corr_id else "-"
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """Formateador de logs estructurados en JSON según UOIT Sección 18."""

    def __init__(self, service_name: str = "ms-segip", environment: str = "development") -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        req_id = getattr(record, "request_id", "-")
        corr_id = getattr(record, "correlation_id", "-")

        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "requestId": req_id if req_id != "-" else None,
            "correlationId": corr_id if corr_id != "-" else None,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "text",
    service_name: str = "ms-segip",
    environment: str = "development",
) -> None:
    """Inicializa la configuración de logging del microservicio."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    filter_instance = SensitiveDataFilter()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(filter_instance)

    if log_format.lower() == "json":
        formatter = JsonFormatter(service_name=service_name, environment=environment)
    else:
        fmt = "%(asctime)s [%(levelname)s] [req_id=%(request_id)s] [corr_id=%(correlation_id)s] %(name)s: %(message)s"
        formatter = StructuredFormatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")

    handler.setFormatter(formatter)

    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Eliminar manejadores existentes para evitar duplicados
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)

    # Configurar loggers de terceros para no inundar con DEBUG
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
