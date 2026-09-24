---
name: fastapi-uoit-service
description: >-
  Use this skill when creating or refactoring REST endpoints, Pydantic V2 models, dependency injection, and exception handling in ms-segip following UOIT 1.0 conventions.
---

# FastAPI & Pydantic V2 — ms-segip Runbook (UOIT 1.0)

Este manual contiene las recetas y patrones para implementar nuevos endpoints REST, modelos de datos y dependencias en `ms-segip` cumpliendo con los estándares institucionales.

---

## 1. Creación de Modelos con Pydantic V2

Todos los modelos de solicitud (*Request*) y datos de respuesta (*Response Data*) deben heredar de `UoitBaseModel` (`app/schemas/common.py`):

```python
from pydantic import Field
from app.schemas.common import UoitBaseModel


class NuevaSolicitudRequest(UoitBaseModel):
    # En Python se usa snake_case; hacia afuera se serializa automáticamente en camelCase
    numero_documento: str = Field(..., description="Cédula de identidad", min_length=4)
    primer_apellido: str = Field(..., description="Primer apellido del titular")
    extraer_fotografia: bool = Field(
        default=False, description="Indica si debe extraerse la fotografía"
    )
```

### Reglas Clave:
* **Heredar de `UoitBaseModel`**: Aplica `alias_generator=to_camel` y `populate_by_name=True`.
* **Prohibido renombrar manualmente campos a `camelCase` en Python**: Escribe `numero_documento`, no `numeroDocumento`. Pydantic se encarga de la traducción bidireccional.

---

## 2. Estructura de Endpoints con `ApiResponse[T]`

Cada endpoint debe retornar el sobre genérico `ApiResponse[T]`:

```python
from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_segip_service
from app.schemas.common import ApiResponse
from app.services.segip_service import SegipService

router = APIRouter(prefix="/recurso", tags=["Recursos"])


@router.post(
    "",
    response_model=ApiResponse[MiModeloRespuestaData],
    status_code=status.HTTP_200_OK,
    summary="Descripción concisa de la operación",
)
async def operacion_endpoint(
    request: NuevaSolicitudRequest,
    service: SegipService = Depends(get_segip_service),
) -> ApiResponse[MiModeloRespuestaData]:
    # Delegar la lógica al servicio de aplicación
    resultado = await service.ejecutar_operacion(request)

    return ApiResponse[MiModeloRespuestaData](
        success=True,
        message="Operación ejecutada exitosamente",
        data=resultado,
    )
```

---

## 3. Inyección de Dependencias

* Las dependencias deben registrarse en `app/api/dependencies.py`.
* Desacoplar la creación de clientes y servicios:
  - `get_settings()` provee la configuración inyectable.
  - `get_segip_client()` provee el cliente HTTP/SOAP singleton o por ciclo de vida.
  - `get_segip_service()` inyecta el cliente y la configuración al servicio.

---

## 4. Manejo de Errores y Excepciones

* **No retornar diccionarios con códigos de error manuales** en los controladores.
* Lanzar excepciones de dominio (`app/core/exceptions.py`), por ejemplo:
  ```python
  raise SegipNoResultsException(details="No se encontró registro para la cédula consultada")
  ```
* El middleware global de excepciones en `app/main.py` captura automáticamente cualquier `AppException` y genera la respuesta estandarizada UOIT:
  ```json
  {
    "success": false,
    "message": "Mensaje de error institucional",
    "data": null,
    "meta": null,
    "error": {
      "code": "SEGIP_NO_RESULTS",
      "details": "Detalles adicionales"
    }
  }
  ```

---

## 5. Verificación de Endpoints
Para verificar que los endpoints respetan el esquema UOIT:
```bash
pytest tests/unit/test_api_endpoints.py -v
```
