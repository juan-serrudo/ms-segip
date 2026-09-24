---
name: rustfs-s3-storage
description: >-
  Use this skill when developing, configuring, troubleshooting, or integrating RustFS / S3 object storage, presigned URLs, AWS SigV4 signatures, or immutable document archiving in ms-segip.
---

# RustFS / S3 Object Storage — ms-segip Runbook

Este manual documenta la arquitectura, directrices operativas y buenas prácticas para la gestión de documentos PDF y fotografías mediante el almacenamiento de objetos compatible con S3 (RustFS) en `ms-segip`.

---

## 1. Arquitectura y Principio de Inmutabilidad

Para cumplir con requerimientos de auditoría y trazabilidad legal en el ámbito judicial y registral:

* **Inmutabilidad Absoluta**: **Nunca se sobrescribe ni se elimina ningún archivo** en RustFS.
* **Historial Completo**: Si una persona cambia de estado civil (soltero a casado/divorciado), decide rectificar su identidad o cambia de género, el nuevo certificado y la nueva fotografía se almacenan en un objeto nuevo en RustFS.
* **Relación con PostgreSQL**:
  - `personas`: Mantiene los datos normalizados vigentes y su columna `fotografia_path` apunta a la **última fotografía emitida**.
  - `certificaciones_segip`: Cada fila registra una emisión con su `pdf_path`, `numero_emision`, `pdf_sha256` y marca temporal.

---

## 2. Convención de Claves (Object Keys)

Todos los objetos dentro del bucket configurado (`segip-archivos`) deben seguir la siguiente nomenclatura determinista e inmutable:

* **Certificados Oficiales PDF**:
  `certificados/{numero_documento}{_complemento}/{YYYYMMDD_HHMMSS}_{sha256[:8]}.pdf`
  *Ejemplo:* `certificados/1146351/20260924_190805_575eb2ed.pdf`
  *Ejemplo con complemento:* `certificados/6842190_1B/20260924_190805_575eb2ed.pdf`
* **Fotografías Recortadas**:
  `fotografias/{numero_documento}{_complemento}/{YYYYMMDD_HHMMSS}_{sha256[:8]}.jpg`
  *Ejemplo:* `fotografias/1146351/20260924_190805_2e9398c5.jpg`

---

## 3. URLs Prefirmadas y Prevención de `SignatureDoesNotMatch`

### El Mecanismo de Firma AWS SigV4
En AWS Signature Version 4, la cabecera HTTP `Host` forma parte obligatoria de la firma criptográfica sellada en `X-Amz-SignedHeaders=host`.

> [!WARNING]
> Si una URL prefirmada se genera firmando `localhost:9000` pero un cliente externo o navegador la invoca usando la IP de red o un dominio institucional (ej. `http://172.27.39.101:9000` o `https://archivos.fiscalia.gob.bo`), RustFS rechazará la petición con el error:
> ```xml
> <Error>
>   <Code>SignatureDoesNotMatch</Code>
>   <Message>The request signature we calculated does not match the signature you provided.</Message>
> </Error>
> ```

### Regla de Oro
**El cliente de Boto3 que genera la URL prefirmada debe tener configurado en su `endpoint_url` exactamente el mismo host público con el que accederá el cliente.**

* En [StorageService](app/services/storage_service.py), se mantiene un cliente específico `_presigned_s3_client` inicializado con `settings.rustfs_public_url`.
* **Configuración en `.env`**:
  ```env
  # Conexión interna para el microservicio
  RUSTFS_ENDPOINT_URL=http://localhost:9000

  # URL pública con la que accederán los clientes (navegadores/frontends)
  RUSTFS_PUBLIC_ENDPOINT_URL=http://172.27.39.101:9000
  ```

---

## 4. Métodos HTTP para Consumo

* Las URLs prefirmadas generadas por el microservicio son de descarga (`ClientMethod="get_object"`).
* **Deben consumirse mediante petición HTTP `GET`** (ej. clic en navegador, `<img src="...">` o descarga estándar).
* Si se intenta probar con `curl -I` (método `HEAD`), RustFS responderá `403 Forbidden` porque el método firmado es `GET`. Para probar con curl:
  ```bash
  curl -s -o documento.pdf "<URL_PREFIRMADA>"
  ```

---

## 5. Inicialización de Buckets en el Ciclo de Vida

Para garantizar que el almacenamiento esté listo antes de atender solicitudes:
* En [app/main.py](app/main.py) dentro del gestor `lifespan`:
  ```python
  from app.services.storage_service import StorageService

  storage = StorageService(settings=settings)
  await storage.asegurar_bucket_existe()
  ```
* El método `asegurar_bucket_existe()` verifica con `head_bucket` y si no existe (código `404` / `NoSuchBucket`), lo crea automáticamente con `create_bucket`.

---

## 6. Variables de Entorno de Almacenamiento

| Variable | Descripción | Valor por Defecto |
| :--- | :--- | :--- |
| `RUSTFS_ENDPOINT_URL` | URL de acceso local/cluster a la API S3 de RustFS | `http://localhost:9000` |
| `RUSTFS_PUBLIC_ENDPOINT_URL` | Host/IP público con el que se firman las URLs para los clientes | `None` (usa `RUSTFS_ENDPOINT_URL`) |
| `RUSTFS_ACCESS_KEY` | Access Key de autenticación S3 | `rustfsadmin` |
| `RUSTFS_SECRET_KEY` | Secret Key de autenticación S3 | `rustfssecret2026` |
| `RUSTFS_BUCKET_NAME` | Nombre del bucket institucional | `segip-archivos` |
| `RUSTFS_REGION` | Región S3 | `us-east-1` |
| `RUSTFS_USE_SSL` | Indica si la comunicación usa HTTPS | `false` |
| `RUSTFS_DEFAULT_PRESIGNED_EXPIRY_SECONDS` | Vigencia por defecto de URLs prefirmadas (en seg.) | `300` (5 minutos) |
