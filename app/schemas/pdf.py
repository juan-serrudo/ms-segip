"""Esquemas de solicitud y respuesta para el procesamiento de documentos PDF."""

from pydantic import BaseModel, Field

from app.schemas.segip import DatosNacimiento, DatosPersona


class DatosCertificadoPdf(BaseModel):
    """Metadatos específicos extraídos del documento de certificación PDF."""

    numero_emision: str | None = Field(
        default=None, description="Número de emisión o certificación del PDF"
    )
    codigo_segip: str | None = Field(default=None, description="Código único de seguimiento SEGIP")
    fecha_emision: str | None = Field(
        default=None, description="Fecha y hora de emisión del certificado"
    )
    motivo_consulta: str | None = Field(
        default=None, description="Motivo de la emisión o usuario solicitante"
    )
    paginas: int = Field(default=1, description="Número total de páginas analizadas")


class PdfExtractBase64Request(BaseModel):
    """Solicitud de extracción de datos enviando el PDF codificado en Base64."""

    pdf_base64: str = Field(
        ..., description="Contenido completo del archivo PDF codificado en Base64"
    )
    extraer_fotografia: bool = Field(
        default=False,
        description="Indica si debe extraerse la fotografía embebida en el certificado",
    )


class PdfExtractResponseData(BaseModel):
    """Datos consolidados y normalizados extraídos del documento PDF de SEGIP."""

    persona: DatosPersona = Field(default_factory=DatosPersona)
    nacimiento: DatosNacimiento = Field(default_factory=DatosNacimiento)
    certificado: DatosCertificadoPdf = Field(default_factory=DatosCertificadoPdf)
