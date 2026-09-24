"""Servicio de integración con almacenamiento de objetos RustFS / S3 (UOIT 1.0)."""

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings
from app.core.exceptions import StorageException

logger = logging.getLogger(__name__)


class StorageService:
    """Gestiona la persistencia inmutable de archivos y generación de URLs prefirmadas en RustFS/S3."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.bucket_name = self.settings.RUSTFS_BUCKET_NAME
        self.default_expiry = self.settings.RUSTFS_DEFAULT_PRESIGNED_EXPIRY_SECONDS

        # Configuración de cliente boto3 S3 optimizado para RustFS/MinIO (path-style addressing)
        boto_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=15,
            retries={"max_attempts": 3, "mode": "standard"},
        )

        self._s3_client: Any = boto3.client(
            "s3",
            endpoint_url=self.settings.RUSTFS_ENDPOINT_URL,
            aws_access_key_id=self.settings.RUSTFS_ACCESS_KEY,
            aws_secret_access_key=self.settings.RUSTFS_SECRET_KEY,
            region_name=self.settings.RUSTFS_REGION,
            use_ssl=self.settings.RUSTFS_USE_SSL,
            config=boto_config,
        )

        # Cliente para generación de URLs prefirmadas: firma el Host público exacto para evitar SignatureDoesNotMatch
        public_url = self.settings.rustfs_public_url
        if public_url == self.settings.RUSTFS_ENDPOINT_URL:
            self._presigned_s3_client = self._s3_client
        else:
            self._presigned_s3_client = boto3.client(
                "s3",
                endpoint_url=public_url,
                aws_access_key_id=self.settings.RUSTFS_ACCESS_KEY,
                aws_secret_access_key=self.settings.RUSTFS_SECRET_KEY,
                region_name=self.settings.RUSTFS_REGION,
                use_ssl=self.settings.RUSTFS_USE_SSL,
                config=boto_config,
            )


    def _asegurar_bucket_sync(self) -> bool:
        """Verifica la existencia del bucket y lo crea si no existe."""
        try:
            self._s3_client.head_bucket(Bucket=self.bucket_name)
            logger.debug("Bucket '%s' verificado en RustFS", self.bucket_name)
            return True
        except ClientError as err:
            error_code = str(err.response.get("Error", {}).get("Code", ""))
            # 404 o NoSuchBucket indica que no existe y debemos crearlo
            if error_code in ("404", "NoSuchBucket"):
                try:
                    logger.info(
                        "Bucket '%s' no encontrado. Creándolo en RustFS...", self.bucket_name
                    )
                    self._s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info("Bucket '%s' creado exitosamente", self.bucket_name)
                    return True
                except Exception as create_err:
                    logger.error("Error al crear bucket '%s': %s", self.bucket_name, create_err)
                    raise StorageException(
                        details=f"No se pudo crear el bucket '{self.bucket_name}': {create_err}"
                    ) from create_err
            logger.warning("Fallo al verificar bucket '%s': %s", self.bucket_name, err)
            return False
        except Exception as err:
            logger.error("Error de conexión al verificar bucket en RustFS: %s", err)
            return False

    async def asegurar_bucket_existe(self) -> bool:
        """Versión asíncrona para asegurar la existencia del bucket."""
        return await asyncio.to_thread(self._asegurar_bucket_sync)

    def _build_doc_folder(self, numero_documento: str, complemento: str | None) -> str:
        """Construye el prefijo de carpeta normalizado para la persona."""
        doc = numero_documento.strip()
        comp = f"_{complemento.strip().upper()}" if complemento and complemento.strip() else ""
        return f"{doc}{comp}"

    def _guardar_objeto_sync(
        self,
        key: str,
        content_bytes: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Sube un flujo de bytes a RustFS de manera sincrónica."""
        try:
            self._s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content_bytes,
                ContentType=content_type,
                Metadata=metadata or {},
            )
            logger.info(
                "Objeto almacenado en RustFS: s3://%s/%s (%d bytes)",
                self.bucket_name,
                key,
                len(content_bytes),
            )
        except Exception as err:
            logger.error("Error al guardar objeto '%s' en RustFS: %s", key, err)
            raise StorageException(details=f"Error al persistir archivo en RustFS: {err}") from err

    async def guardar_pdf(
        self,
        numero_documento: str,
        complemento: str | None,
        pdf_bytes: bytes,
        sha256_hash: str | None = None,
    ) -> tuple[str, str, int]:
        """Almacena de forma inmutable un certificado PDF en RustFS.

        Retorna (key, sha256, tamanio_bytes).
        """
        sha = sha256_hash or hashlib.sha256(pdf_bytes).hexdigest()
        size_bytes = len(pdf_bytes)
        now_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        folder = self._build_doc_folder(numero_documento, complemento)
        key = f"certificados/{folder}/{now_str}_{sha[:8]}.pdf"

        await asyncio.to_thread(
            self._guardar_objeto_sync,
            key=key,
            content_bytes=pdf_bytes,
            content_type="application/pdf",
            metadata={"sha256": sha, "documento": numero_documento},
        )
        return key, sha, size_bytes

    async def guardar_fotografia(
        self,
        numero_documento: str,
        complemento: str | None,
        foto_bytes: bytes,
        content_type: str = "image/jpeg",
    ) -> tuple[str, str, int]:
        """Almacena de forma inmutable una fotografía recortada en RustFS.

        Retorna (key, sha256, tamanio_bytes).
        """
        sha = hashlib.sha256(foto_bytes).hexdigest()
        size_bytes = len(foto_bytes)
        now_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        folder = self._build_doc_folder(numero_documento, complemento)
        ext = "jpg" if "jpeg" in content_type.lower() or "jpg" in content_type.lower() else "png"
        key = f"fotografias/{folder}/{now_str}_{sha[:8]}.{ext}"

        await asyncio.to_thread(
            self._guardar_objeto_sync,
            key=key,
            content_bytes=foto_bytes,
            content_type=content_type,
            metadata={"sha256": sha, "documento": numero_documento},
        )
        return key, sha, size_bytes

    def generar_url_prefirmada(
        self,
        key: str,
        expiracion_segundos: int | None = None,
    ) -> str:
        """Genera una URL prefirmada S3 (GET) con tiempo de vigencia limitado y host firmado correctamente."""
        expires = expiracion_segundos or self.default_expiry
        try:
            return self._presigned_s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires,
            )
        except Exception as err:
            logger.error("Error al generar URL prefirmada para '%s': %s", key, err)
            raise StorageException(details=f"Error al generar enlace de descarga: {err}") from err
