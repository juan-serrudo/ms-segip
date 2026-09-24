---
name: qa-testing-toolkit
description: >-
  Use this skill when writing, executing, or debugging automated tests with pytest, measuring code coverage, mocking SOAP/PDF integrations, or enforcing style checks with Ruff in ms-segip.
---

# QA Testing & Linting Toolkit — ms-segip Runbook

Este manual define los estándares para escribir pruebas unitarias e integración en `ms-segip`, garantizando que la suite se mantenga rápida, determinista, 100% offline y con una cobertura de código superior al 85%.

---

## 1. Pruebas Asíncronas de Endpoints con `ASGITransport`

Para probar la API sin levantar un servidor TCP real en la red:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_endpoint_exitoso():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "UP"
    assert "X-Request-ID" in response.headers
    assert "X-Correlation-ID" in response.headers
```

---

## 2. Mockeo de Llamadas SOAP Externas

Todas las pruebas unitarias DEBEN correr sin acceso a la intranet de SEGIP. Utilizar `pytest-mock` para interceptar llamadas al cliente SOAP:

```python
import pytest
from app.schemas.segip import PersonaNormalizada


@pytest.mark.asyncio
async def test_consulta_persona_con_mock(mocker):
    # Mockear el método del cliente SOAP
    mock_soap = mocker.patch(
        "app.integrations.segip.client.SegipSoapClient.consulta_dato_persona_en_json",
        return_value='{"CodigoRespuesta": 1, "NumeroDocumento": "4892341", "Nombres": "JUAN"}',
    )

    # Ejecutar la prueba
    # ...
    assert mock_soap.called
```

---

## 3. Generación de PDFs Sintéticos para Tests

Para probar el parser de PDF sin utilizar documentos con datos personales reales:

```python
import pymupdf


def crear_pdf_certificado_sintetico() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    # Insertar texto estructurado
    page.insert_text(
        (50, 100),
        "CERTIFICACIÓN DE DATOS DE PERSONA\n"
        "NÚMERO DE DOCUMENTO: 1234567\n"
        "NOMBRES: PEDRO\n"
        "PRIMER APELLIDO: PÉREZ\n"
        "SEGUNDO APELLIDO: GÓMEZ\n"
        "FECHA DE NACIMIENTO: 10/08/1985\n",
    )

    # Insertar imagen simulada (rectángulo de color)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 160), 0)
    pix.set_rect(pix.irect, (100, 150, 200))
    img_bytes = pix.tobytes("jpeg")
    page.insert_image(pymupdf.Rect(400, 100, 520, 260), stream=img_bytes)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
```

---

## 4. Ejecución de Pruebas y Reportes

```bash
# Ejecutar todas las pruebas con reporte de cobertura
pytest --cov=app --cov-report=term-missing

# Ejecutar una prueba específica
pytest tests/unit/test_api_endpoints.py::test_personas_consulta_standard -v

# Ejecutar pruebas contra el SOAP real de SEGIP (Solo si se cuenta con VPN/intranet)
RUN_SEGIP_INTEGRATION_TESTS=true pytest tests/integration/test_segip_live.py -v -s
```

---

## 5. Control de Calidad y Formateo con Ruff

Antes de realizar cualquier commit o finalizar una tarea:

```bash
# Verificar errores de estilo y buenas prácticas
ruff check .

# Corregir errores automáticos
ruff check . --fix

# Verificar formateo de código
ruff format --check .

# Aplicar formateo automático
ruff format .
```
