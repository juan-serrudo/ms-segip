"""Excepciones específicas para la capa de integración SOAP de SEGIP."""

from typing import Any


class SegipIntegrationError(Exception):
    """Excepción base para errores ocurridos en la integración con SEGIP."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class SegipSoapFaultError(SegipIntegrationError):
    """El servicio SEGIP devolvió un error a nivel de protocolo SOAP Fault."""

    def __init__(self, fault_code: str, fault_string: str, detail: str = "") -> None:
        msg = f"SOAP Fault [{fault_code}]: {fault_string}"
        super().__init__(
            message=msg, details={"code": fault_code, "string": fault_string, "detail": detail}
        )
        self.fault_code = fault_code
        self.fault_string = fault_string
        self.detail = detail


class SegipCommunicationError(SegipIntegrationError):
    """Error de conexión o transporte HTTP al contactar con SEGIP."""


class SegipTimeoutError(SegipIntegrationError):
    """Tiempo de espera agotado al conectar o recibir respuesta de SEGIP."""


class SegipAuthError(SegipIntegrationError):
    """Fallo de autenticación con las credenciales institucionales de SEGIP."""


class SegipEmptyResponseError(SegipIntegrationError):
    """El servicio SEGIP respondió con un cuerpo vacío o sin elemento Result."""


class SegipJsonParseError(SegipIntegrationError):
    """Error al parsear el JSON embebido dentro de la respuesta SOAP."""
