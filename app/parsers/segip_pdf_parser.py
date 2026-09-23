"""Parser especializado para extracción y normalización de datos en certificaciones PDF de SEGIP."""

import base64
import logging
import re
from typing import Any

import pymupdf

from app.core.exceptions import (
    PdfCorruptedException,
    PhotoExtractionException,
    UnrecognizedSegipPdfException,
)
from app.schemas.pdf import DatosCertificadoPdf, PdfExtractResponseData
from app.schemas.segip import DatosNacimiento, DatosPersona
from app.utils.text import (
    clean_string,
    normalize_date,
    normalize_gender,
    normalize_marital_status,
    remove_accents,
)

logger = logging.getLogger(__name__)

# Palabras clave indispensables para considerar el PDF un certificado de SEGIP
_SEGIP_KEYWORDS = [
    "SEGIP",
    "SERVICIO GENERAL DE IDENTIFICACION PERSONAL",
    "SISTEMA DE VERIFICACION DE IDENTIDAD CIUDADANA",
    "REPORTE DE VALIDACION",
    "CONVENIO INTER-INSTITUCIONAL",
    "CERTIFICACION DE DATOS",
    "CERTIFICADO DE DATOS",
    "INFORMACION DE LA PERSONA",
    "INFORMACION DEL CIUDADANO NACIONAL",
    "INFORMACION DEL CIUDADANO EXTRANJERO",
    "INFORMACION COMPLEMENTARIA",
    "LUGAR DE NACIMIENTO",
    "DATOS DE LA PERSONA",
    "DATOS DE IDENTIDAD",
]


