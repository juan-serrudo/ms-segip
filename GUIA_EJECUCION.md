# Guía de Ejecución y Pruebas Locales — ms-segip

Esta guía detalla los pasos para levantar y probar el microservicio **`ms-segip`** en tu máquina local, tanto con **Python / Uvicorn** como con **Docker / Docker Compose**, ambos configurados con **recarga automática (*hot-reload*)** para agilizar el ciclo de desarrollo.

---

## 1. Requisitos Previos

Asegúrate de contar con lo siguiente en tu sistema:

* **Linux / macOS / WSL2** (Ubuntu/Debian recomendado).
* **Python 3.12+** (para ejecución nativa con Uvicorn).
* **Docker Engine 24+** y **Docker Compose v2+** (para ejecución en contenedores).
* **Git** y **cURL** instalados.

---

## 2. Configuración Inicial del Entorno

Antes de iniciar el microservicio en cualquiera de las modalidades, configura el archivo de variables de entorno:

```bash
# 1. Situarse en la raíz del proyecto
cd ms-segip

# 2. Crear archivo .env a partir de la plantilla
cp .env.example .env
```

Edita el archivo [`.env`](.env) si requieres ajustar parámetros. Los valores más relevantes son:

| Variable | Valor Típico / Por Defecto | Descripción |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Entorno de ejecución (`development`, `production`). |
| `LOG_LEVEL` | `DEBUG` o `INFO` | Nivel de detalle en logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_FORMAT` | `TEXT` | Formato legible en consola (`TEXT`) o estructurado (`JSON`). |
| `PORT` | `8000` | Puerto TCP local donde escuchará la API. |
| `SEGIP_SERVICE_URL` | `https://segip-api.fiscalia.gob.bo/ServicioExternoInstitucion.svc` | Endpoint SOAP oficial de SEGIP. |
| `SEGIP_INSTITUTION_CODE` | `999` | Código de institución asignado por SEGIP. |

---

## 3. Modalidad 1: Ejecución Nativa con Uvicorn (Hot-Reload)

Esta modalidad ejecuta el microservicio directamente en tu sistema utilizando el intérprete de Python, lo que permite el arranque más rápido e interacción directa con depuradores (*debuggers*).

### Paso 1: Activar el entorno virtual
El proyecto ya cuenta con un entorno virtual preconfigurado en `.venv`:

```bash
source .venv/bin/activate
```

*(Si necesitas regenerar el entorno desde cero: `python3.12 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`).*

### Paso 2: Iniciar el servidor Uvicorn con recarga automática

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **¿Qué hace `--reload`?**
> Uvicorn monitorea todos los archivos dentro del directorio `app/`. Cada vez que guardes cambios en cualquier archivo `.py`, el servidor se reiniciará automáticamente en menos de un segundo sin que tengas que detener el proceso.

### Opciones adicionales de Uvicorn:
* **Cambiar el puerto:**
  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8089
  ```
* **Especificar directorio de monitoreo explícito:**
  ```bash
  uvicorn app.main:app --reload --reload-dir app --port 8000
  ```

---

## 4. Modalidad 2: Ejecución con Docker Compose (Hot-Reload)

Esta modalidad levanta el microservicio en un contenedor Docker idéntico al de producción, pero **con recarga automática activa** gracias al montaje de volumen en tiempo real definido en [`compose.dev.yaml`](compose.dev.yaml).

### Paso 1: Iniciar el contenedor en modo desarrollo

```bash
docker compose -f compose.dev.yaml up --build
```

Si deseas ejecutarlo en segundo plano (*detached mode*):
```bash
docker compose -f compose.dev.yaml up -d
```

### ¿Cómo funciona la recarga automática en Docker?
El archivo `compose.dev.yaml` vincula tu carpeta local `./app` con el directorio `/app/app` dentro del contenedor:
```yaml
volumes:
  - ./app:/app/app
command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```
Cualquier cambio que realices en el código desde tu editor (VS Code, Antigravity IDE, Vim, etc.) se refleja inmediatamente dentro del contenedor y dispara el reinicio automático del proceso Uvicorn.

### Ver logs en tiempo real (si corre en segundo plano):
```bash
docker compose -f compose.dev.yaml logs -f
```

### Detener el contenedor de desarrollo:
```bash
docker compose -f compose.dev.yaml down
```

---

## 5. Modalidad 3: Ejecución de Producción con Docker

Para validar el comportamiento final de la imagen multi-stage (sin volúmenes montados ni banderas `--reload`):

```bash
# Construir y levantar
docker compose up --build -d

# Ver estado y sondas de salud
docker compose ps

