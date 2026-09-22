"""Endpoints de verificación de estado y preparación (liveness & readiness probes) según Convenciones UOIT."""

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_segip_service, get_settings
from app.core.config import Settings
from app.schemas.common import ApiResponse
from app.services.segip_service import SegipService

router = APIRouter(tags=["Salud y Monitoreo"])


@router.get(
    "/health",
    summary="Liveness Probe Informativa",
    description="Comprueba que la aplicación esté levantada y respondiendo peticiones HTTP (UOIT Sección 13 y 29).",
    response_model=ApiResponse[dict[str, Any]],
)
async def health_check(
    settings: Settings = Depends(get_settings),
) -> ApiResponse[dict[str, Any]]:
    """Comprobación básica de vida del microservicio."""
    return ApiResponse[dict[str, Any]](
        success=True,
        message="Microservicio operativo",
        data={
            "status": "healthy",
            "appName": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
    )


@router.get(
    "/ready",
    summary="Readiness Probe Informativa",
    description="Informa separadamente el estado de preparación de la aplicación y la conectividad con SEGIP.",
    response_model=ApiResponse[dict[str, Any]],
)
async def readiness_check(
    response: Response,
    segip_service: SegipService = Depends(get_segip_service),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[dict[str, Any]]:
    """Comprobación de preparación con diagnóstico del servicio externo SEGIP."""
    segip_ok, segip_msg = await segip_service.check_readiness()

    overall_ready = segip_ok
    status_code = status.HTTP_200_OK if overall_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    response.status_code = status_code

    return ApiResponse[dict[str, Any]](
        success=overall_ready,
        message="Comprobación de preparación completada",
        data={
            "status": "ready" if overall_ready else "degraded",
            "components": {
                "application": {
                    "status": "up",
                    "version": settings.APP_VERSION,
                },
                "segipSoap": {
                    "status": "up" if segip_ok else "down",
                    "url": settings.SEGIP_SERVICE_URL,
                    "details": segip_msg,
                },
            },
        },
    )
