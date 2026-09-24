"""Endpoints REST para integración con servicios SOAP de SEGIP según Convenciones UOIT 1.0."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_persona_certificada_service, get_segip_service
from app.core.security import get_auth_dependency
from app.schemas.common import ApiResponse
from app.schemas.persona_certificada import (
    PersonaCertificadaRequest,
    PersonaCertificadaResponseData,
)
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
from app.services.persona_certificada_service import PersonaCertificadaService
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
    response_model=ApiResponse[VersionResponseData],
)
async def get_version(
    segip_service: SegipService = Depends(get_segip_service),
) -> ApiResponse[VersionResponseData]:
    """Retorna la versión del sistema del servicio SOAP SEGIP."""
    data = await segip_service.get_version()
    return ApiResponse[VersionResponseData](
        success=True,
        message="Versión de SEGIP obtenida exitosamente",
        data=data,
    )


@router.post(
    "/personas",
    summary="Consultar Datos de Persona (UOIT)",
    description="Consulta datos personales y fotografía en SEGIP a través de ConsultaDatoPersonaEnJson.",
    response_model=ApiResponse[PersonaNormalizada],
)
@router.post(
    "/personas/consultar",
    summary="Consultar Datos de Persona (Alias)",
    response_model=ApiResponse[PersonaNormalizada],
    include_in_schema=False,
)
async def consultar_persona(
    request: PersonaConsultaRequest,
    segip_service: SegipService = Depends(get_segip_service),
) -> ApiResponse[PersonaNormalizada]:
    """Consulta los datos de una persona en SEGIP y devuelve el esquema normalizado."""
    data = await segip_service.consultar_persona(request)
    return ApiResponse[PersonaNormalizada](
        success=True,
        message="Consulta de persona realizada exitosamente",
        data=data,
    )


@router.post(
    "/certificaciones",
    summary="Obtener Certificación PDF",
    description="Solicita el reporte de certificación oficial de SEGIP en formato PDF Base64.",
    response_model=ApiResponse[CertificacionResponseData],
)
async def solicitar_certificacion(
    request: CertificacionConsultaRequest,
    segip_service: SegipService = Depends(get_segip_service),
) -> ApiResponse[CertificacionResponseData]:
    """Obtiene el documento PDF de certificación de identidad emitido por SEGIP."""
    data = await segip_service.solicitar_certificacion(request)
    return ApiResponse[CertificacionResponseData](
        success=True,
        message="Certificación obtenida exitosamente",
        data=data,
    )


@router.post(
    "/certificaciones/consultar-persona",
    summary="Consultar Persona y Certificación Oficial (Caché Permanente + RustFS)",
    description=(
        "Consulta integral de persona y certificación SEGIP: recupera desde la base de datos local "
        "(para evitar sobrepasar la cuota diaria del servicio) o consulta al servicio SOAP oficial, "
        "almacenando de forma inmutable el PDF y fotografía en RustFS y entregando URLs prefirmadas."
    ),
    response_model=ApiResponse[PersonaCertificadaResponseData],
)
async def consultar_persona_certificada(
    request: PersonaCertificadaRequest,
    persona_certificada_service: PersonaCertificadaService = Depends(
        get_persona_certificada_service
    ),
) -> ApiResponse[PersonaCertificadaResponseData]:
    """Consulta o certifica los datos de una persona con almacenamiento inmutable en RustFS."""
    data = await persona_certificada_service.consultar_o_certificar_persona(request)
    return ApiResponse[PersonaCertificadaResponseData](
        success=True,
        message="Consulta de persona y certificación procesada exitosamente",
        data=data,
    )


@router.post(
    "/certificaciones/qr",
    summary="Verificar Certificación con Código QR (UOIT)",
    description="Valida la autenticidad de una certificación SEGIP mediante el texto leído de su código QR.",
    response_model=ApiResponse[QrVerificacionResponseData],
)
@router.post(
    "/certificaciones/verificar-qr",
    summary="Verificar Certificación con Código QR (Alias)",
    response_model=ApiResponse[QrVerificacionResponseData],
    include_in_schema=False,
)
async def verificar_certificacion_qr(
    request: CertificacionQrRequest,
    segip_service: SegipService = Depends(get_segip_service),
) -> ApiResponse[QrVerificacionResponseData]:
    """Verifica una certificación de identidad a partir de su código QR."""
    data = await segip_service.verificar_qr(request)
    return ApiResponse[QrVerificacionResponseData](
        success=True,
        message="Verificación de código QR ejecutada exitosamente",
        data=data,
    )


@router.post(
    "/contrastaciones",
    summary="Contrastar Datos con SEGIP",
    description="Realiza la contrastación de campos de identidad contra el padrón de SEGIP.",
    response_model=ApiResponse[ContrastacionResponseData],
)
async def contrastar_datos(
    request: ContrastacionRequest,
    segip_service: SegipService = Depends(get_segip_service),
) -> ApiResponse[ContrastacionResponseData]:
    """Contrasta campos de datos personales contra SEGIP."""
    data = await segip_service.contrastar(request)
    return ApiResponse[ContrastacionResponseData](
        success=True,
        message="Contrastación de datos ejecutada exitosamente",
        data=data,
    )
