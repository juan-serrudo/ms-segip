"""Esquemas comunes y envoltorios de respuesta de la API según Convenciones UOIT 1.0."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class UoitBaseModel(BaseModel):
    """Modelo base con serialización camelCase y deserialización flexible (UOIT Sección 10)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ApiErrorDetail(UoitBaseModel):
    """Detalle de error en campos para validaciones (UOIT Sección 15.2)."""

    field: str | None = Field(default=None, description="Campo que originó el error de validación")
    message: str = Field(description="Descripción del error en el campo")


class ApiError(UoitBaseModel):
    """Estructura estándar de error institucional (UOIT Sección 15 y 23)."""

    code: str = Field(
        description="Código funcional de error (ej. VALIDATION_ERROR, SEGIP_UNAVAILABLE)"
    )
    details: Any = Field(
        default=None, description="Detalle explicativo, objeto o lista de errores de campo"
    )
    trace_id: str | None = Field(
        default=None, description="Identificador de trazabilidad/correlación"
    )


class ApiResponse[DataT](UoitBaseModel):
    """Estructura estándar de respuesta institucional (UOIT Sección 13 y 23)."""

    success: bool = Field(description="Indica si la operación fue exitosa")
    message: str = Field(description="Mensaje funcional de la operación")
    data: DataT | None = Field(default=None, description="Información devuelta por el servicio")
    meta: dict[str, Any] | None = Field(
        default=None, description="Metadatos adicionales (ej. paginación)"
    )
    error: ApiError | None = Field(
        default=None, description="Información estructurada del error si ocurrió"
    )


# Alias de retrocompatibilidad
APIResponse = ApiResponse
APIError = ApiError
APIErrorDetail = ApiErrorDetail
