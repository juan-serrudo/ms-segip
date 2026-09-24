"""Punto de entrada principal y configuración de FastAPI según Convenciones UOIT 1.0."""

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.dependencies import get_segip_service
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.database import close_database_engine
from app.core.exceptions import AppException
from app.core.logging import (
    get_correlation_id,
    get_request_id,
    set_correlation_id,
    set_request_id,
    setup_logging,
)
from app.schemas.common import ApiError, ApiResponse
from app.services.segip_service import SegipService

logger = logging.getLogger(__name__)
settings = get_settings()


class TraceabilityMiddleware(BaseHTTPMiddleware):
    """Middleware de trazabilidad distribuida según Convenciones UOIT (Sección 12 y 17)."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        corr_id = request.headers.get("X-Correlation-ID") or req_id

        set_request_id(req_id)
        set_correlation_id(corr_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            set_request_id("-")
            set_correlation_id("-")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ciclo de vida de la aplicación: configuración de logs estructurados y recursos."""
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        service_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
    )
    logger.info(
        "Iniciando %s v%s en entorno [%s] con formato de log [%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
        settings.LOG_FORMAT,
    )
    # Inicializar bucket de almacenamiento en RustFS
    try:
        from app.services.storage_service import StorageService

        storage = StorageService(settings=settings)
        await storage.asegurar_bucket_existe()
    except Exception as err:
        logger.warning(
            "No se pudo verificar o crear el bucket en RustFS durante el arranque: %s", err
        )

    yield
    logger.info("Deteniendo %s...", settings.APP_NAME)
    await close_database_engine()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Microservicio de fachada REST para la integración con los servicios SOAP de SEGIP "
        "y el procesamiento de documentos PDF de certificación de identidad (Norma UOIT 1.0)."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Middleware de Trazabilidad (X-Request-ID y X-Correlation-ID)
app.add_middleware(TraceabilityMiddleware)

# 2. Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Endpoints de Salud Kubernetes UOIT (Sección 29)
# ==============================================================================


@app.get(
    "/health/live",
    tags=["Kubernetes Probes"],
    summary="Liveness Probe Kubernetes",
    description="Determina si el proceso se encuentra activo (UOIT Sección 29).",
)
async def k8s_liveness() -> dict[str, str]:
    """Liveness probe conforme a la convención UOIT Sección 29."""
    return {"status": "UP"}


@app.get(
    "/health/ready",
    tags=["Kubernetes Probes"],
    summary="Readiness Probe Kubernetes",
    description="Determina si el servicio está preparado para recibir tráfico verificando SEGIP (UOIT Sección 29).",
)
async def k8s_readiness(
    response: Response,
    segip_service: SegipService = Depends(get_segip_service),
) -> dict[str, str]:
    """Readiness probe conforme a la convención UOIT Sección 29."""
    segip_ok, _ = await segip_service.check_readiness()
    if not segip_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "DOWN"}
    return {"status": "UP"}


# ==============================================================================
# Manejadores Globales de Excepciones Uniformes (UOIT Sección 15, 23 y 24)
# ==============================================================================


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Manejo de excepciones de dominio según UOIT Sección 15 y 24."""
    req_id = get_request_id()
    corr_id = get_correlation_id()
    logger.warning(
        "AppException [%s]: %s (req_id=%s, corr_id=%s)",
        exc.error_code,
        exc.message,
        req_id,
        corr_id,
    )

    payload = ApiResponse[None](
        success=False,
        message=exc.message,
        data=None,
        meta=None,
        error=ApiError(
            code=exc.error_code,
            details=exc.details or exc.message,
            trace_id=req_id,
        ),
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump(by_alias=True))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Manejo de errores de validación de esquemas (UOIT Sección 15.2)."""
    req_id = get_request_id()
    errors_list: list[dict[str, str]] = []

    for err in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors_list.append(
            {
                "field": field_loc,
                "message": err.get("msg", "Error de validación"),
            }
        )

    payload = ApiResponse[None](
        success=False,
        message="Existen errores de validación",
        data=None,
        meta=None,
        error=ApiError(
            code="VALIDATION_ERROR",
            details=errors_list,
            trace_id=req_id,
        ),
    )
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    return JSONResponse(status_code=status_code, content=payload.model_dump(by_alias=True))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Manejo de excepciones HTTP estándar según UOIT Sección 15."""
    req_id = get_request_id()
    msg = str(exc.detail) if exc.detail else "Ocurrió un error en la solicitud"

    payload = ApiResponse[None](
        success=False,
        message=msg,
        data=None,
        meta=None,
        error=ApiError(
            code=f"HTTP_{exc.status_code}",
            details=msg,
            trace_id=req_id,
        ),
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump(by_alias=True))


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Manejo de errores no controlados sin exponer stack traces al consumidor (UOIT Sección 3.7 y 15)."""
    req_id = get_request_id()
    logger.exception("Error no controlado capturado en handler global: %s", exc)

    payload = ApiResponse[None](
        success=False,
        message="Ocurrió un error interno en el microservicio. Por favor comuníquese con soporte.",
        data=None,
        meta=None,
        error=ApiError(
            code="INTERNAL_ERROR",
            details="Error interno del servidor",
            trace_id=req_id,
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload.model_dump(by_alias=True),
    )


# ==============================================================================
# Registro de Rutas
# ==============================================================================

app.include_router(api_v1_router, prefix="/api/v1")
