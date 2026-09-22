"""Punto de entrada principal y configuración de la aplicación FastAPI ms-segip."""

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_request_id, set_request_id, setup_logging
from app.schemas.common import APIErrorDetail, APIResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware que asegura un Request ID (Correlation ID) único para cada petición."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            set_request_id("-")  # Reset


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ciclo de vida de la aplicación: configuración de logs y limpieza de recursos."""
    setup_logging(settings.LOG_LEVEL)
    logger.info(
        "Iniciando %s v%s en entorno [%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    yield
    logger.info("Deteniendo %s...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Microservicio de fachada REST para la integración con los servicios SOAP de SEGIP "
        "y el procesamiento de documentos PDF de certificación de identidad."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Middleware de Correlation ID
app.add_middleware(CorrelationIdMiddleware)

# 2. Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Manejadores Globales de Excepciones Uniformes
# ==============================================================================


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Manejo de excepciones de dominio específicas del microservicio."""
    req_id = get_request_id()
    logger.warning("AppException [%s]: %s (req_id=%s)", exc.error_code, exc.message, req_id)

    payload = APIResponse(
        success=False,
        message=exc.message,
        request_id=req_id,
        errors=[
            APIErrorDetail(
                code=exc.error_code,
                message=exc.message,
                field=str(exc.details) if exc.details else None,
            )
        ],
        data=None,
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Manejo de errores de validación de esquemas Pydantic / FastAPI."""
    req_id = get_request_id()
    errors_list: list[APIErrorDetail] = []

    for err in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors_list.append(
            APIErrorDetail(
                code="VALIDATION_ERROR",
                message=err.get("msg", "Error de validación"),
                field=field_loc,
            )
        )

    payload = APIResponse(
        success=False,
        message="Los parámetros enviados no cumplen con el formato o validación requerida",
        request_id=req_id,
        errors=errors_list,
        data=None,
    )
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Manejo de excepciones HTTP estándar."""
    req_id = get_request_id()
    msg = str(exc.detail) if exc.detail else "Ocurrió un error en la solicitud"

    payload = APIResponse(
        success=False,
        message=msg,
        request_id=req_id,
        errors=[
            APIErrorDetail(
                code=f"HTTP_{exc.status_code}",
                message=msg,
            )
        ],
        data=None,
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Manejo de errores inesperados sin exponer stack traces al consumidor."""
    req_id = get_request_id()
    logger.exception("Error no controlado capturado en handler global: %s", exc)

    payload = APIResponse(
        success=False,
        message="Ocurrió un error interno en el microservicio. Por favor comuníquese con soporte.",
        request_id=req_id,
        errors=[
            APIErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="Error interno del servidor",
            )
        ],
        data=None,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump()
    )


# ==============================================================================
# Registro de Rutas
# ==============================================================================

app.include_router(api_v1_router, prefix="/api/v1")
