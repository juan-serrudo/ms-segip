"""Generador sintético de documentos PDF en memoria para pruebas unitarias de SEGIP."""

import pymupdf


def create_mock_segip_pdf(
    include_photo: bool = True,
    layout_variant: str = "standard",
) -> bytes:
    """Crea un documento PDF sintético en memoria que emula un certificado SEGIP."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # Formato A4 estándar

    if layout_variant in ("standard", "composite_birth"):
        # 1. Encabezado institucional
        page.insert_text(
            pymupdf.Point(50, 60),
            "ESTADO PLURINACIONAL DE BOLIVIA\n"
            "SERVICIO GENERAL DE IDENTIFICACION PERSONAL\n"
            "SEGIP - CERTIFICACION DE DATOS DE LA PERSONA",
            fontsize=12,
            fontname="helv",
        )

        # 2. Datos del certificado
        page.insert_text(
            pymupdf.Point(50, 120),
            "Número de Emisión: CERT-2026-00452\n"
            "Código SEGIP: SEG-778899\n"
            "Fecha de Emisión: 15/02/2026 10:15:30\n"
            "Motivo de la Consulta: TRAMITE JUDICIAL",
            fontsize=10,
            fontname="helv",
        )

    # 3. Datos de identidad
    if layout_variant == "standard":
        datos_texto = (
            "DATOS DE IDENTIDAD:\n"
            "Cédula de Identidad: 6842190-1B\n"
            "Nombres: ROBERTO CARLOS\n"
            "Primer Apellido: FLORES\n"
            "Segundo Apellido: CONDORI\n"
            "Fecha de Nacimiento: 24/09/1988\n"
            "País de Nacimiento: BOLIVIA\n"
            "Departamento de Nacimiento: COCHABAMBA\n"
            "Provincia de Nacimiento: CERCADO\n"
            "Localidad de Nacimiento: COCHABAMBA\n"
            "Sexo: MASCULINO\n"
            "Estado Civil: CASADO\n"
            "Profesión: ARQUITECTO\n"
            "Domicilio: CALLE LOS PINOS NRO. 450"
        )
    elif layout_variant == "validation_report":
        # Formato de Reporte de Validación SEGIP contemporáneo
        encabezado = (
            "Sistema de Verificación de Identidad Ciudadana\n"
            "Reporte de Validación\n"
            "Sistema: CONVENIO\n"
            "Fecha de impresión: 23-09-2026 2:42:15 PM\n"
            "Institución: FISCALIA GENERAL DEL ESTADO MINISTERIO PUBLICO\n"
            "Nombre de usuario: OPERADOR FISCALIA\n"
            "CI:  1146351\n"
            "Nombre(s): JUAN VICTOR\n"
            "Primer apellido: SERRUDO\n"
            "Segundo apellido: CHAVEZ\n"
            "Fecha de nacimiento: 16/10/1986\n"
            "Procedencia: CONSOLIDADO\n"
            "Tipo de registro: REGISTRO NACIONAL\n"
            "Estado civil: CASADO\n"
            "Domicilio: CLL/INDEPENDENCIA N° 120 ZONA YURAC YURAC-SUCRE\n"
            "Profesión u ocupación: ING. DE SISTEMAS\n"
            "País: BOLIVIA\n"
            "Departamento: CHUQUISACA\n"
            "Provincia: OROPEZA\n"
            "Localidad: SUCRE\n"
            "c4CAXTej-4774047\n"
            "Información de la persona\n"
            "Información complementaria\n"
            "Lugar de nacimiento"
        )
        page.insert_text(pymupdf.Point(50, 100), encabezado, fontsize=9, fontname="helv")
        datos_texto = ""
    elif layout_variant == "convenio_brackets":
        # Formato con delimitadores angulares <...>
        encabezado = (
            "Convenio Inter-Institucional\n"
            "Certificación de datos\n"
            "Sistema: CONVENIO\n"
            "Fecha de impresión: 16-05-2023 10:56:13 AM\n"
            "Institución: FISCALIA GENERAL DEL ESTADO MINISTERIO PUBLICO\n"
            "Nombre de usuario: OPERADOR FISCALIA\n"
            "CI:<7560566-1F>\n"
            "Información del ciudadano nacional\n"
            "Primer apellido:<MENCHACA>\n"
            "Segundo apellido:<ROMERO>\n"
            "Nombre(s):<NOEMI JHUSTIN>\n"
            "Fecha de nacimiento:<29/10/1993>\n"
            "Procedencia: <CONSOLIDADO>\n"
            "Tipo de registro:<REGISTRO NACIONAL>\n"
            "BzxPgh8Y-0347041\n"
            "Información complementaria\n"
            "Domicilio:<CLL/NUEVA ESPERANZA- N°50- Z/ALTO TUCSUPAYA-SUCRE>\n"
            "Profesión u ocupación:<ESTUDIANTE>\n"
            "Estado civil:<SOLTERA>\n"
            "Lugar de nacimiento\n"
            "País:<BOLIVIA>\n"
            "Departamento:<CHUQUISACA>\n"
            "Provincia:<OROPEZA>\n"
            "Localidad:<SUCRE>"
        )
        page.insert_text(pymupdf.Point(50, 100), encabezado, fontsize=9, fontname="helv")
        datos_texto = ""
    else:
        # Variante con lugar de nacimiento compuesto
        datos_texto = (
            "DATOS DE LA PERSONA:\n"
            "Nro. Documento: 7654321\n"
            "Complemento: LP\n"
            "Nombre: MARIA ELENA\n"
            "Primer Apellido: MAMANI\n"
            "Segundo Apellido: GOMEZ\n"
            "Fecha Nacimiento: 1992-11-05\n"
            "Lugar de Nacimiento: BOLIVIA / LA PAZ / MURILLO / LA PAZ\n"
            "Género: FEMENINO\n"
            "Estado Civil: SOLTERA\n"
            "Ocupación: MEDICO CIRUJANO\n"
            "Dirección: AV. AMERICA 890"
        )

    if datos_texto:
        page.insert_text(pymupdf.Point(50, 200), datos_texto, fontsize=10, fontname="helv")

    # 4. Insertar fotografía de retrato si se solicita
    if include_photo:
        # Generar un mapa de bits de 120x160 simulando un retrato
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 160), 0)
        pix.clear_with(200)  # Fondo grisáceo claro
        photo_rect = pymupdf.Rect(420, 180, 540, 340)
        page.insert_image(photo_rect, pixmap=pix)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# Archivos de prueba para validaciones de error
MOCK_CORRUPTED_PDF_BYTES = (
    b"%PDF-1.4\n\x00\xffCorrupted truncated bytes without proper trailer or xref"
)
MOCK_NON_PDF_BYTES = b"<!DOCTYPE html><html><body><h1>No es un PDF</h1></body></html>"
