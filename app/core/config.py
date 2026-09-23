"""Configuración centralizada del microservicio ms-segip."""

import json
from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(v: object) -> list[str]:
    if isinstance(v, str):
        val = v.strip()
        if val.startswith("[") and val.endswith("]"):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in val.split(",") if item.strip()]
    if isinstance(v, list):
        return [str(item).strip() for item in v]
    return ["*"]


CorsOriginsType = Annotated[list[str], BeforeValidator(_parse_cors_origins)]


class Settings(BaseSettings):
    """Parámetros de configuración cargados desde variables de entorno o archivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Configuración de la aplicación
    APP_NAME: str = Field(default="ms-segip", description="Nombre del microservicio")
    APP_VERSION: str = Field(default="1.0.0", description="Versión del microservicio")
    ENVIRONMENT: str = Field(default="development", description="Entorno de despliegue")
    LOG_LEVEL: str = Field(default="INFO", description="Nivel de logs (DEBUG, INFO, WARN, ERROR)")
    LOG_FORMAT: str = Field(
        default="text", description="Formato de logs: 'text' o 'json' (UOIT Sección 18)"
    )
    HOST: str = Field(default="0.0.0.0", description="Host de escucha")
    PORT: int = Field(default=8000, description="Puerto de escucha")

    # Parámetros del servicio SOAP SEGIP
    # Se debe utilizar el nombre de host institucional configurado por DNS, sin IP fija
    SEGIP_SERVICE_URL: str = Field(
        default="https://segip-api.fiscalia.gob.bo/ServicioExternoInstitucion.svc",
        description="URL institucional del servicio SOAP de SEGIP",
    )
    SEGIP_WSDL_URL: str = Field(
        default="https://segip-api.fiscalia.gob.bo/ServicioExternoInstitucion.svc?singleWsdl",
        description="URL del WSDL del servicio SOAP de SEGIP",
    )
    SEGIP_INSTITUTION_CODE: int = Field(
        default=999,
        description="Código de institución asignado por SEGIP",
    )
    SEGIP_USERNAME: str = Field(
        default="",
        description="Usuario institucional para autenticación en SOAP",
    )
    SEGIP_PASSWORD: str = Field(
        default="",
        description="Contraseña institucional para autenticación en SOAP",
    )
    SEGIP_CONNECT_TIMEOUT: float = Field(
        default=5.0,
        description="Timeout de conexión en segundos hacia el servicio SOAP",
    )
    SEGIP_READ_TIMEOUT: float = Field(
        default=15.0,
        description="Timeout de lectura en segundos para respuestas SOAP",
    )
    SEGIP_MAX_RETRIES: int = Field(
        default=3,
        description="Cantidad máxima de reintentos para fallos transitorios de red",
    )
    SEGIP_USUARIO_FINAL: str = Field(
        default="",
        description="Clave o código de acceso de usuario final/operador por defecto (pClaveAccesoUsuarioFinal)",
    )
    SEGIP_FALLBACK_TO_CERTIFICACION: bool = Field(
        default=True,
        description="Recurrir automáticamente a ConsultaDatoPersonaCertificacion si la consulta JSON no está asignada",
    )

    # Parámetros para procesamiento de PDFs
    PDF_MAX_SIZE_MB: float = Field(
        default=10.0,
        description="Tamaño máximo permitido en Megabytes para archivos PDF",
    )

    # Seguridad y CORS
    CORS_ORIGINS: CorsOriginsType = Field(
        default=["*"],
        description="Orígenes permitidos para CORS",
    )
    API_KEY: str | None = Field(
        default=None,
        description="Clave de API opcional para proteger los endpoints si se configura",
    )

    # Pruebas de integración
    RUN_SEGIP_INTEGRATION_TESTS: bool = Field(
        default=False,
        description="Habilita pruebas de integración directas contra la intranet de SEGIP",
    )

    @property
    def pdf_max_size_bytes(self) -> int:
        """Retorna el tamaño máximo de PDF en bytes."""
        return int(self.PDF_MAX_SIZE_MB * 1024 * 1024)

    @property
    def is_production(self) -> bool:
        """Determina si la aplicación se ejecuta en entorno productivo."""
        return self.ENVIRONMENT.lower() in ("production", "prod")


@lru_cache
def get_settings() -> Settings:
    """Retorna una instancia singleton cacheada de Settings."""
    return Settings()
