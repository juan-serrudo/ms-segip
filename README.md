# ms-segip

Microservicio moderno y resiliente en **Python 3.12** y **FastAPI** que actúa como **fachada REST** para la integración con los servicios SOAP del **SEGIP** (Servicio General de Identificación Personal del Estado Plurinacional de Bolivia) y el procesamiento/extracción de datos personales y fotografías de documentos de certificación en formato **PDF**.

---

## Índice

1. [Propósito y Características](#propósito-y-características)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Restricciones de Red e Intranet](#restricciones-de-red-e-intranet)
4. [Instalación y Configuración Local](#instalación-y-configuración-local)
5. [Variables de Entorno](#variables-de-entorno)
6. [Ejecución con Docker y Docker Compose](#ejecución-con-docker-y-docker-compose)
7. [Referencia de Endpoints REST](#referencia-de-endpoints-rest)
8. [Ejecución de Pruebas](#ejecución-de-pruebas)
9. [Funcionamiento de la Integración SOAP](#funcionamiento-de-la-integración-soap)
10. [Cómo Agregar Soporte para una Nueva Versión de PDF](#cómo-agregar-soporte-para-una-nueva-versión-de-pdf)
11. [Seguridad y Protección de Datos Personales](#seguridad-y-protección-de-datos-personales)

---

## Propósito y Características

El microservicio `ms-segip` resuelve la interoperabilidad entre aplicaciones y sistemas institucionales que consumen REST/JSON y el servicio central de SEGIP expuesto mediante SOAP 1.1 WCF en la intranet.

### Capacidades Principales
- **Consulta de Persona**: Obtención de datos personales y fotografía oficial mediante `ConsultaDatoPersonaEnJson` y `ConsultaDocumentoDatoPersonaEnJson`.
- **Emisión de Certificaciones PDF**: Descarga del reporte oficial de certificación generado por SEGIP en formato PDF Base64.
- **Verificación de Códigos QR**: Validación de autenticidad de certificaciones emitidas mediante la lectura de su código QR.
- **Contrastación de Identidad**: Verificación campo a campo contra el padrón de SEGIP.
- **Extracción de Certificados PDF**: Procesamiento en memoria de PDFs de certificación subidos por `multipart/form-data` o `Base64`, extrayendo los datos normalizados y opcionalmente la fotografía de carnet.
- **Respuestas Uniformes**: Modelo de respuesta estandarizado (`APIResponse[T]`) con trazabilidad por `request_id` (Correlation ID).
- **Seguridad**: Enmascaramiento automático de Cédula de Identidad en logs, exclusión total de contraseñas y base64 en logs, y protección contra inyecciones XML y XXE.

---

## Arquitectura del Sistema

El proyecto sigue una arquitectura limpia en capas desacopladas:

```
ms-segip/
├── app/
│   ├── main.py                  # Inicialización FastAPI, middlewares (Correlation ID, CORS), handlers globales
│   ├── api/
│   │   ├── dependencies.py      # Inyección de dependencias (cliente SOAP, servicios)
│   │   └── v1/
│   │       ├── router.py        # Agrupador de rutas v1
│   │       ├── health.py        # Probes /health (liveness) y /ready (readiness con chequeo SEGIP)
│   │       ├── segip.py         # Endpoints REST de operaciones SEGIP
│   │       └── pdf.py           # Endpoints de procesamiento y extracción de PDFs
│   ├── core/
│   │   ├── config.py            # Configuración pydantic-settings
│   │   ├── exceptions.py        # Excepciones de dominio mapeadas a códigos HTTP
│   │   ├── logging.py           # Logging seguro con filtro de enmascaramiento y correlation ID
│   │   └── security.py          # Autenticación desacoplada (API Key / JWT institucional)
│   ├── schemas/
│   │   ├── common.py            # APIResponse[T], APIErrorDetail
│   │   ├── segip.py             # Modelos de consulta, contraste y PersonaNormalizada
│   │   └── pdf.py               # Modelos de extracción de PDFs y metadatos
│   ├── services/
│   │   ├── segip_service.py     # Lógica de negocio y orquestación con SEGIP
│   │   └── pdf_service.py       # Validaciones de seguridad de PDFs y control en memoria
│   ├── integrations/
│   │   └── segip/
│   │       ├── client.py        # Cliente SOAP 1.1 asíncrono con httpx y defusedxml
│   │       ├── mapper.py        # Transformador de XML/JSON de SEGIP a modelos Pydantic
│   │       ├── exceptions.py    # Excepciones de red, SOAP Faults y parsing
│   │       └── resources/
│   │           └── ServicioExternoInstitucion.wsdl  # Contrato WSDL oficial
│   ├── parsers/
│   │   └── segip_pdf_parser.py  # Motor de análisis posicional y extracción con PyMuPDF
│   └── utils/
│       └── text.py              # Normalización de texto, diacríticos, fechas y género
├── tests/
│   ├── conftest.py              # Configuración y cliente HTTP de pruebas
│   ├── fixtures/                # Mocks de respuestas SOAP y generador sintético de PDFs
│   ├── unit/                    # Pruebas unitarias completas (offline)
│   └── integration/             # Pruebas de integración reales con intranet (opcionales)
├── Dockerfile                   # Construcción multietapa con usuario no root
├── compose.yaml                 # Orquestación con Docker Compose
└── pyproject.toml               # Dependencias del proyecto
```

---

## Restricciones de Red e Intranet

El servicio SOAP de SEGIP es accesible **exclusivamente desde la red intranet**:

- **URL Institucional**: `https://segip-api.fiscalia.gob.bo/ServicioExternoInstitucion.svc`
- **WSDL Institucional**: `https://segip-api.fiscalia.gob.bo/ServicioExternoInstitucion.svc?singleWsdl`
- **DNS Interno**: `192.168.20.2`
- **Resolución Interna Actual**: `192.168.20.81`

> [!IMPORTANT]
> **Políticas de Red**:
> 1. La aplicación **no debe contener IPs fijas hardcodeadas**. Utiliza siempre el hostname institucional `segip-api.fiscalia.gob.bo`.
> 2. La resolución DNS es responsabilidad del entorno de despliegue o del servidor DNS configurado (`192.168.20.2`).
> 3. El WSDL oficial publica internamente la dirección `https://wsverificacion.segip.gob.bo/ServicioExternoInstitucion.svc`. El cliente SOAP implementado **sobrescribe automáticamente esa dirección** y utiliza la URL institucional configurada en `SEGIP_SERVICE_URL`.

---

## Instalación y Configuración Local

> [!TIP]
> Para una guía paso a paso completa con ejemplos de comandos cURL, recarga automática en Docker y solución de problemas, consulta la [Guía de Ejecución Local (GUIA_EJECUCION.md)](GUIA_EJECUCION.md).

### Requisitos Previos
- **Python 3.12** o superior.
- Gestor de paquetes `pip` y soporte de `venv`.

### Pasos de Instalación

1. **Clonar el repositorio y situarse en el directorio:**
   ```bash
   cd ms-segip
   ```

2. **Crear y activar el entorno virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

4. **Configurar el archivo de variables de entorno:**
   ```bash
   cp .env.example .env
   ```
   Edita `.env` con las credenciales institucionales otorgadas por SEGIP.

5. **Iniciar el servidor de desarrollo:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   La documentación interactiva estará disponible en:
   - **Swagger UI**: `http://localhost:8000/docs`
   - **ReDoc**: `http://localhost:8000/redoc`

---

## Variables de Entorno

Configuración disponible en `.env`:

| Variable | Tipo | Por Defecto | Descripción |
| :--- | :---: | :---: | :--- |
| `APP_NAME` | `str` | `ms-segip` | Nombre del microservicio |
| `APP_VERSION` | `str` | `1.0.0` | Versión del microservicio |
| `ENVIRONMENT` | `str` | `development` | Entorno (`development`, `production`, `testing`) |
| `LOG_LEVEL` | `str` | `INFO` | Nivel de logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `HOST` | `str` | `0.0.0.0` | Dirección IP de escucha |
| `PORT` | `int` | `8000` | Puerto TCP de escucha |
| `SEGIP_SERVICE_URL` | `str` | `https://segip-api.fiscalia.gob.bo/ServicioExternoInstitucion.svc` | Endpoint SOAP institucional |
| `SEGIP_WSDL_URL` | `str` | `https://segip-api.fiscalia.gob.bo/...` | URL del contrato WSDL |
| `SEGIP_INSTITUTION_CODE` | `int` | `999` | Código de institución asignado por SEGIP |
| `SEGIP_USERNAME` | `str` | `""` | Usuario institucional para el servicio SOAP |
| `SEGIP_PASSWORD` | `str` | `""` | Contraseña institucional para el servicio SOAP |
| `SEGIP_CONNECT_TIMEOUT` | `float` | `5.0` | Timeout de conexión hacia SEGIP (segundos) |
| `SEGIP_READ_TIMEOUT` | `float` | `15.0` | Timeout de lectura de respuesta SOAP (segundos) |
| `SEGIP_MAX_RETRIES` | `int` | `3` | Reintentos con backoff para errores transitorios de red |
| `PDF_MAX_SIZE_MB` | `float` | `10.0` | Tamaño máximo permitido para archivos PDF |
| `CORS_ORIGINS` | `list` | `["*"]` | Lista JSON o separada por comas de orígenes CORS permitidos |
| `API_KEY` | `str` | `None` | Clave API opcional; si se define, exige cabecera `X-API-Key` |
| `RUN_SEGIP_INTEGRATION_TESTS` | `bool` | `false` | Habilita pruebas directas contra intranet |

---

## Ejecución con Docker y Docker Compose

El proyecto incluye un `Dockerfile` multietapa optimizado que ejecuta la aplicación bajo un usuario sin privilegios (`appuser`, UID 10001) e incorpora comprobaciones de salud (`HEALTHCHECK`).

### Uso con Docker Compose

1. **Iniciar el contenedor en segundo plano:**
   ```bash
   docker compose up -d --build
   ```

2. **Verificar estado y logs:**
   ```bash
   docker compose ps
   docker compose logs -f
   ```

3. **Detener el servicio:**
   ```bash
   docker compose down
   ```

Si el host Docker requiere resolución DNS interna hacia la intranet, descomenta la directiva `dns: - 192.168.20.2` en `compose.yaml`.

---

## Referencia de Endpoints REST

Todas las respuestas del microservicio devuelven la estructura uniforme institucional `ApiResponse` (UOIT Sección 13 y 23):
```json
{
  "success": true,
  "message": "Operación completada exitosamente",
  "data": { ... },
  "meta": null,
  "error": null
}
```

En caso de error (UOIT Sección 15):
```json
{
  "success": false,
  "message": "Mensaje funcional del error",
  "data": null,
  "meta": null,
  "error": {
    "code": "CODIGO_FUNCIONAL",
    "details": "Detalle técnico o lista de campos",
    "traceId": "90ba95eb-3fa5-455b-b9b0-a5483f98cda2"
  }
}
```

### 1. Verificación de Salud y Probes de Kubernetes (UOIT Sección 29)

- **`GET /health/live`** (Liveness Probe Kubernetes)
  - Retorna `{"status": "UP"}`.

- **`GET /health/ready`** (Readiness Probe Kubernetes)
  - Diagnostica conectividad con SEGIP. Retorna `HTTP 200` con `{"status": "UP"}` si responde, o `HTTP 503` con `{"status": "DOWN"}` si falla.

- **`GET /api/v1/health`** (Liveness Informativo con `ApiResponse`)
  - Comprueba que la aplicación web responde y retorna versión y entorno.

- **`GET /api/v1/ready`** (Readiness Informativo con `ApiResponse`)
  - Reporta separadamente el estado de la aplicación y de `segipSoap`.

- **`GET /api/v1/segip/version`**
  - Retorna la versión del software de SEGIP (ej. `"8.0.0.0"`).

### 2. Consulta de Datos de Persona (UOIT camelCase)

- **`POST /api/v1/segip/personas`** (Ruta estándar UOIT en plural)
- **`POST /api/v1/segip/personas/consultar`** (Alias de compatibilidad)
  - Si se proporciona `fechaExpiracion`, realiza consulta documental. De lo contrario, consulta estándar.
  - **Ejemplo de Solicitud:**
    ```json
    {
      "numeroDocumento": "4892341",
      "complemento": "1A",
      "nombre": "CARLOS",
      "primerApellido": "MAMANI",
      "segundoApellido": "QUISPE",
      "fechaNacimiento": "1990-05-15"
    }
    ```
  - **Ejemplo de Respuesta Normalizada:**
    ```json
    {
      "success": true,
      "message": "Consulta de persona realizada exitosamente",
      "data": {
        "persona": {
          "numeroDocumento": "4892341",
          "complemento": "1A",
          "nombres": "CARLOS ANDRES",
          "primerApellido": "MAMANI",
          "segundoApellido": "QUISPE",
          "fechaNacimiento": "1990-05-15",
          "sexo": "MASCULINO",
          "estadoCivil": "SOLTERO",
          "domicilio": "AV. MARISCAL SANTA CRUZ #123",
          "profesionOcupacion": "LICENCIADO EN DERECHO",
          "fotografiaBase64": "/9j/4AAQSkZJRgABAQ..."
        },
        "nacimiento": {
          "pais": "BOLIVIA",
          "departamento": "LA PAZ",
          "provincia": "MURILLO",
          "localidad": "NUESTRA SEÑORA DE LA PAZ"
        },
        "consulta": {
          "codigoUnico": "UNIQ-123456789",
          "codigoRespuesta": 1,
          "descripcion": "CONSULTA EXITOSA",
          "fechaConsulta": "2026-09-22T11:45:00.000Z"
        }
      },
      "meta": null,
      "error": null
    }
    ```

### 3. Obtención y Verificación de Certificaciones

- **`POST /api/v1/segip/certificaciones`**
  - Devuelve el reporte oficial en Base64 (`reporte_certificacion_base64`).

- **`POST /api/v1/segip/certificaciones/verificar-qr`**
  - Verifica la validez del certificado a partir de la cadena decodificada del código QR:
    ```json
    {
      "codigo_qr": "https://segip.gob.bo/validador/qr/CERT-998877"
    }
    ```

- **`POST /api/v1/segip/contrastaciones`**
  - Realiza contraste de campos de identidad.

### 4. Procesamiento de Documentos PDF

- **`POST /api/v1/pdfs/extraer`** (Multipart/form-data)
  - Recibe el archivo PDF directamente en el parámetro `file`.
  - Parámetro opcional booleano `extraer_fotografia` (por defecto `false`).
  - Ejemplo con cURL:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/pdfs/extraer" \
      -F "file=@certificado_ejemplo.pdf" \
      -F "extraer_fotografia=true"
    ```

- **`POST /api/v1/pdfs/extraer-base64`** (JSON)
  - Permite enviar el PDF como cadena Base64:
    ```json
    {
      "pdf_base64": "JVBERi0xLjQKJcTl8uXrp/Og0MTGCjQgMCBvYmoK...",
      "extraer_fotografia": true
    }
    ```

---

## Ejecución de Pruebas

El proyecto cuenta con una amplia suite de pruebas que valida el comportamiento sin requerir acceso a la intranet.

### Pruebas Unitarias (Offline)
Ejecuta la suite de pruebas unitarias con reporte de cobertura de código:
```bash
pytest -v --cov=app -m "not integration"
```

### Análisis Estático de Código y Formato (Ruff)
```bash
ruff check .
ruff format --check .
```

### Pruebas de Integración Reales contra SEGIP (Intranet)
Para ejecutar la comprobación de conectividad real contra el endpoint de SEGIP:
```bash
RUN_SEGIP_INTEGRATION_TESTS=true pytest -v tests/integration/test_segip_live.py
```
> [!NOTE]
> La prueba de integración únicamente invoca `ObtieneVersionSistema` para validar el handshake TLS y SOAP sin enviar datos personales de ciudadanos.

---

## Funcionamiento de la Integración SOAP

El cliente SOAP en `app/integrations/segip/client.py`:
1. Utiliza transporte asíncrono puro (`httpx.AsyncClient`) para no bloquear los workers de FastAPI.
2. Construye sobres SOAP 1.1 `document/literal` con el namespace `http://tempuri.org/`.
3. Inyecta la cabecera `SOAPAction` requerida por WCF ASP.NET (ej. `"http://tempuri.org/IServicioExternoInstitucion/ObtieneVersionSistema"`).
4. Sobrescribe la dirección destino configurándola directamente hacia `SEGIP_SERVICE_URL`, evitando desvíos hacia direcciones antiguas presentes en el WSDL original.
5. Emplea `defusedxml` para evitar vulnerabilidades de expansión de entidades (XXE / Billion Laughs).
6. Implementa reintentos automáticos con backoff exponencial para códigos HTTP transitorios (502, 503, 504) o desconexiones de red, sin reintentar errores SOAP Faults ni códigos 4xx.

---

## Cómo Agregar Soporte para una Nueva Versión de PDF

Si SEGIP emite una nueva plantilla o versión del certificado PDF de identidad:

1. **Identificar la nueva estructura:**
   Abre el nuevo PDF con PyMuPDF o inspecciona su texto:
   ```python
   import pymupdf

   doc = pymupdf.open("nuevo_certificado.pdf")
   print(doc[0].get_text("text"))
   ```

2. **Actualizar el Parser (`app/parsers/segip_pdf_parser.py`):**
   - Agrega cualquier nueva palabra clave institucional a `_SEGIP_KEYWORDS` si cambió el encabezado.
   - Si cambiaron las etiquetas de texto (por ejemplo, si "Cédula de Identidad" ahora se rotula como "Documento Nacional:"), amplía la expresión regular en el método correspondiente (`_extract_persona`, `_extract_nacimiento` o `_extract_certificado`).
   - Para fotografías: si las dimensiones o la posición variaron, ajusta los filtros de ancho, alto y relación de aspecto en `_extract_photo()`.

3. **Agregar Caso de Prueba:**
   Añade la nueva variante en `tests/fixtures/mock_pdfs.py` y agrega un test unitario en `tests/unit/test_pdf_parser.py` para asegurar que las versiones previas y la nueva se procesen sin regresiones.

---

## Seguridad y Protección de Datos Personales

- **Enmascaramiento de CI**: En todos los registros de logging, los números de documento se muestran enmascarados (ej. `12***67`).
- **Sanitización de Logs**: Se suprimen automáticamente de los logs contraseñas institucionales (`pContrasenia`, `pClaveAccesoUsuarioFinal`) y cargas útiles extensas en Base64 (fotografías y reportes PDF).
- **Manejo Seguro de Archivos**: Los archivos PDF se procesan en memoria en flujos de bytes temporales; los descriptores se liberan inmediatamente al concluir la petición. No se persisten copias de PDFs ni fotografías en disco salvo petición explícita del consumidor.
- **Protección TLS**: La verificación de certificados TLS permanece activa (`verify=True`).
- **Autenticación Desacoplada**: A través de `app/core/security.py`, es posible activar de inmediato la autenticación por API Key configurando `API_KEY` o extender la inyección hacia tokens JWT o mTLS institucional.