# Detener
docker compose down
```

---

## 6. Verificación y Pruebas de los Servicios

Una vez levantado el servicio (por cualquiera de los métodos anteriores en el puerto 8000), puedes probarlo mediante interfaz gráfica o consola.

### A. Interfaz Interactiva (Swagger UI & ReDoc)
Abre en tu navegador web:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

En Swagger puedes presionar **"Try it out"** en cualquier endpoint para probarlo directamente y ver las cabeceras `X-Request-ID` y `X-Correlation-ID`.

---

### B. Pruebas con cURL desde la Terminal

#### 1. Sondas de Salud (Health Checks)
```bash
# Sonda Liveness (valida que el microservicio esté vivo)
curl -i http://localhost:8000/health/live

# Sonda Readiness (valida si hay conectividad con el SOAP de SEGIP)
curl -i http://localhost:8000/health/ready
```

#### 2. Consultar Versión del Software SEGIP
```bash
curl -i -X GET http://localhost:8000/api/v1/segip/version
```

#### 3. Consultar Datos de una Persona (Formato UOIT camelCase)
```bash
curl -i -X POST http://localhost:8000/api/v1/segip/personas \
  -H "Content-Type: application/json" \
  -d '{
    "numeroDocumento": "4892341",
    "nombre": "CARLOS",
    "primerApellido": "MAMANI",
    "segundoApellido": "QUISPE",
    "fechaNacimiento": "1990-05-15"
  }'
```

#### 4. Extraer Datos y Fotografía de un Certificado PDF (Multipart/form-data)
```bash
curl -i -X POST "http://localhost:8000/api/v1/pdfs?extraerFotografia=true" \
  -F "file=@/ruta/a/tu/certificado_segip.pdf"
```

#### 5. Extraer Datos de un Certificado PDF en Base64
```bash
curl -i -X POST http://localhost:8000/api/v1/pdfs/base64 \
  -H "Content-Type: application/json" \
  -d '{
    "archivoBase64": "JVBERi0xLjQKJcOkw7zDtsOf...",
    "extraerFotografia": true
  }'
```

#### 6. Validar Certificación mediante Código QR
```bash
curl -i -X POST http://localhost:8000/api/v1/segip/certificaciones/qr \
  -H "Content-Type: application/json" \
  -d '{
    "codigoQr": "https://segip.gob.bo/validador/qr/CERT-998877"
  }'
```

---

## 7. Ejecución de la Suite de Pruebas Automatizadas

El proyecto incluye pruebas unitarias offline (con mocks de SOAP y generación de PDFs sintéticos en memoria) y pruebas de integración live:

```bash
# 1. Ejecutar las 62 pruebas unitarias con reporte de cobertura
pytest --cov=app --cov-report=term-missing

# 2. Ejecutar únicamente pruebas del parser de PDF
pytest tests/unit/test_pdf_parser.py -v

# 3. Ejecutar únicamente pruebas del cliente SOAP y mapeador
pytest tests/unit/test_soap_client.py tests/unit/test_segip_mapper.py -v

# 4. Probar endpoints de la API (TestClient)
pytest tests/unit/test_api_endpoints.py -v

# 5. (Opcional) Probar contra el SOAP real de SEGIP (Requiere conexión a intranet fiscal)
RUN_SEGIP_INTEGRATION_TESTS=true pytest tests/integration/test_segip_live.py -v -s
```

---

## 8. Verificación de Calidad de Código (Linters)

Para asegurar el cumplimiento de estándares UOIT y reglas PEP8:

```bash
# Comprobar errores de linting con Ruff
ruff check .

# Corregir errores automáticos si existieran
ruff check . --fix

# Verificar formateo de código
ruff format --check .
```

---

## 9. Preguntas Frecuentes y Solución de Problemas (Troubleshooting)

### Error: `Address already in use` (Puerto 8000 ocupado)
Si otro proceso está utilizando el puerto 8000:
* **Solución en Uvicorn:** Cambia el puerto ejecutando con `--port 8089`.
* **Solución en Docker:** En `compose.dev.yaml`, modifica la sección de puertos a `"8089:8000"` y accede en `http://localhost:8089`.
* **Liberar el puerto:**
  ```bash
  sudo lsof -i :8000
  # Matar el proceso si es seguro: kill -9 <PID>
  ```

### En Docker no resuelve `segip-api.fiscalia.gob.bo`
Si ejecutas Docker dentro de la red corporativa/VPN y el contenedor no resuelve el dominio interno:
* Abre [`compose.dev.yaml`](compose.dev.yaml) y descomenta las líneas del DNS interno:
  ```yaml
  dns:
    - 192.168.20.2
  ```

### El hot-reload de Docker no detecta cambios en Linux
Si utilizas Linux y las modificaciones no disparan la recarga, verifica los límites de monitores inotify del sistema:
```bash
# Comprobar límite actual
cat /proc/sys/fs/inotify/max_user_watches

# Aumentar si fuera necesario
sudo sysctl fs.inotify.max_user_watches=524288
```
