"""Definición de excepciones de dominio para ms-segip."""

from typing import Any


class AppException(Exception):
    """Excepción base para todas las excepciones del microservicio."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


# ==============================================================================
# Excepciones de Integración SOAP SEGIP
# ==============================================================================


class SegipUnavailableException(AppException):
    """El servicio SOAP de SEGIP no responde o no se encuentra disponible."""

    def __init__(
        self,
        message: str = "El servicio de verificación SEGIP no está disponible",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_code="SEGIP_UNAVAILABLE",
            details=details,
        )


class SegipTimeoutException(AppException):
    """Tiempo de espera agotado al conectar o consultar el servicio SEGIP."""

    def __init__(
        self,
        message: str = "Tiempo de espera agotado en la comunicación con SEGIP",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=504,
            error_code="SEGIP_TIMEOUT",
            details=details,
        )


class SegipAuthException(AppException):
    """Las credenciales institucionales fueron rechazadas por SEGIP."""

    def __init__(
        self,
        message: str = "Credenciales institucionales rechazadas por el servicio SEGIP",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="SEGIP_AUTH_ERROR",
            details=details,
        )


class SegipNoResultsException(AppException):
    """La consulta a SEGIP no arrojó resultados para los parámetros ingresados."""

    def __init__(
        self,
        message: str = "No se encontraron registros de la persona en SEGIP",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            error_code="SEGIP_NO_RESULTS",
            details=details,
        )


class SegipInvalidResponseException(AppException):
    """La respuesta SOAP recibida desde SEGIP no cumple con el esquema esperado."""

    def __init__(
        self,
        message: str = "Respuesta SOAP de SEGIP inválida o malformada",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=502,
            error_code="SEGIP_INVALID_RESPONSE",
            details=details,
        )


class SegipInvalidJsonException(AppException):
    """El campo JSON interno devuelto por SEGIP no es un JSON válido."""

    def __init__(
        self,
        message: str = "El contenido JSON interno devuelto por SEGIP no es válido",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=502,
            error_code="SEGIP_INVALID_INTERNAL_JSON",
            details=details,
        )


# ==============================================================================
# Excepciones de Procesamiento de PDF
# ==============================================================================


class NotAPdfException(AppException):
    """El archivo proporcionado no es un documento PDF válido."""

    def __init__(
        self,
        message: str = "El archivo enviado no corresponde a un documento PDF válido",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="NOT_A_PDF",
            details=details,
        )


class PdfTooLargeException(AppException):
    """El archivo PDF excede el tamaño máximo permitido."""

    def __init__(
        self,
        message: str = "El archivo PDF excede el tamaño máximo permitido",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=413,
            error_code="PDF_TOO_LARGE",
            details=details,
        )


class PdfCorruptedException(AppException):
    """El documento PDF se encuentra corrupto o no puede ser abierto."""

    def __init__(
        self,
        message: str = "El documento PDF está corrupto o dañado y no pudo abrirse",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code="PDF_CORRUPTED",
            details=details,
        )


class InvalidPdfBase64Exception(AppException):
    """La cadena Base64 proporcionada para el PDF no es válida."""

    def __init__(
        self,
        message: str = "La cadena proporcionada no es una codificación Base64 válida",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_PDF_BASE64",
            details=details,
        )


class UnrecognizedSegipPdfException(AppException):
    """El contenido del PDF no coincide con la estructura de un certificado SEGIP reconocido."""

    def __init__(
        self,
        message: str = "El formato o layout del PDF no corresponde a una certificación SEGIP reconocida",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code="UNRECOGNIZED_SEGIP_PDF_FORMAT",
            details=details,
        )


class PhotoExtractionException(AppException):
    """Error al intentar extraer la fotografía del documento PDF."""

    def __init__(
        self,
        message: str = "Ocurrió un error al extraer la fotografía del PDF",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_code="PHOTO_EXTRACTION_ERROR",
            details=details,
        )


class UnauthorizedException(AppException):
    """Petición no autorizada si se requiere autenticación por API Key o token."""

    def __init__(
        self,
        message: str = "No autorizado: credenciales faltantes o inválidas",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
            details=details,
        )


class StorageException(AppException):
    """Error en las operaciones de almacenamiento de objetos (RustFS / S3)."""

    def __init__(
        self,
        message: str = "Error en el servicio de almacenamiento de objetos",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_code="STORAGE_ERROR",
            details=details,
        )


class PersonaDuplicadaException(AppException):
    """Existen múltiples registros (homónimos) para el documento y se requiere complemento o fecha de nacimiento."""

    def __init__(
        self,
        message: str = "Se encontraron múltiples registros con el documento indicado. Especifique complemento o fecha de nacimiento",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="PERSONA_DUPLICADA_HOMONIMIA",
            details=details,
        )


class SegipQuotaExceededException(AppException):
    """Se ha alcanzado o sobrepasado la cuota diaria de consultas asignada por SEGIP."""

    def __init__(
        self,
        message: str = "Se ha superado la cuota diaria asignada por SEGIP para consultas externas",
        details: Any = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=429,
            error_code="SEGIP_QUOTA_EXCEEDED",
            details=details,
        )
