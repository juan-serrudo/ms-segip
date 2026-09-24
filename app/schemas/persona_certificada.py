"""Esquemas Pydantic V2 para el servicio unificado de consulta y certificación de persona (UOIT 1.0)."""

from datetime import datetime

from pydantic import Field

from app.schemas.common import UoitBaseModel
from app.schemas.pdf import DatosCertificadoPdf
from app.schemas.segip import DatosNacimiento, DatosPersona


class PersonaCertificadaRequest(UoitBaseModel):
    """Solicitud unificada para consultar o certificar a una persona."""

    # Identificación básica (Cédula obligatoria)
    numero_documento: str = Field(
        ...,
        description="Número de Cédula de Identidad (obligatorio)",
        min_length=4,
        max_length=20,
    )
    complemento: str | None = Field(
        default="",
        description="Complemento de cédula si existe (ej. '1B'). Requerido si existen homónimos",
    )
    fecha_nacimiento: str | None = Field(
        default="",
        description="Fecha de nacimiento (DD/MM/YYYY o YYYY-MM-DD). Permite desambiguar duplicados",
    )

    # Control de caché permanente y cuota diaria
    forzar_actualizacion: bool = Field(
        default=False,
        description="Fuerza la consulta al servicio SOAP de SEGIP actualizando la BD e imágenes",
    )

    # Configuración de URLs prefirmadas en RustFS
    generar_url_pdf: bool = Field(
        default=True,
        description="Indica si debe generarse la URL prefirmada del certificado PDF",
    )
    generar_url_imagen: bool = Field(
        default=True,
        description="Indica si debe generarse la URL prefirmada de la fotografía",
    )
    tiempo_expiracion_url_segundos: int = Field(
        default=300,
        ge=60,
        le=86400,
        description="Tiempo de vigencia de las URLs prefirmadas en segundos (por defecto 300 = 5 minutos)",
    )

    # Datos adicionales opcionales para la llamada SOAP externa
    nombre: str | None = Field(default="", description="Nombres del titular")
    primer_apellido: str | None = Field(default="", description="Primer apellido")
    segundo_apellido: str | None = Field(default="", description="Segundo apellido")
    numero_autorizacion: str | None = Field(
        default="", description="Número de autorización institucional"
    )
    clave_acceso_usuario_final: str | None = Field(
        default="", description="Operador final solicitante"
    )


class ArchivosCertificacion(UoitBaseModel):
    """URLs prefirmadas temporales de acceso a los artefactos resguardados en RustFS/S3."""

    url_presignada_pdf: str | None = Field(
        default=None, description="URL prefirmada temporal para descargar el PDF oficial"
    )
    url_presignada_imagen: str | None = Field(
        default=None, description="URL prefirmada temporal para visualizar la fotografía"
    )
    vigencia_segundos: int = Field(
        default=300, description="Segundos de validez de las URLs generadas"
    )
    fecha_expiracion: datetime | None = Field(
        default=None, description="Marca de tiempo UTC en que expiran los enlaces"
    )


class MetadatosConsultaPersona(UoitBaseModel):
    """Metadatos de auditoría, trazabilidad y control de cuota."""

    origen_datos: str = Field(
        description="Procedencia de los datos: 'CACHE_BD', 'SEGIP_SOAP', o 'CACHE_BD_DEGRADADO'"
    )
    es_refrescado: bool = Field(
        default=False,
        description="Indica si los datos fueron obtenidos en esta llamada desde SEGIP",
    )
    aviso: str | None = Field(
        default=None,
        description="Mensaje informativo si operó el fallback por degradación grácil ante fallo de SEGIP",
    )
    fecha_ultima_consulta_segip: datetime | None = Field(
        default=None, description="Fecha y hora del último documento emitido por SEGIP"
    )
    total_certificaciones_registradas: int = Field(
        default=1, description="Cantidad histórica de certificaciones resguardadas para la persona"
    )


class PersonaCertificadaResponseData(UoitBaseModel):
    """Estructura consolidada de respuesta para la persona certificada."""

    persona: DatosPersona = Field(description="Datos personales normalizados vigentes")
    nacimiento: DatosNacimiento = Field(description="Información del lugar de nacimiento")
    certificado: DatosCertificadoPdf = Field(
        description="Metadatos técnicos y de emisión del certificado oficial"
    )
    archivos: ArchivosCertificacion = Field(
        description="URLs prefirmadas temporales para consumo directo en RustFS"
    )
    metadatos: MetadatosConsultaPersona = Field(
        description="Metadatos de procedencia, cuota y trazabilidad"
    )
