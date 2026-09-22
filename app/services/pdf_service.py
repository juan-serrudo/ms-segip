"""Servicio de validación y procesamiento de documentos PDF."""

import base64
import binascii
import logging

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import (
    InvalidPdfBase64Exception,
    NotAPdfException,
    PdfTooLargeException,
)
from app.parsers.segip_pdf_parser import SegipPdfParser
from app.schemas.pdf import PdfExtractResponseData

logger = logging.getLogger(__name__)

# Firma mágica obligatoria al inicio de cualquier PDF válido
PDF_MAGIC_BYTES = b"%PDF-"


class PdfService:
    """Orquesta la validación de seguridad y extracción de certificaciones PDF."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.max_size_bytes = settings.pdf_max_size_bytes

    async def process_uploaded_pdf(
        self,
        file: UploadFile,
        extraer_fotografia: bool = False,
    ) -> PdfExtractResponseData:
        """Valida y procesa un archivo PDF recibido mediante multipart/form-data."""
        # 1. Validar nombre de archivo y extensión
        filename = (file.filename or "").lower()
        if not filename.endswith(".pdf"):
            raise NotAPdfException(
                details=f"Extensión no permitida para el archivo '{file.filename}'. Debe ser .pdf"
            )

        # 2. Validar Content-Type declarado
        content_type = (file.content_type or "").lower()
        if content_type not in ("application/pdf", "application/x-pdf", "binary/octet-stream"):
            raise NotAPdfException(
                details=f"Tipo de contenido MIME '{content_type}' no corresponde a un documento PDF"
            )

        # 3. Leer contenido en memoria controlando el tamaño máximo
        content = await file.read(self.max_size_bytes + 1)
        if len(content) > self.max_size_bytes:
            raise PdfTooLargeException(
                details=f"El archivo excede el tamaño máximo permitido de {self.settings.PDF_MAX_SIZE_MB} MB"
            )

        # 4. Validar firma de bytes mágicos (%PDF-)
        self._validate_magic_bytes(content)

        # 5. Ejecutar extracción en memoria
        logger.info(
            "Procesando PDF multipart '%s' (%d bytes, extraer_foto=%s)",
            file.filename,
            len(content),
            extraer_fotografia,
        )
        parser = SegipPdfParser(pdf_bytes=content, extraer_fotografia=extraer_fotografia)
        return parser.parse()

    def process_base64_pdf(
        self,
        base64_str: str,
        extraer_fotografia: bool = False,
    ) -> PdfExtractResponseData:
        """Valida y procesa un archivo PDF codificado en Base64."""
        if not base64_str or not base64_str.strip():
            raise InvalidPdfBase64Exception("La cadena Base64 no puede estar vacía")

        # Limpiar posibles prefijos data URI (ej. data:application/pdf;base64,...)
        clean_base64 = base64_str.strip()
        if "," in clean_base64 and clean_base64.startswith("data:"):
            clean_base64 = clean_base64.split(",", 1)[1].strip()

        try:
            pdf_bytes = base64.b64decode(clean_base64, validate=True)
        except (binascii.Error, ValueError) as err:
            raise InvalidPdfBase64Exception(details=str(err)) from err

        if len(pdf_bytes) > self.max_size_bytes:
            raise PdfTooLargeException(
                details=f"El archivo decodificado excede el tamaño máximo de {self.settings.PDF_MAX_SIZE_MB} MB"
            )

        self._validate_magic_bytes(pdf_bytes)

        logger.info(
            "Procesando PDF Base64 (%d bytes, extraer_foto=%s)",
            len(pdf_bytes),
            extraer_fotografia,
        )
        parser = SegipPdfParser(pdf_bytes=pdf_bytes, extraer_fotografia=extraer_fotografia)
        return parser.parse()

    def _validate_magic_bytes(self, content: bytes) -> None:
        """Verifica que el flujo de bytes comience con la cabecera estándar %PDF-."""
        if len(content) < 5 or not content.startswith(PDF_MAGIC_BYTES):
            raise NotAPdfException(
                details="El encabezado del archivo no contiene la firma binaria de un documento PDF válido (%PDF-)"
            )
