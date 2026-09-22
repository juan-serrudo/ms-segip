"""Esquemas y parámetros estándar de paginación según Convenciones UOIT (Sección 7, 14 y 22)."""

from typing import Literal

from fastapi import Query
from pydantic import Field

from app.schemas.common import UoitBaseModel


class PaginationParams(UoitBaseModel):
    """Parámetros de paginación institucional UOIT (Sección 7 y 22)."""

    page: int = Query(default=1, ge=1, description="Número de página (inicia en 1)")
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        alias="pageSize",
        description="Cantidad de elementos por página (por defecto 20, máximo 100)",
    )
    sort: str | None = Query(default=None, description="Campo por el cual ordenar")
    order: Literal["asc", "desc"] = Query(
        default="asc", description="Sentido del ordenamiento ('asc' o 'desc')"
    )


class PaginationMeta(UoitBaseModel):
    """Estructura estándar de metadatos de paginación para el campo 'meta' (UOIT Sección 14)."""

    page: int = Field(description="Página actual")
    page_size: int = Field(description="Elementos por página")
    total_items: int = Field(description="Total de elementos existentes")
    total_pages: int = Field(description="Total de páginas calculadas")
