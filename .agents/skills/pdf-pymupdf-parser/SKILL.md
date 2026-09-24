---
name: pdf-pymupdf-parser
description: >-
  Use this skill when implementing, refactoring, debugging, or testing PDF parsing, text layout extraction, and portrait image extraction using PyMuPDF in ms-segip.
---

# PyMuPDF Parser & Image Extraction — ms-segip Runbook

Este manual establece los procedimientos para manipular documentos PDF y extraer información de certificados de identidad emitidos por SEGIP utilizando **PyMuPDF** de manera segura y eficiente en memoria.

---

## 1. Principios de Manipulación de PDFs en Memoria

Para garantizar privacidad y alto rendimiento (cero escritura en disco):

1. **Importación Moderna**: Siempre utilizar `import pymupdf` (evitar el alias deprecado `import fitz`).
2. **Apertura mediante Stream**:
   ```python
   import pymupdf

   doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
   try:
       # Procesar páginas
       page = doc[0]
       text = page.get_text("text")
   finally:
       doc.close()
   ```
3. **Liberación de Recursos**: Siempre cerrar el documento en un bloque `finally:` o utilizando un context manager para evitar fugas de memoria (*memory leaks*) en procesos con alta concurrencia.

---

## 2. Extracción y Normalización de Texto y Apellidos

Los certificados de SEGIP contienen caracteres especiales del español boliviano (como la `ñ` y `Ñ` en apellidos: *Nuñez*, *Peña*, etc.).

* **Preservación de Caracteres**:
  Al normalizar texto para búsquedas (eliminando tildes), proteger explícitamente `ñ` y `Ñ` antes de aplicar descomposición Unicode NFD:
  ```python
  # Utilizar siempre la utilidad app.utils.text.remove_accents
  from app.utils.text import remove_accents

  clean_text = remove_accents(raw_text)  # Preserva Nuñez, no lo convierte en Nunez
  ```
* **Búsqueda por Expresiones Regulares**:
  Usar expresiones regulares insensibles a mayúsculas/minúsculas y tolerantes a espacios múltiples entre etiquetas y valores:
  ```python
  import re

  patron_ci = re.compile(r"N(?:Ú|U)MERO\s+DE\s+DOCUMENTO\s*[:.-]?\s*([0-9]+)", re.IGNORECASE)
  ```

---

## 3. Heurísticas para Extracción de Fotografía Facial

Un PDF de certificado puede contener múltiples imágenes (logos institucionales, marcas de agua, firmas digitales, sellos y la fotografía del ciudadano).

Para aislar con precisión la fotografía facial:

1. **Recuperación de Imágenes**:
   ```python
   image_list = page.get_images(full=True)
   for img_info in image_list:
       xref = img_info[0]
       base_image = doc.extract_image(xref)
       image_bytes = base_image["image"]
       width = base_image["width"]
       height = base_image["height"]
       ext = base_image["ext"]  # jpeg, png, etc.
   ```
2. **Criterios de Filtrado Heurístico**:
   * **Dimensiones mínimas**: Descartar íconos y viñetas (`width >= 60` y `height >= 80`).
   * **Relación de aspecto vertical (Retrato)**: Las fotos de carnet/certificado tienen orientación vertical:
     $$\text{ratio} = \frac{\text{height}}{\text{width}}$$
     Aceptar únicamente si `0.8 <= ratio <= 2.2`.
   * **Tamaño mínimo de bytes**: Permitir imágenes comprimidas con *FlateDecode* (`len(image_bytes) >= 50`).
3. **Conversión a Base64**:
   Codificar la imagen seleccionada utilizando `base64.b64encode(image_bytes).decode("ascii")`.

---

## 4. Pruebas y Fixtures Sintéticos Offline

Nunca utilizar certificados reales de ciudadanos para pruebas automatizadas. Generar PDFs sintéticos en memoria:

```python
import pymupdf


def generar_pdf_prueba() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), "CERTIFICACIÓN DE DATOS DE PERSONA\nNUMERO DE DOCUMENTO: 4892341")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
```

---

## 5. Verificación
* Ejecutar la suite de pruebas del parser:
  ```bash
  pytest tests/unit/test_pdf_parser.py -v
  ```
