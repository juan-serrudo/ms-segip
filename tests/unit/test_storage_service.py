"""Pruebas unitarias para StorageService (RustFS / S3)."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.services.storage_service import StorageService


@pytest.fixture
def mock_s3_storage():
    """Crea una instancia de StorageService con cliente boto3 mockeado."""
    settings = Settings(
        RUSTFS_ENDPOINT_URL="http://localhost:9000",
        RUSTFS_ACCESS_KEY="rustfsadmin",
        RUSTFS_SECRET_KEY="rustfssecret2026",
        RUSTFS_BUCKET_NAME="test-bucket",
        RUSTFS_PUBLIC_ENDPOINT_URL=None,
        RUSTFS_DEFAULT_PRESIGNED_EXPIRY_SECONDS=300,
    )
    service = StorageService(settings=settings)
    service._s3_client = MagicMock()
    service._presigned_s3_client = service._s3_client
    return service, service._s3_client


@pytest.mark.asyncio
async def test_asegurar_bucket_existe_already_present(mock_s3_storage):
    service, mock_client = mock_s3_storage
    mock_client.head_bucket.return_value = {}

    existe = await service.asegurar_bucket_existe()
    assert existe is True
    mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    mock_client.create_bucket.assert_not_called()


@pytest.mark.asyncio
async def test_asegurar_bucket_crea_cuando_no_existe(mock_s3_storage):
    service, mock_client = mock_s3_storage
    mock_client.head_bucket.side_effect = ClientError(
        error_response={"Error": {"Code": "404", "Message": "Not Found"}},
        operation_name="HeadBucket",
    )
    mock_client.create_bucket.return_value = {}

    existe = await service.asegurar_bucket_existe()
    assert existe is True
    mock_client.create_bucket.assert_called_once_with(Bucket="test-bucket")


@pytest.mark.asyncio
async def test_guardar_pdf_inmutable(mock_s3_storage):
    service, mock_client = mock_s3_storage
    pdf_bytes = b"%PDF-1.4 dummy test content"

    key, sha256_val, size_bytes = await service.guardar_pdf(
        numero_documento="4892341",
        complemento="1A",
        pdf_bytes=pdf_bytes,
    )

    assert key.startswith("certificados/4892341_1A/")
    assert key.endswith(".pdf")
    assert size_bytes == len(pdf_bytes)
    assert len(sha256_val) == 64

    mock_client.put_object.assert_called_once()
    kwargs = mock_client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "test-bucket"
    assert kwargs["Key"] == key
    assert kwargs["ContentType"] == "application/pdf"
    assert kwargs["Body"] == pdf_bytes


@pytest.mark.asyncio
async def test_guardar_fotografia_inmutable(mock_s3_storage):
    service, mock_client = mock_s3_storage
    foto_bytes = b"\xff\xd8\xff\xe0 dummy jpeg bytes"

    key, sha256_val, size_bytes = await service.guardar_fotografia(
        numero_documento="4892341",
        complemento=None,
        foto_bytes=foto_bytes,
        content_type="image/jpeg",
    )

    assert key.startswith("fotografias/4892341/")
    assert key.endswith(".jpg")
    assert size_bytes == len(foto_bytes)
    assert len(sha256_val) == 64

    mock_client.put_object.assert_called_once()
    kwargs = mock_client.put_object.call_args.kwargs
    assert kwargs["ContentType"] == "image/jpeg"


def test_generar_url_prefirmada_default_expiry(mock_s3_storage):
    service, mock_client = mock_s3_storage
    mock_client.generate_presigned_url.return_value = (
        "http://localhost:9000/test-bucket/certificados/test.pdf?sig=123"
    )

    url = service.generar_url_prefirmada("certificados/test.pdf")
    assert url == "http://localhost:9000/test-bucket/certificados/test.pdf?sig=123"
    mock_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "test-bucket", "Key": "certificados/test.pdf"},
        ExpiresIn=300,
    )


def test_generar_url_prefirmada_con_public_endpoint():
    settings = Settings(
        RUSTFS_ENDPOINT_URL="http://ms-segip-rustfs:9000",
        RUSTFS_PUBLIC_ENDPOINT_URL="https://archivos-segip.fiscalia.gob.bo",
        RUSTFS_BUCKET_NAME="segip-archivos",
    )
    service = StorageService(settings=settings)
    service._presigned_s3_client = MagicMock()
    service._presigned_s3_client.generate_presigned_url.return_value = (
        "https://archivos-segip.fiscalia.gob.bo/segip-archivos/cert.pdf?sig=xyz"
    )

    url = service.generar_url_prefirmada("cert.pdf", expiracion_segundos=600)
    assert url.startswith("https://archivos-segip.fiscalia.gob.bo/segip-archivos/cert.pdf?sig=xyz")
    service._presigned_s3_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "segip-archivos", "Key": "cert.pdf"},
        ExpiresIn=600,
    )

