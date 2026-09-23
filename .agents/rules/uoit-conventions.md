# Convenciones UOIT 1.0 — Regla de Workspace (ms-segip)

Esta regla define los estándares institucionales de la **Unidad de Operaciones e Infraestructura Tecnológica (UOIT)** que deben cumplirse estrictamente al modificar, extender o generar código en el microservicio `ms-segip`.

---

## 1. Contratos y Formato de Respuestas REST
* **Estructura de Envoltorio Obligatoria**: Toda respuesta de la API (exitosa o con error) DEBE utilizar el modelo genérico `ApiResponse[DataT]` definido en `app/schemas/common.py`:
  ```json
  {
    "success": true,
    "message": "Mensaje descriptivo en español",
    "data": { ... },
    "meta": null,
    "error": null
  }
  ```
* **Serialización JSON en `camelCase`**: Todas las propiedades expuestas en los contratos JSON de la API deben estar en formato `camelCase` (ej. `numeroDocumento`, `primerApellido`, `codigoRespuesta`).
* **Modelos Pydantic**: Todo nuevo esquema debe heredar de `UoitBaseModel` (`app/schemas/common.py`), el cual aplica automáticamente `alias_generator=to_camel` y `populate_by_name=True`. Dentro de Python se utiliza la convención idiomática `snake_case`.

---

## 2. Nomenclatura de Rutas y Endpoints
* **Sustantivos en Plural**: Los endpoints deben utilizar sustantivos en plural según la especificación REST UOIT (ej. `/personas`, `/certificaciones`, `/pdfs`).
* **Compatibilidad**: Se pueden mantener aliases de rutas con verbos (ej. `/personas/consultar`, `/pdfs/extraer`) si la retrocompatibilidad con sistemas existentes lo exige, pero la ruta primaria siempre es el sustantivo.

---

## 3. Seguridad, Privacidad y Tratamiento de Datos (PII)
* **Enmascaramiento de Carnet de Identidad**: Cualquier registro de log que involucre un número de documento debe enmascarar los dígitos intermedios utilizando el formato estándar: primeros 2 y últimos 2 dígitos visibles (ej. `12***67`).
* **Cero Fuga de Credenciales y Binarios**: Está estrictamente prohibido registrar en logs contraseñas (`pContrasenia`, `pClaveAccesoUsuarioFinal`) o cadenas Base64 de fotografías o archivos PDF.
* **Procesamiento 100% en Memoria**: Nunca almacenar en disco archivos PDF ni imágenes con datos personales de ciudadanos. Procesar mediante buffers de memoria (`BytesIO` o `bytes`).
* **Protección XML**: Todo parseo de documentos XML debe utilizar `defusedxml` para mitigar ataques XXE y *Billion Laughs*.

---

## 4. Trazabilidad y Observabilidad
* **Cabeceras Obligatorias**: Toda petición y respuesta debe propagar:
  - `X-Request-ID`: Identificador único de la petición HTTP actual.
  - `X-Correlation-ID`: Identificador de trazabilidad distribuida a través de la cadena de microservicios.
* **Contexto Asíncrono**: Utilizar las variables contextuales de `app/core/logging.py` para vincular automáticamente estos IDs a los registros de logs.

---

## 5. Sondas de Salud (Kubernetes Probes)
* `/health/live`: Debe validar exclusivamente la capacidad del proceso FastAPI de responder HTTP (sin contactar servicios externos). Debe responder `{"status": "UP"}`.
* `/health/ready`: Evalúa la conectividad con el SOAP de SEGIP sin bloquear el ciclo de vida del contenedor en caso de degradación externa.

---

## 6. Conectividad e Intranet
* **Prohibido 'Hardcodear' IPs**: No codificar directamente la IP `192.168.20.81`. Utilizar siempre el nombre de host institucional configurado en `SEGIP_SERVICE_URL` (`segip-api.fiscalia.gob.bo`) y delegar la resolución al DNS institucional (`192.168.20.2`).
