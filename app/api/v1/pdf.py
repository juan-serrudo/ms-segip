"""Endpoints REST para recepción y extracción de datos en documentos PDF."""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies import get_pdf_service
from app.core.logging import get_request_id
from app.core.security import get_auth_dependency
from app.schemas.common import APIResponse
from app.schemas.pdf import PdfExtractBase64Request, PdfExtractResponseData
from app.services.pdf_service import PdfService

router = APIRouter(
    prefix="/pdfs",
    tags=["Procesamiento de Documentos PDF"],
    dependencies=[Depends(get_auth_dependency())],
)


@router.post(
    "/extraer",
    summary="Extraer Datos de PDF (Multipart)",
    description=(
        "Recibe un archivo PDF de certificación mediante multipart/form-data, "
        "valida su autenticidad y tamaño, y extrae los datos personales y opcionalmente la fotografía."
    ),
    response_model=APIResponse[PdfExtractResponseData],
)
async def extraer_datos_pdf(
    file: UploadFile = File(..., description="Archivo PDF de certificación SEGIP"),
    extraer_fotografia: bool = Form(
        default=False,
        description="Indica si debe extraerse la fotografía embebida en formato Base64",
    ),
    pdf_service: PdfService = Depends(get_pdf_service),
) -> APIResponse[PdfExtractResponseData]:
    """Procesa el archivo PDF subido en memoria y devuelve los campos normalizados."""
    data = await pdf_service.process_uploaded_pdf(
        file=file,
        extraer_fotografia=extraer_fotografia,
    )
    return APIResponse(
        success=True,
        message="Datos extraídos del PDF exitosamente",
        request_id=get_request_id(),
        data=data,
    )


@router.post(
    "/extraer-base64",
    summary="Extraer Datos de PDF (Base64)",
    description=(
        "Alternativa al envío multipart: recibe el documento PDF codificado en Base64 en una carga JSON, "
        "valida su contenido y extrae los datos normalizados."
    ),
    response_model=APIResponse[PdfExtractResponseData],
)
async def extraer_datos_pdf_base64(
    request: PdfExtractBase64Request,
    pdf_service: PdfService = Depends(get_pdf_service),
) -> APIResponse[PdfExtractResponseData]:
    """Procesa una cadena PDF en Base64 y extrae los datos de la certificación."""
    data = pdf_service.process_base64_pdf(
        base64_str=request.pdf_base64,
        extraer_fotografia=request.extraer_fotografia,
    )
    return APIResponse(
        success=True,
        message="Datos extraídos del PDF Base64 exitosamente",
        request_id=get_request_id(),
        data=data,
    )
