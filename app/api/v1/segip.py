"""Endpoints REST para integración con servicios SOAP de SEGIP."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_segip_service
from app.core.logging import get_request_id
from app.core.security import get_auth_dependency
from app.schemas.common import APIResponse
from app.schemas.segip import (
    CertificacionConsultaRequest,
    CertificacionQrRequest,
    CertificacionResponseData,
    ContrastacionRequest,
    ContrastacionResponseData,
    PersonaConsultaRequest,
    PersonaNormalizada,
    QrVerificacionResponseData,
    VersionResponseData,
)
from app.services.segip_service import SegipService

router = APIRouter(
    prefix="/segip",
    tags=["Integración SOAP SEGIP"],
    dependencies=[Depends(get_auth_dependency())],
)


@router.get(
    "/version",
    summary="Consultar Versión de SEGIP",
    description="Invoca la operación SOAP ObtieneVersionSistema para comprobar conectividad y versión de SEGIP.",
    response_model=APIResponse[VersionResponseData],
)
async def get_version(
    segip_service: SegipService = Depends(get_segip_service),
) -> APIResponse[VersionResponseData]:
    """Retorna la versión del sistema del servicio SOAP SEGIP."""
    data = await segip_service.get_version()
    return APIResponse(
        success=True,
        message="Versión de SEGIP obtenida exitosamente",
        request_id=get_request_id(),
        data=data,
    )


@router.post(
    "/personas/consultar",
    summary="Consultar Datos de Persona",
    description="Consulta datos personales y fotografía en SEGIP a través de ConsultaDatoPersonaEnJson.",
    response_model=APIResponse[PersonaNormalizada],
)
async def consultar_persona(
    request: PersonaConsultaRequest,
    segip_service: SegipService = Depends(get_segip_service),
) -> APIResponse[PersonaNormalizada]:
    """Consulta los datos de una persona en SEGIP y devuelve el esquema normalizado."""
    data = await segip_service.consultar_persona(request)
    return APIResponse(
        success=True,
        message="Consulta de persona realizada exitosamente",
        request_id=get_request_id(),
        data=data,
    )


@router.post(
    "/certificaciones",
    summary="Obtener Certificación PDF",
    description="Solicita el reporte de certificación oficial de SEGIP en formato PDF Base64.",
    response_model=APIResponse[CertificacionResponseData],
)
async def solicitar_certificacion(
    request: CertificacionConsultaRequest,
    segip_service: SegipService = Depends(get_segip_service),
) -> APIResponse[CertificacionResponseData]:
    """Obtiene el documento PDF de certificación de identidad emitido por SEGIP."""
    data = await segip_service.solicitar_certificacion(request)
    return APIResponse(
        success=True,
        message="Certificación obtenida exitosamente",
        request_id=get_request_id(),
        data=data,
    )


@router.post(
    "/certificaciones/verificar-qr",
    summary="Verificar Certificación con Código QR",
    description="Valida la autenticidad de una certificación SEGIP mediante el texto leído de su código QR.",
    response_model=APIResponse[QrVerificacionResponseData],
)
async def verificar_certificacion_qr(
    request: CertificacionQrRequest,
    segip_service: SegipService = Depends(get_segip_service),
) -> APIResponse[QrVerificacionResponseData]:
    """Verifica una certificación de identidad a partir de su código QR."""
    data = await segip_service.verificar_qr(request)
    return APIResponse(
        success=True,
        message="Verificación de código QR ejecutada",
        request_id=get_request_id(),
        data=data,
    )


@router.post(
    "/contrastaciones",
    summary="Contrastar Datos con SEGIP",
    description="Realiza la contrastación de campos de identidad contra el padrón de SEGIP.",
    response_model=APIResponse[ContrastacionResponseData],
)
async def contrastar_datos(
    request: ContrastacionRequest,
    segip_service: SegipService = Depends(get_segip_service),
) -> APIResponse[ContrastacionResponseData]:
    """Contrasta campos de datos personales contra SEGIP."""
    data = await segip_service.contrastar(request)
    return APIResponse(
        success=True,
        message="Contrastación de datos ejecutada",
        request_id=get_request_id(),
        data=data,
    )
