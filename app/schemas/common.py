"""Esquemas comunes y envoltorios de respuesta de la API."""

from pydantic import BaseModel, Field


class APIErrorDetail(BaseModel):
    """Detalle de un error en la respuesta de la API."""

    code: str = Field(description="Código identificador del error")
    message: str = Field(description="Mensaje legible para el usuario o cliente")
    field: str | None = Field(
        default=None, description="Campo específico asociado al error, si aplica"
    )


class APIResponse[DataT](BaseModel):
    """Estructura normalizada y consistente para todas las respuestas del microservicio."""

    success: bool = Field(description="Indica si la operación fue exitosa")
    message: str = Field(description="Mensaje descriptivo del resultado")
    request_id: str = Field(description="Identificador de correlación único de la petición")
    data: DataT | None = Field(default=None, description="Carga útil con los datos de respuesta")
    errors: list[APIErrorDetail] = Field(
        default_factory=list, description="Lista de errores si ocurrieron"
    )