class SegipPdfParser:
    """Motor de análisis y extracción de texto e imágenes para certificaciones PDF de SEGIP."""

    def __init__(self, pdf_bytes: bytes, extraer_fotografia: bool = False) -> None:
        self.pdf_bytes = pdf_bytes
        self.extraer_fotografia = extraer_fotografia
        self._doc: pymupdf.Document | None = None

    def parse(self) -> PdfExtractResponseData:
        """Abre el documento en memoria, valida la estructura y extrae los datos."""
        try:
            self._doc = pymupdf.open(stream=self.pdf_bytes, filetype="pdf")
        except Exception as err:
            logger.error("No se pudo abrir el archivo PDF: %s", err)
            raise PdfCorruptedException(details=str(err)) from err

        try:
            total_pages = len(self._doc)
            if total_pages == 0:
                raise PdfCorruptedException("El documento PDF no contiene páginas")

            # Concatenar texto de las páginas
            full_text = ""
            for page in self._doc:
                full_text += page.get_text("text") + "\n"

            # Validar que corresponde a un certificado SEGIP
            text_normalized_no_accents = remove_accents(full_text).upper()
            is_segip = any(kw in text_normalized_no_accents for kw in _SEGIP_KEYWORDS)
            if not is_segip:
                raise UnrecognizedSegipPdfException(
                    details="El documento no contiene las marcas institucionales reconocidas de SEGIP"
                )

            # Extraer campos
            persona = self._extract_persona(full_text)
            nacimiento = self._extract_nacimiento(full_text)
            certificado = self._extract_certificado(full_text, total_pages)

            # Extraer fotografía si fue solicitada
            if self.extraer_fotografia:
                persona.fotografia_base64 = self._extract_photo()

            return PdfExtractResponseData(
                persona=persona,
                nacimiento=nacimiento,
                certificado=certificado,
            )

        finally:
            if self._doc:
                self._doc.close()

    def _extract_persona(self, text: str) -> DatosPersona:
        """Extrae los campos de identidad personal desde el texto del PDF."""
        # 1. Cédula de Identidad y Complemento
        # Formatos usuales:
        # Cédula de Identidad: 1234567 LP
        # Cédula de Identidad: 1234567-1B
        # CI:<7560566-1F>
        # CI:  1146351
        ci_pattern = re.compile(
            r"(?:C[eé]dula(?:\s+de\s+Identidad)?|Nro\.?\s*Documento|N[uú]mero\s*de\s*Documento|C\.?I\.?)\s*[:.]?\s*<?\s*(\d{4,10})(?:[- ]([A-Za-z0-9]{1,3}))?>?",
            re.IGNORECASE,
        )
        ci_match = ci_pattern.search(text)
        numero_documento = ci_match.group(1).strip() if ci_match else None
        complemento = ci_match.group(2).strip() if (ci_match and ci_match.group(2)) else None

        # Si el complemento tiene su propia etiqueta
        comp_match = re.search(r"Complemento\s*[:.]?\s*<?([A-Za-z0-9]{1,3})>?", text, re.IGNORECASE)
        if comp_match and not complemento:
            complemento = comp_match.group(1).strip()

        # 2. Nombres (evitar coincidir con 'Nombre de usuario' o 'Nombre de usuario final')
        nombres = self._extract_regex(
            text,
            r"(?:Nombre\(s\)|Nombres?|Nombre(?!\s+de\s+usuario)(?:\s+Completo)?)\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)>?(?=\n\s*(?:Primer\s+Apellido|Apellido|Paterno|Fecha|$))",
        )

        # 3. Primer Apellido
        primer_apellido = self._extract_regex(
            text,
            r"(?:Primer\s+Apellido|Apellido\s+Paterno|Paterno)\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)>?(?=\n\s*(?:Segundo\s+Apellido|Materno|Fecha|$))",
        )

        # 4. Segundo Apellido
        segundo_apellido = self._extract_regex(
            text,
            r"(?:Segundo\s+Apellido|Apellido\s+Materno|Materno)\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s-]+?)>?(?=\n\s*(?:Apellido|Nombre|Fecha|Sexo|Procedencia|$))",
        )

        # 5. Fecha de Nacimiento (tolera saltos de línea intermedios como 'Fecha de\nnacimiento:')
        raw_fecha_nac = self._extract_regex(
            text,
            r"Fecha\s+(?:de\s+)?nacimiento\s*[:.]?\s*\n*\s*<?([0-9]{2}[/-][0-9]{2}[/-][0-9]{4}|[0-9]{4}[/-][0-9]{2}[/-][0-9]{2})>?",
        )
        fecha_nacimiento = normalize_date(raw_fecha_nac) if raw_fecha_nac else None

        # 6. Estado Civil
        raw_estado = self._extract_regex(
            text,
            r"Estado\s+Civil\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)>?(?=\n|Profesi[oó]n|Domicilio|$)",
        )
        estado_civil = normalize_marital_status(raw_estado)

        # 7. Sexo / Género (explícito o inferido por desinencia gramatical de estado civil)
        raw_sexo = self._extract_regex(
            text,
            r"(?:Sexo|G[eé]nero)\s*[:.]?\s*<?([A-Za-z]+)>?",
        )
        sexo = normalize_gender(raw_sexo)
        if not sexo and estado_civil:
            norm_est = remove_accents(estado_civil).upper()
            if norm_est.endswith("A"):
                sexo = "FEMENINO"
            elif norm_est.endswith("O"):
                sexo = "MASCULINO"

        # 8. Profesión u Ocupación
        profesion = self._extract_regex(
            text,
            r"(?:Profesi[oó]n(?:\s*[/yu]\s*Ocupaci[oó]n)?|Ocupaci[oó]n)\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s\d,.-]+?)>?(?=\n|Domicilio|Direcci[oó]n|Pa[ií]s|Estado|$)",
        )

        # 9. Domicilio (soporta delimitadores angulares y domicilios en varias líneas)
        dom_bracket = re.search(r"(?:Domicilio|Direcci[oó]n)\s*[:.]?\s*<([^>]+)>", text, re.IGNORECASE)
        if dom_bracket:
            domicilio = dom_bracket.group(1).strip()
        else:
            dom_match = re.search(
                r"(?:Domicilio|Direcci[oó]n)\s*[:.]?\s*\n*\s*([\s\S]+?)(?=\n\s*(?:Profesi[oó]n|Ocupaci[oó]n|Pa[ií]s|Lugar|Estado|$))",
                text,
                re.IGNORECASE,
            )
            if dom_match:
                domicilio = " ".join(dom_match.group(1).split())
            else:
                domicilio = self._extract_regex(
                    text,
                    r"(?:Domicilio|Direcci[oó]n)\s*[:.]?\s*([^\n\r]+)",
                )

        return DatosPersona(
            numero_documento=clean_string(numero_documento),
            complemento=clean_string(complemento),
            nombres=clean_string(nombres),
            primer_apellido=clean_string(primer_apellido),
            segundo_apellido=clean_string(segundo_apellido),
            fecha_nacimiento=fecha_nacimiento,
            sexo=sexo,
            estado_civil=estado_civil,
            domicilio=clean_string(domicilio),
            profesion_ocupacion=clean_string(profesion),
            fotografia_base64=None,
        )

    def _extract_nacimiento(self, text: str) -> DatosNacimiento:
        """Extrae datos de lugar de nacimiento desde el texto del PDF."""
        # Puede figurar como etiquetas separadas o una sola línea:
        # Lugar de Nacimiento: BOLIVIA / LA PAZ / MURILLO / NUESTRA SEÑORA DE LA PAZ
        # o País: BOLIVIA, Departamento: LA PAZ...
        pais = self._extract_regex(
            text,
            r"Pa[ií]s(?:\s+de\s+Nacimiento)?\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)>?(?=\n|Depto|Departamento|Provincia|Localidad|$)",
        )
        departamento = self._extract_regex(
            text,
            r"(?:Departamento|Depto\.?)(?:\s+de\s+Nacimiento)?\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s-]+?)>?(?=\n|Provincia|Localidad|$)",
        )
        provincia = self._extract_regex(
            text,
            r"Provincia(?:\s+de\s+Nacimiento)?\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s-]+?)>?(?=\n|Localidad|Secci[oó]n|$)",
        )
        localidad = self._extract_regex(
            text,
            r"Localidad(?:\s+de\s+Nacimiento)?\s*[:.]?\s*<?([A-Za-zÁÉÍÓÚáéíóúÑñ\s-]+?)>?(?=\n|Fecha|Estado|$)",
        )

        # Alternativa de línea compuesta "Lugar de Nacimiento: BOLIVIA, LA PAZ, MURILLO, LA PAZ"
        if not pais and not departamento:
            compuesto = self._extract_regex(
                text, r"Lugar(?:\s+de)?\s+Nacimiento\s*[:.]?\s*([^\n\r]+)"
            )
            if compuesto:
                partes = [p.strip() for p in re.split(r"[/,-]", compuesto) if p.strip()]
                if len(partes) >= 1:
                    pais = partes[0]
                if len(partes) >= 2:
                    departamento = partes[1]
                if len(partes) >= 3:
                    provincia = partes[2]
                if len(partes) >= 4:
                    localidad = partes[3]

        return DatosNacimiento(
            pais=clean_string(pais),
            departamento=clean_string(departamento),
            provincia=clean_string(provincia),
            localidad=clean_string(localidad),
        )

    def _extract_certificado(self, text: str, total_pages: int) -> DatosCertificadoPdf:
        """Extrae metadatos institucionales del certificado PDF."""
        nro_emision = self._extract_regex(
            text,
            r"(?:N[uú]mero\s+de\s+Emisi[oó]n|Nro\.?\s*Certificaci[oó]n|Nro\.?\s*Certificado|Certificado\s*N[°ºo]?)\s*[:.]?\s*([A-Za-z0-9\-]+)",
        )
        codigo_segip = self._extract_regex(
            text,
            r"(?:C[oó]digo\s+(?:SEGIP|de\s+Control|Verificaci[oó]n|Único))\s*[:.]?\s*([A-Za-z0-9\-]+)",
        )
        # Si no hay código por etiqueta, buscar el identificador QR de seguimiento alfanumérico con guión (ej. c4CAXTej-4774047)
        if not codigo_segip:
            qr_match = re.search(r"\b([A-Za-z0-9]{5,15}-[0-9]{4,12})\b", text)
            if qr_match:
                codigo_segip = qr_match.group(1).strip()
                if not nro_emision:
                    nro_emision = codigo_segip

        fecha_emision = self._extract_regex(
            text,
            r"(?:Fecha(?:\s+y\s+Hora)?\s+de\s+(?:Emisi[oó]n|Impresi[oó]n)|Emitido\s+el)\s*[:.]?\s*([0-9]{2}[/-][0-9]{2}[/-][0-9]{4}(?:\s+[0-9]{1,2}:[0-9]{2}:[0-9]{2}(?:\s*[APap][Mm])?)?)",
        )
        motivo = self._extract_regex(
            text,
            r"(?:Motivo(?:\s+de\s+la\s+Consulta)?|Solicitante)\s*[:.]?\s*([^\n\r]+)",
        )
        if not motivo:
            inst_match = re.search(
                r"(?:^|\n)\s*Instituci[oó]n\s*[:.]?\s*([^\n\r]+)", text, re.IGNORECASE
            )
            institucion = inst_match.group(1).strip() if inst_match else None
            sist_match = re.search(
                r"^\s*Sistema\s*:\s*([^\n\r]+)", text, re.IGNORECASE | re.MULTILINE
            )
            sistema = sist_match.group(1).strip() if sist_match else None
            if institucion and sistema:
                motivo = f"{sistema} - {institucion}"
            elif institucion:
                motivo = institucion
            elif sistema:
                motivo = sistema

        return DatosCertificadoPdf(
            numero_emision=clean_string(nro_emision),
            codigo_segip=clean_string(codigo_segip),
            fecha_emision=clean_string(fecha_emision),
            motivo_consulta=clean_string(motivo),
            paginas=total_pages,
        )

    def _extract_photo(self) -> str | None:
        """Busca y extrae la imagen de fotografía de la persona en el documento."""
        if not self._doc:
            return None

        try:
            candidate_images: list[dict[str, Any]] = []

            for page_index in range(len(self._doc)):
                page = self._doc[page_index]
                image_list = page.get_images(full=True)

                for img_info in image_list:
                    xref = img_info[0]
                    base_image = self._doc.extract_image(xref)
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    image_bytes = base_image.get("image", b"")

                    # Filtrar íconos pequeños, sellos de agua o barras horizontales de encabezado
                    # Una fotografía de carnet estándar tiene ancho >= 60, alto >= 80 y relación de aspecto vertical/retrato
                    if width >= 60 and height >= 80 and len(image_bytes) > 50:
                        aspect_ratio = height / width
                        # Rango de aspecto para retratos en certificados oficiales (0.6 a 2.5)
                        if 0.6 <= aspect_ratio <= 2.5:
                            candidate_images.append(
                                {
                                    "width": width,
                                    "height": height,
                                    "bytes": image_bytes,
                                    "size": len(image_bytes),
                                }
                            )

            if not candidate_images:
                logger.info(
                    "No se encontró una fotografía que cumpla las dimensiones de retrato en el PDF"
                )
                return None

            # Seleccionar la imagen más grande que encaja con una fotografía
            candidate_images.sort(key=lambda x: x["size"], reverse=True)
            chosen_photo = candidate_images[0]["bytes"]

            return base64.b64encode(chosen_photo).decode("ascii")

        except Exception as err:
            logger.warning("Fallo al extraer fotografía del PDF: %s", err)
            raise PhotoExtractionException(details=str(err)) from err

    def _extract_regex(self, text: str, pattern: str) -> str | None:
        """Busca un patrón regex y retorna el primer grupo limpio."""
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            return match.group(1).strip()
        return None
